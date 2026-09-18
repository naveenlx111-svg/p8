"""Black-box perception: builds an Observation plus an observation-scoped element registry.

The registry maps (observation_id, element_id) -> live Playwright ElementHandle. It is never persisted,
never stamped into the target DOM, and is discarded when the next observation is taken.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from playwright.async_api import ElementHandle, Page

from backend.runtime.fingerprint import canonical_route, state_fingerprint
from backend.schemas import ObservedElement, Observation, short_id

# Collects visible interactive controls with their user-perceivable role and accessible name.
# Returns {els: Element[], info: object[]} so handles can be taken without mutating the DOM.
COLLECT_JS = r"""
(maxElements) => {
  const SEL = 'button, a[href], input:not([type=hidden]), textarea, select, summary, [role=button], [role=link], [role=tab], [role=menuitem], [role=checkbox], [role=switch], [tabindex]:not([tabindex="-1"])';
  const txt = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const isVisible = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity) === 0) return false;
    return !el.closest('[hidden],[aria-hidden="true"]');
  };
  const byIds = (ids) => txt(ids.split(/\s+/).map(id => document.getElementById(id)?.innerText || '').join(' '));
  const accName = (el) => {
    if (el.getAttribute('aria-labelledby')) { const n = byIds(el.getAttribute('aria-labelledby')); if (n) return n; }
    if (el.getAttribute('aria-label')) return txt(el.getAttribute('aria-label'));
    if (['INPUT','TEXTAREA','SELECT'].includes(el.tagName)) {
      if (el.id) { const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`); if (l) return txt(l.innerText); }
      const wrap = el.closest('label'); if (wrap) return txt(wrap.innerText);
      if (el.type === 'submit' || el.type === 'button') return txt(el.value);
      return txt(el.getAttribute('title'));
    }
    const inner = txt(el.innerText);
    if (inner) return inner.slice(0, 80);
    const img = el.querySelector('img[alt]'); if (img) return txt(img.alt);
    return txt(el.getAttribute('title'));
  };
  const roleOf = (el) => {
    const r = el.getAttribute('role'); if (r) return r;
    const t = el.tagName;
    if (t === 'A') return 'link';
    if (t === 'BUTTON' || t === 'SUMMARY') return 'button';
    if (t === 'SELECT') return 'combobox';
    if (t === 'TEXTAREA') return 'textbox';
    if (t === 'INPUT') {
      const ty = (el.type || 'text').toLowerCase();
      if (['submit','button','reset','image'].includes(ty)) return 'button';
      if (ty === 'checkbox') return 'checkbox';
      if (ty === 'radio') return 'radio';
      if (ty === 'search') return 'searchbox';
      return 'textbox';
    }
    return 'generic';
  };
  const dialogs = [...document.querySelectorAll('[role=dialog],[role=alertdialog],dialog[open]')].filter(isVisible);
  const modal = dialogs.find(d => d.getAttribute('aria-modal') === 'true' || d.tagName === 'DIALOG') || null;
  const covered = (el) => {
    const r = el.getBoundingClientRect();
    const x = r.left + r.width / 2, y = r.top + r.height / 2;
    if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) return false;
    const top = document.elementFromPoint(x, y);
    return !!top && top !== el && !el.contains(top) && !top.contains(el);
  };
  const all = [...document.querySelectorAll(SEL)].filter(isVisible);
  // Controls inside an open dialog come first: that is what the user is confronted with.
  const ordered = modal ? [...all.filter(e => modal.contains(e)), ...all.filter(e => !modal.contains(e))] : all;
  const els = [], info = [];
  for (const el of ordered) {
    if (els.length >= maxElements) break;
    const r = el.getBoundingClientRect();
    els.push(el);
    info.push({
      role: roleOf(el), name: accName(el), tag: el.tagName.toLowerCase(),
      input_type: el.tagName === 'INPUT' ? (el.type || 'text') : null,
      placeholder: el.getAttribute('placeholder') || null,
      value: (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') ? (el.type === 'password' ? (el.value ? '••••••' : null) : (el.value || null)) : null,
      disabled: !!el.disabled || el.getAttribute('aria-disabled') === 'true',
      in_dialog: !!(dialogs.find(d => d.contains(el))),
      covered: covered(el),
      bbox: { x: r.x, y: r.y, width: r.width, height: r.height },
    });
  }
  const main = document.querySelector('main') || document.body;
  const dialog = dialogs[0];
  return {
    els, info,
    heading: txt(document.querySelector('h1')?.innerText),
    title: document.title,
    visible_text: txt(main.innerText).slice(0, 1800),
    dialog_open: dialogs.length > 0,
    dialog_name: dialog ? (dialog.getAttribute('aria-label') || byIds(dialog.getAttribute('aria-labelledby') || '') || txt(dialog.innerText).slice(0, 80)) : '',
    dialog_text: dialog ? txt(dialog.innerText).slice(0, 400) : '',
  };
}
"""


@dataclass
class ElementRegistry:
    observation_id: str
    handles: dict[int, ElementHandle] = field(default_factory=dict)
    elements: dict[int, ObservedElement] = field(default_factory=dict)

    def resolve(self, observation_id: str, element_id: int | None) -> tuple[ElementHandle, ObservedElement] | None:
        if observation_id != self.observation_id or element_id is None:
            return None
        if element_id not in self.handles:
            return None
        return self.handles[element_id], self.elements[element_id]


async def aria_snapshot(page: Page, limit: int = 3500) -> str:
    try:
        snap = await page.locator("body").aria_snapshot(timeout=2000)
    except Exception as exc:  # snapshot is context, never fatal
        return f"(aria snapshot unavailable: {type(exc).__name__})"
    return snap[:limit]


async def observe(page: Page, max_elements: int = 40) -> tuple[Observation, ElementRegistry]:
    obs_id = "obs_" + short_id()
    handle = await page.evaluate_handle(COLLECT_JS, max_elements)
    try:
        data = await (await handle.get_property("info")).json_value()
        els_prop = await handle.get_property("els")
        props = await els_prop.get_properties()
        meta = {}
        for key in ("heading", "title", "visible_text", "dialog_open", "dialog_name", "dialog_text"):
            meta[key] = await (await handle.get_property(key)).json_value()
    finally:
        await handle.dispose()

    registry = ElementRegistry(observation_id=obs_id)
    elements: list[ObservedElement] = []
    for idx, info in enumerate(data):
        el_handle = props[str(idx)].as_element()
        if el_handle is None:
            continue
        name = info["name"]
        el = ObservedElement(
            element_id=idx, role=info["role"], name=name, tag=info["tag"], input_type=info["input_type"],
            placeholder=info["placeholder"], value=info["value"], disabled=info["disabled"],
            in_dialog=info["in_dialog"], covered=info["covered"], bbox=info["bbox"],
        )
        registry.handles[idx] = el_handle
        registry.elements[idx] = el
        elements.append(el)

    controls = [f"{e.role}:{e.name}" for e in elements if not e.covered]
    visible_text = meta["visible_text"]
    if meta["dialog_open"]:
        visible_text = f"[DIALOG] {meta['dialog_text']}\n{visible_text}"
    obs = Observation(
        observation_id=obs_id, url=page.url, route=canonical_route(page.url), title=meta["title"],
        heading=meta["heading"], visible_text=visible_text, aria_snapshot=await aria_snapshot(page),
        elements=elements, dialog_open=meta["dialog_open"], dialog_name=meta["dialog_name"],
    )
    obs.fingerprint = state_fingerprint(obs.url, obs.heading, obs.dialog_name, controls, meta["visible_text"])
    return obs, registry
