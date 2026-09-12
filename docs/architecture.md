# RAJIH architecture

## Scope

RAJIH is an inspectable orchestration runtime. It can use a ChatGPT-authenticated Codex CLI, call OpenRouter, OpenAI, Anthropic, Gemini, or DeepSeek directly, or use an external coding-agent environment. Workflow state remains local under `.rajih/`.

```text
Human
  ↕
Orchestrator ──────── State store / audit log
  ├─ Scout           public facts and prior art
  ├─ Ideator A       grounded path, isolated
  ├─ Ideator B       transformational path, isolated
  ├─ Ideator C       demo-first path, isolated
  ├─ Critic          adversarial weaknesses
  └─ Jury            rubric scoring, not final novelty authority
```

Specialists do not communicate directly. Their outputs return to the orchestrator through explicit contracts. This hub-and-spoke topology makes provenance, routing, and termination easier to audit.

In direct mode, Scout, Ideator, Critic, and Jury may each use a different provider and model. The orchestrator remains deterministic application code and records the role-to-model mapping with the run.

## State machine

| State | Exit evidence | Next actor |
|---|---|---|
| UNDERSTAND | challenge, track, criteria, team, constraints classified | Scout or Human |
| RESEARCH | official rules and material public gaps searched | Human only for private gaps |
| CLARIFY_BRIEF | one high-value private or team-specific gap resolved | Ideators |
| DIVERGE | independent candidates exist from configured personas | Critic |
| CRITIQUE | each finalist has falsifiable risks | Ideator |
| REFINE | revisions preserve `parent_id` | Scout |
| VERIFY | prior-art search and evidence coverage recorded | Jury |
| CONVERGE | blind rubric scores and rank uncertainty computed | Human or Orchestrator |
| HUMAN_GATE | a close consequential choice resolved by the human | Orchestrator |
| DECIDE | decision and rationale persisted | Orchestrator |
| DONE | invariants pass | none |

## Observable uncertainty

Reference implementation uses three inspectable signals:

1. Intake missingness: missing required brief fields divided by five.
2. Evidence coverage: finalists with at least one sourced, access-stamped candidate record divided by finalist count.
3. Winner margin: difference between the two highest mean rubric scores.

These are conservative defaults, not universal thresholds. Operators should tune them for their workflow and record any changes in the run log.

## Invariants

- Idea IDs are unique and revisions reference an existing parent.
- No final decision exists without at least one candidate.
- No novelty claim is `verified` solely from model judgment.
- External evidence retains its source and access metadata.
- Runtime configuration, routing decisions, and evidence snapshots are recorded for each run.
- Demo results remain labeled synthetic.

## Extension boundary

Direct provider integrations sit behind the `AgentBackend` protocol. Keep provider-specific credentials and configuration outside the repository. Persist the actual provider and model snapshot in each run so results remain interpretable when models change.
