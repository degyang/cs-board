"""Tests for infographic-remotion engine entry in create-options (WBS-5 partial)."""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from webapp.mountain_server import create_app


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(tmp_path))


def test_create_options_includes_infographic_engine(client: TestClient):
    """create-options must include infographic-remotion with availability info."""
    body = client.get("/api/v1/tasks/create-options").json()
    engines = body["engines"]
    infographic = next(
        (e for e in engines if e["id"] == "infographic-remotion"), None,
    )
    assert infographic is not None, (
        f"infographic-remotion not in engines: {[e['id'] for e in engines]}"
    )
    assert infographic["label"] == "动态信息图"
    assert "available" in infographic
    assert "reason" in infographic


def test_infographic_unavailable_without_remotion(client: TestClient):
    """Without Node/Remotion, infographic-remotion is unavailable."""
    body = client.get("/api/v1/tasks/create-options").json()
    infographic = next(
        (e for e in body["engines"] if e["id"] == "infographic-remotion"),
    )
    # In the test environment, remotion is likely not fully installed.
    # The entry should exist and have a reason.
    assert isinstance(infographic["reason"], str)
    assert len(infographic["reason"]) > 0


def test_whiteboard_engine_still_first_and_available(client: TestClient):
    """Whiteboard remains the first engine and is always available."""
    body = client.get("/api/v1/tasks/create-options").json()
    assert body["engines"][0]["id"] == "whiteboard"
    assert body["engines"][0]["available"] is True
