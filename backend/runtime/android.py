"""Android black-box runtime backed by ADB and the platform UIAutomator hierarchy.

The adapter deliberately mirrors ``BrowserSession``.  The reasoning loop only sees
an ephemeral, observation-scoped semantic action space; it never receives resource
IDs, XPath expressions, or application source code.
"""
from __future__ import annotations

import asyncio
import os
import re
import shutil
import signal
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from backend.runtime.executor import ActionResult
from backend.runtime.fingerprint import state_fingerprint
from backend.schemas import (
    ActionType,
    AxeNode,
    AxeViolation,
    BrowserAction,
    Observation,
    ObservedElement,
    short_id,
)


class AndroidError(RuntimeError):
    pass


@dataclass
class AndroidDevice:
    serial: str
    status: str
    model: str = ""
    product: str = ""
    transport_id: str = ""

    def model_dump(self) -> dict[str, str]:
        return {
            "serial": self.serial,
            "status": self.status,
            "model": self.model,
            "product": self.product,
            "transport_id": self.transport_id,
        }


def adb_executable() -> str:
    found = shutil.which("adb")
    if found:
        return found
    for key in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        root = os.environ.get(key)
        if root:
            candidate = Path(root) / "platform-tools" / ("adb.exe" if os.name == "nt" else "adb")
            if candidate.exists():
                return str(candidate)
    raise AndroidError("ADB was not found. Install Android SDK Platform-Tools and put adb on PATH.")


async def _command(*args: str, timeout: float = 30, check: bool = True) -> tuple[bytes, bytes]:
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError:
        proc.kill()
        await proc.communicate()
        raise AndroidError(f"command timed out after {timeout:g}s: {Path(args[0]).name} {' '.join(args[1:3])}")
    if check and proc.returncode:
        message = (stderr or stdout).decode("utf-8", "replace").strip()
        raise AndroidError(message or f"command failed with exit code {proc.returncode}")
    return stdout, stderr


async def list_devices() -> list[AndroidDevice]:
    stdout, _ = await _command(adb_executable(), "devices", "-l", timeout=10)
    devices: list[AndroidDevice] = []
    for raw in stdout.decode("utf-8", "replace").splitlines()[1:]:
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        values = dict(token.split(":", 1) for token in parts[2:] if ":" in token)
        devices.append(AndroidDevice(
            serial=parts[0], status=parts[1] if len(parts) > 1 else "unknown",
            model=values.get("model", "").replace("_", " "),
            product=values.get("product", ""), transport_id=values.get("transport_id", ""),
        ))
    return devices


def _aapt_candidates() -> list[Path]:
    candidates: list[Path] = []
    direct = shutil.which("aapt")
    if direct:
        candidates.append(Path(direct))
    roots = [os.environ.get("ANDROID_HOME"), os.environ.get("ANDROID_SDK_ROOT")]
    try:
        roots.append(str(Path(adb_executable()).resolve().parent.parent))
    except AndroidError:
        pass
    name = "aapt.exe" if os.name == "nt" else "aapt"
    for root in filter(None, roots):
        candidates.extend(sorted((Path(root) / "build-tools").glob(f"*/{name}"), reverse=True))
    return candidates


async def apk_package(apk: Path) -> str:
    if not apk.is_file():
        raise AndroidError("uploaded APK no longer exists")
    candidates = _aapt_candidates()
    if not candidates:
        raise AndroidError("aapt was not found in Android SDK Build-Tools; package name cannot be verified")
    # Some valid system APKs make aapt return non-zero for an unresolved icon even
    # though it has already emitted the authoritative package line. Parse that line
    # first; only treat the command as invalid when the package is absent.
    stdout, stderr = await _command(str(candidates[0]), "dump", "badging", str(apk), timeout=30, check=False)
    match = re.search(rb"^package:\s+name='([^']+)'", stdout, re.MULTILINE)
    if not match:
        detail = stderr.decode("utf-8", "replace").strip().splitlines()
        raise AndroidError(detail[-1] if detail else "the uploaded file is not a readable Android APK")
    return match.group(1).decode("utf-8", "replace")


