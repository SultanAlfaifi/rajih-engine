# Run RAJIH directly with a model provider

RAJIH can use the official Codex CLI with a ChatGPT subscription, or call a selected API provider over HTTPS. Run state remains on your machine.

Supported adapters:

| Provider | API key variable | Optional model variable | Structured response mechanism |
|---|---|---|---|
| Codex CLI | None; run `codex login` | Inherits Codex config; optional `--model` | `codex exec --output-schema` |
| OpenRouter | `OPENROUTER_API_KEY` | `OPENROUTER_MODEL` | Chat Completions JSON Schema |
| OpenAI | `OPENAI_API_KEY` | `OPENAI_MODEL` | Responses API JSON Schema |
| Anthropic | `ANTHROPIC_API_KEY` | `ANTHROPIC_MODEL` | Messages API structured output |
| Gemini | `GEMINI_API_KEY` | `GEMINI_MODEL` | Generate Content JSON Schema |
| DeepSeek | `DEEPSEEK_API_KEY` | `DEEPSEEK_MODEL` | JSON Output plus local schema validation |

Official references: [Codex authentication](https://developers.openai.com/codex/auth), [Codex non-interactive mode](https://developers.openai.com/codex/noninteractive), [OpenRouter quickstart](https://openrouter.ai/docs/quickstart), [OpenRouter structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs), [OpenAI Responses](https://developers.openai.com/api/reference/cli/resources/responses/methods/create), [Anthropic Messages](https://platform.claude.com/docs/en/api/messages/create), [Gemini Generate Content](https://ai.google.dev/api/generate-content), and [DeepSeek JSON Output](https://api-docs.deepseek.com/guides/json_mode/).

## Requirements

- Python 3.11 or newer.
- For Codex: an installed Codex CLI signed in with ChatGPT and available subscription usage.
- For an API adapter: an API key with model access and sufficient provider budget.

RAJIH does not create, purchase, or validate API keys.

## Codex with ChatGPT subscription

ChatGPT subscriptions and OpenAI API billing are separate. RAJIH does not convert a subscription into an API key. Instead, the `codex` provider invokes the official non-interactive Codex CLI and reuses its saved ChatGPT authentication:

```powershell
codex login
codex login status
rajih run examples/brief.json --provider codex
```

No `OPENAI_API_KEY` is needed and this path does not create separate OpenAI API charges. It consumes the usage available to your Codex/ChatGPT plan and remains subject to plan limits. RAJIH uses `--ephemeral`, `--sandbox read-only`, and `--output-schema`; it does not access or export Codex's cached credential.

Optional web research:

```powershell
rajih run examples/brief.json --provider codex --web-search
```

Each specialist call launches a separate Codex execution, so a complete run consumes multiple subscription requests.

With the default three candidates, a full run without web search makes 12 model calls: ideation, critique, refinement, and jury scoring for each candidate. Enabling web search adds shared-context research and candidate-specific verification calls. If candidate evidence is unavailable, RAJIH requires a human choice instead of treating the Jury score as an evidence-backed automatic decision.

## OpenRouter

```powershell
$env:OPENROUTER_API_KEY = Read-Host "OpenRouter API key"
rajih run examples/brief.json --provider openrouter --model "OPENROUTER_MODEL_ID"
```

OpenRouter is independent of ChatGPT subscriptions. It may charge for requests according to the selected model and account. Use a model that supports structured outputs. `--web-search` enables OpenRouter's web plugin for Scout and can add cost.

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
- `--web-search`: Codex, OpenRouter, or OpenAI Scout only; provider search usage and charges may apply.
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
- Codex subscription mode is not unlimited and does not include OpenRouter usage.

The automated test suite uses fake HTTP transports and a fake Codex subprocess runner. It never makes paid model requests.
