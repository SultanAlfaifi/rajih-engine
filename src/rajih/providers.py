from __future__ import annotations

import json
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol


class ProviderError(RuntimeError):
    """A safe, user-facing provider failure."""


Transport = Callable[[urllib.request.Request, float], dict[str, Any]]


class JsonGenerationClient(Protocol):
    model: str

    def generate_json(
        self,
        *,
        instructions: str,
        input_text: str,
        schema_name: str,
        schema: dict[str, Any],
        web_search: bool = False,
    ) -> dict[str, Any]: ...


def _http_transport(request: urllib.request.Request, timeout: float) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
            message = parsed.get("error", {}).get("message", body)
        except (AttributeError, json.JSONDecodeError):
            message = body
        raise ProviderError(f"Provider API returned HTTP {exc.code}: {str(message)[:500]}") from exc
    except urllib.error.URLError as exc:
        raise ProviderError(f"Could not reach the provider API: {exc.reason}") from exc


def _request_json(
    *,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
    transport: Transport,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    return transport(request, timeout)


def _parse_json_object(text: str, schema: dict[str, Any]) -> dict[str, Any]:
    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProviderError("The model returned invalid JSON.") from exc
    if not isinstance(result, dict):
        raise ProviderError("The model response must be a JSON object.")
    _validate_value(result, schema, "response")
    return result


def _validate_value(value: Any, schema: dict[str, Any], path: str) -> None:
    expected = schema.get("type")
    if expected == "object":
        if not isinstance(value, dict):
            raise ProviderError(f"{path} must be an object.")
        for key in schema.get("required", []):
            if key not in value:
                raise ProviderError(f"{path}.{key} is required.")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unknown = set(value) - set(properties)
            if unknown:
                raise ProviderError(f"{path} contains unsupported fields: {', '.join(sorted(unknown))}")
        for key, child in properties.items():
            if key in value:
                _validate_value(value[key], child, f"{path}.{key}")
    elif expected == "array":
        if not isinstance(value, list):
            raise ProviderError(f"{path} must be an array.")
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", float("inf")):
            raise ProviderError(f"{path} has an invalid number of items.")
        for index, item in enumerate(value):
            _validate_value(item, schema.get("items", {}), f"{path}[{index}]")
    elif expected == "string" and not isinstance(value, str):
        raise ProviderError(f"{path} must be a string.")
    elif expected == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ProviderError(f"{path} must be a number.")
        if value < schema.get("minimum", float("-inf")) or value > schema.get("maximum", float("inf")):
            raise ProviderError(f"{path} is outside the permitted range.")
    elif expected == "boolean" and not isinstance(value, bool):
        raise ProviderError(f"{path} must be a boolean.")


@dataclass(slots=True)
class OpenAIResponsesClient:
    api_key: str
    model: str
    base_url: str = "https://api.openai.com/v1"
    timeout: float = 120.0
    transport: Transport = _http_transport

    def generate_json(self, *, instructions: str, input_text: str, schema_name: str, schema: dict[str, Any], web_search: bool = False) -> dict[str, Any]:
        self._check_configuration("OPENAI_API_KEY")
        payload: dict[str, Any] = {
            "model": self.model,
            "instructions": instructions,
            "input": input_text,
            "store": False,
            "text": {"format": {"type": "json_schema", "name": schema_name, "strict": True, "schema": schema}},
        }
        if web_search:
            payload["tools"] = [{"type": "web_search"}]
        response = _request_json(
            url=f"{self.base_url.rstrip('/')}/responses",
            payload=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout,
            transport=self.transport,
        )
        return _parse_json_object(self._extract_output_text(response), schema)

    def _check_configuration(self, key_name: str) -> None:
        if not self.api_key:
            raise ProviderError(f"{key_name} is required for this provider.")
        if not self.model:
            raise ProviderError("A model identifier is required.")

    @staticmethod
    def _extract_output_text(response: dict[str, Any]) -> str:
        direct = response.get("output_text")
        if isinstance(direct, str) and direct:
            return direct
        for item in response.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "output_text" and content.get("text"):
                    return str(content["text"])
        raise ProviderError("The OpenAI response contained no output text.")


@dataclass(slots=True)
class AnthropicMessagesClient:
    api_key: str
    model: str
    base_url: str = "https://api.anthropic.com"
    timeout: float = 120.0
    transport: Transport = _http_transport

    def generate_json(self, *, instructions: str, input_text: str, schema_name: str, schema: dict[str, Any], web_search: bool = False) -> dict[str, Any]:
        if web_search:
            raise ProviderError("Web search is not enabled in the RAJIH Anthropic adapter.")
        if not self.api_key:
            raise ProviderError("ANTHROPIC_API_KEY is required for this provider.")
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "system": instructions,
            "messages": [{"role": "user", "content": input_text}],
            "output_config": {"format": {"type": "json_schema", "schema": schema}},
        }
        response = _request_json(
            url=f"{self.base_url.rstrip('/')}/v1/messages",
            payload=payload,
            headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
            timeout=self.timeout,
            transport=self.transport,
        )
        for block in response.get("content", []):
            if block.get("type") == "text" and block.get("text"):
                return _parse_json_object(str(block["text"]), schema)
        raise ProviderError("The Anthropic response contained no text block.")


