from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol

from .models import Evidence, Idea, RunState, Stage
from .router import UncertaintyRouter


class AgentBackend(Protocol):
    def research(self, state: RunState) -> list[Evidence]: ...
    def ideate(self, state: RunState, persona: str, count: int) -> list[Idea]: ...
    def critique(self, state: RunState, idea: Idea) -> list[str]: ...
    def score(self, state: RunState, idea: Idea) -> dict[str, float]: ...


class DemoBackend:
    """Offline backend for installation tests and reproducible examples."""

    PERSONA_LABELS = {
        "grounded": "Operational Signal",
        "transformational": "Constraint Flip",
        "demo-first": "Visible Proof",
    }

    def research(self, state: RunState) -> list[Evidence]:
        return [Evidence("Demo mode does not verify external claims.", "demo://offline", "demo", 1.0)]

    def ideate(self, state: RunState, persona: str, count: int) -> list[Idea]:
        challenge = str(state.brief.get("challenge", "the challenge"))
        result = []
        for index in range(count):
            token = hashlib.sha1(f"{state.run_id}:{persona}:{index}".encode()).hexdigest()[:6]
            idea_id = f"IDEA-{len(state.ideas) + index + 1:02d}"
            label = self.PERSONA_LABELS[persona]
            result.append(Idea(idea_id, f"{label} {token}", challenge, f"A {persona} prototype that turns one measurable constraint in {challenge} into a testable intervention.", persona))
        return result

    def critique(self, state: RunState, idea: Idea) -> list[str]:
        return ["No externally verified prior art in demo mode.", "Define one measurable user outcome before implementation."]

    def score(self, state: RunState, idea: Idea) -> dict[str, float]:
        seed = int(hashlib.sha1(idea.idea_id.encode()).hexdigest()[:4], 16)
        return {
            "innovation": 2.5 + (seed % 20) / 10,
            "feasibility": 2.8 + (seed % 18) / 10,
            "impact": 2.7 + (seed % 19) / 10,
            "rule_fit": 3.0 + (seed % 15) / 10,
        }


@dataclass(slots=True)
class RajihEngine:
    backend: AgentBackend
    router: UncertaintyRouter

    def run_demo(self, state: RunState, ideas_per_persona: int = 2) -> RunState:
        state.stage = Stage.DIVERGE
        for persona in ("grounded", "transformational", "demo-first"):
            state.ideas.extend(self.backend.ideate(state, persona, ideas_per_persona))
        state.completed.append("independent ideation")
        state.stage = Stage.CRITIQUE
        for idea in state.ideas:
            idea.risks.extend(self.backend.critique(state, idea))
            idea.evidence.extend(self.backend.research(state))
            idea.scores = self.backend.score(state, idea)
        state.completed.extend(["critique", "demo evidence annotation", "jury scoring"])
        state.stage = Stage.CONVERGE
        ranked = sorted(state.ideas, key=lambda item: item.mean_score, reverse=True)
        winner = ranked[0]
        state.decisions.append({"decision": f"Select {winner.idea_id}", "reason": "Highest mean demo score; requires human and prior-art validation."})
        state.metrics = {"idea_count": float(len(state.ideas)), "winner_score": round(winner.mean_score, 3), "external_evidence_coverage": 0.0}
        state.stage = Stage.DONE
        state.completed.append("demo decision")
        return state

    def run_live(self, state: RunState, ideas_per_persona: int = 1) -> RunState:
        state.stage = Stage.RESEARCH
        evidence = self.backend.research(state)
        state.completed.append("public evidence collection" if evidence else "evidence collection skipped")

        state.stage = Stage.DIVERGE
        for persona in ("grounded", "transformational", "demo-first"):
            candidates = self.backend.ideate(state, persona, ideas_per_persona)
            for candidate in candidates:
                candidate.evidence.extend(evidence)
            state.ideas.extend(candidates)
        state.completed.append("independent ideation")

        state.stage = Stage.CRITIQUE
        for idea in state.ideas:
            idea.risks.extend(self.backend.critique(state, idea))
        state.completed.append("independent critique")

        state.stage = Stage.CONVERGE
        for idea in state.ideas:
            idea.scores = self.backend.score(state, idea)
        state.completed.append("jury scoring")

        ranked = sorted(state.ideas, key=lambda item: item.mean_score, reverse=True)
        margin = self.router.winner_margin(state)
        state.metrics = {
            "idea_count": float(len(state.ideas)),
            "winner_score": round(ranked[0].mean_score, 3),
            "winner_margin": round(margin, 3),
            "external_evidence_coverage": self.router.evidence_coverage(state),
        }
        if margin < self.router.winner_margin_threshold:
            state.stage = Stage.HUMAN_GATE
            state.unknowns.append("Finalists are close; choose a candidate with the rajih choose command.")
            return state

        winner = ranked[0]
        state.decisions.append(
            {
                "decision": f"Select {winner.idea_id}",
                "reason": "Highest mean jury score with a margin above the configured human-gate threshold.",
            }
        )
        state.stage = Stage.DONE
        state.completed.append("final decision")
        return state

