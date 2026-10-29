import json

import pytest

from simready.review.auth import AuthenticationError, AuthorizationError, AuthStore
from simready.scene.store import SceneStore


def test_distinct_opaque_credentials_hash_only_database_and_idempotent_bootstrap(tmp_path):
    auth = AuthStore(SceneStore(tmp_path / "studio"))
    path = auth.bootstrap()
    assert path.stat().st_mode & 0o777 == 0o600
    credentials = json.loads(path.read_text())
    a, b = credentials["builder"]["token"], credentials["reviewer"]["token"]
    assert a != b and len(a) >= 40 and len(b) >= 40
    builder = auth.authenticate("Bearer " + a)
    reviewer = auth.authenticate("Bearer " + b)
    assert builder.role == "builder" and reviewer.role == "reviewer"
    assert builder.user_id != reviewer.user_id
    assert auth.bootstrap() == path and path.read_text() == json.dumps(credentials, indent=2) + "\n"
    with auth.scenes.connect() as db:
        rows = db.execute("SELECT * FROM accounts").fetchall()
        assert len(rows) == 2
        assert all(row["token_sha256"] not in (a, b) for row in rows)
        assert all(a not in str(tuple(row)) and b not in str(tuple(row)) for row in rows)
    with pytest.raises(AuthorizationError):
        auth.require(builder, "reviewer")
    auth.require(reviewer, "reviewer")


def test_server_roles_revoke_and_invalid_tokens(tmp_path):
    auth = AuthStore(SceneStore(tmp_path / "studio"))
    user, token = auth.create_user("alice", "Alice", "builder")
    assert auth.authenticate("Bearer " + token).user_id == user.user_id
    for invalid in (None, "", "builder", "Bearer fake", "Bearer " + "x" * 43):
        with pytest.raises(AuthenticationError):
            auth.authenticate(invalid)
    with auth.scenes.connect() as db:
        db.execute("UPDATE accounts SET role='reviewer' WHERE user_id='alice'")
    assert auth.authenticate("Bearer " + token).role == "reviewer"
    with auth.scenes.connect() as db:
        db.execute("UPDATE accounts SET active=0 WHERE user_id='alice'")
    with pytest.raises(AuthenticationError):
        auth.authenticate("Bearer " + token)
    with pytest.raises(ValueError, match="already exists"):
        auth.create_user("alice", "Alice again", "reviewer")
