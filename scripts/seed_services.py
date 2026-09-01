"""Seed Services — 从 PROVIDER_PROFILES 迁移到 ServiceDefinition。

幂等迁移：不覆盖用户已有服务。
不复制 Secret 明文。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 旧 PROVIDER_PROFILES 映射
LEGACY_PROFILES = [
    {
        "service_id": "text_model",
        "display_name": "Text Model (OpenAI-compatible)",
        "capability": "text_generation",
        "adapter_type": "openai_compatible",
        "endpoint": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "config": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o", "api_mode": "chat-completions"},
        "required_secrets": ["api_key"],
        "optional_secrets": [],
        "priority": 100,
    },
    {
        "service_id": "image_model",
        "display_name": "Image Model (OpenAI-compatible)",
        "capability": "image_generation",
        "adapter_type": "openai_compatible",
        "endpoint": "https://api.openai.com/v1",
        "model": "gpt-image-1",
        "config": {"base_url": "https://api.openai.com/v1", "model": "gpt-image-1"},
        "required_secrets": ["api_key"],
        "optional_secrets": [],
        "priority": 100,
    },
    {
        "service_id": "tts",
        "display_name": "Text-to-Speech (IndexTTS)",
        "capability": "speech_synthesis",
        "adapter_type": "indextts",
        "endpoint": "http://127.0.0.1:7860",
        "model": "",
        "config": {"url": "http://127.0.0.1:7860", "mode": "gradio"},
        "required_secrets": [],
        "optional_secrets": [],
        "priority": 100,
    },
    {
        "service_id": "alignment",
        "display_name": "Alignment (Whisper)",
        "capability": "speech_alignment",
        "adapter_type": "whisper",
        "endpoint": "",
        "model": "",
        "config": {"mode": "node"},
        "required_secrets": [],
        "optional_secrets": [],
        "priority": 100,
    },
    {
        "service_id": "renderer",
        "display_name": "Renderer (Whiteboard)",
        "capability": "rendering",
        "adapter_type": "local_process",
        "endpoint": "",
        "model": "",
        "config": {},
        "required_secrets": [],
        "optional_secrets": [],
        "priority": 100,
    },
    {
        "service_id": "media",
        "display_name": "Media (FFmpeg)",
        "capability": "media",
        "adapter_type": "ffmpeg",
        "endpoint": "",
        "model": "",
        "config": {},
        "required_secrets": [],
        "optional_secrets": [],
        "priority": 100,
    },
]


def seed(data_dir: Path) -> dict:
    """幂等迁移：不覆盖用户已有服务。"""
    services_dir = data_dir / "settings" / "services"
    services_dir.mkdir(parents=True, exist_ok=True)

    existing_ids = set()
    for path in services_dir.glob("*.json"):
        existing_ids.add(path.stem)

    created = 0
    for profile in LEGACY_PROFILES:
        sid = profile["service_id"]
        if sid in existing_ids:
            continue
        service = {
            "schema_version": 1,
            "revision": 1,
            "service_id": sid,
            "display_name": profile["display_name"],
            "capability": profile["capability"],
            "adapter_type": profile["adapter_type"],
            "endpoint": profile["endpoint"],
            "model": profile["model"],
            "enabled": True,
            "priority": profile["priority"],
            "is_default": True,
            "config": profile["config"],
            "required_secrets": profile["required_secrets"],
            "optional_secrets": profile["optional_secrets"],
            "created_at": "2026-08-31T00:00:00Z",
            "updated_at": "2026-08-31T00:00:00Z",
        }
        path = services_dir / f"{sid}.json"
        path.write_text(json.dumps(service, ensure_ascii=False, indent=2), encoding="utf-8")
        created += 1

    return {"ok": True, "message": "seed 完成", "created": created, "skipped": len(LEGACY_PROFILES) - created}


def main() -> int:
    data_dir = ROOT / ".webapp"
    if len(sys.argv) > 1:
        data_dir = Path(sys.argv[1])
    result = seed(data_dir)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
