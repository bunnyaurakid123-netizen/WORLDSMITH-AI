# WorldSmith AI

WorldSmith AI is a standalone Minecraft Java world editor and procedural builder. It is **not a Minecraft mod** and does not need to run inside Minecraft.

## Current features

- Automatically discovers Minecraft Java `saves` directories on Windows/macOS/Linux, including common `.minecraft` and TLauncher locations.
- Opens existing worlds through Amulet Core and saves edits directly back to the world.
- Makes a timestamped backup before generation by default.
- Multi-provider AI planning with **Ollama + OpenAI + Gemini**.
- Runs configured providers in parallel, validates their structured plans, then uses an available model to reconcile them.
- Offline fallback planner when no remote provider is configured.
- Transparent **AI activity log** showing what stage/provider is running without exposing private model chain-of-thought.
- Persistent local **AI memory** stored in SQLite, with manual remember/forget controls and recent-session recall.
- Interactive **3D terrain preview** using Qt OpenGL before writing a plan into a world.
- Google account sign-in using desktop OAuth/OpenID Connect for identity only. WorldSmith does not request Gmail message access.
- Procedural mountain terrain with layered deterministic noise.
- Roads, castles/towers, village shells, basic furnished interiors and a compact redstone gate mechanism.
- User-provided provider credentials remain local and are never committed to the repository.

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
        +-- AI Activity Events
        |
        +-- Local Memory (SQLite)
        |
        +-- Planner / Sanitizer
        |
        +-- 3D Preview (Qt OpenGL)
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

## Install from source

Python 3.10+ is required. PySide6 itself is a native desktop Qt binding, and the official Qt for Python docs recommend using a virtual environment. citeturn703611search3turn703611search7

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python run_worldsmith.py
```

On Linux/macOS, activate `.venv/bin/activate` instead.

## AI providers

Ollama is used locally at `http://localhost:11434` by default. Each user can enter their own OpenAI and Gemini API keys in Settings. No shared key is bundled into WorldSmith.

The current Gemini integration uses the model HTTP API, and Google’s current developer docs also provide the `google-genai` SDK as the recommended modern Python library. citeturn284555search0turn284555search4

## Google login setup

WorldSmith uses Google OAuth for **account identity**, not Gmail mailbox access. The desktop OAuth flow requires a Google Cloud OAuth client of type **Desktop app**; Google documents that setup for installed applications. citeturn284555search3

1. Create a Desktop app OAuth client in Google Cloud.
2. Download its JSON client file.
3. In WorldSmith Settings, choose that JSON file under **Google account**.
4. Press **Sign in with Google**.
5. The browser completes OAuth and WorldSmith stores the refresh token through the operating-system keyring.

## Memory

Memory is stored locally in `~/.worldsmith/memory.db`.

WorldSmith recalls relevant saved preferences and recent sessions when building a new plan. The user can inspect and delete memories from the Memory page.

## World editing

WorldSmith works on the actual Java save directory and should be used while Minecraft is closed. A timestamped backup is created before edits by default.

The generation engine is intentionally structured so new terrain, city, biome, dungeon, interior and redstone generators can be added without changing the AI interface.

## Windows EXE

PyInstaller can package a Python application as a single executable with `--onefile`, and its documentation notes that Windows executables should be built on Windows rather than cross-compiled. citeturn640067search0turn640067search1

For a local Windows build:

```powershell
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean worldsmith.spec
```

The executable is produced as:

```text
dist\\WorldSmithAI.exe
```

A GitHub Actions workflow also builds this Windows executable automatically on pushes to `main` and uploads it as the `WorldSmithAI-windows` artifact.
