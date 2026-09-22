"""ParticipantAgent: the event loop only. Wires coordination, fast_path,
slow_path, and tool_router together. This is the entry point declared in
submission.yaml.

Owner: Person A. Everyone else's code plugs into this, so its interfaces
(event dispatch, AgentState shape) should be scaffolded first, even before
fully correct.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, List, Optional

from . import fallback, fast_path, tool_router
from .coordination import AgentState

SCENARIO_END_GRACE_SECONDS = 6


class ParticipantAgent:
    def __init__(self, in_queue: asyncio.Queue, out_queue: asyncio.Queue) -> None:
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.state = AgentState()

    async def setup(self) -> None:
        """Called once before run(), off the clock — model/client init
        that shouldn't count against per-scenario latency goes here.
        """

    async def run(self) -> None:
        """Reads events off self.in_queue, dispatches by event_type,
        writes actions to self.out_queue. No synchronous/blocking calls
        here — all I/O goes through slow_path's async client or
        asyncio.to_thread.
        """
        while True:
            event = await self.in_queue.get()
            event_type = event.get("event_type")

            if event_type == "tool_manifest":
                self._on_tool_manifest(event)
            elif event_type == "user_speech_chunk":
                await self._on_user_speech_chunk(event)
            elif event_type == "user_audio_chunk":
                await self._on_user_audio_chunk(event)
            elif event_type == "video_frame":
                await self._on_video_frame(event)
            elif event_type == "interruption":
                await self._on_interruption(event)
            elif event_type == "tool_result":
                await self._on_tool_result(event)
            elif event_type == "scenario_end":
                await self._on_scenario_end(event)
                break

    async def _emit(self, action: str, payload: dict[str, Any] | None = None, **extra: Any) -> None:
        """{"action": "<type>", "payload": {...}} envelope, plus any
        top-level extras (e.g. final_response's state_snapshot).
        """
        await self.out_queue.put({"action": action, "payload": payload or {}, **extra})

    async def _call_tool(self, api_name: str, args: dict[str, Any]) -> str | None:
        """Registers and emits a tool_call, respecting the duplicate-write
        guard. Returns the call_id, or None if the call was suppressed as
        a duplicate.
        """
        if self.state.has_duplicate(api_name, args):
            return None
        call_id = self.state.register_call(api_name, args)
        await self._emit("tool_call", {"call_id": call_id, "api_name": api_name, "args": args})
        return call_id

    def _on_tool_manifest(self, event: dict[str, Any]) -> None:
        self.state.manifest = event.get("payload", {}).get("tools")

    async def _on_user_speech_chunk(self, event: dict[str, Any]) -> None:
        # TODO: buffer partial text; on end_of_turn, call slow_path to
        # extract intent/slots, then route through tool_router.
        filler = fast_path.make_filler(self.state)
        if filler:
            await self._emit(filler["action"], filler["payload"])

    async def _on_user_audio_chunk(self, event: dict[str, Any]) -> None:
        # TODO: buffer audio; on end_of_turn, call slow_path.transcribe_and_extract_audio.
        pass

    async def _on_video_frame(self, event: dict[str, Any]) -> None:
        # TODO: call slow_path.interpret_video_frame + embed_image in parallel.
        pass

    async def _on_interruption(self, event: dict[str, Any]) -> None:
        """Cancel stale in-flight calls, bump plan_version, diff slots,
        and emit an explicit cancel_tool for every cancelled call within
        the 800ms grace period — never a silent discard.
        """
        self.state.bump_plan_version()
        for call_id in self.state.cancel_stale_calls():
            await self._emit("cancel_tool", {"call_id": call_id})

    async def _on_tool_result(self, event: dict[str, Any]) -> None:
        # TODO: mark the corresponding pending_call completed, fold result
        # into state, decide whether a final_response is ready.
        pass

    async def _on_scenario_end(self, event: dict[str, Any]) -> None:
        """Finish pending work within the grace period — never leave a
        call abandoned.
        """
        text = fallback.templated_response(self.state.intent, self.state.slots)
        await self._emit("final_response", {"text": text}, state_snapshot=self.state.snapshot())


CITY_CANON = {
    "boston": "Boston", "bos": "Boston",
    "new york": "New York", "nyc": "New York",
    "chicago": "Chicago", "denver": "Denver",
    "seattle": "Seattle", "miami": "Miami", "austin": "Austin",
}
_CITY_PATTERN = re.compile(
    r"\b(" + "|".join(sorted(CITY_CANON, key=len, reverse=True)) + r")\b", re.I)


class BaselineAgent:
    """Minimal reference agent from the hackathon kit — handles only
    pub_01/pub_02 (single-city flight search + one interruption). Kept
    here as the `run_local.py` default (`--agent agent.agent:BaselineAgent`)
    so we always have a ~57/100 baseline to beat. Not our submission —
    ParticipantAgent above is the real entry point.
    """

    def __init__(self, in_queue: asyncio.Queue, out_queue: asyncio.Queue):
        self.in_q = in_queue
        self.out_q = out_queue
        self.buffer: List[str] = []
        self.state: Dict[str, Any] = {"intent": None, "slots": {}}
        self.call_seq = 0
        self.pending: Dict[str, Dict] = {}
        self.tools: Dict[str, Any] = {}

    async def emit(self, action: str, payload: Dict[str, Any]):
        msg: Dict[str, Any] = {"action": action, "payload": payload}
        if action == "final_response":
            msg["state_snapshot"] = {"intent": self.state["intent"],
                                     "slots": dict(self.state["slots"])}
        await self.out_q.put(msg)

    async def call_tool(self, api_name: str, args: Dict[str, Any]) -> str:
        self.call_seq += 1
        call_id = f"c{self.call_seq}"
        self.pending[call_id] = {"api": api_name, "args": args}
        await self.emit("tool_call",
                        {"call_id": call_id, "api_name": api_name, "args": args})
        return call_id

    async def cancel_all_pending(self):
        for call_id in list(self.pending):
            await self.emit("cancel_tool", {"call_id": call_id})
            del self.pending[call_id]

    @staticmethod
    def find_city(text: str) -> Optional[str]:
        matches = _CITY_PATTERN.findall(text)
        return CITY_CANON[matches[-1].lower()] if matches else None

    async def run(self):
        while True:
            event = await self.in_q.get()
            etype = event.get("event_type")
            payload = event.get("payload", {})
            if etype == "tool_manifest":
                self.tools = payload.get("tools", {})
            elif etype == "user_speech_chunk":
                await self.on_user_text(payload.get("text", ""),
                                        payload.get("end_of_turn", False))
            elif etype == "interruption":
                await self.on_interruption(payload.get("text", ""))
            elif etype == "tool_result":
                await self.on_tool_result(payload)

    async def on_user_text(self, text: str, end_of_turn: bool):
        self.buffer.append(text)
        if not end_of_turn:
            return
        turn = " ".join(self.buffer).strip()
        self.buffer = []
        low = turn.lower()

        if any(w in low for w in ("flight", "fly", "flights")):
            city = self.find_city(low)
            if city is None:
                await self.emit("clarification_request",
                                {"text": "Sure — which city would you like to fly to?"})
                return
            self.state["intent"] = "book_flight"
            self.state["slots"]["destination"] = city
            await self.emit("filler_speech",
                            {"text": f"Looking up flights to {city} — one moment."})
            await self.call_tool("flight_search", {"destination": city})
            return

        self.state["intent"] = "chitchat"
        await self.emit("final_response",
                        {"text": "Hi! I can help you search for flights — "
                                 "just tell me where you want to fly."})

    async def on_interruption(self, text: str):
        new_city = self.find_city(text)
        await self.emit("filler_speech",
                        {"text": f"Got it — switching to {new_city}." if new_city
                                 else "Okay, one moment."})
        await self.cancel_all_pending()
        if new_city:
            self.state["intent"] = "book_flight"
            self.state["slots"]["destination"] = new_city
            await self.call_tool("flight_search", {"destination": new_city})

    async def on_tool_result(self, payload: Dict[str, Any]):
        call_id = payload.get("call_id", "")
        if self.pending.pop(call_id, None) is None:
            return
        result = payload.get("result", {})

        if payload.get("status") == "error":
            await self.emit("final_response",
                            {"text": "Sorry — I couldn't complete that right now."})
            return

        flights = result.get("flights", [])
        if not flights:
            await self.emit("final_response",
                            {"text": "I couldn't find any flights for that search."})
            return
        best = flights[0]
        self.state["slots"]["flight_id"] = best["flight_id"]
        await self.emit("final_response",
                        {"text": f"I found a flight to "
                                 f"{self.state['slots']['destination']}: "
                                 f"{best['flight_id']} departing {best['depart']} "
                                 f"for ${best['price_usd']}."})
