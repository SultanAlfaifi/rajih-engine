from __future__ import annotations

import json
from dataclasses import dataclass
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
        return [Evidence(**item) for item in result["evidence"]]

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
            input_text=json.dumps(state.brief, ensure_ascii=False),
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
                "Use the full scale. Scores are decision support, not proof of novelty or correctness."
            ),
            input_text=json.dumps(
                {"brief": state.brief, "candidate": {"problem": idea.problem, "solution": idea.solution, "risks": idea.risks}},
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

    def score(self, state: RunState, idea: Idea) -> dict[str, float]:
        return self.jury.score(state, idea)
