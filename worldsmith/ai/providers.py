from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class AIResponse:
    provider: str
    text: str


class ProviderError(RuntimeError):
    pass


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None, timeout: int = 90) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ProviderError(f"HTTP {exc.code}: {exc.read().decode(errors='replace')[:1000]}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ProviderError(str(exc)) from exc


def call_openai(api_key: str, model: str, prompt: str) -> AIResponse:
    if not api_key:
        raise ProviderError("OpenAI key not configured")
    data = _post_json(
        "https://api.openai.com/v1/responses",
        {"model": model or "gpt-5.1", "input": prompt},
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
        raise ProviderError("OpenAI returned no text")
    return AIResponse("openai", text)


def call_gemini(api_key: str, model: str, prompt: str) -> AIResponse:
    if not api_key:
        raise ProviderError("Gemini key not configured")
    try:
        from google import genai
    except ImportError as exc:
        raise ProviderError("google-genai is not installed") from exc

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=model or "gemini-3.7-flash", contents=prompt)
        text = str(getattr(response, "text", "") or "").strip()
    except Exception as exc:
        raise ProviderError(f"Gemini SDK error: {exc}") from exc
    if not text:
        raise ProviderError("Gemini returned no text")
    return AIResponse("gemini", text)


def call_ollama(base_url: str, model: str, prompt: str) -> AIResponse:
    data = _post_json(
        base_url.rstrip("/") + "/api/chat",
        {"model": model or "gemma3", "messages": [{"role": "user", "content": prompt}], "stream": False},
    )
    text = str(data.get("message", {}).get("content", "")).strip()
    if not text:
        raise ProviderError("Ollama returned no text")
    return AIResponse("ollama", text)
