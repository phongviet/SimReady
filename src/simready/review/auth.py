"""Local opaque bearer tokens: roles come only from the server-side account table."""

import hashlib
import json
import os
import secrets
from pathlib import Path
from typing import Literal

from pydantic import Field

from simready.data.schema import Contract, Identifier
from simready.scene.store import SceneStore, utc_now

Role = Literal["builder", "reviewer"]


class AuthenticationError(Exception):
    pass


class AuthorizationError(Exception):
    pass


class Principal(Contract):
    user_id: Identifier
    display_name: str = Field(min_length=1, max_length=100)
    role: Role


class AuthStore:
    def __init__(self, scenes: SceneStore):
        self.scenes = scenes
        with scenes.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS accounts (
                user_id TEXT PRIMARY KEY, display_name TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('builder','reviewer')),
                token_sha256 TEXT NOT NULL UNIQUE, active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL)""")

    @staticmethod
    def token_digest(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def create_user(self, user_id: str, display_name: str, role: Role) -> tuple[Principal, str]:
        principal = Principal(user_id=user_id, display_name=display_name, role=role)
        token = secrets.token_urlsafe(32)
        with self.scenes.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] >= 32:
                raise ValueError("local account limit is 32; revoke/reuse an existing account")
            if db.execute("SELECT 1 FROM accounts WHERE user_id=?", (user_id,)).fetchone():
                raise ValueError("account ID already exists")
            db.execute(
                "INSERT INTO accounts VALUES(?,?,?,?,?,?)",
                (user_id, display_name, role, self.token_digest(token), 1, utc_now()),
            )
        return principal, token

    def bootstrap(self) -> Path:
        """Provision two distinct local demo identities once, without logging their tokens."""
        path = self.scenes.root / "local-credentials.json"
        with self.scenes.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]:
                if not path.is_file():
                    raise ValueError(
                        "accounts already provisioned; local demo credentials are unavailable"
                    )
                return path
            credentials = {"schema_version": "1.0"}
            for role, name in (("builder", "Local Builder"), ("reviewer", "Local Reviewer")):
                user_id, token = f"local-{role}", secrets.token_urlsafe(32)
                db.execute(
                    "INSERT INTO accounts VALUES(?,?,?,?,?,?)",
                    (user_id, name, role, self.token_digest(token), 1, utc_now()),
                )
                credentials[role] = {"user_id": user_id, "token": token}
            # O_EXCL prevents overwriting existing credentials after an interrupted initialization.
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as file:
                json.dump(credentials, file, indent=2)
                file.write("\n")
        return path

    def authenticate(self, authorization: str | None) -> Principal:
        if not authorization or not authorization.startswith("Bearer "):
            raise AuthenticationError("Local account bearer token required")
        token = authorization.removeprefix("Bearer ")
        if not 40 <= len(token) <= 100:
            raise AuthenticationError("Invalid or revoked local account token")
        with self.scenes.connect() as db:
            row = db.execute(
                "SELECT user_id,display_name,role FROM accounts WHERE token_sha256=? AND active=1",
                (self.token_digest(token),),
            ).fetchone()
        if row is None:
            raise AuthenticationError("Invalid or revoked local account token")
        return Principal(**dict(row))

    @staticmethod
    def require(principal: Principal, role: Role) -> None:
        if principal.role != role:
            raise AuthorizationError(f"This operation requires a server-assigned {role} account")
