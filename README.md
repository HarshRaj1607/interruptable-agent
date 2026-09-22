# Interruptible Agents Hackathon

Implementation plan: [docs/Interruptible Agents Hackathon — Implementation Plan.pdf](docs/Interruptible%20Agents%20Hackathon%20%E2%80%94%20Implementation%20Plan.pdf)

## Layout

```
agent/
  agent.py          # ParticipantAgent — event loop, wires everything below   (Person A)
  coordination.py   # AgentState, plan_version, pending_calls, call_id, dup-write guard (Person A)
  fast_path.py       # rule-based fillers/acks/clarifications, no I/O          (Person B)
  tool_router.py     # schema-driven arg builder from tool_manifest           (Person B)
  fallback.py        # deterministic regex/keyword extraction                 (Person B)
  slow_path.py        # Gemini client wrapper: text/audio/vision/embedding    (Person C)
submission.yaml
```

`harness/`, `scenarios/`, `run_local.py`, `eval_submission.py` are provided by the
hackathon kit and are **not yet in this repo** — dropping these in, unchanged, is the
first task before any further logic-writing, since nobody can self-test locally without
them.

## Protocol notes (from kit review)

- `ParticipantAgent(in_queue, out_queue)` — queues are constructor args, stored on
  `self`; `run()` takes no arguments.
- Every action emitted is `{"action": "<type>", "payload": {...}}`; `final_response`
  additionally carries a top-level `state_snapshot`.
- `tool_manifest` events carry the manifest at `event["payload"]["tools"]`.
- `submission.yaml` uses `team` and `python`, not `team_name`/`python_version`.

## Status

Module interfaces are scaffolded per the plan and corrected against the kit's actual
protocol (constructor/run signature, action envelope, manifest location); logic bodies
are `TODO`/`NotImplementedError` stubs. See the plan's section 5 (implementation
checklist) for build order.
