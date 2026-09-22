"""Fast path: pure rule-based/templated reactions, zero LLM calls, zero
network I/O. Must produce a spoken action within 800ms of end-of-turn or
an interruption for full credit, degrading to zero credit at 2500ms — so
nothing in this module may block or await network/IO.

Owner: Person B.
"""

from __future__ import annotations

import re
from typing import Any

from .coordination import AgentState

FILLER_BUDGET = 4

# Cycled (never repeated verbatim) when no content-aware phrase can be
# built from the turn text alone.
_GENERIC_FILLERS = [
    "One moment...",
    "Let me look into that.",
    "Working on it now.",
    "Just a second...",
]

_TOPIC_KEYWORDS = {
    "book_flight": ("flight", "fly", "flights", "book a"),
    "cancel_booking": ("cancel",),
    "lookup_manual": ("manual", "how do i", "how to", "port", "connect"),
    "create_support_ticket": ("ticket", "broken", "support"),
}
_TOPIC_FILLERS = {
    "book_flight": "Looking up flights for you...",
    "cancel_booking": "One moment, pulling up that booking...",
    "lookup_manual": "Checking the manual...",
    "create_support_ticket": "Let me open a ticket for that...",
}

_CITY_CANON = {
    "boston": "Boston", "bos": "Boston",
    "new york": "New York", "nyc": "New York",
    "chicago": "Chicago", "denver": "Denver",
    "seattle": "Seattle", "miami": "Miami", "austin": "Austin",
}
_CITY_PATTERN = re.compile(
    r"\b(" + "|".join(sorted(_CITY_CANON, key=len, reverse=True)) + r")\b", re.I)


def sniff_city(text: str) -> str | None:
    """Best-effort, last-mention-wins city extraction — cheap enough to
    run synchronously on every turn/interruption."""
    matches = _CITY_PATTERN.findall(text)
    return _CITY_CANON[matches[-1].lower()] if matches else None


def sniff_topic(text: str) -> str | None:
    low = text.lower()
    for topic, keywords in _TOPIC_KEYWORDS.items():
        if any(kw in low for kw in keywords):
            return topic
    return None


def make_filler(state: AgentState, text: str = "") -> dict[str, Any] | None:
    """Content-aware where a quick keyword/city sniff on `text` succeeds,
    otherwise a varied generic phrase. Returns None once the scenario's
    filler budget is already spent, so we don't chase latency credit at
    the cost of a safety deduction.
    """
    if state.fillers_sent >= FILLER_BUDGET:
        return None

    city = sniff_city(text)
    if city:
        content = f"Looking into {city}..."
    else:
        topic = sniff_topic(text)
        content = _TOPIC_FILLERS.get(topic) or _GENERIC_FILLERS[state.fillers_sent % len(_GENERIC_FILLERS)]

    return {"action": "filler_speech", "payload": {"text": content}}


def make_clarification(missing_slot: str) -> dict[str, Any]:
    return {
        "action": "clarification_request",
        "payload": {"text": f"Could you clarify the {missing_slot}?"},
    }