@dataclass(slots=True)
class GeminiGenerateContentClient:
    api_key: str
    model: str
    base_url: str = "https://generativelanguage.googleapis.com"
    timeout: float = 120.0
    transport: Transport = _http_transport

    def generate_json(self, *, instructions: str, input_text: str, schema_name: str, schema: dict[str, Any], web_search: bool = False) -> dict[str, Any]:
        if web_search:
            raise ProviderError("Web search is not enabled in the RAJIH Gemini adapter.")
        if not self.api_key:
            raise ProviderError("GEMINI_API_KEY is required for this provider.")
        model = urllib.parse.quote(self.model, safe="-._")
        payload = {
            "systemInstruction": {"parts": [{"text": instructions}]},
            "contents": [{"role": "user", "parts": [{"text": input_text}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": schema},
            "store": False,
        }
        response = _request_json(
            url=f"{self.base_url.rstrip('/')}/v1beta/models/{model}:generateContent",
            payload=payload,
            headers={"x-goog-api-key": self.api_key},
            timeout=self.timeout,
            transport=self.transport,
        )
        try:
            parts = response["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("The Gemini response contained no candidate text.") from exc
        text = "".join(str(part.get("text", "")) for part in parts)
        return _parse_json_object(text, schema)


@dataclass(slots=True)
class DeepSeekChatClient:
    api_key: str
    model: str
    base_url: str = "https://api.deepseek.com"
    timeout: float = 120.0
    transport: Transport = _http_transport

    def generate_json(self, *, instructions: str, input_text: str, schema_name: str, schema: dict[str, Any], web_search: bool = False) -> dict[str, Any]:
        if web_search:
            raise ProviderError("Web search is not enabled in the RAJIH DeepSeek adapter.")
        if not self.api_key:
            raise ProviderError("DEEPSEEK_API_KEY is required for this provider.")
        system = f"{instructions}\nReturn JSON only. Follow this JSON Schema exactly:\n{json.dumps(schema)}"
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": input_text}],
            "response_format": {"type": "json_object"},
            "max_tokens": 4096,
            "stream": False,
        }
        response = _request_json(
            url=f"{self.base_url.rstrip('/')}/chat/completions",
            payload=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout,
            transport=self.transport,
        )
        try:
            text = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("The DeepSeek response contained no message content.") from exc
        if not text:
            raise ProviderError("The DeepSeek response returned empty content; retry the request.")
        return _parse_json_object(str(text), schema)


@dataclass(slots=True)
class OpenRouterChatClient:
    api_key: str
    model: str
    base_url: str = "https://openrouter.ai/api/v1"
    timeout: float = 120.0
    transport: Transport = _http_transport

    def generate_json(self, *, instructions: str, input_text: str, schema_name: str, schema: dict[str, Any], web_search: bool = False) -> dict[str, Any]:
        if not self.api_key:
            raise ProviderError("OPENROUTER_API_KEY is required for this provider.")
        if not self.model:
            raise ProviderError("A model identifier is required.")
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": input_text},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
            },
            "provider": {"require_parameters": True},
            "stream": False,
        }
        if web_search:
            payload["plugins"] = [{"id": "web"}]
        response = _request_json(
            url=f"{self.base_url.rstrip('/')}/chat/completions",
            payload=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "X-OpenRouter-Title": "RAJIH Engine",
            },
            timeout=self.timeout,
            transport=self.transport,
        )
        try:
            text = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("The OpenRouter response contained no message content.") from exc
        if not text:
            raise ProviderError("The OpenRouter response returned empty content; retry the request.")
        return _parse_json_object(str(text), schema)


ProcessRunner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(slots=True)
class CodexSubscriptionClient:
    """Use the official Codex CLI and its saved ChatGPT authentication."""

    model: str = "codex-default"
    executable: str = "codex"
    timeout: float = 600.0
    runner: ProcessRunner = subprocess.run

    def generate_json(self, *, instructions: str, input_text: str, schema_name: str, schema: dict[str, Any], web_search: bool = False) -> dict[str, Any]:
        prompt = (
            f"{instructions}\n\n"
            "Complete only the requested reasoning task. Do not modify files or run commands. "
            "Return only the JSON object required by the supplied output schema.\n\n"
            f"Input:\n{input_text}"
        )
        try:
            with tempfile.TemporaryDirectory(prefix="rajih-codex-") as temp_dir:
                temp_path = Path(temp_dir)
                schema_path = temp_path / f"{schema_name}.schema.json"
                output_path = temp_path / "response.json"
                schema_path.write_text(json.dumps(schema), encoding="utf-8")

                command = [self.executable]
                if web_search:
                    command.append("--search")
                command.extend(["exec", "--ephemeral", "--sandbox", "read-only"])
                if self.model and self.model != "codex-default":
                    command.extend(["--model", self.model])
                command.extend([
                    "--output-schema",
                    str(schema_path),
                    "--output-last-message",
                    str(output_path),
                    "-",
                ])
                result = self.runner(
                    command,
                    cwd=Path.cwd(),
                    capture_output=True,
                    text=True,
                    input=prompt,
                    timeout=self.timeout,
                    check=False,
                )
                if result.returncode != 0:
                    detail = (result.stderr or result.stdout or "unknown Codex CLI error").strip()
                    raise ProviderError(f"Codex CLI failed: {detail[:500]}")
                if not output_path.exists():
                    raise ProviderError("Codex CLI did not write its final response.")
                return _parse_json_object(output_path.read_text(encoding="utf-8"), schema)
        except FileNotFoundError as exc:
            raise ProviderError("Codex CLI was not found. Install it, then run 'codex login'.") from exc
        except subprocess.TimeoutExpired as exc:
            raise ProviderError(f"Codex CLI exceeded the {self.timeout:g}-second timeout.") from exc
