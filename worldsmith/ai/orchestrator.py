from __future__ import annotations

import concurrent.futures
import json
import re
from dataclasses import dataclass
from typing import Callable

from .providers import AIResponse, call_gemini, call_ollama, call_openai
from worldsmith.config import Settings

SYSTEM_PROMPT = """You are WorldSmith, an expert Minecraft Java world architect and procedural level designer.
Return ONLY valid JSON. Never return markdown.
Design edits for an existing Minecraft Java save and preserve player-built areas.
Think in terms of spatial composition, believable terrain, architecture, gameplay flow and block-efficient construction.
Prefer purpose-built structures over repetitive cubes. Use primitive voxel operations only for details and terrain accents.
Schema:
{
  "summary": string,
  "style": string,
  "seed": integer,
  "center": [int,int,int],
  "terrain": {
    "enabled": bool,
    "radius": int,
    "mountain_height": int,
    "roughness": number,
    "water": bool,
    "vegetation": bool
  },
  "builds": [
    {"type":string,"x":int,"y":int,"z":int,"width":int,"depth":int,"height":int,"style":string,"interior":bool,"redstone":bool}
  ],
  "roads": [{"x1":int,"z1":int,"x2":int,"z2":int,"y":int,"width":int}],
  "bridges": [{"type":string,"x":int,"y":int,"z":int,"x2":int,"z2":int,"width":int}],
  "operations": [
    {"op":"fill_box|hollow_box|sphere|cylinder","block":string,"x1":int,"y1":int,"z1":int,"x2":int,"y2":int,"z2":int,"x":int,"y":int,"z":int,"radius":int,"height":int}
  ],
  "notes": [string]
}
Use up to 24 major structures and at most 48 primitive operations. Keep primitive operations compact and purposeful. Prefer varied sizes and purposeful locations. Use real coordinates around the requested center.
"""

Activity = Callable[[str], None]


@dataclass
class EnsembleResult:
    plan: dict
    responses: list[AIResponse]
    errors: list[str]
    activity: list[str]


def extract_json(text: str) -> dict:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    candidate = match.group(1) if match else text
    start, end = candidate.find("{"), candidate.rfind("}")
    candidate = candidate[start:end + 1] if start >= 0 and end > start else candidate
    return json.loads(candidate)


def built_in_plan(prompt, center=(0, 100, 0), radius=96):
    x, y, z = center
    return {
        "summary": prompt,
        "style": "cinematic natural fantasy",
        "seed": 1337,
        "center": [x, y, z],
        "terrain": {"enabled": True, "radius": radius, "mountain_height": 80, "roughness": 1.0, "water": True, "vegetation": True},
        "builds": [
            {"type": "castle", "x": x, "y": y + 3, "z": z, "width": 31, "depth": 31, "height": 28, "style": "stone spruce medieval", "interior": True, "redstone": True},
            {"type": "village", "x": x + 42, "y": y + 3, "z": z + 28, "width": 21, "depth": 21, "height": 10, "style": "spruce medieval", "interior": True, "redstone": False},
            {"type": "tower", "x": x - 38, "y": y + 3, "z": z - 22, "width": 11, "depth": 11, "height": 22, "style": "stone watchtower", "interior": True, "redstone": False},
        ],
        "roads": [{"x1": x, "z1": z, "x2": x + 42, "z2": z + 28, "y": y + 4, "width": 3}],
        "bridges": [],
        "operations": [],
        "notes": ["Offline deterministic fallback plan"],
    }


class Ensemble:
    def __init__(self, settings: Settings):
        self.settings = settings

    def plan(self, user_prompt, context="", center=(0, 100, 0), activity: Activity | None = None):
        log: list[str] = []

        def emit(message: str):
            log.append(message)
            if activity:
                activity(message)

        prompt = SYSTEM_PROMPT + "\nWORLD CONTEXT:\n" + context[:12000] + "\nUSER REQUEST:\n" + user_prompt
        jobs = {}
        emit("Analyzing request, world context and long-term memory…")
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            if self.settings.openai_key:
                emit(f"OpenAI • generating candidate with {self.settings.openai_model}")
                jobs[pool.submit(call_openai, self.settings.openai_key, self.settings.openai_model, prompt)] = "openai"
            else:
                emit("OpenAI • skipped (no key configured)")
            if self.settings.gemini_key:
                emit(f"Gemini • generating candidate with {self.settings.gemini_model}")
                jobs[pool.submit(call_gemini, self.settings.gemini_key, self.settings.gemini_model, prompt)] = "gemini"
            else:
                emit("Gemini • skipped (no key configured)")
            emit(f"Ollama • generating candidate with {self.settings.ollama_model}")
            jobs[pool.submit(call_ollama, self.settings.ollama_url, self.settings.ollama_model, prompt)] = "ollama"

            responses, errors = [], []
            for future in concurrent.futures.as_completed(jobs):
                provider = jobs[future]
                try:
                    response = future.result(); responses.append(response); emit(f"{provider.title()} • candidate received")
                except Exception as exc:
                    errors.append(f"{provider}: {exc}"); emit(f"{provider.title()} • failed: {exc}")

        plans = []
        for response in responses:
            try:
                parsed = extract_json(response.text); parsed["_provider"] = response.provider; plans.append(parsed); emit(f"{response.provider.title()} • JSON candidate validated")
            except Exception as exc:
                errors.append(f"{response.provider}: invalid JSON ({exc})"); emit(f"{response.provider.title()} • invalid candidate discarded")

        if not plans:
            emit("No model candidate survived • using deterministic offline fallback")
            return EnsembleResult(built_in_plan(user_prompt, center, self.settings.default_radius), responses, errors, log)

        judge_prompt = SYSTEM_PROMPT + "\nYou are the WorldSmith planning judge. Reconcile ALL candidate plans into ONE superior plan. Favor natural terrain, coherent geography, varied architecture, useful interiors, purposeful roads, precise voxel detail and safe non-destructive edits. Return only the final JSON object.\nCANDIDATES:\n" + json.dumps(plans, indent=2)[:24000]
        chosen, judge_name = None, None
        judges = []
        if self.settings.openai_key: judges.append(("openai", lambda: call_openai(self.settings.openai_key, self.settings.openai_model, judge_prompt)))
        if self.settings.gemini_key: judges.append(("gemini", lambda: call_gemini(self.settings.gemini_key, self.settings.gemini_model, judge_prompt)))
        judges.append(("ollama", lambda: call_ollama(self.settings.ollama_url, self.settings.ollama_model, judge_prompt)))

        for name, fn in judges:
            try:
                emit(f"{name.title()} • judging and reconciling candidates")
                judge_response = fn(); chosen = extract_json(judge_response.text); judge_name = name
                responses.append(AIResponse(name + "-judge", judge_response.text)); emit(f"{name.title()} • final plan accepted"); break
            except Exception as exc:
                errors.append(f"{name}-judge: {exc}"); emit(f"{name.title()} • judge failed: {exc}")

        merged = built_in_plan(user_prompt, center, self.settings.default_radius)
        for key, value in (chosen or plans[0]).items():
            if not key.startswith("_"): merged[key] = value
        merged["_ensemble"] = [p.get("_provider", "unknown") for p in plans]
        if judge_name: merged["_judge"] = judge_name
        emit("Plan complete • ready for 3D preview")
        return EnsembleResult(merged, responses, errors, log)
