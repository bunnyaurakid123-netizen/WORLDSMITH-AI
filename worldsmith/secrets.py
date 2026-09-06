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
    def set(cls, provider: str, value: str) -> bool:
        name = cls.KEYS.get(provider)
        if not name:
            raise ValueError(f"Unknown secret provider: {provider}")
        if not value:
            cls.delete(provider)
            return True
        try:
            keyring.set_password(SERVICE, name, value)
            return True
        except Exception:
            return False

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
    def migrate_from_settings(cls, settings) -> bool:
        migrated = False
        for provider, field in (("openai", "openai_key"), ("gemini", "gemini_key")):
            value = getattr(settings, field, "")
            if value and cls.set(provider, value):
                setattr(settings, field, "")
                migrated = True
        if not migrated:
            settings.openai_key = cls.get("openai")
            settings.gemini_key = cls.get("gemini")
        return migrated
