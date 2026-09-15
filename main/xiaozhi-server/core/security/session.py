"""Short lived, revocable device sessions.

The device token is intentionally an opaque signed envelope.  It carries only
identity and authorization metadata; third-party credentials never belong in it.
"""
import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Iterable, Optional


class SessionError(Exception):
    def __init__(self, status: int, message: str = "设备认证失败"):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class SessionContext:
    tenant_id: str
    user_id: str
    device_id: str
    client_id: str
    scopes: frozenset[str]
    audience: str
    issued_at: int
    expires_at: int
    token_id: str

    def allows(self, scope: str) -> bool:
        return scope in self.scopes or "*" in self.scopes


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class DeviceSessionAuthenticator:
    """Issue and validate device sessions with constant time signature checks.

    ``revoked_token_ids`` is a small process-local fallback.  Deployments with
    multiple workers should provide a shared revocation store by calling
    ``revoke`` from their durable identity service as well.
    """

    def __init__(self, secret: str, audience: str = "xiaozhi", clock=None):
        if not isinstance(secret, str) or len(secret) < 32:
            raise ValueError("device session secret must contain at least 32 characters")
        self._secret = secret.encode("utf-8")
        self.audience = audience
        self._clock = clock or time.time
        self._revoked: set[str] = set()

    def issue(
        self,
        tenant_id: str,
        user_id: str,
        device_id: str,
        client_id: str,
        scopes: Iterable[str],
        ttl_seconds: int = 900,
    ) -> str:
        now = int(self._clock())
        if ttl_seconds <= 0 or ttl_seconds > 86400:
            raise ValueError("device session ttl must be between 1 second and 24 hours")
        payload = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "device_id": device_id,
            "client_id": client_id,
            "scopes": sorted(set(scopes)),
            "audience": self.audience,
            "issued_at": now,
            "expires_at": now + ttl_seconds,
            "token_id": secrets.token_urlsafe(18),
        }
        encoded = _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
        signature = hmac.new(self._secret, encoded.encode("ascii"), hashlib.sha256).digest()
        return "v1." + encoded + "." + _b64(signature)

    def revoke(self, token_or_context):
        token_id = token_or_context.token_id if isinstance(token_or_context, SessionContext) else self.decode(token_or_context).token_id
        self._revoked.add(token_id)

    def decode(self, token: str) -> SessionContext:
        try:
            version, encoded, supplied_sig = token.split(".")
            if version != "v1":
                raise ValueError("unsupported session version")
            expected_sig = hmac.new(self._secret, encoded.encode("ascii"), hashlib.sha256).digest()
            if not hmac.compare_digest(_unb64(supplied_sig), expected_sig):
                raise ValueError("invalid signature")
            payload = json.loads(_unb64(encoded).decode("utf-8"))
            required = {"tenant_id", "user_id", "device_id", "client_id", "scopes", "audience", "issued_at", "expires_at", "token_id"}
            if required - payload.keys() or payload["audience"] != self.audience:
                raise ValueError("invalid claims")
            if not isinstance(payload["scopes"], list) or not payload["scopes"]:
                raise ValueError("invalid scopes")
            if int(self._clock()) >= int(payload["expires_at"]):
                raise ValueError("expired session")
            if payload["token_id"] in self._revoked:
                raise ValueError("revoked session")
            return SessionContext(
                tenant_id=str(payload["tenant_id"]), user_id=str(payload["user_id"]),
                device_id=str(payload["device_id"]), client_id=str(payload["client_id"]),
                scopes=frozenset(str(s) for s in payload["scopes"]), audience=str(payload["audience"]),
                issued_at=int(payload["issued_at"]), expires_at=int(payload["expires_at"]),
                token_id=str(payload["token_id"]),
            )
        except (ValueError, TypeError, KeyError, json.JSONDecodeError, UnicodeDecodeError, base64.binascii.Error) as exc:
            raise SessionError(401) from exc

    def authenticate(self, authorization: Optional[str], device_id: Optional[str], required_scope: Optional[str] = None) -> SessionContext:
        if not authorization or not authorization.startswith("Bearer "):
            raise SessionError(401)
        context = self.decode(authorization[7:].strip())
        if not device_id or not hmac.compare_digest(context.device_id.lower(), device_id.lower()):
            raise SessionError(403, "设备与会话不匹配")
        if required_scope and not context.allows(required_scope):
            raise SessionError(403, "会话权限不足")
        return context
