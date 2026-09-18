"""Structured journey-fact memory.

LLM -> perceives visible information and proposes facts.
Python -> grounds each fact in the observed page text, stores it, and verifies cross-state inconsistencies.
"""
from __future__ import annotations

import re

from backend.schemas import CriticFinding, ModelFact, Observation, PageFact

_NON_WORD = re.compile(r"[^a-z0-9+ ]+")


def normalize_entity(name: str) -> str:
    return " ".join(_NON_WORD.sub(" ", name.lower()).split())


def _price_variants(value: float) -> set[str]:
    """Exact-value string forms the page could plausibly show. Never rounds: a proposed 29.99 must not be
    grounded against a page that only shows 30 - that would accept a wrong price as if it were confirmed."""
    is_whole = abs(value - round(value)) < 1e-9
    if not is_whole:
        return {f"{value:.2f}"}
    n = int(round(value))
    indian = _indian_grouping(n)
    return {str(n), f"{n:,}", indian, f"{n:,}.00", f"{indian}.00"}


def _indian_grouping(n: int) -> str:
    s = str(n)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups + [tail])


_MONEY = re.compile(
    r"[₹$€£]\s*\d[\d,]*(?:\.\d{1,2})?|\b\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?\b|\b\d+\.\d{1,2}\b")


def _entity_spans(entity: str, text: str) -> list[tuple[int, int]]:
    """Find visible product-name occurrences while allowing ordinary whitespace differences."""
    normalized = " ".join(entity.split())
    if not normalized:
        return []
    pattern = re.escape(normalized).replace(r"\ ", r"\s+")
    return [m.span() for m in re.finditer(pattern, text, re.I)]


def _gap(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(b[0] - a[1], a[0] - b[1], 0)


def _overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def _associated_price(fact: ModelFact, text: str) -> bool:
    """Require the claimed price to be the closest visible price to the named product.

    This is deliberately conservative. A value elsewhere on a results page is not evidence that it belongs
    to this product; the entity and amount must occur in the same short text region, with no closer price.
    """
    entities = _entity_spans(fact.entity, text)
    if not entities:
        return False
    price_spans = [m.span() for m in _MONEY.finditer(text)]
    candidates = []
    for value in _price_variants(fact.value):
        candidates.extend(m.span() for m in re.finditer(rf"(?<![\d,.]){re.escape(value)}(?![\d,])", text))
    for entity in entities:
        nearby = [p for p in price_spans if _gap(entity, p) <= 160]
        if not nearby:
            continue
        closest = min(_gap(entity, p) for p in nearby)
        closest_prices = [p for p in nearby if _gap(entity, p) == closest]
        if any(_overlap(candidate, price) for candidate in candidates for price in closest_prices):
            return True
    return False


def is_grounded(fact: ModelFact, obs: Observation) -> bool:
    """A price is accepted only when its exact visible amount is associated with its named product."""
    text = obs.visible_text
    value_visible = any(re.search(rf"(?<![\d,.]){re.escape(v)}(?![\d,])", text) for v in _price_variants(fact.value))
    if not value_visible:
        return False
    return fact.kind != "product_price" or _associated_price(fact, text)


_SYMBOL_CODE = {"₹": "INR", "$": "USD", "€": "EUR", "£": "GBP"}


def detect_currency(fact: ModelFact, obs: Observation) -> str:
    """Currency from the symbol printed right before the number on the page (not from the model)."""
    for v in sorted(_price_variants(fact.value), key=len, reverse=True):
        m = re.search(rf"([₹$€£])\s?{re.escape(v)}(?![\d,])", obs.visible_text)
        if m:
            return _SYMBOL_CODE[m.group(1)]
    return fact.currency or "INR"


def absorb_facts(facts: list[PageFact], new: list[ModelFact], obs: Observation, step: int, state_id: str) -> tuple[list[PageFact], list[ModelFact]]:
    """Adds grounded, non-duplicate facts. Returns (accepted, rejected_as_ungrounded)."""
    accepted, rejected = [], []
    for f in new:
        if not is_grounded(f, obs):
            rejected.append(f)
            continue
        dup = any(p.kind == f.kind and normalize_entity(p.entity) == normalize_entity(f.entity)
                  and p.value == f.value and p.state_id == state_id for p in facts)
        if dup:
            continue
        pf = PageFact(kind=f.kind, entity=f.entity.strip(), value=f.value, currency=detect_currency(f, obs),
                      context=f.context, step_number=step, url=obs.route, state_id=state_id)
        facts.append(pf)
        accepted.append(pf)
    return accepted, rejected


SYMBOLS = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}


def money(v: float, currency: str = "INR") -> str:
    if currency.upper() in ("INR", "RS", "₹"):
        return "₹" + _indian_grouping(int(round(v)))
    sym = SYMBOLS.get(currency.upper(), currency.upper() + " ")
    return f"{sym}{v:,.2f}" if v != int(v) else f"{sym}{int(v):,}"


def detect_price_conflicts(facts: list[PageFact], already_reported: set[str]) -> list[CriticFinding]:
    """Same product, different price across different UI states -> verified semantic inconsistency."""
    by_entity: dict[str, list[PageFact]] = {}
    for f in facts:
        if f.kind == "product_price":
            by_entity.setdefault(normalize_entity(f.entity), []).append(f)

    findings = []
    for key, obs in by_entity.items():
        # The advertised product-page price is the reference when we have one.
        first = next((f for f in obs if f.context == "product_page"), obs[0])
        for later in obs:
            if later.step_number < first.step_number:
                continue
            if later.value == first.value or later.state_id == first.state_id:
                continue
            if later.currency != first.currency:
                continue  # a currency change fully explains a numeric difference; not a suspected defect
            sig = f"{key}:{first.value}->{later.value}"
            if sig in already_reported:
                continue
            already_reported.add(sig)
            diff = later.value - first.value
            pct = diff / first.value * 100 if first.value else 0.0
            cur = first.currency
            where_a = first.context.replace("_", " ")
            where_b = later.context.replace("_", " ")
            findings.append(CriticFinding(
                category="semantic_inconsistency",
                severity="high" if abs(pct) >= 1 else "medium",
                title=f"Price inconsistency: {first.entity}",
                evidence=(f"{where_a.capitalize()} shows {money(first.value, cur)} (step {first.step_number}); "
                          f"{where_b} shows {money(later.value, cur)} (step {later.step_number}). "
                          f"Difference {'+' if diff >= 0 else '-'}{money(abs(diff), cur)} ({pct:+.1f}%)."),
                recommendation="Ensure the price shown on the product page is the price charged in cart and checkout.",
                step_number=later.step_number, state_id=later.state_id, source="deterministic", verified=True,
                data={"entity": first.entity, "before": first.value, "after": later.value, "difference": diff,
                      "percent": round(pct, 1), "before_state": first.state_id, "after_state": later.state_id,
                      "before_context": first.context, "after_context": later.context,
                      "before_step": first.step_number, "after_step": later.step_number, "currency": cur},
            ))
    return findings


def facts_summary(facts: list[PageFact]) -> str:
    if not facts:
        return "(none yet)"
    return "\n".join(f"- step {f.step_number} [{f.context}] {f.kind}: {f.entity} = {money(f.value, f.currency)}" for f in facts[-12:])
