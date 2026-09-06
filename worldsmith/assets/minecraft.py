from __future__ import annotations

import json
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AssetSource:
    root: Path
    kind: str  # directory | jar | resource_pack
    label: str


class MinecraftAssetCatalog:
    """Discover vanilla/resource-pack assets for the local Minecraft installation."""

    def __init__(self, sources: list[AssetSource] | None = None):
        self.sources = sources or self.discover()
        self._json_cache: dict[tuple[str, str], dict | None] = {}

    @staticmethod
    def minecraft_roots() -> list[Path]:
        home = Path.home()
        roots: list[Path] = []
        appdata = os.getenv("APPDATA")
        if appdata:
            roots.append(Path(appdata) / ".minecraft")
        roots.extend([
            home / "AppData/Roaming/.minecraft",
            home / ".minecraft",
            home / "AppData/Roaming/.tlauncher/legacy/Minecraft/game",
            home / ".tlauncher/legacy/Minecraft/game",
        ])
        result: list[Path] = []
        seen: set[Path] = set()
        for root in roots:
            try:
                root = root.expanduser().resolve()
            except OSError:
                continue
            if root not in seen and root.is_dir():
                seen.add(root)
                result.append(root)
        return result

    @classmethod
    def discover(cls) -> list[AssetSource]:
        sources: list[AssetSource] = []
        seen: set[Path] = set()
        for root in cls.minecraft_roots():
            versions = root / "versions"
            if versions.is_dir():
                jars = sorted(versions.glob("*/*.jar"), key=lambda p: p.stat().st_mtime, reverse=True)
                for jar in jars[:8]:
                    if jar in seen:
                        continue
                    seen.add(jar)
                    sources.append(AssetSource(jar, "jar", f"Vanilla {jar.parent.name}"))

            packs = root / "resourcepacks"
            if packs.is_dir():
                for pack in sorted(packs.iterdir(), key=lambda p: p.name.casefold()):
                    if pack.is_file() and pack.suffix.lower() == ".zip":
                        sources.append(AssetSource(pack, "resource_pack", pack.stem))
                    elif pack.is_dir() and (pack / "assets").is_dir():
                        sources.append(AssetSource(pack, "resource_pack", pack.name))

        return sources

    def _read_bytes(self, source: AssetSource, relative: str) -> bytes | None:
        relative = relative.replace("\\", "/").lstrip("/")
        if source.kind in {"jar", "resource_pack"} and source.root.is_file():
            try:
                with zipfile.ZipFile(source.root) as archive:
                    return archive.read(relative)
            except (KeyError, OSError, zipfile.BadZipFile):
                return None
        if source.kind in {"jar", "resource_pack", "directory"}:
            path = source.root / relative
            try:
                return path.read_bytes() if path.is_file() else None
            except OSError:
                return None
        return None

    def read_json(self, source: AssetSource, relative: str) -> dict | None:
        key = (str(source.root), relative)
        if key in self._json_cache:
            return self._json_cache[key]
        raw = self._read_bytes(source, relative)
        if raw is None:
            self._json_cache[key] = None
            return None
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            value = None
        self._json_cache[key] = value
        return value if isinstance(value, dict) else None

    @staticmethod
    def resource_path(namespace: str, category: str, name: str, suffix: str = ".json") -> str:
        namespace = namespace.strip() or "minecraft"
        name = name.lstrip("/").replace("\\", "/")
        return f"assets/{namespace}/{category}/{name}{suffix}"

    def blockstate(self, block_id: str, source: AssetSource | None = None) -> dict | None:
        namespace, name = self._split(block_id)
        candidates = [source] if source else self.sources
        for item in candidates:
            if item is None:
                continue
            result = self.read_json(item, self.resource_path(namespace, "blockstates", name))
            if result is not None:
                return result
        return None

    def block_model(self, model_id: str, source: AssetSource | None = None) -> dict | None:
        namespace, name = self._split(model_id)
        candidates = [source] if source else self.sources
        for item in candidates:
            if item is None:
                continue
            result = self.read_json(item, self.resource_path(namespace, "models/block", name))
            if result is not None:
                return result
        return None

    def model_texture_ids(self, model: dict) -> set[str]:
        textures = model.get("textures", {})
        if not isinstance(textures, dict):
            return set()
        return {str(value) for value in textures.values() if isinstance(value, str)}

    def texture_bytes(self, texture_id: str, source: AssetSource | None = None) -> bytes | None:
        namespace, name = self._split(texture_id)
        relative = self.resource_path(namespace, "textures", name, ".png")
        candidates = [source] if source else self.sources
        for item in candidates:
            if item is None:
                continue
            raw = self._read_bytes(item, relative)
            if raw is not None:
                return raw
        return None

    @staticmethod
    def _split(identifier: str) -> tuple[str, str]:
        identifier = str(identifier).strip()
        if ":" in identifier:
            return identifier.split(":", 1)
        return "minecraft", identifier

    def preferred_source(self) -> AssetSource | None:
        # Resource packs override vanilla assets; discovery order preserves explicit packs after vanilla.
        for source in reversed(self.sources):
            if source.kind == "resource_pack":
                return source
        return self.sources[0] if self.sources else None
