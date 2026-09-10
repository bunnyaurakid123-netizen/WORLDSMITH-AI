from __future__ import annotations

import concurrent.futures
import json
from dataclasses import dataclass
from typing import Callable

from .providers import AIResponse, call_gemini, call_ollama, call_openai


PLAN_REVIEW_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "score": {"type": "number"},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "issues": {"type": "array", "items": {"type": "string"}},
        "improvements": {"type": "array", "items": {"type": "string"}},
        "must_preserve": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["score", "strengths", "issues", "improvements", "must_preserve"],
}


@dataclass(frozen=True)
class PlanReview:
    provider: str
    score: float
    strengths: tuple[str, ...]
    issues: tuple[str, ...]
    improvements: tuple[str, ...]
    must_preserve: tuple[str, ...]


@dataclass
class CriticResult:
    reviews: list[PlanReview]
    errors: list[str]

    @property
    def average_score(self) -> float:
        return round(sum(r.score for r in self.reviews) / len(self.reviews), 2) if self.reviews else 0.0

    def feedback(self, limit: int = 18) -> list[str]:
        items: list[str] = []
        seen: set[str] = set()
        for review in sorted(self.reviews, key=lambda r: r.score, reverse=True):
            for text in (*review.issues, *review.improvements):
                text = str(text).strip()
                if text and text.lower() not in seen:
                    seen.add(text.lower())
                    items.append(text)
                    if len(items) >= limit:
                        return items
        return items


def _extract_json(text: str) -> dict:
    value = json.loads(str(text).strip())
    if not isinstance(value, dict):
        raise ValueError("reviewer output is not an object")
    return value


def _review_prompt(plan: dict, world_context: str) -> str:
    return (
        "You are WorldSmith's independent quality critic. Review this proposed Minecraft Java world plan. "
        "Do not redesign the whole plan. Evaluate it for spatial composition, terrain plausibility, settlement logic, "
        "architectural variety, interior intent, road/bridge connectivity, redstone intent, performance and safety. "
        "Return ONLY the requested JSON review. Keep issues actionable and concise.\n\n"
        "WORLD CONTEXT:\n" + world_context[:10000] + "\n\nPLAN:\n" + json.dumps(plan, indent=2)[:28000]
    )


class PlanCritic:
    def __init__(self, settings):
        self.settings = settings

    def review(self, plan: dict, world_context: str = "", activity: Callable[[str], None] | None = None) -> CriticResult:
        prompt = _review_prompt(plan, world_context)
        jobs: dict[str, Callable[[], AIResponse]] = {}
        if self.settings.openai_key:
            jobs["openai"] = lambda: call_openai(self.settings.openai_key, self.settings.openai_model, prompt, self.settings.ai_reasoning, PLAN_REVIEW_SCHEMA)
        if self.settings.gemini_key:
            level = self.settings.ai_reasoning if str(self.settings.ai_reasoning).lower() in {"low", "medium", "high"} else "high"
            jobs["gemini"] = lambda: call_gemini(self.settings.gemini_key, self.settings.gemini_model, prompt, level, PLAN_REVIEW_SCHEMA)
        jobs["ollama"] = lambda: call_ollama(self.settings.ollama_url, self.settings.ollama_model, prompt, PLAN_REVIEW_SCHEMA)

        reviews: list[PlanReview] = []
        errors: list[str] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            futures = {pool.submit(fn): name for name, fn in jobs.items()}
            for future in concurrent.futures.as_completed(futures):
                provider = futures[future]
                try:
                    response = future.result()
                    payload = _extract_json(response.text)
                    score = max(0.0, min(100.0, float(payload.get("score", 0))))
                    review = PlanReview(
                        provider=provider,
                        score=score,
                        strengths=tuple(str(x)[:220] for x in payload.get("strengths", [])[:8]),
                        issues=tuple(str(x)[:260] for x in payload.get("issues", [])[:10]),
                        improvements=tuple(str(x)[:260] for x in payload.get("improvements", [])[:10]),
                        must_preserve=tuple(str(x)[:220] for x in payload.get("must_preserve", [])[:8]),
                    )
                    reviews.append(review)
                    if activity:
                        activity(f"{provider.title()} • critic score={score:.1f}")
                except Exception as exc:
                    errors.append(f"{provider}: {exc}")
                    if activity:
                        activity(f"{provider.title()} • critic failed: {exc}")
        return CriticResult(reviews, errors)
