from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from pathlib import Path

from .engine import DemoBackend, RajihEngine
from .models import RunState
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
    status = commands.add_parser("status", help="Show one run or list all runs")
    status.add_argument("run_id", nargs="?")
    validate = commands.add_parser("validate", help="Validate a run's required invariants")
    validate.add_argument("run_id")
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


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    store = RunStore(args.store)
    try:
        if args.command in {"init", "demo"}:
            brief = load_brief(args.brief)
            title = getattr(args, "title", None) or str(brief.get("title", "RAJIH run"))
            state = RunState(f"{slug(title)}-{uuid.uuid4().hex[:6]}", title, brief)
            if args.command == "demo":
                engine = RajihEngine(DemoBackend(), UncertaintyRouter())
                state = engine.run_demo(state, max(1, args.ideas_per_persona))
            path = store.save(state)
            print(json.dumps({"run_id": state.run_id, "stage": state.stage.value, "state": str(path)}, ensure_ascii=False))
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
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

