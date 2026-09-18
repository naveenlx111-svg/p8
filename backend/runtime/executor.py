"""Executes one BrowserAction against the ephemeral registry and normalises the outcome.

success -> action executed
stale   -> observation/handle no longer valid; re-observe
blocked -> interaction could not progress (e.g. click intercepted by an overlay); kept as UX evidence
failed  -> anything else; controlled recovery path
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from backend.runtime.observer import ElementRegistry
from backend.schemas import ActionType, BrowserAction, Outcome, TargetDescriptor

SETTLE_JS = "() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"


@dataclass
class ActionResult:
    outcome: Outcome
    duration_ms: int
    target: TargetDescriptor | None = None
    error: str | None = None


async def settle(page: Page) -> None:
    """Wait until the UI is stable enough to observe: DOM ready, AJAX quiet (capped), two paint frames."""
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=3000)
    except PlaywrightError:
        pass  # navigation mid-settle is fine; the next observation captures the resulting state
    try:
        await page.wait_for_load_state("networkidle", timeout=2500)  # AJAX-rendered sites
    except PlaywrightError:
        pass  # sites with long-polling/analytics never go idle; the cap keeps the loop moving
    try:
        await page.evaluate(SETTLE_JS)
    except PlaywrightError:
        pass


def _describe_error(exc: Exception) -> str:
    lines = [l.strip() for l in str(exc).splitlines() if l.strip()]
    head = lines[0] if lines else type(exc).__name__
    # Playwright's call log names the element that swallowed the click: valuable UX evidence.
    blocker = next((l for l in lines if "intercepts pointer events" in l), None)
    return (head + (" | " + blocker.lstrip("- ") if blocker else ""))[:400]


def _classify(exc: Exception) -> Outcome:
    msg = str(exc).lower()
    if "detached" in msg or "not attached" in msg or "has been disposed" in msg or "context was destroyed" in msg:
        return "stale"
    if isinstance(exc, PlaywrightTimeoutError) or "intercepts pointer events" in msg or "not visible" in msg:
        return "blocked"
    return "failed"


async def execute(page: Page, registry: ElementRegistry, action: BrowserAction, timeout_ms: int) -> ActionResult:
    start = time.perf_counter()
    target = None

    def done(outcome: Outcome, error: str | None = None) -> ActionResult:
        return ActionResult(outcome, int((time.perf_counter() - start) * 1000), target, error)

    needs_element = action.action in (ActionType.CLICK, ActionType.TYPE)
    if needs_element:
        resolved = registry.resolve(action.observation_id, action.element_id)
        if resolved is None:
            return done("stale", f"element {action.element_id} not in observation {action.observation_id}")
        handle, element = resolved
        target = element.descriptor()
        if element.disabled:
            return done("blocked", f'{element.role} "{element.name}" is disabled')

    try:
        if action.action == ActionType.CLICK:
            await handle.click(timeout=timeout_ms)
        elif action.action == ActionType.TYPE:
            await handle.fill(action.text or "", timeout=timeout_ms)
            # A person submits a search box with Enter; small models often forget to ask for it.
            is_search = element.role == "searchbox" or "search" in (element.name or element.placeholder or "").lower()
            if action.submit or is_search:
                await handle.press("Enter", timeout=timeout_ms)
        elif action.action == ActionType.SCROLL:
            await page.mouse.wheel(0, -600 if action.direction == "up" else 600)
        elif action.action == ActionType.BACK:
            await page.go_back(timeout=timeout_ms)
        elif action.action == ActionType.PRESS:
            await page.keyboard.press(action.key or "Escape")
        elif action.action == ActionType.WAIT:
            await page.wait_for_timeout(800)
        await settle(page)
        return done("success")
    except Exception as exc:  # classified, never swallowed: the outcome + message become evidence
        return done(_classify(exc), _describe_error(exc))
