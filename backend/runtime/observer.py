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
({maxElements, focusWords}) => {
  const SEL = 'button, a[href], input:not([type=hidden]), textarea, select, summary, [role=button], [role=link], [role=tab], [role=menuitem], [role=checkbox], [role=switch], [tabindex]:not([tabindex="-1"])';
  const txt = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const isVisible = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    // Parked off-page horizontally (screen-reader-only helpers, e.g. keyboard-shortcut menus): not seen by a sighted user.
    if (r.right <= 0 || r.left >= Math.max(document.documentElement.scrollWidth, innerWidth)) return false;
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
  // A dialog only counts if it actually confronts the user: modal, or an overlay covering real screen area.
  // (Sites use role=dialog for permanent layout panels, e.g. filter sidebars; those are not interruptions.)
  const blocking = (d) => {
    if (d.getAttribute('aria-modal') === 'true') return true;
    try { if (d.matches(':modal')) return true; } catch (e) {}
    const cs = getComputedStyle(d), r = d.getBoundingClientRect();
    const w = Math.max(0, Math.min(r.right, innerWidth) - Math.max(r.left, 0));
    const h = Math.max(0, Math.min(r.bottom, innerHeight) - Math.max(r.top, 0));
    return (cs.position === 'fixed' || cs.position === 'absolute') && w * h >= 0.1 * innerWidth * innerHeight;
  };
  const dialogs = [...document.querySelectorAll('[role=dialog],[role=alertdialog],dialog[open]')].filter(isVisible).filter(blocking);
  const modal = dialogs.find(d => d.getAttribute('aria-modal') === 'true' || d.tagName === 'DIALOG') || null;
  const covered = (el) => {
    const r = el.getBoundingClientRect();
    const x = r.left + r.width / 2, y = r.top + r.height / 2;
    if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) return false;
    const top = document.elementFromPoint(x, y);
    return !!top && top !== el && !el.contains(top) && !top.contains(el);
  };
  const all = [...document.querySelectorAll(SEL)].filter(isVisible);
  const totalInteractive = all.length;
  // Rank what a user is confronted with: open dialog first, then controls on screen (reading order),
  // then off-screen controls by distance from the viewport. Large pages (e.g. marketplaces) have hundreds.
  const dist = (el) => {
    const r = el.getBoundingClientRect();
    if (r.bottom >= 0 && r.top <= innerHeight) return 0;
    return r.top > innerHeight ? r.top - innerHeight : -r.bottom;
  };
  const CHROME = 'header, nav, footer, [role=banner], [role=navigation], [role=contentinfo]';
  const words = (focusWords || []).map(w => w.toLowerCase());
  const relevant = (el) => {
    const n = (accName(el) + ' ' + (el.getAttribute('placeholder') || '')).toLowerCase();
    return words.some(w => n.includes(w));
  };
  // Tiers: open dialog, goal-relevant, main content on screen, main content off screen (by distance), site chrome.
  const rank = (el) => {
    if (modal && modal.contains(el)) return -2;
    if (relevant(el)) return -1;
    if (el.closest(CHROME)) return 2;
    return dist(el) === 0 ? 0 : 1;
  };
  const ordered = all.map((el, i) => ({el, i, k: rank(el), d: dist(el)}))
    .sort((a, b) => a.k - b.k || (a.k === 1 ? a.d - b.d : a.i - b.i)).map(o => o.el);
  const seen = new Set();
  const els = [], info = [];
  for (const el of ordered) {
    if (els.length >= maxElements) break;
    // The same destination is often linked twice (image + title); keep the first, it costs the model nothing.
    const href = el.tagName === 'A' ? el.getAttribute('href') : null;
    const dupKey = href ? roleOf(el) + '|' + accName(el) + '|' + href : null;
    if (dupKey) { if (seen.has(dupKey)) continue; seen.add(dupKey); }
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
      visibility: dist(el) === 0 ? 'visible' : 'offscreen',
      checked: (el.type === 'checkbox' || el.type === 'radio' || el.getAttribute('role') === 'switch') ? !!el.checked : null,
      selected: el.tagName === 'SELECT' ? el.selectedIndex >= 0 : null,
      bbox: { x: r.x, y: r.y, width: r.width, height: r.height },
    });
  }
  // Page text a user reads: main content first, without the repeated site chrome (header/nav/footer).
  const main = document.querySelector('main, [role=main]');
  let pageText = '';
  if (main) { pageText = txt(main.innerText); }
  else {
    const parts = [];
    const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let total = 0, node;
    while ((node = walk.nextNode()) && total < 2600) {
      const p = node.parentElement;
      if (!p || p.closest('script,style,noscript,template') || p.closest(CHROME) || !p.getClientRects().length) continue;
      const t = txt(node.textContent);
      if (t) { parts.push(t); total += t.length + 1; }
    }
    pageText = parts.join(' ');
  }
  const dialog = dialogs[0];
  return {
    els, info,
    heading: txt(document.querySelector('h1')?.innerText),
    title: document.title,
    visible_text: pageText.slice(0, 2400),
    dialog_open: dialogs.length > 0,
    dialog_name: dialog ? (dialog.getAttribute('aria-label') || byIds(dialog.getAttribute('aria-labelledby') || '') || txt(dialog.innerText).slice(0, 80)) : '',
    dialog_text: dialog ? txt(dialog.innerText).slice(0, 400) : '',
    total_interactive: totalInteractive,
    controls_truncated: ordered.length > els.length,
    text_truncated: pageText.length > 2400,
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


async def observe(page: Page, max_elements: int = 40, focus_words: list[str] | None = None) -> tuple[Observation, ElementRegistry]:
    obs_id = "obs_" + short_id()
    handle = await page.evaluate_handle(COLLECT_JS, {"maxElements": max_elements, "focusWords": focus_words or []})
    try:
        data = await (await handle.get_property("info")).json_value()
        els_prop = await handle.get_property("els")
        props = await els_prop.get_properties()
        meta = {}
        for key in ("heading", "title", "visible_text", "dialog_open", "dialog_name", "dialog_text",
                    "total_interactive", "controls_truncated", "text_truncated"):
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
            visibility=info["visibility"], checked=info["checked"], selected=info["selected"],
        )
        registry.handles[idx] = el_handle
        registry.elements[idx] = el
        elements.append(el)

    controls = [e.fingerprint_descriptor() for e in elements if not e.covered]
    visible_text = meta["visible_text"]
    if meta["dialog_open"]:
        visible_text = f"[DIALOG] {meta['dialog_text']}\n{visible_text}"
    obs = Observation(
        observation_id=obs_id, url=page.url, route=canonical_route(page.url), title=meta["title"],
        heading=meta["heading"], visible_text=visible_text, aria_snapshot=await aria_snapshot(page),
        elements=elements, dialog_open=meta["dialog_open"], dialog_name=meta["dialog_name"],
        total_interactive=meta["total_interactive"], controls_truncated=meta["controls_truncated"],
        text_truncated=meta["text_truncated"],
    )
    obs.fingerprint = state_fingerprint(obs.url, obs.heading, obs.dialog_name, controls, meta["visible_text"])
    return obs, registry
