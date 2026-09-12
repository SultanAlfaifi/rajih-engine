import json
import subprocess
import unittest

from rajih.engine import RajihEngine
from rajih.live_backend import RoutedProviderBackend
from rajih.models import Evidence, Idea, RunState, Stage
from rajih.providers import (
    AnthropicMessagesClient,
    CodexSubscriptionClient,
    DeepSeekChatClient,
    GeminiGenerateContentClient,
    OpenAIResponsesClient,
    OpenRouterChatClient,
    ProviderError,
)
from rajih.router import UncertaintyRouter


BRIEF = {
    "challenge": "Reduce food waste",
    "tracks": ["sustainability"],
    "criteria": ["impact", "feasibility"],
    "team": ["software"],
    "constraints": ["48 hours"],
}


class FakeBackend:
    def research(self, state):
        return [Evidence("Public claim", "https://example.org", "web", 0.8)]

    def ideate(self, state, persona, count):
        start = len(state.ideas) + 1
        return [
            Idea(f"IDEA-{start + index:02d}", f"{persona} idea", "problem", "solution", persona)
            for index in range(count)
        ]

    def critique(self, state, idea):
        return ["Test adoption assumptions", "Validate the prototype constraint"]

    def score(self, state, idea):
        number = int(idea.idea_id.split("-")[1])
        return {"impact": 5.0 - number * 0.5, "feasibility": 5.0 - number * 0.5}


class LiveEngineTests(unittest.TestCase):
    def test_live_run_persists_evidence_scores_and_decision(self):
        state = RunState("live-1", "Live", BRIEF)
        result = RajihEngine(FakeBackend(), UncertaintyRouter(winner_margin=0.35)).run_live(state)
        self.assertEqual(result.stage, Stage.DONE)
        self.assertEqual(len(result.ideas), 3)
        self.assertTrue(all(idea.evidence and idea.risks and idea.scores for idea in result.ideas))
        self.assertEqual(result.decisions[0]["decision"], "Select IDEA-01")

    def test_routed_backend_dispatches_each_role_independently(self):
        calls = []

        class RoleBackend:
            def __init__(self, role):
                self.role = role

            def research(self, state):
                calls.append(self.role)
                return []

            def ideate(self, state, persona, count):
                calls.append(self.role)
                return []

            def critique(self, state, idea):
                calls.append(self.role)
                return []

            def score(self, state, idea):
                calls.append(self.role)
                return {}

        routed = RoutedProviderBackend(
            scout=RoleBackend("scout"),
            ideator=RoleBackend("ideator"),
            critic=RoleBackend("critic"),
            jury=RoleBackend("jury"),
        )
        state = RunState("route-1", "Route", BRIEF)
        idea = Idea("IDEA-01", "title", "problem", "solution", "grounded")
        routed.research(state)
        routed.ideate(state, "grounded", 1)
        routed.critique(state, idea)
        routed.score(state, idea)
        self.assertEqual(calls, ["scout", "ideator", "critic", "jury"])


