from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from .models import Evidence, Idea, RunState
from .providers import JsonGenerationClient


OBJECT_SCHEMA_BASE: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
}


class ProviderBackend:
    """Provider-neutral role prompts for standalone RAJIH runs."""

    def __init__(self, client: JsonGenerationClient, enable_web_search: bool = False):
        self.client = client
        self.enable_web_search = enable_web_search

    def research(self, state: RunState) -> list[Evidence]:
        if not self.enable_web_search:
            return []
        schema = {
            **OBJECT_SCHEMA_BASE,
            "properties": {
                "evidence": {
                    "type": "array",
                    "items": {
                        **OBJECT_SCHEMA_BASE,
                        "properties": {
                            "claim": {"type": "string"},
                            "source": {"type": "string"},
                            "source_type": {"type": "string"},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        },
                        "required": ["claim", "source", "source_type", "confidence"],
                    },
                }
            },
            "required": ["evidence"],
        }
        result = self.client.generate_json(
            instructions=(
                "You are the RAJIH Scout. Find only decision-relevant public evidence and prior art. "
                "Use web search, provide the exact source URL, avoid unsupported novelty claims, and return concise evidence records."
            ),
            input_text=json.dumps(state.brief, ensure_ascii=False),
            schema_name="rajih_evidence",
            schema=schema,
            web_search=True,
        )
        accessed_at = datetime.now(timezone.utc).isoformat()
        return [Evidence(**item, relationship="context", accessed_at=accessed_at) for item in result["evidence"]]

    def ideate(self, state: RunState, persona: str, count: int) -> list[Idea]:
        schema = {
            **OBJECT_SCHEMA_BASE,
            "properties": {
                "ideas": {
                    "type": "array",
                    "minItems": count,
                    "maxItems": count,
                    "items": {
                        **OBJECT_SCHEMA_BASE,
                        "properties": {
                            "title": {"type": "string"},
                            "problem": {"type": "string"},
                            "solution": {"type": "string"},
                        },
                        "required": ["title", "problem", "solution"],
                    },
                }
            },
            "required": ["ideas"],
        }
        result = self.client.generate_json(
            instructions=(
                f"You are an independent RAJIH {persona} ideator. Generate exactly {count} distinct, testable hackathon ideas. "
                "Do not assume access to other ideators. Respect every stated constraint and avoid claiming verified novelty."
            ),
            input_text=json.dumps(
                {"brief": state.brief, "shared_context": [asdict(item) for item in state.context_evidence]},
                ensure_ascii=False,
            ),
            schema_name="rajih_ideas",
            schema=schema,
        )
        start = len(state.ideas) + 1
        return [
            Idea(f"IDEA-{start + index:02d}", raw["title"], raw["problem"], raw["solution"], persona)
            for index, raw in enumerate(result["ideas"])
        ]

    def critique(self, state: RunState, idea: Idea) -> list[str]:
        schema = {
            **OBJECT_SCHEMA_BASE,
            "properties": {
                "risks": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 5,
                    "items": {"type": "string"},
                }
            },
            "required": ["risks"],
        }
        result = self.client.generate_json(
            instructions=(
                "You are the independent RAJIH Critic. Identify concrete, falsifiable product, feasibility, adoption, "
                "demo, and evidence risks. Do not rewrite the idea and do not invent facts."
            ),
            input_text=json.dumps({"brief": state.brief, "idea": idea.solution}, ensure_ascii=False),
            schema_name="rajih_risks",
            schema=schema,
        )
        return [str(risk) for risk in result["risks"]]

    def refine(self, state: RunState, idea: Idea) -> Idea:
        schema = {
            **OBJECT_SCHEMA_BASE,
            "properties": {
                "title": {"type": "string"},
                "problem": {"type": "string"},
                "solution": {"type": "string"},
            },
            "required": ["title", "problem", "solution"],
        }
        result = self.client.generate_json(
            instructions=(
                "You are the RAJIH Refiner. Produce one concrete revision that addresses the recorded risks while preserving "
                "the useful core of the candidate. Do not claim that novelty, feasibility, or impact has been verified."
            ),
            input_text=json.dumps(
                {
                    "brief": state.brief,
                    "candidate": {"title": idea.title, "problem": idea.problem, "solution": idea.solution},
                    "risks": idea.risks,
                    "shared_context": [asdict(item) for item in state.context_evidence],
                },
                ensure_ascii=False,
            ),
            schema_name="rajih_revision",
            schema=schema,
        )
        return Idea("", result["title"], result["problem"], result["solution"], idea.persona, parent_id=idea.idea_id, risks=list(idea.risks))

    def verify(self, state: RunState, idea: Idea) -> list[Evidence]:
        if not self.enable_web_search:
            return []
        schema = {
            **OBJECT_SCHEMA_BASE,
            "properties": {
                "evidence": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 6,
                    "items": {
                        **OBJECT_SCHEMA_BASE,
                        "properties": {
                            "claim": {"type": "string"},
                            "source": {"type": "string"},
                            "source_type": {"type": "string"},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            "relationship": {"type": "string", "enum": ["supports", "contradicts", "prior_art", "context"]},
                        },
                        "required": ["claim", "source", "source_type", "confidence", "relationship"],
                    },
                }
            },
            "required": ["evidence"],
        }
        result = self.client.generate_json(
            instructions=(
                "You are the RAJIH Verification Scout. Search for candidate-specific prior art and evidence relevant to "
                "the proposed mechanism and feasibility. Include evidence that contradicts or weakens the candidate. "
                "Use exact public URLs. Relationship must be one of supports, contradicts, prior_art, or context."
            ),
            input_text=json.dumps(
                {"brief": state.brief, "candidate": {"problem": idea.problem, "solution": idea.solution}},
                ensure_ascii=False,
            ),
            schema_name="rajih_candidate_evidence",
            schema=schema,
            web_search=True,
        )
        accessed_at = datetime.now(timezone.utc).isoformat()
        return [Evidence(**item, accessed_at=accessed_at) for item in result["evidence"]]

    def score(self, state: RunState, idea: Idea) -> dict[str, float]:
        criteria = [str(item) for item in state.brief.get("criteria", [])]
        if not criteria:
            criteria = ["innovation", "impact", "feasibility", "presentation"]
        properties = {criterion: {"type": "number", "minimum": 1, "maximum": 5} for criterion in criteria}
        schema = {
            **OBJECT_SCHEMA_BASE,
            "properties": {"scores": {**OBJECT_SCHEMA_BASE, "properties": properties, "required": criteria}},
            "required": ["scores"],
        }
        result = self.client.generate_json(
            instructions=(
                "You are the RAJIH Product Jury. Score the anonymized candidate from 1 to 5 against each supplied criterion. "
                "Use the full scale and consider candidate-specific evidence, contradictions, and missing evidence. "
                "A source's presence is not proof that its claim is true. Scores are decision support, not proof of novelty or correctness."
            ),
            input_text=json.dumps(
                {
                    "brief": state.brief,
                    "candidate": {
                        "problem": idea.problem,
                        "solution": idea.solution,
                        "risks": idea.risks,
                        "evidence": [asdict(item) for item in idea.evidence],
                    },
                },
                ensure_ascii=False,
            ),
            schema_name="rajih_scores",
            schema=schema,
        )
        return {key: float(value) for key, value in result["scores"].items()}


@dataclass(slots=True)
class RoutedProviderBackend:
    """Route RAJIH roles to independently configured provider backends."""

    scout: ProviderBackend
    ideator: ProviderBackend
    critic: ProviderBackend
    jury: ProviderBackend

    def research(self, state: RunState) -> list[Evidence]:
        return self.scout.research(state)

    def ideate(self, state: RunState, persona: str, count: int) -> list[Idea]:
        return self.ideator.ideate(state, persona, count)

    def critique(self, state: RunState, idea: Idea) -> list[str]:
        return self.critic.critique(state, idea)

    def refine(self, state: RunState, idea: Idea) -> Idea:
        return self.ideator.refine(state, idea)

    def verify(self, state: RunState, idea: Idea) -> list[Evidence]:
        return self.scout.verify(state, idea)

    def score(self, state: RunState, idea: Idea) -> dict[str, float]:
        return self.jury.score(state, idea)
