"""Mountain 新产品默认服务目录。

首次启动幂等安装，不覆盖用户服务，也不写入任何 Secret。
"""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_SERVICES = [
    {
        "service_id": "openai-compatible-text",
        "display_name": "OpenAI 兼容文本模型",
        "capability": "text_generation",
        "adapter_type": "openai_compatible",
        "endpoint": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "config": {"api_mode": "chat-completions"},
        "required_secrets": ["api_key"],
        "optional_secrets": [],
        "priority": 100,
    },
    {
        "service_id": "openai-compatible-image",
        "display_name": "OpenAI 兼容图片模型",
        "capability": "image_generation",
        "adapter_type": "openai_compatible",
        "endpoint": "https://api.openai.com/v1",
        "model": "gpt-image-1",
        "config": {},
        "required_secrets": ["api_key"],
        "optional_secrets": [],
        "priority": 100,
    },
    {
        "service_id": "local-indextts",
        "display_name": "本地 IndexTTS",
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
        "service_id": "local-whisper",
        "display_name": "本地 Whisper 对齐",
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
        "service_id": "whiteboard-renderer",
        "display_name": "白板动画渲染器",
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
        "service_id": "local-ffmpeg",
        "display_name": "本地 FFmpeg",
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
    for profile in DEFAULT_SERVICES:
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

    return {"ok": True, "message": "默认服务安装完成", "created": created, "skipped": len(DEFAULT_SERVICES) - created}
