"""Semantic UI-state fingerprinting (pure functions, unit tested).

A state is identified by canonical route + heading + open dialog + visible semantic controls + key visible text,
NOT by URL alone (an open modal and a closed modal share a URL).
"""
from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit

NOISE_PARAMS = re.compile(r"^(utm_.*|fbclid|gclid|sessionid|session|sid|ts|timestamp|_)$", re.I)
_WS = re.compile(r"\s+")
_LONG_DIGITS = re.compile(r"\d{7,}")  # timestamps / random ids
_HEXISH = re.compile(r"\b[0-9a-f]{12,}\b", re.I)
_TIME = re.compile(r"\b\d{1,2}:\d{2}(:\d{2})?\b")


def canonical_route(url: str) -> str:
    """Path + hash route with noisy query params removed and params sorted."""
    parts = urlsplit(url)
    frag = parts.fragment or ""
    frag_path, _, frag_query = frag.partition("?")

    def clean(q: str) -> str:
        kept = sorted((k, v) for k, v in parse_qsl(q, keep_blank_values=True) if not NOISE_PARAMS.match(k))
        return urlencode(kept)

    route = parts.path or "/"
    q = clean(parts.query)
    if q:
        route += "?" + q
    if frag_path or frag_query:
        route += "#" + (frag_path or "/")
        fq = clean(frag_query)
        if fq:
            route += "?" + fq
    return route


def normalize_text(text: str) -> str:
    text = text.lower()
    text = _LONG_DIGITS.sub("#", text)
    text = _HEXISH.sub("#", text)
    text = _TIME.sub("#", text)
    return _WS.sub(" ", text).strip()


def state_fingerprint(url: str, heading: str, dialog_name: str, controls: list[str], visible_text: str) -> str:
    # Include origin so identical routes on separate target sites cannot merge into one journey state.
    parts = urlsplit(url)
    origin = f"{parts.scheme}://{parts.netloc}".lower()
    material = "\n".join([
        origin,
        canonical_route(url),
        normalize_text(heading),
        "dialog:" + normalize_text(dialog_name),
        "|".join(sorted(normalize_text(c) for c in controls)),
        normalize_text(visible_text)[:600],
    ])
    return hashlib.sha256(material.encode()).hexdigest()[:12]
