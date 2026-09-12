import json
import tempfile
import unittest
from pathlib import Path

from rajih.cli import validate_state
from rajih.engine import DemoBackend, RajihEngine
from rajih.models import RunState, Stage
from rajih.router import UncertaintyRouter
from rajih.store import RunStore


BRIEF = {
    "challenge": "Reduce food waste at university events",
    "tracks": ["sustainability"],
    "criteria": ["impact", "feasibility", "innovation"],
    "team": ["software", "design"],
    "constraints": ["48-hour prototype"],
}


class EngineTests(unittest.TestCase):
    def test_complete_brief_routes_to_ideation(self):
        state = RunState("r1", "test", BRIEF)
        decision = UncertaintyRouter().decide(state)
        self.assertEqual(decision.next_stage, Stage.DIVERGE)
        self.assertFalse(decision.needs_human)

    def test_missing_challenge_requests_human(self):
        state = RunState("r1", "test", {})
        decision = UncertaintyRouter().decide(state)
        self.assertTrue(decision.needs_human)
        self.assertEqual(decision.next_stage, Stage.CLARIFY_BRIEF)

    def test_close_finalists_route_to_distinct_human_gate(self):
        state = RajihEngine(DemoBackend(), UncertaintyRouter()).run_demo(RunState("r2", "test", BRIEF))
        state.stage = Stage.CONVERGE
        state.ideas[0].scores = {"quality": 4.0}
        state.ideas[1].scores = {"quality": 3.9}
        for idea in state.ideas[2:]:
            idea.scores = {"quality": 2.0}
        decision = UncertaintyRouter(winner_margin=0.35).decide(state)
        self.assertEqual(decision.next_stage, Stage.HUMAN_GATE)
        self.assertTrue(decision.needs_human)

    def test_demo_is_persisted_and_valid(self):
        state = RajihEngine(DemoBackend(), UncertaintyRouter()).run_demo(RunState("r1", "test", BRIEF))
        self.assertEqual(state.stage, Stage.DONE)
        self.assertEqual(len(state.ideas), 6)
        self.assertEqual(validate_state(state), [])
        with tempfile.TemporaryDirectory() as directory:
            store = RunStore(Path(directory))
            store.save(state)
            restored = store.load("r1")
            self.assertEqual(restored.to_dict(), state.to_dict())
            self.assertTrue((Path(directory) / "r1" / "decisions.md").exists())


if __name__ == "__main__":
    unittest.main()
