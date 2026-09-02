from starlette.testclient import TestClient
from webapp.mountain_server import create_app

def test_create_options_are_server_owned_and_mark_unavailable_paths(tmp_path):
    body = TestClient(create_app(tmp_path)).get("/api/v1/tasks/create-options").json()
    assert body["defaults"]["engine"] == "whiteboard"
    assert next(item for item in body["visual_sources"] if item["id"] == "custom-reference")["available"] is False
    assert next(item for item in body["voice_sources"] if item["id"] == "voice-asset")["reason"] == "CAPABILITY_NOT_AVAILABLE"
