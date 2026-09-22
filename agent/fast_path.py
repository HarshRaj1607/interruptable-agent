"""Fast path: pure rule-based/templated reactions, zero LLM calls, zero
network I/O. Must produce a spoken action within 800ms of end-of-turn or
an interruption for full credit, degrading to zero credit at 2500ms — so
nothing in this module may block or await network/IO.

Owner: Person B.
"""

from __future__ import annotations

from typing import Any

from .coordination import AgentState


def make_filler(state: AgentState) -> dict[str, Any] | None:
    """Template string filled with whatever slot value is already known
    synchronously, e.g. "Looking into {city}...". Returns None if there's
    nothing useful to say yet (don't force a filler with no content).
    """
    # TODO: content-aware filler templates, slot-filled from state.slots.
    return None


def make_clarification(missing_slot: str) -> dict[str, Any]:
    return {
        "action": "clarification_request",
        "payload": {"text": f"Could you clarify the {missing_slot}?"},
    }


def make_ack() -> dict[str, Any]:
    return {"action": "filler_speech", "payload": {"text": "One moment..."}}
