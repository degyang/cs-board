from pathlib import Path
from unittest.mock import patch

from starlette.testclient import TestClient

from csboard.domain.provider_types import TTSResult
from webapp.mountain_server import create_app


def test_provider_voice_profiles_are_projected_without_secrets(tmp_path: Path):
    client = TestClient(create_app(tmp_path))
    service = {
        "service_id": "mimo-tts",
        "display_name": "Configured speech provider",
        "capability": "speech_synthesis",
        "adapter_type": "openai_compatible",
        "model": "mimo-v2.5-tts",
        "endpoint": "https://mimo.example/v1",
        "required_secrets": ["api_key"],
        "config": {
            "api_key": "never-return-this",
            "voice_profiles": [{
                "profile_id": "mimo-bingtang", "name": "Bingtang", "kind": "provider-preset",
                "remote_voice_id": "bingtang", "language": "zh-CN", "tags": ["natural"],
            }],
            "voice_style_profiles": [{
                "style_profile_id": "mimo-warm", "name": "Warm", "instruction": "Speak warmly",
                "tags": ["warm"],
            }],
        },
    }
    assert client.post("/api/v1/services", json=service).status_code == 200

    response = client.get("/api/v1/voice-profiles")
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["provider_id"] == "mimo-tts"
    assert body["items"][0]["capability_snapshot"]["speech.synthesize"] is True
    assert "never-return-this" not in response.text
    assert client.get("/api/v1/voice-style-profiles").json()["items"][0]["provider_id"] == "mimo-tts"


def test_invalid_provider_metadata_is_ignored(tmp_path: Path):
    client = TestClient(create_app(tmp_path))
    service = {
        "service_id": "metadata-only",
        "display_name": "Metadata",
        "capability": "speech_synthesis",
        "adapter_type": "local_process",
        "config": {"voice_profiles": [{"name": "missing kind"}]},
    }
    assert client.post("/api/v1/services", json=service).status_code == 200
    assert client.get("/api/v1/voice-profiles").json()["items"] == []


def test_profile_crud_requires_configured_speech_provider_and_survives_rebuild(tmp_path: Path):
    client = TestClient(create_app(tmp_path))
    service = {
        "service_id": "mimo", "display_name": "MiMo", "capability": "speech_synthesis",
        "adapter_type": "openai_compatible", "model": "mimo-v2.5-tts", "required_secrets": ["api_key"],
    }
    assert client.post("/api/v1/services", json=service).status_code == 200
    assert client.post("/api/v1/voice-profiles", json={"profile_id": "x", "name": "X", "kind": "provider-preset", "provider_id": "mimo", "remote_voice_id": "x"}).status_code == 400
    assert client.post("/api/v1/services/mimo/secrets", json={"key": "api_key", "value": "secret-value"}).status_code == 200
    created = client.post("/api/v1/voice-profiles", json={"profile_id": "mimo-x", "name": "X", "kind": "provider-preset", "provider_id": "mimo", "remote_voice_id": "x"})
    assert created.status_code == 200
    assert "secret-value" not in created.text
    assert client.post("/api/v1/voice-style-profiles", json={"style_profile_id": "warm", "name": "Warm", "provider_id": "mimo", "instruction": "warm"}).status_code == 200
    rebuilt = TestClient(create_app(tmp_path))
    assert rebuilt.get("/api/v1/voice-profiles", params={"provider_id": "mimo"}).json()["total"] == 9
    assert rebuilt.get("/api/v1/voice-style-profiles", params={"provider_id": "mimo"}).json()["total"] == 1


def test_profile_kind_requirements_and_provider_capability(tmp_path: Path):
    client = TestClient(create_app(tmp_path))
    assert client.post("/api/v1/voice-profiles", json={"profile_id": "x", "name": "X", "kind": "provider-preset", "provider_id": "local-ffmpeg", "remote_voice_id": "x"}).status_code == 400


