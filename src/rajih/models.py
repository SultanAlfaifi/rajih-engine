from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Stage(StrEnum):
    UNDERSTAND = "understand"
    RESEARCH = "research"
    CLARIFY_BRIEF = "clarify_brief"
    DIVERGE = "diverge"
    CRITIQUE = "critique"
    REFINE = "refine"
    VERIFY = "verify"
    CONVERGE = "converge"
    HUMAN_GATE = "human_gate"
    DECIDE = "decide"
    DONE = "done"


@dataclass(slots=True)
class Evidence:
    claim: str
    source: str
    source_type: str = "other"
    confidence: float = 0.5


@dataclass(slots=True)
class Idea:
    idea_id: str
    title: str
    problem: str
    solution: str
    persona: str
    parent_id: str | None = None
    scores: dict[str, float] = field(default_factory=dict)
    risks: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)

    @property
    def mean_score(self) -> float:
        return sum(self.scores.values()) / len(self.scores) if self.scores else 0.0


@dataclass(slots=True)
class RunState:
    run_id: str
    title: str
    brief: dict[str, Any]
    stage: Stage = Stage.UNDERSTAND
    completed: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    ideas: list[Idea] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    runtime: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["stage"] = self.stage.value
        return data
