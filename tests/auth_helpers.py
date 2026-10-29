"""Server-issued test identities; no client role bypass or authentication disable switch."""

import uuid

from fastapi.testclient import TestClient


def authorized_client(app, role="builder"):
    _, token = app.state.auth.create_user(uuid.uuid4().hex, "Test " + role, role)
    return TestClient(app, headers={"Authorization": "Bearer " + token})
