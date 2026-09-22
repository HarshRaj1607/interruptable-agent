"""Gemini client wrapper: text intent/slot extraction, native audio calls,
vision calls for video frames, and Gemini Embedding 2 calls. Every call is
async and wrapped in a ~1.5s timeout with a deterministic fallback into
fallback.py on timeout or error.

Owner: Person C.

Locked decisions this module must respect:
- Audio: raw MP3 sent directly to a multimodal Gemini call for
  transcription + intent in one shot (no local Whisper step). On failure,
  emit a clarification_request rather than guessing.
- Image embedding is a bonus checkpoint only: omit the field if the call
  errors, never fake a value.
- No speculative tool calls on partial/mid-turn text — this module may
  start parsing eagerly on partial text so slot-filling is warm by
  end_of_turn, but callers must not fire a tool_call before end_of_turn.
"""

from __future__ import annotations

import asyncio
from typing import Any

from . import fallback

GEMINI_TIMEOUT_SECONDS = 1.5


async def _with_timeout(coro, fallback_value: Any):
    try:
        return await asyncio.wait_for(coro, timeout=GEMINI_TIMEOUT_SECONDS)
    except (asyncio.TimeoutError, Exception):
        return fallback_value


async def extract_intent_and_slots(text: str, expected_slots: list[str]) -> dict[str, Any]:
    """Gemini text call for intent + slot extraction from buffered
    end_of_turn text. Falls back to fallback.extract_slots on timeout/error.
    """

    async def _call() -> dict[str, Any]:
        # TODO: actual Gemini text-generation call.
        raise NotImplementedError

    return await _with_timeout(_call(), {"intent": None, "slots": fallback.extract_slots(text, expected_slots)})


async def transcribe_and_extract_audio(audio_bytes: bytes) -> dict[str, Any] | None:
    """Raw MP3 -> multimodal Gemini call -> transcription + intent in one
    shot. Returns None on failure so the caller emits a
    clarification_request instead of guessing.
    """

    async def _call() -> dict[str, Any]:
        # TODO: actual Gemini native-audio call.
        raise NotImplementedError

    return await _with_timeout(_call(), None)


async def interpret_video_frame(frame_bytes: bytes, context: dict[str, Any]) -> dict[str, Any] | None:
    """Gemini vision call: identify what's being referred to in a
    video_frame (e.g. port type)."""

    async def _call() -> dict[str, Any]:
        # TODO: actual Gemini vision call.
        raise NotImplementedError

    return await _with_timeout(_call(), None)


async def embed_image(frame_bytes: bytes) -> list[float] | None:
    """Gemini Embedding 2 call, run in parallel with the vision-reasoning
    call. Bonus checkpoint only — returns None (field omitted) on error,
    never a fabricated vector.
    """

    async def _call() -> list[float]:
        # TODO: actual Gemini Embedding 2 call.
        raise NotImplementedError

    return await _with_timeout(_call(), None)
