# Run RAJIH with OpenCode

Verified against the official OpenCode agent documentation on 2026-09-10: project agents are discovered under `.opencode/agents/`, a primary agent can invoke subagents, and task permissions can restrict which agents it may call.

Official references: [OpenCode agents](https://opencode.ai/docs/agents) and [OpenCode introduction](https://opencode.ai/en/docs).

## Setup

1. Install OpenCode using a method listed in its current official introduction.
2. Open this repository in a terminal and run `opencode`.
3. Configure your desired providers through OpenCode. RAJIH deliberately omits hard-coded provider/model names because availability and identifiers change.
4. Confirm the primary agent is `rajih`; use Tab or the configured switch-agent key if needed.

## Start a run

First initialize durable state:

```powershell
rajih init examples/brief.json
```

Then tell OpenCode:

```text
Run RAJIH for the newest run under .rajih/runs. Follow AGENTS.md and docs/architecture.md. Use scout first only for missing public facts. Run the three ideator agents independently without sharing their first-round outputs. Then use critic, verify prior art, anonymize finalists for jury scoring, and stop at a human decision gate if the winner margin is below the configured threshold. Persist every route decision and citation.
```

## Verification

Inspect child sessions before accepting the merge. Then run:

```powershell
rajih validate <run-id>
```

OpenCode tool names and configuration formats can change. If an agent is not discovered, compare the files with the current official agents page instead of silently falling back to one general agent.

