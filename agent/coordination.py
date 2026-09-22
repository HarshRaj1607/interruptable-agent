"""Coordination layer: AgentState, call_id tracking, plan versioning,
interruption/re-plan handling, and the duplicate-write guard.

Owner: Person A. This is the integration point everything else plugs into,
so its interfaces should stay stable even before the logic is fully correct.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CallStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class PendingCall:
    tool: str
    args: dict[str, Any]
    plan_version: int
    status: CallStatus = CallStatus.PENDING


@dataclass
class AgentState:
    """Single shared state object passed into fast_path, slow_path, and
    tool_router. No hidden global state — each module should be unit
    testable against a mocked instance of this.
    """

    slots: dict[str, Any] = field(default_factory=dict)
    intent: str | None = None
    plan_version: int = 0
    pending_calls: dict[str, PendingCall] = field(default_factory=dict)
    manifest: dict[str, Any] | None = None

    _call_id_counter: itertools.count = field(default_factory=itertools.count, repr=False)

    def next_call_id(self) -> str:
        return f"call_{next(self._call_id_counter)}"

    def has_duplicate(self, tool: str, args: dict[str, Any]) -> bool:
        """True if a pending or completed call already exists for this
        tool+args combination, per the idempotency rule: never re-emit a
        state-modifying call for an intent that already has one in flight
        or done with the same args.
        """
        return any(
            call.tool == tool and call.args == args and call.status != CallStatus.CANCELLED
            for call in self.pending_calls.values()
        )

    def register_call(self, tool: str, args: dict[str, Any]) -> str:
        call_id = self.next_call_id()
        self.pending_calls[call_id] = PendingCall(tool=tool, args=args, plan_version=self.plan_version)
        return call_id

    def cancel_stale_calls(self) -> list[str]:
        """Bump the plan version and mark every still-pending call from an
        older plan version as cancelled. Returns the cancelled call_ids so
        the caller can emit cancel_tool actions for each.
        """
        stale_ids = [
            call_id
            for call_id, call in self.pending_calls.items()
            if call.status == CallStatus.PENDING and call.plan_version < self.plan_version
        ]
        for call_id in stale_ids:
            self.pending_calls[call_id].status = CallStatus.CANCELLED
        return stale_ids

    def bump_plan_version(self) -> int:
        self.plan_version += 1
        return self.plan_version

    def snapshot(self) -> dict[str, Any]:
        """state_snapshot attached to every final_response (and optionally
        other actions). Convention used by all ground truth (docs/PROTOCOL.md
        §2.5): exactly {"intent": <string>, "slots": {...}} — no extra keys.
        """
        return {"intent": self.intent, "slots": dict(self.slots)}


def diff_slots(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Returns the subset of `new` whose values differ from `old`, used to
    decide what changed across a re-plan (interruption / repaired value).
    """
    return {k: v for k, v in new.items() if old.get(k) != v}
