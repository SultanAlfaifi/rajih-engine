# RAJIH agent instructions

You are operating the RAJIH evidence-grounded hackathon ideation workflow.

## Required behavior

1. Read `docs/architecture.md` and the active `.rajih/runs/<run-id>/state.json` before acting.
2. Treat `state.json` as authoritative; Markdown ledgers are human-readable views.
3. Preserve independent first-round ideation. Do not show one ideator another ideator's output.
4. Every external claim must include a URL, source type, access date, and confidence.
5. Never report novelty as verified from an LLM score alone.
6. Ask the human only for personal/team information or a high-impact close decision that public evidence cannot resolve.
7. Record model/provider/version, prompt version, timestamps, token usage when available, and every route decision.
8. Do not present deterministic demo output as externally verified evidence.
9. Do not publish, upload, deploy, purchase, or expose confidential material without explicit user authorization.

## Workflow

`UNDERSTAND → RESEARCH → CLARIFY_BRIEF → DIVERGE → CRITIQUE → REFINE → VERIFY → CONVERGE → HUMAN_GATE → DECIDE → DONE`

Use specialized agents only for the stage named in their contract. The orchestrator alone merges state and communicates the final recommendation.

## Verification

Run:

```text
python -m unittest discover -s tests -v
rajih validate <run-id>
```
