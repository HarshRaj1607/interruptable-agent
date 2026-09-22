"""ParticipantAgent: the event loop only. Wires coordination, fast_path,
slow_path, and tool_router together. This is the entry point declared in
submission.yaml.

Owner: Person A. Everyone else's code plugs into this, so its interfaces
(event dispatch, AgentState shape) should be scaffolded first, even before
fully correct.
"""

from __future__ import annotations

import asyncio
from typing import Any

from . import fast_path, tool_router
from .coordination import AgentState

SCENARIO_END_GRACE_SECONDS = 6


class ParticipantAgent:
    def __init__(self) -> None:
        self.state = AgentState()

    async def run(self, in_queue: asyncio.Queue, out_queue: asyncio.Queue) -> None:
        """Reads events off in_queue, dispatches by event_type, writes
        actions to out_queue. No synchronous/blocking calls here — all I/O
        goes through slow_path's async client or asyncio.to_thread.
        """
        while True:
            event = await in_queue.get()
            event_type = event.get("event_type")

            if event_type == "tool_manifest":
                self._on_tool_manifest(event)
            elif event_type == "user_speech_chunk":
                await self._on_user_speech_chunk(event, out_queue)
            elif event_type == "user_audio_chunk":
                await self._on_user_audio_chunk(event, out_queue)
            elif event_type == "video_frame":
                await self._on_video_frame(event, out_queue)
            elif event_type == "interruption":
                await self._on_interruption(event, out_queue)
            elif event_type == "tool_result":
                await self._on_tool_result(event, out_queue)
            elif event_type == "scenario_end":
                await self._on_scenario_end(event, out_queue)
                break

    def _on_tool_manifest(self, event: dict[str, Any]) -> None:
        self.state.manifest = event.get("manifest")

    async def _on_user_speech_chunk(self, event: dict[str, Any], out_queue: asyncio.Queue) -> None:
        # TODO: buffer partial text; on end_of_turn, call slow_path to
        # extract intent/slots, then route through tool_router.
        filler = fast_path.make_filler(self.state)
        if filler:
            await out_queue.put(filler)

    async def _on_user_audio_chunk(self, event: dict[str, Any], out_queue: asyncio.Queue) -> None:
        # TODO: buffer audio; on end_of_turn, call slow_path.transcribe_and_extract_audio.
        pass

    async def _on_video_frame(self, event: dict[str, Any], out_queue: asyncio.Queue) -> None:
        # TODO: call slow_path.interpret_video_frame + embed_image in parallel.
        pass

    async def _on_interruption(self, event: dict[str, Any], out_queue: asyncio.Queue) -> None:
        """Cancel stale in-flight calls, bump plan_version, diff slots,
        and emit an explicit cancel_tool for every cancelled call within
        the 800ms grace period — never a silent discard.
        """
        self.state.bump_plan_version()
        for call_id in self.state.cancel_stale_calls():
            await out_queue.put({"type": "cancel_tool", "call_id": call_id})

    async def _on_tool_result(self, event: dict[str, Any], out_queue: asyncio.Queue) -> None:
        # TODO: mark the corresponding pending_call completed, fold result
        # into state, decide whether a final_response is ready.
        pass

    async def _on_scenario_end(self, event: dict[str, Any], out_queue: asyncio.Queue) -> None:
        """Finish pending work within the grace period — never leave a
        call abandoned.
        """
        await out_queue.put({"type": "final_response", "state_snapshot": self.state.snapshot()})


def main() -> None:
    raise NotImplementedError("Wired up by the harness via run_local.py / eval_submission.py")


if __name__ == "__main__":
    main()
