from __future__ import annotations

import keyring

SERVICE = "WorldSmith AI"


class SecretStore:
    """OS-backed secret storage for provider API keys."""

    KEYS = {"openai": "openai-api-key", "gemini": "gemini-api-key"}

    @classmethod
    def get(cls, provider: str) -> str:
        name = cls.KEYS.get(provider)
        if not name:
            raise ValueError(f"Unknown secret provider: {provider}")
        try:
            return keyring.get_password(SERVICE, name) or ""
        except Exception:
            return ""

    @classmethod
    def set(cls, provider: str, value: str) -> None:
        name = cls.KEYS.get(provider)
        if not name:
            raise ValueError(f"Unknown secret provider: {provider}")
        if value:
            keyring.set_password(SERVICE, name, value)
        else:
            cls.delete(provider)

    @classmethod
    def delete(cls, provider: str) -> None:
        name = cls.KEYS.get(provider)
        if not name:
            raise ValueError(f"Unknown secret provider: {provider}")
        try:
            keyring.delete_password(SERVICE, name)
        except Exception:
            pass

    @classmethod
    def migrate_from_settings(cls, settings) -> None:
        """Move legacy plaintext API keys out of settings and into the OS keyring."""
        migrated = False
        for provider, field in (("openai", "openai_key"), ("gemini", "gemini_key")):
            value = getattr(settings, field, "")
            if value:
                cls.set(provider, value)
                setattr(settings, field, "")
                migrated = True
        if migrated:
            return
        settings.openai_key = cls.get("openai")
        settings.gemini_key = cls.get("gemini")
