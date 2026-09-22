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
hackathon kit and are not yet in this repo — drop them in unchanged once available.

## Status

Module interfaces are scaffolded per the plan; logic bodies are `TODO`/`NotImplementedError`
stubs. See the plan's section 5 (implementation checklist) for build order.
