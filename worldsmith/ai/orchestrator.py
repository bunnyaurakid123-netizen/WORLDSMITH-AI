from __future__ import annotations

import concurrent.futures
import json
import re
from dataclasses import dataclass
from typing import Callable

from .providers import AIResponse, call_gemini, call_ollama, call_openai
from .schema import WORLD_PLAN_SCHEMA
from worldsmith.config import Settings

SYSTEM_PROMPT = """You are WorldSmith, an expert Minecraft Java world architect, level designer and world-editing agent.
Return ONLY a single JSON object matching the supplied schema.
You are planning edits for a real Minecraft Java save. Preserve player-built areas and avoid destructive assumptions.
Work from the actual world context and requested center. Design the whole scene, not isolated buildings.
Think in layers: geography -> climate -> terrain -> water -> transportation -> districts -> landmarks -> architecture -> interiors -> redstone -> decoration -> gameplay.
Prefer irregular, believable compositions over repeated cubes. Buildings need purposeful footprints, varied dimensions, readable entrances and interiors where requested.
Terrain should feel continuous: mountain ranges have foothills and valleys, rivers follow low terrain, roads follow geography, and settlements have civic logic.
Use primitive voxel operations only for bounded detail. Keep operations compact and explain important choices in notes.
"""

Activity = Callable[[str], None]


@dataclass
class EnsembleResult:
    plan: dict
    responses: list[AIResponse]
    errors: list[str]
    activity: list[str]
    candidate_scores: dict[str, float] | None = None


def extract_json(text: str) -> dict:
    text = str(text).strip()
    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    candidate = match.group(1) if match else text
    start, end = candidate.find("{"), candidate.rfind("}")
    if start >= 0 and end > start:
        candidate = candidate[start:end + 1]
    value = json.loads(candidate)
    if not isinstance(value, dict):
        raise ValueError("model output is not a JSON object")
    return value


