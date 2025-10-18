"""Role based access control helpers."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


@dataclass
class Principal:
    key_id: str
    roles: List[str]


class RBACManager:
    """Validates API keys and role memberships."""

    def __init__(self) -> None:
        self._principals: Dict[str, Principal] = {}
        self._hashes: Dict[str, bytes] = {}

    def register_key(self, key_id: str, raw_secret: str, roles: Iterable[str]) -> None:
        hashed = bcrypt.hashpw(raw_secret.encode("utf-8"), bcrypt.gensalt())
        self._principals[key_id] = Principal(key_id=key_id, roles=list(roles))
        self._hashes[key_id] = hashed

    def authenticate(self, key_id: str, raw_secret: str) -> Principal:
        hashed = self._hashes.get(key_id)
        if not hashed:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown API key")
        if not bcrypt.checkpw(raw_secret.encode("utf-8"), hashed):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key secret")
        return self._principals[key_id]

    def authorise(self, key_id: str, raw_secret: str, role: str) -> Principal:
        principal = self.authenticate(key_id, raw_secret)
        if role not in principal.roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges")
        return principal


_security = HTTPBearer(auto_error=False)
_rbac_singleton: Optional[RBACManager] = None


def get_rbac_manager() -> RBACManager:
    global _rbac_singleton
    if _rbac_singleton is None:
        _rbac_singleton = RBACManager()
        default_key = os.getenv("GENESIS_API_KEY_ID")
        default_secret = os.getenv("GENESIS_API_KEY_SECRET")
        default_roles = os.getenv("GENESIS_API_KEY_ROLES", "viewer").split(",")
        if default_key and default_secret:
            _rbac_singleton.register_key(default_key, default_secret, default_roles)
    return _rbac_singleton


def require_role(role: str):
    async def dependency(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
        manager: RBACManager = Depends(get_rbac_manager),
    ) -> Principal:
        if credentials is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing credentials")
        scheme = credentials.scheme.lower()
        if scheme != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unsupported auth scheme")
        token = credentials.credentials
        if ":" not in token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token")
        key_id, raw_secret = token.split(":", 1)
        return manager.authorise(key_id, raw_secret, role)

    return dependency
