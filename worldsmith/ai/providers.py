from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .system_prompt import WORLDsmith_AI_SYSTEM_PROMPT

@dataclass
class AIResponse:
    provider: str
    text: str
    raw: dict[str, Any] | None = None
    usage: dict[str, Any] | None = None
    model: str | None = None

class ProviderError(RuntimeError): pass


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None, timeout: int = 120) -> dict[str, Any]:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **(headers or {})}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read().decode())
    except urllib.error.HTTPError as e: raise ProviderError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:1200]}") from e
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e: raise ProviderError(str(e)) from e


def _effort(value: str) -> str:
    v = str(value or "high").lower().strip(); return v if v in {"none", "low", "medium", "high", "xhigh", "max"} else "high"


def _extract_json_text(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"): text = text[:-3]
    return text.strip()


def call_openai(api_key: str, model: str, prompt: str, schema: dict[str, Any] | None = None, reasoning: str = "high") -> AIResponse:
    if not api_key: raise ProviderError("OpenAI key not configured")
    payload: dict[str, Any] = {
        "model": model or "gpt-5.6", "instructions": WORLDsmith_AI_SYSTEM_PROMPT,
        "input": prompt, "reasoning": {"effort": _effort(reasoning)},
    }
    if schema:
        payload["text"] = {"format": {"type": "json_schema", "name": "world_plan", "strict": True, "schema": schema}}
    last = None
    for attempt in range(2):
        try:
            data = _post_json("https://api.openai.com/v1/responses", payload, {"Authorization": f"Bearer {api_key}"})
            text = str(data.get("output_text", "")).strip()
            if not text:
                parts=[]
                for item in data.get("output", []):
                    for c in item.get("content", []):
                        if c.get("type") in {"output_text", "text"} and c.get("text"): parts.append(str(c["text"]))
                text="\n".join(parts).strip()
            if not text: raise ProviderError("OpenAI returned no text")
            return AIResponse("openai", _extract_json_text(text), data, data.get("usage"), data.get("model"))
        except ProviderError as e:
            last=e
    raise last or ProviderError("OpenAI request failed")


def call_gemini(api_key: str, model: str, prompt: str, schema: dict[str, Any] | None = None, reasoning: str = "high") -> AIResponse:
    if not api_key: raise ProviderError("Gemini key not configured")
    try: from google import genai
    except ImportError as e: raise ProviderError("google-genai is not installed") from e
    try:
        client=genai.Client(api_key=api_key); model=model or "gemini-3.8-flash"; cfg={"thinking_level": _effort(reasoning)}
        if schema: cfg.update({"response_mime_type":"application/json", "response_schema":schema})
        response=client.models.generate_content(model=model, contents=f"{WORLDsmith_AI_SYSTEM_PROMPT}\n\n{prompt}", config=cfg)
        text=str(getattr(response, "text", "") or "").strip()
        if not text: raise ProviderError("Gemini returned no text")
        usage=getattr(response, "usage_metadata", None); usage=vars(usage) if usage and hasattr(usage,"__dict__") else None
        return AIResponse("gemini", _extract_json_text(text), None, usage, model)
    except ProviderError: raise
    except Exception as e: raise ProviderError(f"Gemini SDK error: {e}") from e


def call_ollama(base_url: str, model: str, prompt: str, schema: dict[str, Any] | None = None, reasoning: str = "high") -> AIResponse:
    payload={"model":model or "gemma3", "messages":[{"role":"system","content":WORLDsmith_AI_SYSTEM_PROMPT},{"role":"user","content":prompt}], "stream":False, "think":_effort(reasoning)}
    if schema: payload["format"]=schema
    data=_post_json(base_url.rstrip("/")+"/api/chat", payload)
    msg=data.get("message",{}); text=str(msg.get("content","")).strip()
    if not text: raise ProviderError("Ollama returned no text")
    return AIResponse("ollama", _extract_json_text(text), data, {"total_duration":data.get("total_duration"),"eval_count":data.get("eval_count")}, model or "gemma3")


def call_provider(provider: str, *, prompt: str, schema: dict[str, Any] | None = None, api_key: str = "", model: str = "", ollama_url: str = "http://127.0.0.1:11434", reasoning: str = "high") -> AIResponse:
    p=provider.lower().strip()
    if p=="openai": return call_openai(api_key, model, prompt, schema, reasoning)
    if p=="gemini": return call_gemini(api_key, model, prompt, schema, reasoning)
    if p=="ollama": return call_ollama(ollama_url, model, prompt, schema, reasoning)
    raise ProviderError(f"Unknown provider: {provider}")
