# Interruptible Agents Hackathon

Implementation plan: [docs/Interruptible Agents Hackathon — Implementation Plan.pdf](docs/Interruptible%20Agents%20Hackathon%20%E2%80%94%20Implementation%20Plan.pdf)
Kit walkthrough: [WALKTHROUGH.md](WALKTHROUGH.md) · protocol reference: [docs/PROTOCOL.md](docs/PROTOCOL.md)

## Layout

```
agent/
  agent.py          # ParticipantAgent (our submission) + BaselineAgent (kit reference)  (Person A)
  coordination.py   # AgentState, plan_version, pending_calls, call_id, dup-write guard   (Person A)
  fast_path.py       # rule-based fillers/acks/clarifications, no I/O                     (Person B)
  tool_router.py     # schema-driven arg builder from tool_manifest                       (Person B)
  fallback.py        # deterministic regex/keyword extraction                             (Person B)
  slow_path.py        # Gemini client wrapper: text/audio/vision/embedding                (Person C)
harness/  scenarios/  audio/  frames/  run_local.py  eval_submission.py   # kit, unchanged
submission.yaml
```

## Quickstart

```bash
# one scenario, live trace, our agent
python run_local.py --scenario scenarios/pub_02_text_interrupt.json --agent agent.agent:ParticipantAgent

# all public scenarios, fast
python run_local.py --all --time-scale 8 --quiet --agent agent.agent:ParticipantAgent

# same, but the kit's minimal reference agent (~52/100 on the public set) for comparison
python run_local.py --all --time-scale 8 --quiet

# dry-run the official submission evaluator against this package
python eval_submission.py . --time-scale 8 --reps 1
```

Current state: module interfaces are wired and verified end-to-end through the real
harness (no crashes, no `protocol_error`s) — but the actual decision logic (intent/slot
extraction, tool routing, Gemini calls) is still `TODO` stubs, so scores are low. That's
the next phase of work, per the plan's section 5 implementation checklist.

## Protocol notes (verified against the kit)

- `ParticipantAgent(in_queue, out_queue)` — queues are constructor args, stored on
  `self`; `run()` takes no arguments; optional `async def setup()` runs off the clock.
- Every action is `{"action": "<type>", "payload": {...}}`; `final_response`
  additionally carries a top-level `state_snapshot` = `{"intent": ..., "slots": {...}}`
  (exactly those two keys — this is the convention the scorer checks against).
- `tool_manifest` events carry the manifest at `event["payload"]["tools"]`, a dict keyed
  by tool name, each value `{"kind", "delay_range_ms", "description", "args": {...},
  "default_result": {...}}` — flat `args` map, not an OpenAI-style
  `parameters.properties` schema.
- `submission.yaml` uses `team` and `python`, not `team_name`/`python_version`.

## Before submitting

Run [docs/SUBMISSION.md](docs/SUBMISSION.md)'s checklist — in particular
`python eval_submission.py . --reps 3` (real time, official procedure) and confirm no
secrets are committed (`SECRET_*` env var names only, values registered on the event
portal).
