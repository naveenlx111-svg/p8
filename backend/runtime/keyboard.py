"""Experiential keyboard checks that static DOM accessibility rules cannot prove."""
from __future__ import annotations

from playwright.async_api import ElementHandle, Page


ACTIVE_INFO_JS = r"""
() => {
  const el = document.activeElement;
  const modal = document.querySelector('[aria-modal="true"], dialog:modal');
  const text = (value) => (value || '').replace(/\s+/g, ' ').trim();
  const name = el ? (el.getAttribute('aria-label') || text(el.innerText) || el.getAttribute('placeholder') || el.id || el.tagName) : '';
  return { name: name.slice(0, 100), inside_modal: !!(modal && el && modal.contains(el)) };
}
"""

MODAL_META_JS = """
() => {
  const modal = document.querySelector('[aria-modal="true"], dialog:modal');
  if (!modal) return null;
  const focusable = [...modal.querySelectorAll('a[href],button,input,select,textarea,[tabindex]:not([tabindex="-1"])')]
    .filter(el => !el.disabled && el.getClientRects().length > 0);
  return { focusable_count: focusable.length };
}
"""


async def audit_modal_focus(page: Page) -> list[dict[str, str]]:
    """Tab through one cycle of a modal and report verified focus failures.

    The original focused element is restored. No target DOM attributes or test hooks
    are added, and no click/submit action is performed.
    """
    meta = await page.evaluate(MODAL_META_JS)
    if not meta:
        return []

    original: ElementHandle | None = (await page.evaluate_handle("document.activeElement")).as_element()
    initial = await page.evaluate(ACTIVE_INFO_JS)
    issues: list[dict[str, str]] = []
    if not initial["inside_modal"]:
        issues.append({
            "rule": "modal-focus-entry",
            "title": "Focus did not move into the modal",
            "evidence": f'When the modal opened, keyboard focus remained on "{initial["name"] or "page background"}".',
        })

    escaped_to = ""
    # One full cycle plus two steps is enough to prove whether focus can leave the modal.
    for _ in range(max(2, min(int(meta["focusable_count"]) + 2, 12))):
        await page.keyboard.press("Tab")
        active = await page.evaluate(ACTIVE_INFO_JS)
        if not active["inside_modal"]:
            escaped_to = active["name"] or "page background"
            break
    if escaped_to:
        issues.append({
            "rule": "modal-focus-trap",
            "title": "Keyboard focus escapes the modal",
            "evidence": f'Tabbing moved focus outside the open modal to "{escaped_to}".',
        })

    if original:
        try:
            await original.focus()
        finally:
            await original.dispose()
    return issues