_BOUNDS = re.compile(r"\[(\d+),(\d+)]\[(\d+),(\d+)]")


def _truth(value: str | None) -> bool:
    return value == "true"


def _role(class_name: str, attrs: dict[str, str]) -> str:
    tail = class_name.rsplit(".", 1)[-1].lower()
    if "edittext" in tail:
        return "textbox"
    if "checkbox" in tail:
        return "checkbox"
    if "radiobutton" in tail:
        return "radio"
    if "switch" in tail or "toggle" in tail:
        return "switch"
    if "button" in tail:
        return "button"
    if "image" in tail and _truth(attrs.get("clickable")):
        return "button"
    if "spinner" in tail:
        return "combobox"
    if "recycler" in tail or "listview" in tail:
        return "list"
    if _truth(attrs.get("clickable")):
        return "button"
    return "text"


def _box(value: str) -> dict[str, float] | None:
    match = _BOUNDS.fullmatch(value or "")
    if not match:
        return None
    x1, y1, x2, y2 = map(float, match.groups())
    return {"x": x1, "y": y1, "width": max(0.0, x2 - x1), "height": max(0.0, y2 - y1)}


def parse_hierarchy(
    xml: str,
    observation_id: str,
    serial: str,
    package: str,
    activity: str = "",
    max_elements: int = 80,
) -> tuple[Observation, list[dict[str, str]]]:
    """Turn a UIAutomator XML dump into PathLens' platform-neutral observation."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise AndroidError(f"UIAutomator returned invalid hierarchy XML: {exc}") from exc

    raw_nodes: list[dict[str, str]] = []
    for node in root.iter("node"):
        attrs = dict(node.attrib)
        # Android frequently makes a whole preference row clickable while putting its
        # spoken label on child TextViews. UIAutomator exposes both nodes separately;
        # derive the container's semantic name exactly from those visible descendants.
        derives_semantics = any(_truth(attrs.get(key)) for key in ("clickable", "checkable"))
        if derives_semantics and not (attrs.get("content-desc", "").strip() or attrs.get("text", "").strip()):
            descendant_names: list[str] = []
            for child in node.iter("node"):
                if child is node:
                    continue
                label = child.attrib.get("content-desc", "").strip() or child.attrib.get("text", "").strip()
                if label and label not in descendant_names:
                    descendant_names.append(label)
            if descendant_names:
                attrs["pathlens-derived-name"] = " · ".join(descendant_names)[:180]
        raw_nodes.append(attrs)
    elements: list[ObservedElement] = []
    visible: list[str] = []
    tree_lines: list[str] = []
    heading = ""
    for attrs in raw_nodes:
        text = " ".join(filter(None, (attrs.get("text", "").strip(), attrs.get("content-desc", "").strip())))
        if text and text not in visible:
            visible.append(text)
        class_name = attrs.get("class", "")
        role = _role(class_name, attrs)
        name = (attrs.get("content-desc", "").strip() or attrs.get("text", "").strip()
                or attrs.get("pathlens-derived-name", "").strip())
        box = _box(attrs.get("bounds", ""))
        interactive = any(_truth(attrs.get(k)) for k in ("clickable", "checkable", "scrollable")) \
            or role in {"textbox", "button", "checkbox", "radio", "switch", "combobox"}
        if not heading and name and not interactive:
            heading = name
        if name or interactive:
            tree_lines.append(
                f'{role} "{name or "(unlabelled)"}" bounds={attrs.get("bounds", "?")}'
                + (" focused" if _truth(attrs.get("focused")) else "")
                + (" disabled" if not _truth(attrs.get("enabled", "true")) else "")
            )
        if not interactive or len(elements) >= max_elements:
            continue
        is_password = _truth(attrs.get("password"))
        value = attrs.get("text", "") or None
        if is_password and value:
            value = "••••••"
        elements.append(ObservedElement(
            element_id=len(elements), role=role, name=name, tag=class_name,
            input_type="password" if is_password else ("text" if role == "textbox" else None),
            value=value, disabled=not _truth(attrs.get("enabled", "true")),
            checked=_truth(attrs.get("checked")) if role in {"checkbox", "radio", "switch"} else None,
            selected=_truth(attrs.get("selected")) if role in {"combobox"} or _truth(attrs.get("selected")) else None,
            focused=_truth(attrs.get("focused")), bbox=box,
        ))

    url = f"android://{serial}/{package}"
    if activity:
        url += "/" + activity.lstrip(".")
    visible_text = "\n".join(visible)
    tree = "\n".join(tree_lines)
    fingerprint = state_fingerprint(
        url, heading, "", [element.fingerprint_descriptor() for element in elements], visible_text,
    )
    return Observation(
        observation_id=observation_id, url=url, route=f"/{package}/{activity}".rstrip("/"),
        title=package, heading=heading or activity or package, visible_text=visible_text,
        aria_snapshot=tree, elements=elements, fingerprint=fingerprint,
        total_interactive=sum(
            any(_truth(attrs.get(k)) for k in ("clickable", "checkable", "scrollable"))
            or _role(attrs.get("class", ""), attrs) in {"textbox", "button", "checkbox", "radio", "switch", "combobox"}
            for attrs in raw_nodes
        ),
        controls_truncated=len(elements) >= max_elements,
    ), raw_nodes


class AndroidRegistry:
    def __init__(self, observation_id: str, elements: list[ObservedElement]):
        self.observation_id = observation_id
        self.elements = {element.element_id: element for element in elements}

    def resolve(self, observation_id: str, element_id: int | None):
        if observation_id != self.observation_id or element_id is None:
            return None
        element = self.elements.get(element_id)
        return (None, element) if element else None


class AndroidSession:
    page = None  # makes optional browser-only audits explicitly unavailable

    def __init__(
        self,
        run_dir: Path,
        serial: str | None,
        package: str,
        apk_path: str | None = None,
        activity: str | None = None,
        record_video: bool = True,
        max_elements: int = 80,
    ):
        self.run_dir = run_dir
        self.serial = serial
        self.package = package
        self.apk_path = apk_path
        self.activity = activity or ""
        self.record_video = record_video
        self.max_elements = max_elements
        self.registry: AndroidRegistry | None = None
        self._shot_counter = 0
        self._raw_nodes: list[dict[str, str]] = []
        self._recording: asyncio.subprocess.Process | None = None
        self._remote_video = f"/sdcard/pathlens_{short_id()}.mp4"
        self.video_name: str | None = None
        self.density = 1.0

    def _adb(self, *args: str) -> tuple[str, ...]:
        return (adb_executable(), "-s", str(self.serial), *args)

    async def start(self, _url: str) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        devices = [device for device in await list_devices() if device.status == "device"]
        if self.serial:
            if not any(device.serial == self.serial for device in devices):
                raise AndroidError(f'Android device "{self.serial}" is not connected and authorised')
        elif len(devices) == 1:
            self.serial = devices[0].serial
        elif not devices:
            raise AndroidError("no authorised Android device/emulator is connected; run `adb devices`")
        else:
            raise AndroidError("multiple Android devices are connected; select a device serial")

        if self.apk_path:
            await _command(*self._adb("install", "-r", self.apk_path), timeout=180)

        density_out, _ = await _command(*self._adb("shell", "wm", "density"), timeout=10, check=False)
        density_match = re.search(rb"(?:Physical|Override) density:\s*(\d+)", density_out)
        if density_match:
            self.density = max(1.0, int(density_match.group(1)) / 160)

        if self.activity:
            component = f"{self.package}/{self.activity}"
            await _command(*self._adb("shell", "am", "start", "-W", "-S", "-n", component), timeout=30)
        else:
            await _command(*self._adb("shell", "am", "force-stop", self.package), timeout=15)
            await _command(
                *self._adb("shell", "monkey", "-p", self.package, "-c", "android.intent.category.LAUNCHER", "1"),
                timeout=30,
            )
        await asyncio.sleep(0.8)
        if self.record_video:
            self._recording = await asyncio.create_subprocess_exec(
                *self._adb("shell", "screenrecord", "--time-limit", "180", self._remote_video),
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
            )

    async def _focused_activity(self) -> tuple[str, str]:
        stdout, _ = await _command(*self._adb("shell", "dumpsys", "window", "windows"), timeout=12, check=False)
        text = stdout.decode("utf-8", "replace")
        match = re.search(r"mCurrentFocus=.*?\s([A-Za-z0-9_.$-]+)/([A-Za-z0-9_.$-]+)", text)
        if not match:
            match = re.search(r"mFocusedApp=.*?\s([A-Za-z0-9_.$-]+)/([A-Za-z0-9_.$-]+)", text)
        return (match.group(1), match.group(2)) if match else (self.package, self.activity)

    async def observe(self) -> Observation:
        self._shot_counter += 1
        obs_id = short_id()
        remote_tree = f"/sdcard/pathlens_{obs_id}.xml"
        xml_bytes = b""
        for attempt in range(3):
            await _command(*self._adb("shell", "uiautomator", "dump", remote_tree), timeout=20, check=False)
            xml_bytes, _ = await _command(*self._adb("exec-out", "cat", remote_tree), timeout=15, check=False)
            start = xml_bytes.find(b"<?xml")
            if start < 0:
                start = xml_bytes.find(b"<hierarchy")
            if start >= 0:
                xml_bytes = xml_bytes[start:]
                break
            if attempt < 2:
                await asyncio.sleep(0.7)
        await _command(*self._adb("shell", "rm", remote_tree), timeout=10, check=False)
        if not xml_bytes.lstrip().startswith((b"<?xml", b"<hierarchy")):
            preview = xml_bytes[:160].decode("utf-8", "replace")
            raise AndroidError(f"UIAutomator did not produce a hierarchy after 3 attempts: {preview or 'empty output'}")
        package, activity = await self._focused_activity()
        xml = xml_bytes.decode("utf-8", "replace")
        obs, self._raw_nodes = parse_hierarchy(
            xml, obs_id, str(self.serial), package or self.package, activity, self.max_elements,
        )
        tree_name = f"tree_step_{self._shot_counter:02d}.xml"
        (self.run_dir / tree_name).write_text(xml, encoding="utf-8")
        obs.accessibility_tree_id = tree_name
        shot_name = f"step_{self._shot_counter:02d}.png"
        shot, _ = await _command(*self._adb("exec-out", "screencap", "-p"), timeout=20)
        (self.run_dir / shot_name).write_bytes(shot)
        obs.screenshot_id = shot_name
        self.registry = AndroidRegistry(obs_id, obs.elements)
        return obs

    async def execute(self, action: BrowserAction) -> ActionResult:
        started = time.perf_counter()
        resolved = self.registry.resolve(action.observation_id, action.element_id) if self.registry else None
        element = resolved[1] if resolved else None

        def result(outcome: str, error: str | None = None, note: str | None = None) -> ActionResult:
            return ActionResult(outcome, int((time.perf_counter() - started) * 1000),
                                element.descriptor() if element else None, error, note)

        targeted = action.action in {
            ActionType.CLICK, ActionType.TYPE, ActionType.SELECT, ActionType.CHECK,
            ActionType.UNCHECK, ActionType.HOVER,
        }
        if targeted and not element:
            return result("stale", "element does not belong to the current Android observation")
        try:
            if action.action in {ActionType.CLICK, ActionType.CHECK, ActionType.UNCHECK, ActionType.SELECT}:
                if not element.bbox:
                    return result("failed", "Android control has no actionable screen bounds")
                x = int(element.bbox["x"] + element.bbox["width"] / 2)
                y = int(element.bbox["y"] + element.bbox["height"] / 2)
                await _command(*self._adb("shell", "input", "tap", str(x), str(y)), timeout=12)
            elif action.action == ActionType.TYPE:
                if not element.bbox:
                    return result("failed", "Android text field has no actionable screen bounds")
                x = int(element.bbox["x"] + element.bbox["width"] / 2)
                y = int(element.bbox["y"] + element.bbox["height"] / 2)
                await _command(*self._adb("shell", "input", "tap", str(x), str(y)), timeout=12)
                await _command(*self._adb("shell", "input", "text", (action.text or "").replace(" ", "%s")), timeout=15)
                if action.submit:
                    await _command(*self._adb("shell", "input", "keyevent", "66"), timeout=10)
            elif action.action == ActionType.SCROLL:
                direction = action.direction or "down"
                y1, y2 = ((500, 1200) if direction == "up" else (1200, 500))
                await _command(*self._adb("shell", "input", "swipe", "540", str(y1), "540", str(y2), "350"), timeout=12)
            elif action.action == ActionType.BACK:
                await _command(*self._adb("shell", "input", "keyevent", "4"), timeout=10)
            elif action.action == ActionType.PRESS:
                keycodes = {"Enter": "66", "Escape": "4", "Tab": "61", "ArrowDown": "20", "ArrowUp": "19"}
                await _command(*self._adb("shell", "input", "keyevent", keycodes[action.key]), timeout=10)
            elif action.action == ActionType.WAIT:
                await asyncio.sleep(0.8)
            elif action.action == ActionType.HOVER:
                return result("failed", "hover has no equivalent on a touch-only Android journey")
            await asyncio.sleep(0.45)
            return result("success")
        except Exception as exc:
            return result("failed", str(exc)[:400])

    async def audit(self, final: bool = False) -> list[AxeViolation]:
        del final
        rules: dict[str, tuple[str, str, str, list[AxeNode]]] = {
            "android-missing-label": (
                "serious", "Interactive Android controls need a meaningful accessible label",
                "Add android:contentDescription or visible text that accurately names the control.", [],
            ),
            "android-editable-name": (
                "critical", "Editable Android fields need an accessible name",
                "Associate a visible label/hint with the field and expose it to accessibility services.", [],
            ),
            "android-touch-target-size": (
                "serious", "Android touch targets should be at least 48dp by 48dp",
                "Increase the interactive target to at least 48dp in both dimensions or provide equivalent spacing.", [],
            ),
        }
        for attrs in self._raw_nodes:
            role = _role(attrs.get("class", ""), attrs)
            interactive = any(_truth(attrs.get(k)) for k in ("clickable", "checkable")) \
                or role in {"textbox", "button", "checkbox", "radio", "switch", "combobox"}
            if not interactive or not _truth(attrs.get("visible-to-user", "true")):
                continue
            name = (attrs.get("content-desc", "").strip() or attrs.get("text", "").strip()
                    or attrs.get("pathlens-derived-name", "").strip())
            snippet = f'<node class="{attrs.get("class", "")}" text="{attrs.get("text", "")}" content-desc="{attrs.get("content-desc", "")}" bounds="{attrs.get("bounds", "")}" />'
            target = [attrs.get("bounds", "")]
            if not name:
                rule = "android-editable-name" if role == "textbox" else "android-missing-label"
                rules[rule][3].append(AxeNode(
                    html=snippet, target=target,
                    failure_summary="The accessibility hierarchy exposes this interactive control without a name.",
                ))
            box = _box(attrs.get("bounds", ""))
            if box and (box["width"] / self.density < 48 or box["height"] / self.density < 48):
                rules["android-touch-target-size"][3].append(AxeNode(
                    html=snippet, target=target,
                    failure_summary=(f'Touch target is approximately {box["width"] / self.density:.0f}dp × '
                                     f'{box["height"] / self.density:.0f}dp.'),
                ))
        return [
            AxeViolation(id=rule, impact=impact, description=help_text, help=description,
                         help_url="https://developer.android.com/guide/topics/ui/accessibility/apps",
                         nodes=nodes[:5], total_nodes=len(nodes))
            for rule, (impact, description, help_text, nodes) in rules.items() if nodes
        ]

    async def close(self) -> None:
        if self._recording:
            if self._recording.returncode is None:
                try:
                    self._recording.send_signal(signal.SIGINT)
                    await asyncio.wait_for(self._recording.wait(), timeout=8)
                except Exception:
                    self._recording.kill()
                    await self._recording.wait()
            local = self.run_dir / "journey.mp4"
            try:
                await _command(*self._adb("pull", self._remote_video, str(local)), timeout=45)
                if local.exists() and local.stat().st_size:
                    self.video_name = local.name
            except Exception:
                pass
            await _command(*self._adb("shell", "rm", self._remote_video), timeout=10, check=False)
