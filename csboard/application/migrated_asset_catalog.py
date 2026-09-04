"""Built-in custom styles and voice examples migrated from the frozen baseline."""

from __future__ import annotations

from pathlib import Path

from csboard.adapters.filesystem.asset_repository import FilesystemAssetRepository
from csboard.domain.style_template import StyleTemplate


ROOT = Path(__file__).resolve().parents[2]
SEED_ROOT = ROOT / "assets" / "seed-voices"
SEED_TIME = "2026-08-31T00:00:00Z"

CUSTOM_STYLES = (
    {
        "style_id": "cs-1",
        "name": "我的科普风",
        "prompt_text": "清晰友好的科普讲解风格。",
        "characters": [
            {"character_id": "ch-1", "name": "主讲人 · 小林", "description": "理性、语速平稳，承担主要讲解，画面常居中。", "reference_asset_ids": []},
            {"character_id": "ch-2", "name": "助手 · 喵", "description": "俏皮活泼，负责举例与互动，画面偏右下角。", "reference_asset_ids": []},
        ],
    },
    {
        "style_id": "cs-2",
        "name": "复古漫画风",
        "prompt_text": "复古漫画叙事风格。",
        "characters": [
            {"character_id": "ch-3", "name": "旁白", "description": "统一旁白音色，承接转场与总结。", "reference_asset_ids": []},
        ],
    },
)

# id, file, name, duration_ms, sample_rate, channels, language, emotion mode,
# weight, example text, tags, availability, status note, optional emotion ref.
VOICE_EXAMPLES = (
    ("vc-01", "voice_03.wav", "纪念品介绍 · 中文自然", 2111, 48000, 2, "ZH", "speaker", None,
     "这个呀，就是我们精心制作准备的纪念品，大家可以看到这个色泽和这个材质啊，哎呀多么的光彩照人。",
     ["中文", "自然", "介绍", "热情"], "available", "IndexTTS-2 在 FP16 下支持中文音色自带情感。", None),
    ("vc-02", "voice_04.wav", "专业人士语气 · 中文自然", 2346, 48000, 2, "ZH", "speaker", None,
     "你就需要我这种专业人士的帮助，就像手无缚鸡之力的人进入雪山狩猎，一定需要最老练的猎人指导。",
     ["中文", "自信", "叙述", "专业"], "available", "IndexTTS-2 在 FP16 下支持中文音色自带情感。", None),
    ("vc-03", "voice_01.wav", "英文自然 · 惊讶疑问", 2439, 48000, 1, "EN", "speaker", None,
     "Translate for me, what is a surprise!", ["英文", "惊讶", "疑问"], "available",
     "IndexTTS-2 在 FP16 下支持英文音色自带情感。", None),
    ("vc-04", "voice_02.wav", "英文自然 · 责问质询", 2927, 48000, 1, "EN", "speaker", None,
     "If you’d ever treated me like a human being, would they have dared to do this?",
     ["英文", "责问", "缩读"], "available", "英文标点与缩读覆盖样例。", None),
    ("vc-08", "voice_05.wav", "剑道叙述 · 中文长段落", 8406, 44100, 2, "ZH", "speaker", None,
     "在真正的日本剑道中，格斗过程极其短暂，常常短至半秒，最长也不超过两秒，利剑相击的转瞬间，已有一方倒在血泊中。但在这电光石火的对决之前，双方都要以一个石雕般凝固的姿势站定，长时间的逼视对方，这一过程可能长达十分钟！",
     ["中文", "长文本", "叙述", "分段"], "available", "长文本分段示例；8GB 显存建议按自然段落粒度送合成。", None),
    ("vc-09", "voice_06.wav", "诗句转折 · 中文风趣", 6229, 24000, 1, "ZH", "speaker", None,
     "床前明月光，疑是地上霜，举头望明月，我叫郭德纲。", ["中文", "诗句", "韵律", "风趣"], "available",
     "短中文韵律样例。", None),
    ("vc-10", "voice_07.wav", "情感参考 · 不满与厌恶", 2036, 48000, 2, "ZH", "reference_audio", 0.65,
     "你看看你，对我还有没有一点父子之间的信任了。", ["中文", "情感参考", "厌恶", "责备"], "available",
     "情感参考音频无需 QwenEmotion 即可支持；参考片段极短，适合作为官方行为样例。", "emo_hate.wav"),
    ("vc-11", "voice_08.wav", "情感参考 · 悲伤与孤独", 1451, 48000, 2, "ZH", "reference_audio", 0.8,
     "我站在人海中，却感觉比任何时候都要孤独。", ["中文", "情感参考", "悲伤", "孤独"], "verified",
     "用户已在 GTX 1070 Ti 本地生成成功（2026-08-22）。", "emo_sad.wav"),
    ("vc-12", "voice_09.wav", "情绪向量 · 撒娇式悲伤", 10194, 44100, 2, "ZH", "vector", 0.8,
     "对不起嘛！我的记性真的不太好，但是和你在一起的事情，我都会努力记住的~", ["中文", "情绪向量", "悲伤", "撒娇"], "available",
     "悲伤维度的 WebUI 折算系数为 1.0，源向量与 CLI 向量一致。", None),
    ("vc-13", "voice_11.wav", "情绪文本 · 极度悲伤", 7862, 48000, 1, "ZH", "text", 1.0,
     "这些年的时光终究是错付了...", ["中文", "情绪文本", "悲伤"], "limited",
     "情绪文本依赖 QwenEmotion；8GB 低显存档不加载，建议改用显式情绪向量。", None),
    ("vc-14", "voice_12.wav", "情绪文本 · 惊恐", 2673, 48000, 2, "ZH", "text", 1.0,
     "快躲起来！是他要来了！他要来抓我们了！", ["中文", "情绪文本", "惊恐"], "limited",
     "情绪文本依赖 QwenEmotion；8GB 低显存档不加载，建议改用显式情绪向量。", None),
)


