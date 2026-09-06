# WorldSmith AI

WorldSmith AI is a standalone Minecraft Java world editor and procedural builder. It is not a Minecraft mod and does not need to run inside Minecraft.

## What it does

- Automatically discovers Minecraft Java `saves` directories on Windows/macOS/Linux, including common `.minecraft` and TLauncher locations.
- Opens existing worlds through Amulet Core and saves edits directly back to the world.
- Makes a timestamped backup before generation by default.
- Uses a multi-provider AI planner with Ollama + OpenAI + Gemini.
- Runs configured providers in parallel, validates their JSON plans, then asks an available provider to reconcile the candidates into one plan.
- Includes an offline fallback planner when no provider is available.
- Generates procedural mountain terrain with layered deterministic noise.
- Generates roads, castles/towers, village shells, basic furnished interiors and a compact redstone gate mechanism.
- Keeps AI credentials user-local and out of the repository.

## Architecture

```text
Desktop UI (PySide6)
        |
        +-- Save Scanner
        |
        +-- World Service (Amulet Core)
        |
        +-- AI Ensemble
        |     +-- Ollama (local)
        |     +-- OpenAI
        |     +-- Gemini
        |
        +-- Planner / Sanitizer
        |
        +-- Procedural Builder
        |     +-- Terrain
        |     +-- Roads
        |     +-- Structures
        |     +-- Interiors
        |     +-- Redstone
        |
        +-- Backup / Save
```

## Install

Python 3.10+ is required.

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python -m worldsmith.app
```

On Linux/macOS, activate `.venv/bin/activate` instead.

## AI providers

Ollama is used locally at `http://localhost:11434` by default. Each user enters their own OpenAI and Gemini API keys in Settings; no shared secret is bundled into the program.

## World editing

WorldSmith works on the actual Java save directory and should be used while Minecraft is closed. A timestamped backup is created before edits by default.

The current generation engine focuses on a strong, deterministic foundation: layered mountain terrain, roads, architectural shells, interiors and a redstone gate. The plan schema is intentionally structured so additional terrain, city, dungeon, biome and redstone generators can be added without changing the AI interface.

## Build Windows executable

```bash
pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --name WorldSmithAI run_worldsmith.py
```

A GitHub Actions workflow is included for Windows builds.