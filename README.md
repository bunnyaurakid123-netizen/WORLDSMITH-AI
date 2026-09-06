# WorldSmith AI

WorldSmith AI is a standalone desktop application for editing Minecraft Java saves. It is **not a Minecraft mod**.

## What is actually implemented

### Desktop editor
- PySide6 desktop UI with Overview, AI Builder, 3D Preview, Memory, World Inspector, Settings and AAA voxel tools.
- Automatically discovers common Minecraft Java save locations, including `.minecraft` and common TLauncher locations.
- Opens and writes real Java saves through Amulet Core.
- Timestamped backups before edits by default.
- Background AI planning and background world generation so large operations do not intentionally block the GUI.

### Multi-AI planning
- Ollama local backend.
- OpenAI backend.
- Gemini backend.
- Candidate plans can be generated in parallel and reconciled by a judge model.
- Structured JSON plan format for terrain, structures, roads, bridges and primitive voxel operations.
- Offline deterministic fallback when remote AI providers are unavailable.
- Stage-level AI activity log; private model chain-of-thought is not exposed.

### AI memory
- Local SQLite memory database under `~/.worldsmith/memory.db`.
- User memories and recent build sessions can be recalled during planning.
- Manual remember/forget controls.

### AAA editor foundation
- Transactional voxel editing with undo/redo.
- Fill, hollow, sphere and cylinder brushes.
- Selection normalization and volume limits.
- Live sampling of the opened Minecraft world.
- Interactive OpenGL preview with orbit, pan and zoom.
- Local Minecraft/resource-pack asset discovery.
- Asset-driven preview color resolution when matching block models/textures are available.

### Generation engine
- Deterministic multi-scale terrain noise.
- Mountain and ridge generation.
- River carving and water placement.
- Basic climate/biome material variation.
- Roads and bridges.
- Castle, village, city, tower and generic structure generation.
- Interior furnishing pass.
- Architecture finishing pass with roofs, chimneys, balconies, lighting and furniture.
- Explicit-state redstone gate generation.
- AI-authored primitive voxel operations with hard operation and block-budget limits.

### Quality and safety
- Plan sanitization before building.
- Coordinate and size limits.
- Structure overlap detection.
- Deterministic low-risk plan repairs.
- Post-build factual verification of expected structures and road endpoints.
- Persistent build audit JSON reports under `~/.worldsmith/runs/`.
- Player-build protection settings are part of the planning policy.

### Credentials and login
- OpenAI and Gemini API keys are stored through the operating-system keyring rather than the settings JSON.
- Google OAuth is identity-only with `openid`, `email` and `profile` scopes. No Gmail mailbox access is requested.

## Important current limitation

This repository is an evolving AAA editor/generation foundation. The viewport is a lightweight OpenGL voxel/heightfield renderer, not a full Minecraft-compatible renderer yet. The procedural builders are substantially more capable than the original prototype, but they are not equivalent to a hand-authored AAA Minecraft world or a complete Minecraft client renderer.

Redstone generation currently performs explicit-state placement and topology checks; it is **not yet a full redstone simulator**.

## Install from source

Python 3.10+ is required.

```bash
python -m venv .venv
.venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python run_worldsmith.py
```

On Linux/macOS, use `.venv/bin/activate` instead.

## AI providers

Ollama defaults to `http://localhost:11434`. Each user configures their own OpenAI and Gemini API keys in WorldSmith Settings.

## Google account setup

1. Create a Google OAuth client of type **Desktop app** in Google Cloud.
2. Download the OAuth client JSON.
3. Select the JSON file in WorldSmith Settings.
4. Press **Sign in with Google**.

WorldSmith uses this for application identity only.

## Windows executable

### One-click local build

Run:

```text
BUILD_WORLDSMITH.bat
```

The finished executable is placed at:

```text
dist\\WorldSmithAI.exe
```

To launch an existing build, use:

```text
RUN_WORLDSMITH.bat
```

GitHub Actions also contains a Windows build workflow that installs dependencies, runs the test suite, builds the EXE with PyInstaller and verifies that `dist\\WorldSmithAI.exe` exists before uploading it as an artifact.

## Tests

The test suite covers planning, save scanning, editor transactions/brushes, primitive-operation limits, quality repair, asset catalog behavior, secrets, audit persistence, redstone contracts and post-build verification.
