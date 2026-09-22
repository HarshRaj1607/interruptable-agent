"""Schema-driven tool-call argument builder, generic to unseen tools —
reads whatever tool_manifest the harness sends (pub_09: no tool-specific
hardcoding) and builds args from extracted slots.

Owner: Person B.

Tool schema shape (docs/TOOLS.md, harness/mock_env.py TOOL_REGISTRY):

    {"kind": "read_only" | "state_modifying",
     "delay_range_ms": [lo, hi],
     "description": "...",
     "args": {
         "<name>": {"type": "string"|"number"|"boolean"|"array"|"object",
                    "required": bool,
                    "enum": [...],            # optional, on strings
                    "items": "number", ...    # optional, on arrays
                    "properties": {...}},     # optional, on nested objects
         ...
     },
     "default_result": {...}}

This is a flat map keyed by arg name — not an OpenAI-style
`parameters.properties` schema.
"""

from __future__ import annotations

from typing import Any


def build_args(tool_schema: dict[str, Any], slots: dict[str, Any]) -> dict[str, Any]:
    """Maps known slots onto a tool's declared args by name. Handles
    required/enum/nested-object/array args generically since they're all
    just entries in `args` — no per-tool special-casing, since pub_09
    exercises a tool never seen before via its manifest alone.
    """
    arg_names = tool_schema.get("args", {})
    return {name: slots[name] for name in arg_names if name in slots}


def missing_required(tool_schema: dict[str, Any], args: dict[str, Any]) -> list[str]:
    required = [name for name, spec in tool_schema.get("args", {}).items() if spec.get("required")]
    return [name for name in required if name not in args]
