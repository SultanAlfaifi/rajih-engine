from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from pathlib import Path

from .engine import DemoBackend, RajihEngine
from .live_backend import ProviderBackend, RoutedProviderBackend
from .models import RunState, Stage
from .providers import (
    AnthropicMessagesClient,
    DeepSeekChatClient,
    GeminiGenerateContentClient,
    JsonGenerationClient,
    OpenAIResponsesClient,
    ProviderError,
)
from .router import UncertaintyRouter
from .store import RunStore


def slug(value: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9-]+", "-", value).strip("-").lower()
    return clean[:40] or uuid.uuid4().hex[:8]


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="rajih", description="RAJIH evidence-grounded ideation engine")
    root.add_argument("--store", default=".rajih/runs", help="Run store directory")
    commands = root.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create a run from a JSON brief")
    init.add_argument("brief", type=Path)
    init.add_argument("--title")
    demo = commands.add_parser("demo", help="Run the deterministic offline demonstration")
    demo.add_argument("brief", type=Path)
    demo.add_argument("--ideas-per-persona", type=int, default=2)
    run = commands.add_parser("run", help="Run RAJIH directly with a model provider")
    run.add_argument("brief", type=Path)
    run.add_argument("--title")
    run.add_argument("--provider", choices=("openai", "anthropic", "gemini", "deepseek"), default="openai")
    run.add_argument("--model")
    run.add_argument("--base-url")
    for role in ("scout", "ideator", "critic", "jury"):
        run.add_argument(f"--{role}-provider", choices=("openai", "anthropic", "gemini", "deepseek"))
        run.add_argument(f"--{role}-model")
    run.add_argument("--web-search", action="store_true", help="Allow the Scout to use provider web search")
    run.add_argument("--ideas-per-persona", type=int, default=1)
    run.add_argument("--timeout", type=float, default=120.0)
    status = commands.add_parser("status", help="Show one run or list all runs")
    status.add_argument("run_id", nargs="?")
    validate = commands.add_parser("validate", help="Validate a run's required invariants")
    validate.add_argument("run_id")
    choose = commands.add_parser("choose", help="Resolve a human gate by selecting a candidate")
    choose.add_argument("run_id")
    choose.add_argument("idea_id")
    choose.add_argument("--reason", default="Selected by the human operator.")
    return root


def load_brief(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Brief must be a JSON object.")
    return data


def validate_state(state: RunState) -> list[str]:
    errors = []
    if not state.brief.get("challenge"):
        errors.append("brief.challenge is required")
    ids = [idea.idea_id for idea in state.ideas]
    if len(ids) != len(set(ids)):
        errors.append("idea IDs must be unique")
    if state.decisions and not state.ideas:
        errors.append("a decision cannot exist without candidate ideas")
    return errors


def build_provider_client(provider: str, model: str | None, base_url: str | None, timeout: float) -> JsonGenerationClient:
    settings = {
        "openai": (OpenAIResponsesClient, "OPENAI_API_KEY", "OPENAI_MODEL"),
        "anthropic": (AnthropicMessagesClient, "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"),
        "gemini": (GeminiGenerateContentClient, "GEMINI_API_KEY", "GEMINI_MODEL"),
        "deepseek": (DeepSeekChatClient, "DEEPSEEK_API_KEY", "DEEPSEEK_MODEL"),
    }
    client_type, key_name, model_name = settings[provider]
    selected_model = model or os.getenv(model_name)
    if not selected_model:
        raise ValueError(f"--model is required unless {model_name} is set")
    kwargs = {
        "api_key": os.getenv(key_name, ""),
        "model": selected_model,
        "timeout": timeout,
    }
    if base_url:
        kwargs["base_url"] = base_url
    return client_type(**kwargs)


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    store = RunStore(args.store)
    try:
        if args.command in {"init", "demo", "run"}:
            brief = load_brief(args.brief)
            title = getattr(args, "title", None) or str(brief.get("title", "RAJIH run"))
            state = RunState(f"{slug(title)}-{uuid.uuid4().hex[:6]}", title, brief)
            if args.command == "demo":
                engine = RajihEngine(DemoBackend(), UncertaintyRouter())
                state = engine.run_demo(state, max(1, args.ideas_per_persona))
            if args.command == "run":
                role_settings = {}
                for role in ("scout", "ideator", "critic", "jury"):
                    provider = getattr(args, f"{role}_provider") or args.provider
                    explicit_model = getattr(args, f"{role}_model")
                    inherited_model = args.model if provider == args.provider else None
                    role_settings[role] = (provider, explicit_model or inherited_model)
                if args.web_search and role_settings["scout"][0] != "openai":
                    raise ValueError("--web-search is currently supported only by the openai adapter")
                clients = {
                    role: build_provider_client(provider, model, args.base_url if provider == args.provider else None, args.timeout)
                    for role, (provider, model) in role_settings.items()
                }
                state.runtime = {
                    "mode": "direct",
                    "roles": {
                        role: {"provider": role_settings[role][0], "model": client.model}
                        for role, client in clients.items()
                    },
                    "web_search": args.web_search,
                }
                store.save(state)
                try:
                    backend = RoutedProviderBackend(
                        scout=ProviderBackend(clients["scout"], args.web_search),
                        ideator=ProviderBackend(clients["ideator"]),
                        critic=ProviderBackend(clients["critic"]),
                        jury=ProviderBackend(clients["jury"]),
                    )
                    state = RajihEngine(backend, UncertaintyRouter()).run_live(
                        state, max(1, args.ideas_per_persona)
                    )
                except ProviderError as exc:
                    state.unknowns.append(str(exc))
                    store.save(state)
                    raise
            path = store.save(state)
            print(
                json.dumps(
                    {
                        "run_id": state.run_id,
                        "stage": state.stage.value,
                        "needs_human": state.stage.value == "human_gate",
                        "state": str(path),
                    },
                    ensure_ascii=False,
                )
            )
            return 0
        if args.command == "status":
            if not args.run_id:
                print(json.dumps(store.list_runs(), ensure_ascii=False))
            else:
                print(json.dumps(store.load(args.run_id).to_dict(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "validate":
            errors = validate_state(store.load(args.run_id))
            print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False))
            return 0 if not errors else 1
        if args.command == "choose":
            state = store.load(args.run_id)
            if state.stage.value != "human_gate":
                raise ValueError("choose is only valid when the run is waiting at the human gate")
            selected = next((idea for idea in state.ideas if idea.idea_id == args.idea_id), None)
            if selected is None:
                raise ValueError(f"unknown idea ID: {args.idea_id}")
            state.decisions.append({"decision": f"Select {selected.idea_id}", "reason": args.reason})
            state.unknowns = [item for item in state.unknowns if "rajih choose" not in item]
            state.stage = Stage.DONE
            state.completed.append("human decision")
            path = store.save(state)
            print(json.dumps({"run_id": state.run_id, "stage": state.stage.value, "state": str(path)}))
            return 0
    except (FileNotFoundError, ValueError, json.JSONDecodeError, ProviderError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

