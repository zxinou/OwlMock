from __future__ import annotations

import secrets
import time
from pathlib import Path
from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from config.settings import Settings

OWNER_ID = "default"
SESSION_COOKIE = "owlmock_session"
_SESSION_SECRET_FILE = ".session-secret"


class SessionSigner:
    """Issue and verify signed, expiring user-session tokens."""

    def __init__(self, secret: str, max_age_seconds: int) -> None:
        self._serializer = URLSafeTimedSerializer(
            secret_key=secret,
            salt="owlmock.user-session.v2",
        )
        self.max_age_seconds = max_age_seconds

    @classmethod
    def from_settings(cls, settings: Settings) -> SessionSigner:
        secret = settings.OWLMOCK_SESSION_SECRET or _load_or_create_secret(
            settings.data_dir
        )
        return cls(secret, settings.OWLMOCK_SESSION_DAYS * 24 * 60 * 60)

    def issue(self, user_id: str = OWNER_ID) -> str:
        if not user_id:
            raise ValueError("A user id is required to issue a session")
        return self._serializer.dumps({"sub": user_id, "iat": int(time.time())})

    def verify(self, token: str) -> dict[str, Any] | None:
        try:
            payload = self._serializer.loads(token, max_age=self.max_age_seconds)
        except (BadSignature, SignatureExpired):
            return None
        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("sub"), str)
            or not payload["sub"]
        ):
            return None
        return payload


def _load_or_create_secret(data_dir: Path) -> str:
    data_dir.mkdir(parents=True, exist_ok=True)
    secret_path = data_dir / _SESSION_SECRET_FILE
    if secret_path.exists():
        secret = secret_path.read_text(encoding="utf-8").strip()
        if secret:
            return secret

    secret = secrets.token_urlsafe(48)
    secret_path.write_text(secret, encoding="utf-8")
    try:
        secret_path.chmod(0o600)
    except OSError:
        pass
    return secret