def test_ui_shaped_preset_create_generates_stable_identity_id_and_is_idempotent(tmp_path: Path):
    """Exercise the HTTP contract used by the preset-voice dialog, not catalog internals."""
    service = {
        "service_id": "speech-provider", "display_name": "Speech provider", "capability": "speech_synthesis",
        "adapter_type": "local_process", "model": "tts-v1,tts-v2", "required_secrets": ["api_key"],
    }
    body = {
        "name": "同名音色", "kind": "provider-preset", "provider_id": "speech-provider",
        "model_id": "tts-v1", "remote_voice_id": "远程音色", "tags": ["new"],
    }
    client = TestClient(create_app(tmp_path))
    assert client.post("/api/v1/services", json=service).status_code == 200
    assert client.post("/api/v1/services/speech-provider/secrets", json={"key": "api_key", "value": "secret"}).status_code == 200

    created = client.post("/api/v1/voice-profiles", json=body)
    assert created.status_code == 200
    profile = created.json()
    assert profile["profile_id"].startswith("preset-")
    assert len(profile["profile_id"]) == len("preset-") + 64
    assert profile["remote_voice_id"] == "远程音色"

    repeated = client.post("/api/v1/voice-profiles", json={**body, "name": "ignored on repeat"})
    assert repeated.status_code == 200
    assert repeated.json() == profile
    rebuilt = TestClient(create_app(tmp_path))
    rebuilt_items = rebuilt.get("/api/v1/voice-profiles", params={"provider_id": "speech-provider"}).json()["items"]
    assert [item["profile_id"] for item in rebuilt_items] == [profile["profile_id"]]

    # Same display name but a distinct provider/model/remote identity never reuses the ID.
    distinct = client.post("/api/v1/voice-profiles", json={**body, "model_id": "tts-v2", "remote_voice_id": "另一个远程音色"})
    assert distinct.status_code == 200
    assert distinct.json()["profile_id"] != profile["profile_id"]
    assert client.post("/api/v1/services", json={**service, "service_id": "other-speech-provider"}).status_code == 200
    assert client.post("/api/v1/services/other-speech-provider/secrets", json={"key": "api_key", "value": "secret"}).status_code == 200
    other_provider = client.post("/api/v1/voice-profiles", json={**body, "provider_id": "other-speech-provider"})
    assert other_provider.status_code == 200
    assert other_provider.json()["profile_id"] != profile["profile_id"]


def test_mimo_audio_generation_alias_projects_adapter_presets(tmp_path: Path):
    client = TestClient(create_app(tmp_path))
    service = {"service_id": "mimo-alias", "display_name": "MiMo", "capability": "audio_generation",
               "adapter_type": "openai_compatible", "model": "mimo-v2.5-tts,mimo-v2.5-tts-voicedesign",
               "required_secrets": ["api_key"]}
    assert client.post("/api/v1/services", json=service).status_code == 200
    assert client.post("/api/v1/services/mimo-alias/secrets", json={"key": "api_key", "value": "secret"}).status_code == 200
    body = client.get("/api/v1/voice-profiles", params={"provider_id": "mimo-alias"}).json()
    assert body["total"] == 8
    assert {item["kind"] for item in body["items"]} == {"provider-preset"}
    assert {item["remote_voice_id"] for item in body["items"]} >= {"冰糖", "茉莉", "苏打", "白桦"}
    assert "secret" not in str(body)


