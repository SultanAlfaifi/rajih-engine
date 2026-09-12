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
    def refine(self, state: RunState, idea: Idea) -> Idea: ...
    def verify(self, state: RunState, idea: Idea) -> list[Evidence]: ...
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

    def refine(self, state: RunState, idea: Idea) -> Idea:
        return Idea("", f"{idea.title} - revised", idea.problem, f"{idea.solution} The revision addresses the recorded risks with one measurable validation step.", idea.persona, parent_id=idea.idea_id, risks=list(idea.risks))

    def verify(self, state: RunState, idea: Idea) -> list[Evidence]:
        return [Evidence("Synthetic candidate-specific evidence for offline demonstration only.", f"demo://offline/{idea.idea_id}", "demo", 1.0, "demo", "synthetic")]

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
        state.runtime = {"mode": "demo", "pipeline_version": "0.4", "evidence": "synthetic"}
        result = self.run_live(state, ideas_per_persona)
        if result.stage == Stage.HUMAN_GATE:
            winner = max(self._finalists(result), key=lambda item: item.mean_score)
            result.route_log.extend([
                {"from": "human_gate", "to": "decide", "actor": "demo", "reason": "Offline demonstration auto-resolves synthetic close scores.", "needs_human": False},
                {"from": "decide", "to": "done", "actor": "orchestrator", "reason": "The synthetic demo decision was persisted.", "needs_human": False},
            ])
            result.decisions.append({"idea_id": winner.idea_id, "decision": f"Select {winner.idea_id}", "reason": "Highest synthetic demo score; not a real-world recommendation."})
            result.unknowns = [item for item in result.unknowns if "rajih choose" not in item]
            result.completed.append("synthetic demo decision")
            result.stage = Stage.DONE
        return result

    def run_live(self, state: RunState, ideas_per_persona: int = 1) -> RunState:
        while state.stage != Stage.DONE:
            if state.stage == Stage.UNDERSTAND:
                self._advance(state)
            elif state.stage == Stage.RESEARCH:
                state.context_evidence = self.backend.research(state)
                state.completed.append("shared context research" if state.context_evidence else "shared context research skipped")
                self._advance(state)
            elif state.stage == Stage.CLARIFY_BRIEF:
                message = "Required brief fields are missing; update the brief and start a new run."
                if message not in state.unknowns:
                    state.unknowns.append(message)
                return state
            elif state.stage == Stage.DIVERGE:
                for persona in ("grounded", "transformational", "demo-first"):
                    state.ideas.extend(self.backend.ideate(state, persona, ideas_per_persona))
                state.finalist_ids = [idea.idea_id for idea in state.ideas]
                state.completed.append("independent ideation")
                self._advance(state)
            elif state.stage == Stage.CRITIQUE:
                for idea in self._finalists(state):
                    idea.risks.extend(self.backend.critique(state, idea))
                state.completed.append("candidate-specific critique")
                self._advance(state)
            elif state.stage == Stage.REFINE:
                revisions = []
                for parent in self._finalists(state):
                    revision = self.backend.refine(state, parent)
                    revision.idea_id = self._next_idea_id(state, len(revisions))
                    revision.parent_id = parent.idea_id
                    revisions.append(revision)
                state.ideas.extend(revisions)
                state.finalist_ids = [idea.idea_id for idea in revisions]
                state.completed.append("traceable refinement")
                self._advance(state)
            elif state.stage == Stage.VERIFY:
                for idea in self._finalists(state):
                    idea.evidence.extend(self.backend.verify(state, idea))
                state.completed.append("candidate-specific verification")
                self._advance(state)
            elif state.stage == Stage.CONVERGE:
                finalists = self._finalists(state)
                for idea in finalists:
                    idea.scores = self.backend.score(state, idea)
                if not finalists:
                    raise ValueError("No finalists are available for scoring.")
                ranked = sorted(finalists, key=lambda item: item.mean_score, reverse=True)
                margin = self.router.winner_margin(state)
                state.metrics = {
                    "idea_count": float(len(state.ideas)),
                    "finalist_count": float(len(finalists)),
                    "winner_score": round(ranked[0].mean_score, 3),
                    "winner_margin": round(margin, 3),
                    "candidate_evidence_coverage": self.router.evidence_coverage(state),
                }
                state.completed.append("evidence-informed jury scoring")
                self._advance(state)
                if state.stage == Stage.HUMAN_GATE:
                    state.unknowns.append(f"{state.route_log[-1]['reason']} Choose a finalist with the rajih choose command.")
                    return state
            elif state.stage == Stage.HUMAN_GATE:
                return state
            elif state.stage == Stage.DECIDE:
                winner = max(self._finalists(state), key=lambda item: item.mean_score)
                state.decisions.append({
                    "idea_id": winner.idea_id,
                    "decision": f"Select {winner.idea_id}",
                    "reason": "Highest evidence-informed jury score above the configured routing thresholds.",
                })
                state.completed.append("final decision")
                self._advance(state)
        return state

    def _advance(self, state: RunState) -> None:
        previous = state.stage
        decision = self.router.decide(state)
        state.route_log.append({
            "from": previous.value,
            "to": decision.next_stage.value,
            "actor": decision.agent,
            "reason": decision.reason,
            "needs_human": decision.needs_human,
        })
        state.stage = decision.next_stage

    @staticmethod
    def _finalists(state: RunState) -> list[Idea]:
        selected = set(state.finalist_ids)
        return [idea for idea in state.ideas if idea.idea_id in selected]

    @staticmethod
    def _next_idea_id(state: RunState, offset: int = 0) -> str:
        numbers = [int(idea.idea_id.split("-")[-1]) for idea in state.ideas if idea.idea_id.startswith("IDEA-") and idea.idea_id.split("-")[-1].isdigit()]
        return f"IDEA-{max(numbers, default=0) + offset + 1:02d}"

