# Run RAJIH with Codex

Verified from official OpenAI documentation on 2026-09-10. Codex reads repository `AGENTS.md` before work, supports project custom agents under `.codex/agents/`, and can run subagent workflows when requested.

Official references: [Codex CLI](https://developers.openai.com/codex/cli), [AGENTS.md instructions](https://developers.openai.com/codex/guides/agents-md), and [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).

## Setup

1. Install and sign in to Codex using the current official CLI instructions.
2. Enter the repository root and run `codex`.
3. Use `/status` to confirm the repository root and `/permissions` to select boundaries appropriate for your data.
4. Ask Codex to summarize the active `AGENTS.md` instructions. The repository also includes project-scoped `scout`, `ideator`, `critic`, and `jury` custom agents.

## Start a run

```powershell
rajih init examples/brief.json
codex --search
```

Prompt:

```text
Run RAJIH for the newest run in .rajih/runs. Follow AGENTS.md and docs/architecture.md. Delegate the three first-round ideation perspectives as independent subagent tasks and wait for all of them. Use scout for missing public evidence and prior art, critic for adversarial review, and jury only on anonymized finalists. The root agent alone may merge state. Record sources, access dates, model metadata, costs when available, route decisions, and the final human gate.
```

In Codex CLI, `/agent` can inspect active agent threads. Subagent work consumes additional tokens, so use the sparse route instead of launching every role automatically.

## Verify

```powershell
python -m unittest discover -s tests -v
rajih validate <run-id>
git diff --check
```

Model selection remains a user/runtime choice. Important run records should include the actual model and reasoning setting rather than assuming a model alias is stable.