class ResponsesClientTests(unittest.TestCase):
    SCHEMA = {
        "type": "object",
        "properties": {"ok": {"type": "boolean"}},
        "required": ["ok"],
        "additionalProperties": False,
    }

    def test_structured_response_request_is_private_and_parseable(self):
        captured = {}

        def transport(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": '{"ok":true}'}],
                    }
                ]
            }

        client = OpenAIResponsesClient("test-key", "test-model", transport=transport)
        result = client.generate_json(
            instructions="Return JSON",
            input_text="hello",
            schema_name="test",
            schema=self.SCHEMA,
        )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(captured["url"], "https://api.openai.com/v1/responses")
        self.assertFalse(captured["payload"]["store"])

    def test_missing_api_key_fails_before_transport(self):
        client = OpenAIResponsesClient("", "test-model")
        with self.assertRaises(ProviderError):
            client.generate_json(
                instructions="Return JSON",
                input_text="hello",
                schema_name="test",
                schema={"type": "object", "properties": {}, "required": [], "additionalProperties": False},
            )

    def test_anthropic_structured_request(self):
        captured = {}

        def transport(request, timeout):
            captured["url"] = request.full_url
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return {"content": [{"type": "text", "text": '{"ok":true}'}]}

        client = AnthropicMessagesClient("test-key", "test-model", transport=transport)
        result = client.generate_json(
            instructions="Return JSON", input_text="hello", schema_name="test", schema=self.SCHEMA
        )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(captured["url"], "https://api.anthropic.com/v1/messages")
        self.assertEqual(captured["payload"]["output_config"]["format"]["type"], "json_schema")

    def test_gemini_structured_request(self):
        captured = {}

        def transport(request, timeout):
            captured["url"] = request.full_url
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return {"candidates": [{"content": {"parts": [{"text": '{"ok":true}'}]}}]}

        client = GeminiGenerateContentClient("test-key", "test-model", transport=transport)
        result = client.generate_json(
            instructions="Return JSON", input_text="hello", schema_name="test", schema=self.SCHEMA
        )
        self.assertEqual(result, {"ok": True})
        self.assertIn("models/test-model:generateContent", captured["url"])
        self.assertEqual(captured["payload"]["generationConfig"]["responseMimeType"], "application/json")
        self.assertFalse(captured["payload"]["store"])

    def test_deepseek_json_request_is_locally_schema_validated(self):
        captured = {}

        def transport(request, timeout):
            captured["url"] = request.full_url
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return {"choices": [{"message": {"content": '{"ok":true}'}}]}

        client = DeepSeekChatClient("test-key", "test-model", transport=transport)
        result = client.generate_json(
            instructions="Return JSON", input_text="hello", schema_name="test", schema=self.SCHEMA
        )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(captured["url"], "https://api.deepseek.com/chat/completions")
        self.assertEqual(captured["payload"]["response_format"], {"type": "json_object"})

    def test_openrouter_uses_structured_outputs_and_optional_web_plugin(self):
        captured = {}

        def transport(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return {"choices": [{"message": {"content": '{"ok":true}'}}]}

        client = OpenRouterChatClient("test-key", "test-model", transport=transport)
        result = client.generate_json(
            instructions="Return JSON",
            input_text="hello",
            schema_name="test",
            schema=self.SCHEMA,
            web_search=True,
        )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(captured["url"], "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(captured["payload"]["response_format"]["type"], "json_schema")
        self.assertEqual(captured["payload"]["provider"], {"require_parameters": True})
        self.assertEqual(captured["payload"]["plugins"], [{"id": "web"}])

    def test_openrouter_requires_its_own_api_key(self):
        client = OpenRouterChatClient("", "test-model")
        with self.assertRaises(ProviderError):
            client.generate_json(
                instructions="Return JSON", input_text="hello", schema_name="test", schema=self.SCHEMA
            )

    def test_codex_uses_ephemeral_read_only_exec_and_saved_login(self):
        captured = {}

        def runner(command, **kwargs):
            captured["command"] = command
            captured["kwargs"] = kwargs
            output_path = command[command.index("--output-last-message") + 1]
            with open(output_path, "w", encoding="utf-8") as output:
                output.write('{"ok":true}')
            return subprocess.CompletedProcess(command, 0, "", "")

        client = CodexSubscriptionClient(runner=runner)
        result = client.generate_json(
            instructions="Return JSON",
            input_text="hello",
            schema_name="test",
            schema=self.SCHEMA,
            web_search=True,
        )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(captured["command"][:3], ["codex", "--search", "exec"])
        self.assertIn("--ephemeral", captured["command"])
        self.assertEqual(
            captured["command"][captured["command"].index("--sandbox") + 1], "read-only"
        )
        self.assertNotIn("--model", captured["command"])
        self.assertEqual(captured["command"][-1], "-")
        self.assertIn("Input:\nhello", captured["kwargs"]["input"])
        self.assertFalse(captured["kwargs"]["check"])

    def test_codex_can_override_the_subscription_model(self):
        captured = {}

        def runner(command, **kwargs):
            captured["command"] = command
            output_path = command[command.index("--output-last-message") + 1]
            with open(output_path, "w", encoding="utf-8") as output:
                output.write('{"ok":true}')
            return subprocess.CompletedProcess(command, 0, "", "")

        client = CodexSubscriptionClient(model="gpt-test", runner=runner)
        client.generate_json(
            instructions="Return JSON", input_text="hello", schema_name="test", schema=self.SCHEMA
        )
        model_index = captured["command"].index("--model")
        self.assertEqual(captured["command"][model_index + 1], "gpt-test")

    def test_local_schema_validation_rejects_wrong_types(self):
        def transport(request, timeout):
            return {"choices": [{"message": {"content": '{"ok":"yes"}'}}]}

        client = DeepSeekChatClient("test-key", "test-model", transport=transport)
        with self.assertRaises(ProviderError):
            client.generate_json(
                instructions="Return JSON", input_text="hello", schema_name="test", schema=self.SCHEMA
            )


if __name__ == "__main__":
    unittest.main()
