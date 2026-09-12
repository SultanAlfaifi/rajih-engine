from __future__ import annotations

from dataclasses import dataclass

from .models import RunState, Stage


@dataclass(frozen=True, slots=True)
class RouteDecision:
    next_stage: Stage
    agent: str
    reason: str
    needs_human: bool = False


class UncertaintyRouter:
    """Transparent reference policy used by the product and benchmark.

    Uncertainty is intentionally observable: missing required fields, weak
    evidence coverage, and a small finalist score margin. It is not a model's
    uncalibrated statement that it feels uncertain.
    """

    REQUIRED = ("challenge", "tracks", "criteria", "team", "constraints")

    def __init__(self, human_threshold: float = 0.55, winner_margin: float = 0.35):
        self.human_threshold = human_threshold
        self.winner_margin_threshold = winner_margin

    def intake_uncertainty(self, state: RunState) -> float:
        missing = sum(not state.brief.get(key) for key in self.REQUIRED)
        return missing / len(self.REQUIRED)

    def evidence_coverage(self, state: RunState) -> float:
        if not state.ideas:
            return 0.0
        return sum(bool(idea.evidence) for idea in state.ideas) / len(state.ideas)

    def winner_margin(self, state: RunState) -> float:
        ranked = sorted((idea.mean_score for idea in state.ideas), reverse=True)
        return ranked[0] - ranked[1] if len(ranked) >= 2 else 0.0

    def decide(self, state: RunState) -> RouteDecision:
        if state.stage == Stage.UNDERSTAND:
            uncertainty = self.intake_uncertainty(state)
            if uncertainty >= self.human_threshold and not state.brief.get("challenge"):
                return RouteDecision(Stage.CLARIFY_BRIEF, "human", "The challenge itself is missing.", True)
            if uncertainty > 0:
                return RouteDecision(Stage.RESEARCH, "scout", "Required public context is incomplete.")
            return RouteDecision(Stage.DIVERGE, "ideator", "The minimum brief is complete.")
        if state.stage == Stage.RESEARCH:
            return RouteDecision(Stage.CLARIFY_BRIEF, "human", "Only personal or team-specific gaps should be asked.", True)
        if state.stage == Stage.CLARIFY_BRIEF:
            return RouteDecision(Stage.DIVERGE, "ideator", "High-value gaps have been resolved.")
        if state.stage == Stage.DIVERGE:
            return RouteDecision(Stage.CRITIQUE, "critic", "Independent candidate ideas are available.")
        if state.stage == Stage.CRITIQUE:
            return RouteDecision(Stage.REFINE, "ideator", "Critiques should produce traceable revisions.")
        if state.stage == Stage.REFINE:
            return RouteDecision(Stage.VERIFY, "scout", "Finalists need external prior-art evidence.")
        if state.stage == Stage.VERIFY:
            return RouteDecision(Stage.CONVERGE, "jury", "Evidence-backed scoring can begin.")
        if state.stage == Stage.CONVERGE:
            uncertain = self.winner_margin(state) < self.winner_margin_threshold
            return RouteDecision(Stage.HUMAN_GATE if uncertain else Stage.DECIDE, "human" if uncertain else "orchestrator", "Finalist scores are close." if uncertain else "A stable leader exists.", uncertain)
        if state.stage == Stage.HUMAN_GATE:
            return RouteDecision(Stage.DECIDE, "orchestrator", "The human preference has resolved the close decision.")
        if state.stage == Stage.DECIDE:
            return RouteDecision(Stage.DONE, "orchestrator", "The decision and rationale are recorded.")
        return RouteDecision(Stage.DONE, "none", "Run is complete.")
