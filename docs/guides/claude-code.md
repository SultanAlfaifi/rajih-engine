# Run RAJIH with Claude Code

Verified against Anthropic's official Claude Code setup and CLI references on 2026-09-10. Claude Code starts with `claude`, supports project instructions through `CLAUDE.md`, and supports project subagents under `.claude/agents/` in current releases.

Official references: [Claude Code setup](https://docs.anthropic.com/en/docs/claude-code/getting-started), [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code/cli-usage), and [custom subagents](https://docs.anthropic.com/en/docs/claude-code/sub-agents).

## Setup

1. Install Claude Code with the method in Anthropic's current setup guide and run `claude doctor`.
2. Enter the repository root and run `claude`.
3. Confirm Claude read `CLAUDE.md`, which imports the shared RAJIH instructions.
4. Review tool permissions before exposing private team or hackathon material.

## Start a run

```powershell
rajih init examples/brief.json
claude
```

Prompt:

```text
Run RAJIH for the newest run under .rajih/runs. Use the project subagents sparsely. Keep the ideators isolated in their first round, use scout for verifiable public facts and prior art, use critic for falsifiable risks, and give anonymized finalists to jury. The main session alone merges state. Stop for the user when a private information gap or close high-impact choice cannot be resolved by research.
```

For automation, Claude Code documents print mode (`claude -p`) and `--output-format json`, but an interactive session is recommended for RAJIH's human gates.

## Verify

```powershell
rajih validate <run-id>
python -m unittest discover -s tests -v
```

If current Claude Code rejects a subagent frontmatter field, consult the latest subagent documentation and update only that adapter; the shared RAJIH state schema remains unchanged.
