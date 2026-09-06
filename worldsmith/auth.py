from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

import keyring
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCOPES = ["openid", "email", "profile"]
SERVICE_NAME = "WorldSmith AI"
TOKEN_NAME = "google-oauth-token"


class GoogleAuthError(RuntimeError):
    pass


class GoogleAuth:
    """Desktop Google account sign-in. Only identity scopes are requested."""

    def __init__(self, client_secret_path: Path):
        self.client_secret_path = client_secret_path

    def _load_saved(self) -> Credentials | None:
        try:
            raw = keyring.get_password(SERVICE_NAME, TOKEN_NAME)
        except Exception:
            raw = None
        if not raw:
            return None
        try:
            return Credentials.from_authorized_user_info(json.loads(raw), SCOPES)
        except (ValueError, TypeError, json.JSONDecodeError):
            return None

    def _save(self, credentials: Credentials) -> None:
        keyring.set_password(SERVICE_NAME, TOKEN_NAME, credentials.to_json())

    def sign_in(self) -> dict[str, str]:
        if not self.client_secret_path.exists():
            raise GoogleAuthError(
                f"Google OAuth desktop credentials were not found at {self.client_secret_path}. "
                "Create a Desktop OAuth client in Google Cloud and select its JSON file in Settings."
            )

        credentials = self._load_saved()
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            self._save(credentials)
        elif not credentials or not credentials.valid:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(str(self.client_secret_path), SCOPES)
                credentials = flow.run_local_server(port=0, access_type="offline", prompt="select_account")
                self._save(credentials)
            except Exception as exc:
                raise GoogleAuthError(str(exc)) from exc

        req = urllib.request.Request(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {credentials.token}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                profile = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            raise GoogleAuthError(f"Could not read Google profile: {exc}") from exc

        return {
            "sub": str(profile.get("sub", "")),
            "email": str(profile.get("email", "")),
            "name": str(profile.get("name", profile.get("email", "Google user"))),
            "picture": str(profile.get("picture", "")),
        }

    def sign_out(self) -> None:
        try:
            keyring.delete_password(SERVICE_NAME, TOKEN_NAME)
        except keyring.errors.PasswordDeleteError:
            pass
        except Exception:
            pass
