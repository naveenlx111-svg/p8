"""Deterministic accessibility auditing with locally vendored axe-core, plus the risk-score heuristic."""
from __future__ import annotations

from playwright.async_api import Page

from backend.schemas import AxeViolation

# Small predictable rule set during the live journey (keeps each scan fast and stable).
AXE_LIVE_RULES = ["button-name", "label", "color-contrast", "aria-dialog-name", "link-name", "image-alt"]
# Final audit on the goal state: all WCAG 2.x A/AA tagged rules.
AXE_FINAL_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]

AXE_RUN_JS = """
async ({rules, tags}) => {
  if (typeof axe === 'undefined') return {error: 'axe not loaded'};
  const runOnly = rules ? {type: 'rule', values: rules} : {type: 'tag', values: tags};
  const result = await axe.run(document, {runOnly, resultTypes: ['violations']});
  return {violations: result.violations.map(v => ({
    id: v.id, impact: v.impact, description: v.description, help: v.help, help_url: v.helpUrl,
    nodes: v.nodes.slice(0, 3).map(n => ({html: n.html, target: n.target, failure_summary: n.failureSummary}))
  }))};
}
"""

IMPACT_WEIGHTS = {"critical": 25, "serious": 14, "moderate": 6, "minor": 2}

DISCLAIMER = "Automated heuristic based on detected accessibility violations; not a WCAG certification."


async def run_axe(page: Page, final: bool = False) -> list[AxeViolation]:
    args = {"rules": None, "tags": AXE_FINAL_TAGS} if final else {"rules": AXE_LIVE_RULES, "tags": None}
    result = await page.evaluate(AXE_RUN_JS, args)
    if "error" in result:
        raise RuntimeError(result["error"])
    return [AxeViolation.model_validate(v) for v in result["violations"]]


def risk_score(violations: list[AxeViolation]) -> int:
    """100 - weighted count of UNIQUE violated rules (not affected nodes)."""
    unique = {v.id: v.impact for v in violations}
    return max(0, 100 - sum(IMPACT_WEIGHTS.get(impact or "minor", 2) for impact in unique.values()))


def impact_counts(violations: list[AxeViolation]) -> dict[str, int]:
    counts = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
    for v in {v.id: v for v in violations}.values():
        counts[v.impact or "minor"] += 1
    return counts
