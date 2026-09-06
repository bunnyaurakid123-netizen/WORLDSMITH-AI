from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable

from .orchestrator import AIResponse, extract_json
from .providers import call_gemini, call_ollama, call_openai
from worldsmith.config import Settings


@dataclass(frozen=True)
class RepairResult:
    plan: dict
    provider: str
    response: AIResponse | None
    errors: tuple[str, ...]


class PlanRepairAgent:
    """Ask the configured AI ensemble to revise a plan using concrete QA findings."""

    SYSTEM = """You are the WorldSmith repair engineer.
Return ONLY a valid JSON object matching the WorldSmith plan schema.
You are repairing an existing plan after deterministic quality or post-build QA found issues.
Preserve all good existing work. Make the smallest practical changes necessary.
Never invent private player data, credentials, or hidden reasoning.
Prefer corrections to positions, dimensions, roads, bridges, interiors, redstone intent, and primitive operations.
Keep the result within normal WorldSmith safety bounds: <=24 major structures, <=48 primitive operations, bounded coordinates and sizes.
"""

    def __init__(self, settings: Settings):
        self.settings = settings

    def _call(self, provider: str, prompt: str):
        if provider == "openai":
            return call_openai(self.settings.openai_key, self.settings.openai_model, prompt, self.settings.ai_reasoning)
        if provider == "gemini":
            level = self.settings.ai_reasoning if self.settings.ai_reasoning in {"low", "medium", "high"} else "high"
            return call_gemini(self.settings.gemini_key, self.settings.gemini_model, prompt, level)
        return call_ollama(self.settings.ollama_url, self.settings.ollama_model, prompt)

    def repair(self, plan: dict, issues: list[dict] | list[str], activity: Callable[[str], None] | None = None) -> RepairResult:
        prompt = self.SYSTEM + "\nCURRENT PLAN:\n" + json.dumps(plan, indent=2)[:22000]
        prompt += "\nQA FINDINGS:\n" + json.dumps(issues, indent=2)[:12000]
        prompt += "\nReturn the revised complete plan only."

        providers: list[str] = []
        if self.settings.openai_key:
            providers.append("openai")
        if self.settings.gemini_key:
            providers.append("gemini")
        providers.append("ollama")

        errors: list[str] = []
        for provider in providers:
            try:
                if activity:
                    activity(f"Repair AI • {provider.title()} revising the plan from QA findings")
                response = self._call(provider, prompt)
                revised = extract_json(response.text)
                if activity:
                    activity(f"Repair AI • {provider.title()} returned a revised plan")
                return RepairResult(revised, provider, response, tuple(errors))
            except Exception as exc:
                errors.append(f"{provider}: {exc}")
                if activity:
                    activity(f"Repair AI • {provider.title()} failed: {exc}")
        return RepairResult(dict(plan), "none", None, tuple(errors))
