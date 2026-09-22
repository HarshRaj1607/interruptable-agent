"""Deterministic regex/keyword slot extraction and templated responses,
used when a Gemini call in slow_path times out or errors.

Owner: Person B. Zero network I/O — must always return *something*, even
if it's an empty/low-confidence result, so the caller can fall back to a
clarification_request rather than guessing.
"""

from __future__ import annotations

import re
from typing import Any


def extract_slots(text: str, expected_slots: list[str]) -> dict[str, Any]:
    """Best-effort regex/keyword extraction of `expected_slots` from raw
    user text. Returns only slots it's confident about — callers should
    treat missing keys as "not extracted", not as null values.
    """
    found: dict[str, Any] = {}
    for slot in expected_slots:
        # TODO: per-slot regex/keyword rules live here (e.g. city names,
        # dates, yes/no confirmations). Keep these narrow and deterministic.
        pass
    return found


def templated_response(intent: str | None, slots: dict[str, Any]) -> str:
    """Deterministic templated phrasing used in place of a Gemini-authored
    response when the slow path is unavailable.
    """
    if not intent:
        return "Sorry, could you repeat that?"
    return f"Got it — working on {intent} with what I have so far."
