# Run RAJIH directly with a model provider

Direct mode does not require OpenCode, Codex, or Claude Code. It calls the selected provider over HTTPS and keeps RAJIH state files on your machine.

Supported adapters:

| Provider | API key variable | Optional model variable | Structured response mechanism |
|---|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `OPENAI_MODEL` | Responses API JSON Schema |
| Anthropic | `ANTHROPIC_API_KEY` | `ANTHROPIC_MODEL` | Messages API structured output |
| Gemini | `GEMINI_API_KEY` | `GEMINI_MODEL` | Generate Content JSON Schema |
| DeepSeek | `DEEPSEEK_API_KEY` | `DEEPSEEK_MODEL` | JSON Output plus local schema validation |

Official references: [OpenAI Responses](https://developers.openai.com/api/reference/cli/resources/responses/methods/create), [Anthropic Messages](https://platform.claude.com/docs/en/api/messages/create), [Gemini Generate Content](https://ai.google.dev/api/generate-content), and [DeepSeek JSON Output](https://api-docs.deepseek.com/guides/json_mode/).

## Requirements

- Python 3.11 or newer.
- An API key with access to the selected model.
- Sufficient provider budget for multiple model calls.

RAJIH does not create, purchase, or validate API keys.

## Run

OpenAI:

```powershell
$env:OPENAI_API_KEY = Read-Host "OpenAI API key"
rajih run examples/brief.json --provider openai --model "YOUR_MODEL_ID" --web-search
```

Anthropic:

```powershell
$env:ANTHROPIC_API_KEY = Read-Host "Anthropic API key"
rajih run examples/brief.json --provider anthropic --model "YOUR_MODEL_ID"
```

Gemini:

```powershell
$env:GEMINI_API_KEY = Read-Host "Gemini API key"
rajih run examples/brief.json --provider gemini --model "YOUR_MODEL_ID"
```

DeepSeek:

```powershell
$env:DEEPSEEK_API_KEY = Read-Host "DeepSeek API key"
rajih run examples/brief.json --provider deepseek --model "YOUR_MODEL_ID"
```

Model identifiers are deliberately not pinned because availability varies by account and changes over time. You may omit `--model` after setting the provider's model environment variable.

## Route roles across providers

The deterministic RAJIH orchestrator can route each specialist role to a different provider:

```powershell
rajih run examples/brief.json `
  --provider openai --model "OPENAI_MODEL_ID" `
  --jury-provider openai --jury-model "OPENAI_MODEL_ID" `
  --ideator-provider deepseek --ideator-model "DEEPSEEK_MODEL_ID" `
  --critic-provider anthropic --critic-model "ANTHROPIC_MODEL_ID" `
  --scout-provider gemini --scout-model "GEMINI_MODEL_ID"
```

Available role overrides are `--scout-provider`, `--ideator-provider`, `--critic-provider`, and `--jury-provider`, with corresponding `--<role>-model` flags. A role without an override inherits the default `--provider` and `--model`.

The orchestrator itself is deterministic Python code and does not consume a model call. Provider and model selection for every role is written to the run's `runtime` metadata.

Optional flags:

- `--ideas-per-persona N`: candidates per isolated ideator; default is 1.
- `--web-search`: OpenAI adapter only; permits the Scout request to use provider web search.
- `--timeout SECONDS`: per-request HTTP timeout; default is 120.
- `--base-url URL`: override the selected adapter's API base URL.

## Human gate

RAJIH automatically selects a clear scoring leader. When the finalist margin is below the configured threshold, the run stops without manufacturing a winner:

```powershell
rajih status <run-id>
rajih choose <run-id> IDEA-01 --reason "Best fit for the available team and deadline"
rajih validate <run-id>
```

## Privacy and cost

- OpenAI and Gemini direct requests set `store: false`. Other providers use the documented request behavior of their APIs.
- Do not place keys in JSON briefs, command arguments, committed files, or run logs.
- Review the selected provider's data controls and terms before sending private material.
- Every ideator, critic, and jury action is a separate request. Increasing `--ideas-per-persona` increases usage.
- Web search can create additional tool usage and cost.

The automated test suite uses fake HTTP transports and never makes paid API requests.