def seed(data_dir: Path, seed_root: Path | None = None) -> dict[str, int | bool]:
    """Idempotently install missing migrated examples into the real repository."""
    repository = FilesystemAssetRepository(data_dir)
    root = seed_root or SEED_ROOT
    installed_customs = 0
    installed_voices = 0

    for item in CUSTOM_STYLES:
        template = StyleTemplate(
            style_id=item["style_id"], revision=1, name=item["name"], kind="custom",
            prompt_text=item["prompt_text"], engine="whiteboard", status="active",
            created_at=SEED_TIME, updated_at=SEED_TIME,
            config={"source": "frozen WebUI baseline SEED_CUSTOMS"},
            characters=item["characters"],
        )
        installed_customs += int(repository.install_style_template_if_missing(template))

    reference_ids: dict[str, str] = {}
    for filename in ("emo_hate.wav", "emo_sad.wav"):
        source = root / filename
        reference_ids[filename] = repository.save_asset(
            source.read_bytes(), filename, "audio/wav",
        ).asset_id

    for (voice_id, filename, name, duration_ms, sample_rate, channels, language,
         emotion_mode, emotion_weight, example_text, tags, availability, status_note,
         emotion_reference) in VOICE_EXAMPLES:
        limitations = [status_note] if availability == "limited" else []
        metadata = {
            "tags": tags,
            "language": language,
            "emotion_mode": emotion_mode,
            "emotion_weight": emotion_weight,
            "emotion_reference_asset_id": reference_ids.get(emotion_reference or "", ""),
            "example_text": example_text,
            "availability_status": availability,
            "status_note": status_note,
            "engine": "indextts-2",
            "source": "index-tts examples · webui-demo",
            "compatibility": {
                "engines": ["indextts-2"],
                "emotion_modes": [emotion_mode],
                "limitations": limitations,
            },
        }
        source = root / filename
        installed_voices += int(repository.install_voice_asset_if_missing(
            voice_id, source.read_bytes(), name, duration_ms, sample_rate, channels, metadata,
        ))

    return {"ok": True, "customs": installed_customs, "voices": installed_voices}
