from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Evidence, Idea, RunState, Stage


class RunStore:
    def __init__(self, root: Path | str = ".rajih/runs"):
        self.root = Path(root)

    def save(self, state: RunState) -> Path:
        target = self.root / state.run_id
        target.mkdir(parents=True, exist_ok=True)
        path = target / "state.json"
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)
        self._write_markdown_views(target, state)
        return path

    def load(self, run_id: str) -> RunState:
        data = json.loads((self.root / run_id / "state.json").read_text(encoding="utf-8"))
        ideas = []
        for raw in data.get("ideas", []):
            raw["evidence"] = [Evidence(**item) for item in raw.get("evidence", [])]
            ideas.append(Idea(**raw))
        data["ideas"] = ideas
        data["stage"] = Stage(data["stage"])
        return RunState(**data)

    def list_runs(self) -> list[str]:
        if not self.root.exists():
            return []
        return sorted(p.name for p in self.root.iterdir() if (p / "state.json").exists())

    @staticmethod
    def _write_markdown_views(target: Path, state: RunState) -> None:
        brief = [f"# {state.title}", "", *[f"- **{k}:** {v}" for k, v in state.brief.items()]]
        ideas = ["# Ideas", ""]
        for idea in state.ideas:
            ideas.extend([f"## {idea.idea_id}: {idea.title}", "", idea.solution, ""])
        decisions = ["# Decisions", ""] + [f"- {d.get('decision')}: {d.get('reason')}" for d in state.decisions]
        progress = ["# Progress", "", f"Current stage: **{state.stage.value}**", ""]
        if state.runtime:
            progress.extend(["## Runtime", "", *[f"- **{key}:** {value}" for key, value in state.runtime.items()], ""])
        progress.extend(f"- [x] {step}" for step in state.completed)
        for filename, lines in {"brief.md": brief, "ideas.md": ideas, "decisions.md": decisions, "progress.md": progress}.items():
            (target / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")