def _number(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def score_plan(plan: dict) -> float:
    """Deterministic plan quality score used before the model judge."""
    terrain = plan.get("terrain", {}) if isinstance(plan.get("terrain"), dict) else {}
    builds = [b for b in plan.get("builds", []) if isinstance(b, dict)]
    roads = [r for r in plan.get("roads", []) if isinstance(r, dict)]
    bridges = [b for b in plan.get("bridges", []) if isinstance(b, dict)]
    ops = [o for o in plan.get("operations", []) if isinstance(o, dict)]
    score = 0.0
    score += min(20.0, len(builds) * 1.2)
    score += min(12.0, len(roads) * 0.75)
    score += min(6.0, len(bridges) * 1.2)
    score += min(10.0, sum(bool(b.get("interior")) for b in builds) * 0.6)
    score += min(8.0, sum(bool(b.get("redstone")) for b in builds) * 0.8)
    score += min(10.0, len(ops) * 0.25)
    if terrain.get("enabled", False): score += 6.0
    if terrain.get("water", False): score += 3.0
    if terrain.get("vegetation", False): score += 3.0
    if terrain.get("caves", False): score += 2.0
    if str(plan.get("style", "")).strip(): score += 3.0
    if str(plan.get("summary", "")).strip(): score += 2.0
    # Penalize repeated dimensions: variation is a simple proxy for authored composition.
    dimensions = {(b.get("width"), b.get("depth"), b.get("height")) for b in builds}
    if builds:
        score += min(8.0, len(dimensions) * 0.7)
    if len(builds) >= 5 and len(roads) >= 2: score += 5.0
    if len(builds) >= 4 and not roads: score -= 8.0
    if any(_number(b.get("width"), 0) < 5 or _number(b.get("depth"), 0) < 5 for b in builds): score -= 8.0
    return max(0.0, round(score, 2))


def built_in_plan(prompt, center=(0, 100, 0), radius=96):
    """Offline fallback that still produces a complete small world plan."""
    x, y, z = center
    lower = prompt.lower()
    city = any(word in lower for word in ("city", "town", "kingdom", "capital"))
    fortress = any(word in lower for word in ("castle", "fortress", "keep", "palace"))
    coast = any(word in lower for word in ("coast", "port", "harbor", "sea", "ocean"))
    snowy = any(word in lower for word in ("snow", "snowy", "alpine", "frozen"))
    style = "snowy medieval" if snowy else "cinematic natural fantasy"
    builds = [
        {"type": "castle" if fortress or not city else "city_hall", "x": x, "y": y + 3, "z": z, "width": 39 if fortress else 25, "depth": 39 if fortress else 25, "height": 30 if fortress else 22, "style": style, "interior": True, "redstone": True},
        {"type": "village" if not city else "market", "x": x + 46, "y": y + 3, "z": z + 24, "width": 25, "depth": 25, "height": 12, "style": style, "interior": True, "redstone": False},
        {"type": "tower", "x": x - 44, "y": y + 3, "z": z - 20, "width": 13, "depth": 13, "height": 25, "style": "stone watchtower", "interior": True, "redstone": False},
    ]
    if city:
        builds.extend([
            {"type": "blacksmith", "x": x - 34, "y": y + 3, "z": z + 32, "width": 11, "depth": 13, "height": 10, "style": style, "interior": True, "redstone": False},
            {"type": "warehouse", "x": x + 28, "y": y + 3, "z": z - 38, "width": 15, "depth": 17, "height": 12, "style": style, "interior": True, "redstone": False},
            {"type": "temple", "x": x - 4, "y": y + 3, "z": z + 50, "width": 19, "depth": 23, "height": 18, "style": style, "interior": True, "redstone": False},
        ])
    if coast:
        builds.append({"type": "lighthouse", "x": x + 56, "y": y + 3, "z": z - 52, "width": 11, "depth": 11, "height": 32, "style": "coastal stone", "interior": True, "redstone": True})
    roads = [
        {"x1": x, "z1": z, "x2": b["x"], "z2": b["z"], "y": y + 4, "width": 3}
        for b in builds[1:7]
    ]
    bridges = []
    if city:
        bridges.append({"type": "stone_bridge", "x": x - 8, "y": y + 6, "z": z + 10, "x2": x + 18, "z2": z + 10, "width": 4})
    return {
        "summary": prompt,
        "style": style,
        "seed": 1337,
        "center": [x, y, z],
        "terrain": {"enabled": True, "radius": radius, "mountain_height": 88 if snowy else 76, "roughness": 1.15, "water": True, "vegetation": True, "caves": True},
        "builds": builds,
        "roads": roads,
        "bridges": bridges,
        "operations": [],
        "notes": ["Offline deterministic fallback plan", "Use the generated plan as a safe baseline when no model is reachable."],
    }


class Ensemble:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _candidate_jobs(self, prompt: str, reasoning: str):
        jobs = {}
        if self.settings.openai_key:
            jobs["openai"] = lambda: call_openai(self.settings.openai_key, self.settings.openai_model, prompt, reasoning)
        if self.settings.gemini_key:
            jobs["gemini"] = lambda: call_gemini(self.settings.gemini_key, self.settings.gemini_model, prompt, reasoning)
        jobs["ollama"] = lambda: call_ollama(self.settings.ollama_url, self.settings.ollama_model, prompt)
        return jobs

    def plan(self, user_prompt, context="", center=(0, 100, 0), activity: Activity | None = None):
        log: list[str] = []

        def emit(message: str):
            log.append(message)
            if activity:
                activity(message)

        prompt = SYSTEM_PROMPT + "\nOUTPUT SCHEMA:\n" + json.dumps(WORLD_PLAN_SCHEMA) + "\nWORLD CONTEXT:\n" + context[:14000] + "\nUSER REQUEST:\n" + user_prompt
        reasoning = self.settings.ai_reasoning
        emit("Director • decomposing request into geography, architecture, systems and gameplay")

        responses: list[AIResponse] = []
        errors: list[str] = []
        jobs = self._candidate_jobs(prompt, reasoning)
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            futures = {pool.submit(fn): name for name, fn in jobs.items()}
            for future in concurrent.futures.as_completed(futures):
                name = futures[future]
                try:
                    response = future.result()
                    responses.append(response)
                    emit(f"{name.title()} • candidate received in {response.latency_ms} ms")
                except Exception as exc:
                    errors.append(f"{name}: {exc}")
                    emit(f"{name.title()} • failed: {exc}")

        plans = []
        for response in responses:
            try:
                parsed = extract_json(response.text)
                parsed["_provider"] = response.provider
                score = score_plan(parsed)
                plans.append((score, parsed, response.provider))
                emit(f"{response.provider.title()} • structured plan accepted • score={score:.2f}")
            except Exception as exc:
                errors.append(f"{response.provider}: invalid structured plan ({exc})")
                emit(f"{response.provider.title()} • candidate rejected: {exc}")

        if not plans:
            emit("Director • no provider candidate survived; using deterministic fallback")
            fallback = built_in_plan(user_prompt, center, self.settings.default_radius)
            return EnsembleResult(fallback, responses, errors, log, {"offline": score_plan(fallback)})

        plans.sort(key=lambda item: item[0], reverse=True)
        score_map = {provider: score for score, _, provider in plans}
        emit("Arbiter • ranking candidates before final reconciliation")
        shortlisted = [plan for _, plan, _ in plans[:3]]
        judge_prompt = (
            SYSTEM_PROMPT
            + "\nYou are the final WorldSmith architect. Reconcile the shortlisted candidates below. Preserve the strongest ideas, remove conflicts, improve spatial composition, and return ONE complete schema-valid plan. Do not merely copy one candidate.\n"
            + json.dumps(shortlisted, indent=2)[:36000]
        )
        chosen = None
        judge_name = None
        judge_order = []
        if self.settings.openai_key:
            judge_order.append(("openai", lambda: call_openai(self.settings.openai_key, self.settings.openai_model, judge_prompt, reasoning)))
        if self.settings.gemini_key:
            level = reasoning if str(reasoning).lower() in {"low", "medium", "high"} else "high"
            judge_order.append(("gemini", lambda: call_gemini(self.settings.gemini_key, self.settings.gemini_model, judge_prompt, level)))
        judge_order.append(("ollama", lambda: call_ollama(self.settings.ollama_url, self.settings.ollama_model, judge_prompt)))

        for name, fn in judge_order:
            try:
                emit(f"{name.title()} • final architecture arbitration")
                judge_response = fn()
                candidate = extract_json(judge_response.text)
                chosen_score = score_plan(candidate)
                best_score = plans[0][0]
                # Reject a judge output that is materially worse than the best candidate.
                if chosen_score + 6.0 < best_score:
                    raise ValueError(f"judge score {chosen_score:.2f} below candidate floor {best_score - 6.0:.2f}")
                chosen = candidate
                judge_name = name
                responses.append(judge_response)
                emit(f"{name.title()} • final plan accepted • score={chosen_score:.2f}")
                break
            except Exception as exc:
                errors.append(f"{name}-judge: {exc}")
                emit(f"{name.title()} • arbitration failed: {exc}")

        merged = built_in_plan(user_prompt, center, self.settings.default_radius)
        source = chosen or plans[0][1]
        for key, value in source.items():
            if not key.startswith("_"):
                merged[key] = value
        merged["_ensemble"] = [provider for _, _, provider in plans]
        merged["_candidate_scores"] = score_map
        if judge_name:
            merged["_judge"] = judge_name
        emit("Director • plan complete • ready for validation and 3D preview")
        return EnsembleResult(merged, responses, errors, log, score_map)
