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
        candidates = [idea for idea in state.ideas if idea.idea_id in state.finalist_ids]
        if not candidates:
            candidates = state.ideas
        if not candidates:
            return 0.0
        def usable(item) -> bool:
            external = item.source.startswith(("http://", "https://")) and bool(item.accessed_at)
            synthetic_demo = state.runtime.get("mode") == "demo" and item.source_type == "demo"
            return external or synthetic_demo

        return sum(any(usable(item) for item in idea.evidence) for idea in candidates) / len(candidates)

    def winner_margin(self, state: RunState) -> float:
        candidates = [idea for idea in state.ideas if idea.idea_id in state.finalist_ids]
        if not candidates:
            candidates = state.ideas
        ranked = sorted((idea.mean_score for idea in candidates), reverse=True)
        return ranked[0] - ranked[1] if len(ranked) >= 2 else 0.0

    def decide(self, state: RunState) -> RouteDecision:
        if state.stage == Stage.UNDERSTAND:
            uncertainty = self.intake_uncertainty(state)
            if uncertainty >= self.human_threshold and not state.brief.get("challenge"):
                return RouteDecision(Stage.CLARIFY_BRIEF, "human", "The challenge itself is missing.", True)
            if uncertainty > 0:
                return RouteDecision(Stage.RESEARCH, "scout", "Required public context is incomplete.")
            return RouteDecision(Stage.RESEARCH, "scout", "The minimum brief is complete; collect shared context.")
        if state.stage == Stage.RESEARCH:
            if self.intake_uncertainty(state) > 0:
                return RouteDecision(Stage.CLARIFY_BRIEF, "human", "Private or team-specific brief gaps remain.", True)
            return RouteDecision(Stage.DIVERGE, "ideator", "The brief and shared context are ready.")
        if state.stage == Stage.CLARIFY_BRIEF:
            if self.intake_uncertainty(state) > 0:
                return RouteDecision(Stage.CLARIFY_BRIEF, "human", "Required brief fields are still missing.", True)
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
            if self.evidence_coverage(state) < 1.0:
                return RouteDecision(Stage.HUMAN_GATE, "human", "One or more finalists lack candidate-specific evidence.", True)
            uncertain = self.winner_margin(state) < self.winner_margin_threshold
            return RouteDecision(Stage.HUMAN_GATE if uncertain else Stage.DECIDE, "human" if uncertain else "orchestrator", "Finalist scores are close." if uncertain else "An evidence-informed scoring leader exists.", uncertain)
        if state.stage == Stage.HUMAN_GATE:
            return RouteDecision(Stage.DECIDE, "orchestrator", "The human preference has resolved the close decision.")
        if state.stage == Stage.DECIDE:
            return RouteDecision(Stage.DONE, "orchestrator", "The decision and rationale are recorded.")
        return RouteDecision(Stage.DONE, "none", "Run is complete.")
