"""Schema-driven tool-call argument builder, generic to unseen tools —
reads whatever tool_manifest the harness sends (pub_09: no tool-specific
hardcoding) and builds args from extracted slots.

Owner: Person B.
"""

from __future__ import annotations

from typing import Any


def build_args(tool_schema: dict[str, Any], slots: dict[str, Any]) -> dict[str, Any]:
    """Maps known slots onto a tool's declared parameter schema. Must
    handle required fields, enums, nested objects, and arrays generically
    — no per-tool special-casing, since pub_09 exercises a tool never seen
    before via its manifest alone.
    """
    params = tool_schema.get("parameters", {}).get("properties", {})
    args: dict[str, Any] = {}
    for name in params:
        if name in slots:
            args[name] = slots[name]
    return args


def missing_required(tool_schema: dict[str, Any], args: dict[str, Any]) -> list[str]:
    required = tool_schema.get("parameters", {}).get("required", [])
    return [name for name in required if name not in args]