def test_preset_identity_deduplicates_rebuilds_and_keeps_same_named_distinct_models(tmp_path: Path):
    client = TestClient(create_app(tmp_path))
    service = {
        "service_id": "voice-service", "display_name": "Any display name", "capability": "speech_synthesis",
        "adapter_type": "openai_compatible", "model": "mimo-v2.5-tts,mimo-v2.5-tts-alt", "required_secrets": ["api_key"],
        "config": {"voice_profiles": [
            # This is the same remote identity as the adapter's MiMo preset,
            # despite a different presentation name and local profile id.
            {"profile_id": "configured-bingtang", "name": "Renamed", "kind": "provider-preset", "remote_voice_id": "冰糖", "model_id": "mimo-v2.5-tts"},
            # A same-name remote voice on a different declared model is distinct.
            {"profile_id": "alt-bingtang", "name": "Renamed", "kind": "provider-preset", "remote_voice_id": "冰糖", "model_id": "mimo-v2.5-tts-alt"},
        ]},
    }
    assert client.post("/api/v1/services", json=service).status_code == 200
    first = client.get("/api/v1/voice-profiles", params={"provider_id": "voice-service"}).json()
    second = TestClient(create_app(tmp_path)).get("/api/v1/voice-profiles", params={"provider_id": "voice-service"}).json()
    assert first["total"] == second["total"] == 9
    assert first["items"] == second["items"]
    bingtang = [item for item in first["items"] if item["remote_voice_id"] == "冰糖"]
    assert {item["model_id"] for item in bingtang} == {"mimo-v2.5-tts", "mimo-v2.5-tts-alt"}
    assert next(item for item in bingtang if item["model_id"] == "mimo-v2.5-tts")["profile_id"] == "configured-bingtang"
    assert all(item["identity_key"] == "voice-service|" + item["model_id"] + "|冰糖" for item in bingtang)


def test_provider_preview_writes_only_controlled_audio_and_redacts_failures(tmp_path: Path):
    client = TestClient(create_app(tmp_path))
    service = {
        "service_id": "mimo-preview", "display_name": "MiMo", "capability": "audio_generation",
        "adapter_type": "openai_compatible", "model": "mimo-v2.5-tts", "required_secrets": ["api_key"],
    }
    assert client.post("/api/v1/services", json=service).status_code == 200
    assert client.post("/api/v1/services/mimo-preview/secrets", json={"key": "api_key", "value": "top-secret"}).status_code == 200
    profile_id = "mimo-preview-bingtang"
    with patch("csboard.adapters.openai_compatible.tts_adapter.OpenAITTSAdapter.synthesize", return_value=TTSResult(audio=b"RIFFpreview", duration_ms=10)) as synthesize:
        response = client.post(f"/api/v1/voice-profiles/{profile_id}/preview")
    assert response.status_code == 200
    assert response.json()["audio_url"] == f"/api/v1/voice-profiles/{profile_id}/preview"
    audio = client.get(response.json()["audio_url"])
    assert audio.status_code == 200
    assert audio.content == b"RIFFpreview"
    request = synthesize.call_args.args[0]
    assert request.voice_id == "冰糖"
    assert request.voice_config == {"format": "wav"}
    assert request.text

    with patch("csboard.adapters.openai_compatible.tts_adapter.OpenAITTSAdapter.synthesize", side_effect=RuntimeError("Bearer top-secret")):
        failed = client.post(f"/api/v1/voice-profiles/{profile_id}/preview")
    assert failed.status_code == 400
    assert failed.json()["detail"] == "VOICE_PREVIEW_FAILED"
    assert "top-secret" not in failed.text
    assert client.get(f"/api/v1/voice-profiles/{profile_id}/preview").status_code == 404


def test_patch_generated_preset_persists_editable_override(tmp_path: Path):
    client = TestClient(create_app(tmp_path))
    service = {"service_id": "mimo-edit", "display_name": "MiMo", "capability": "speech_synthesis",
               "adapter_type": "openai_compatible", "model": "mimo-v2.5-tts", "required_secrets": ["api_key"]}
    assert client.post("/api/v1/services", json=service).status_code == 200
    response = client.patch("/api/v1/voice-profiles/mimo-edit-bingtang", json={"name": "Custom name", "tags": ["edited"]})
    assert response.status_code == 200
    assert response.json()["revision"] == 2
    rebuilt = TestClient(create_app(tmp_path)).get("/api/v1/voice-profiles", params={"provider_id": "mimo-edit"}).json()
    edited = next(item for item in rebuilt["items"] if item["profile_id"] == "mimo-edit-bingtang")
    assert edited["name"] == "Custom name"
    assert edited["tags"] == ["edited"]
