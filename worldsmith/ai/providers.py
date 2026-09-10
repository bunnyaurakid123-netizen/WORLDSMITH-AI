from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from .schema import WORLD_PLAN_SCHEMA


@dataclass
class AIResponse:
    provider: str
    text: str
    latency_ms: int = 0
    usage: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class ProviderError(RuntimeError):
    pass


def _post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout: int = 90,
    retries: int = 2,
) -> dict[str, Any]:
    last: Exception | None = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", **(headers or {})},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")[:2000]
            if exc.code in {400, 401, 403, 404}:
                raise ProviderError(f"HTTP {exc.code}: {body}") from exc
            last = ProviderError(f"HTTP {exc.code}: {body}")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
        if attempt < retries:
            time.sleep(0.7 * (2**attempt))
    raise ProviderError(str(last or "request failed"))


def _effort(value: str) -> str:
    value = str(value or "high").lower().strip()
    return value if value in {"none", "low", "medium", "high", "xhigh", "max"} else "high"


def _gemini_effort(value: str) -> str:
    value = _effort(value)
    return value if value in {"low", "medium", "high"} else "high"


def _timed(fn: Callable[[], AIResponse]) -> AIResponse:
    started = time.perf_counter()
    result = fn()
    result.latency_ms = int((time.perf_counter() - started) * 1000)
    return result


def _openai_call(api_key: str, model: str, prompt: str, reasoning: str, schema: dict) -> AIResponse:
    data = _post_json(
        "https://api.openai.com/v1/responses",
        {
            "model": model or "gpt-5.6",
            "input": prompt,
            "store": False,
            "reasoning": {"effort": _effort(reasoning)},
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "worldsmith_plan",
                    "description": "A safe, deterministic Minecraft world editing plan.",
                    "strict": True,
                    "schema": schema,
                }
            },
        },
        {"Authorization": f"Bearer {api_key}"},
    )
    text = str(data.get("output_text", "")).strip()
    if not text:
        parts: list[str] = []
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    parts.append(str(content["text"]))
        text = "\n".join(parts).strip()
    if not text:
        raise ProviderError("OpenAI returned no structured text")
    return AIResponse("openai", text, usage=data.get("usage"), metadata={"model": model or "gpt-5.6"})


def call_openai(api_key: str, model: str, prompt: str, reasoning: str = "high", schema: dict | None = None) -> AIResponse:
    if not api_key:
        raise ProviderError("OpenAI key not configured")
    return _timed(lambda: _openai_call(api_key, model, prompt, reasoning, schema or WORLD_PLAN_SCHEMA))


def _gemini_call(api_key: str, model: str, prompt: str, reasoning: str, schema: dict) -> AIResponse:
    try:
        from google import genai
    except ImportError as exc:
        raise ProviderError("google-genai is not installed") from exc

    client = genai.Client(api_key=api_key)
    model_name = model or "gemini-3.8-flash"
    level = _gemini_effort(reasoning)
    response = None
    interactions = getattr(client, "interactions", None)
    if interactions is not None and hasattr(interactions, "create"):
        response = interactions.create(
            model=model_name,
            input=prompt,
            generation_config={"thinking_level": level},
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": schema,
            },
        )
        text = str(getattr(response, "output_text", "") or "").strip()
    else:
        try:
            from google.genai import types
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
        except Exception as exc:
            raise ProviderError(f"Gemini structured-output call failed: {exc}") from exc
        text = str(getattr(response, "text", "") or "").strip()
    if not text:
        raise ProviderError("Gemini returned no structured text")
    return AIResponse("gemini", text, metadata={"model": model_name, "thinking_level": level})


def call_gemini(api_key: str, model: str, prompt: str, reasoning: str = "high", schema: dict | None = None) -> AIResponse:
    if not api_key:
        raise ProviderError("Gemini key not configured")
    return _timed(lambda: _gemini_call(api_key, model, prompt, reasoning, schema or WORLD_PLAN_SCHEMA))


def _ollama_call(base_url: str, model: str, prompt: str, schema: dict) -> AIResponse:
    model_name = model or "gemma3"
    data = _post_json(
        base_url.rstrip("/") + "/api/chat",
        {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": schema,
            "options": {"temperature": 0},
        },
        timeout=120,
    )
    message = data.get("message", {}) or {}
    text = str(message.get("content", "")).strip()
    if not text:
        raise ProviderError("Ollama returned no structured text")
    usage = {
        key: data.get(key)
        for key in ("total_duration", "load_duration", "prompt_eval_count", "eval_count")
        if key in data
    }
    return AIResponse("ollama", text, usage=usage, metadata={"model": model_name})


def call_ollama(base_url: str, model: str, prompt: str, schema: dict | None = None) -> AIResponse:
    return _timed(lambda: _ollama_call(base_url, model, prompt, schema or WORLD_PLAN_SCHEMA))


def provider_probe(settings) -> dict[str, str]:
    """Cheap configuration probe; never sends user world data."""
    result = {
        "openai": "configured" if getattr(settings, "openai_key", "") else "missing-key",
        "gemini": "configured" if getattr(settings, "gemini_key", "") else "missing-key",
        "ollama": "configured" if getattr(settings, "ollama_url", "") else "missing-url",
    }
    return result
