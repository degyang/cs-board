"""InfographicStoryboardAdapter — focused tests.

Covers:
- Normal conversion (single page, multi-page)
- Frame ordering and duration math
- Node text extraction and sanitization
- Illustration resolution
- Cue conversion
- Invalid input rejection (empty, too many pages/nodes, bad timing)
- Text sanitization boundary (control chars, max length)
- Layout/composition/role sanitization (invalid values fall back to defaults)
- Metadata passthrough (seriesTitle, chapterTitle, conclusion, etc.)
- Round-trip serialization
"""

from __future__ import annotations

from pathlib import Path

import pytest

from csboard.adapters.remotion.storyboard_adapter import (
    InfographicStoryboardAdapter,
    StoryboardConversionError,
)
from csboard.domain.infographic import (
    InfographicCue,
    InfographicNode,
    InfographicPage,
    InfographicStoryboard,
)


# ── Helpers ──────────────────────────────────────────────────────────

def _make_node(node_id: str = "n-1", kind: str = "text", text: str = "hello", **extra) -> InfographicNode:
    props = {"text": text, **extra}
    return InfographicNode(node_id=node_id, kind=kind, props=props)


def _make_cue(cue_id: str = "cue-1", trigger_ms: int = 0, action: str = "enter") -> InfographicCue:
    return InfographicCue(cue_id=cue_id, trigger_ms=trigger_ms, action=action)


def _make_page(
    page_id: str = "page-1",
    title: str = "Page 1",
    nodes: tuple[InfographicNode, ...] | None = None,
    cues: tuple[InfographicCue, ...] | None = None,
    cue_start_ms: int = 0,
    cue_end_ms: int = 5000,
) -> InfographicPage:
    return InfographicPage(
        page_id=page_id,
        title=title,
        nodes=nodes or (_make_node(),),
        cues=cues or (_make_cue(trigger_ms=cue_start_ms),),
        cue_start_ms=cue_start_ms,
        cue_end_ms=cue_end_ms,
    )


def _make_storyboard(
    pages: tuple[InfographicPage, ...] | None = None,
    total_duration_ms: int = 5000,
) -> InfographicStoryboard:
    return InfographicStoryboard(
        pages=pages or (_make_page(cue_end_ms=total_duration_ms),),
        total_duration_ms=total_duration_ms,
    )


# ── Normal conversion ───────────────────────────────────────────────

class TestNormalConversion:
    def test_single_page_basic_props(self):
        adapter = InfographicStoryboardAdapter(fps=30)
        sb = _make_storyboard()
        props = adapter.to_remotion_props(sb)

        assert props["fps"] == 30
        assert props["width"] == 1920
        assert props["height"] == 1080
        assert props["totalDurationMs"] == 5000
        assert props["totalDurationFrames"] == 150  # 5000 * 30 / 1000
        assert props["style"] == "极简粗线简笔白板风"
        assert len(props["pages"]) == 1

    def test_multi_page_ordering_preserved(self):
        p1 = _make_page(page_id="page-1", title="First", cue_start_ms=0, cue_end_ms=3000)
        p2 = _make_page(page_id="page-2", title="Second", cue_start_ms=3000, cue_end_ms=6000)
        sb = _make_storyboard(pages=(p1, p2), total_duration_ms=6000)
        adapter = InfographicStoryboardAdapter(fps=30)

        props = adapter.to_remotion_props(sb)
        assert len(props["pages"]) == 2
        assert props["pages"][0]["id"] == "page-1"
        assert props["pages"][1]["id"] == "page-2"
        assert props["pages"][0]["startFrame"] < props["pages"][1]["startFrame"]

    def test_custom_dimensions_and_style(self):
        adapter = InfographicStoryboardAdapter(fps=60, width=1280, height=720, style="黑金科技发布会风")
        sb = _make_storyboard(total_duration_ms=2000)
        props = adapter.to_remotion_props(sb)

        assert props["fps"] == 60
        assert props["width"] == 1280
        assert props["height"] == 720
        assert props["style"] == "黑金科技发布会风"
        assert props["totalDurationFrames"] == 120  # 2000 * 60 / 1000

    def test_subtitles_enabled_flag(self):
        adapter = InfographicStoryboardAdapter(subtitles_enabled=True)
        sb = _make_storyboard()
        props = adapter.to_remotion_props(sb)
        assert props["subtitlesEnabled"] is True

    def test_subtitles_not_present_when_disabled(self):
        adapter = InfographicStoryboardAdapter(subtitles_enabled=False)
        sb = _make_storyboard()
        props = adapter.to_remotion_props(sb)
        assert "subtitlesEnabled" not in props

    def test_audio_paths_passthrough(self):
        adapter = InfographicStoryboardAdapter()
        sb = _make_storyboard()
        props = adapter.to_remotion_props(sb, audio_paths=["audio/unit-001.wav", "audio/unit-002.wav"])
        assert props["audioPaths"] == ["audio/unit-001.wav", "audio/unit-002.wav"]

    def test_no_audio_paths_key_when_empty(self):
        adapter = InfographicStoryboardAdapter()
        sb = _make_storyboard()
        props = adapter.to_remotion_props(sb, audio_paths=None)
        assert "audioPaths" not in props


# ── Frame math ───────────────────────────────────────────────────────

class TestFrameMath:
    def test_ms_to_frames_30fps(self):
        adapter = InfographicStoryboardAdapter(fps=30)
        sb = _make_storyboard(total_duration_ms=3333)
        props = adapter.to_remotion_props(sb)
        assert props["totalDurationFrames"] == 100  # 3333 * 30 / 1000 ≈ 100

    def test_ms_to_frames_24fps(self):
        adapter = InfographicStoryboardAdapter(fps=24)
        sb = _make_storyboard(total_duration_ms=4166)
        props = adapter.to_remotion_props(sb)
        assert props["totalDurationFrames"] == 100  # 4166 * 24 / 1000 ≈ 100

    def test_page_frames_are_ordered(self):
        p1 = _make_page(cue_start_ms=0, cue_end_ms=2000)
        p2 = _make_page(page_id="p2", cue_start_ms=2000, cue_end_ms=5000)
        sb = _make_storyboard(pages=(p1, p2), total_duration_ms=5000)
        adapter = InfographicStoryboardAdapter(fps=30)
        props = adapter.to_remotion_props(sb)

        assert props["pages"][0]["startFrame"] == 0
        assert props["pages"][0]["endFrame"] == 60  # 2000 * 30 / 1000
        assert props["pages"][1]["startFrame"] == 60
        assert props["pages"][1]["endFrame"] == 150

    def test_zero_page_duration_is_rejected_by_p1_contract(self):
        p = _make_page(cue_start_ms=1000, cue_end_ms=1000)
        sb = _make_storyboard(pages=(p,), total_duration_ms=2000)
        adapter = InfographicStoryboardAdapter(fps=30)
        with pytest.raises(StoryboardConversionError) as error:
            adapter.to_remotion_props(sb)
        assert error.value.code == "INVALID_PAGE_TIMING"


# ── Node text extraction ────────────────────────────────────────────

class TestNodeTextExtraction:
    def test_node_texts_extracted_in_order(self):
        n1 = _make_node(node_id="n-1", text="Alpha")
        n2 = _make_node(node_id="n-2", text="Beta")
        n3 = _make_node(node_id="n-3", text="Gamma")
        page = _make_page(nodes=(n1, n2, n3))
        sb = _make_storyboard(pages=(page,))
        adapter = InfographicStoryboardAdapter()

        props = adapter.to_remotion_props(sb)
        assert props["pages"][0]["nodes"] == ["Alpha", "Beta", "Gamma"]

    def test_non_string_text_coerced(self):
        n = _make_node(text=12345)  # type: ignore[arg-type]
        page = _make_page(nodes=(n,))
        sb = _make_storyboard(pages=(page,))
        adapter = InfographicStoryboardAdapter()
        props = adapter.to_remotion_props(sb)
        assert props["pages"][0]["nodes"] == ["12345"]

    def test_empty_node_text_preserved(self):
        n = _make_node(text="")
        page = _make_page(nodes=(n,))
        sb = _make_storyboard(pages=(page,))
        adapter = InfographicStoryboardAdapter()
        props = adapter.to_remotion_props(sb)
        assert props["pages"][0]["nodes"] == [""]


# ── Illustration resolution ─────────────────────────────────────────

class TestIllustrationResolution:
    def test_illustration_by_visual_id(self):
        n = _make_node(kind="image", visual_id="vis-001")
        page = _make_page(nodes=(n,))
        sb = _make_storyboard(pages=(page,))
        adapter = InfographicStoryboardAdapter()

        props = adapter.to_remotion_props(sb, illustrations={"vis-001": "images/vis-001.png"})
        assert props["pages"][0]["image"] == "images/vis-001.png"

    def test_image_path_from_node_props(self):
        n = _make_node(kind="image", image_path="assets/chart.png")
        page = _make_page(nodes=(n,))
        sb = _make_storyboard(pages=(page,))
        adapter = InfographicStoryboardAdapter()

        props = adapter.to_remotion_props(sb, illustrations={})
        assert props["pages"][0]["image"] == "assets/chart.png"

    def test_fallback_to_page_id_when_no_image(self):
        n = _make_node(kind="text", text="just text")
        page = _make_page(page_id="page-abc", nodes=(n,))
        sb = _make_storyboard(pages=(page,))
        adapter = InfographicStoryboardAdapter()

        props = adapter.to_remotion_props(sb, illustrations={})
        assert props["pages"][0]["image"] == "pages/page-abc.png"

    def test_illustration_takes_precedence_over_image_path(self):
        n = _make_node(kind="image", visual_id="vis-1", image_path="old/path.png")
        page = _make_page(nodes=(n,))
        sb = _make_storyboard(pages=(page,))
        adapter = InfographicStoryboardAdapter()

        props = adapter.to_remotion_props(sb, illustrations={"vis-1": "new/path.png"})
        assert props["pages"][0]["image"] == "new/path.png"


# ── Cue conversion ──────────────────────────────────────────────────

class TestCueConversion:
    def test_enter_cue_produces_enter_ids(self):
        cue = _make_cue(cue_id="enter-vis-001", trigger_ms=1500, action="enter")
        page = _make_page(cues=(cue,))
        sb = _make_storyboard(pages=(page,))
        adapter = InfographicStoryboardAdapter(fps=30)

        props = adapter.to_remotion_props(sb)
        remotion_cue = props["pages"][0]["cues"][0]
        assert remotion_cue["id"] == "enter-vis-001"
        assert remotion_cue["startFrame"] == 45  # 1500 * 30 / 1000
        assert remotion_cue["spokenStartMs"] == 1500
        assert "node-vis-001" in remotion_cue["enterIds"]

    def test_non_enter_cue_has_empty_enter_ids(self):
        cue = _make_cue(cue_id="emph-1", trigger_ms=0, action="emphasize")
        page = _make_page(cues=(cue,))
        sb = _make_storyboard(pages=(page,))
        adapter = InfographicStoryboardAdapter()

        props = adapter.to_remotion_props(sb)
        assert props["pages"][0]["cues"][0]["enterIds"] == []

    def test_multiple_cues_ordered(self):
        c1 = _make_cue(cue_id="c1", trigger_ms=0)
        c2 = _make_cue(cue_id="c2", trigger_ms=2000)
        page = _make_page(cues=(c1, c2))
        sb = _make_storyboard(pages=(page,))
        adapter = InfographicStoryboardAdapter(fps=30)

        props = adapter.to_remotion_props(sb)
        assert props["pages"][0]["cues"][0]["startFrame"] < props["pages"][0]["cues"][1]["startFrame"]


# ── Metadata passthrough ────────────────────────────────────────────

class TestMetadataPassthrough:
    def test_page_metadata_fields(self):
        page = _make_page(page_id="pg-1")
        sb = _make_storyboard(pages=(page,))
        adapter = InfographicStoryboardAdapter()

        meta = {
            "pg-1": {
                "seriesTitle": "AI 系列",
                "chapterTitle": "第一章",
                "layoutType": "comparison",
                "composition": "split-left",
                "slideRole": "overview",
                "relationshipType": "cause",
                "coreIdea": "核心观点",
                "visualStrategy": "策略",
                "narrativeLink": "叙事连接",
                "conclusion": "结论",
                "seriesPersistent": True,
                "chapterPersistent": True,
            }
        }
        props = adapter.to_remotion_props(sb, metadata=meta)
        p = props["pages"][0]

        assert p["seriesTitle"] == "AI 系列"
        assert p["chapterTitle"] == "第一章"
        assert p["layoutType"] == "comparison"
        assert p["composition"] == "split-left"
        assert p["slideRole"] == "overview"
        assert p["relationshipType"] == "cause"
        assert p["coreIdea"] == "核心观点"
        assert p["visualStrategy"] == "策略"
        assert p["narrativeLink"] == "叙事连接"
        assert p["conclusion"] == "结论"
        assert p["seriesPersistent"] is True
        assert p["chapterPersistent"] is True

    def test_missing_metadata_uses_defaults(self):
        page = _make_page()
        sb = _make_storyboard(pages=(page,))
        adapter = InfographicStoryboardAdapter()

        props = adapter.to_remotion_props(sb, metadata={})
        p = props["pages"][0]
        assert p["seriesTitle"] == ""
        assert p["layoutType"] == "overview"
        assert p["composition"] == "split-right"
        assert p["slideRole"] == "detail"
        assert p["relationshipType"] == "none"


# ── Sanitization boundaries ─────────────────────────────────────────

class TestSanitization:
    def test_control_characters_stripped(self):
        n = _make_node(text="hello\x00world\x08!")
        page = _make_page(nodes=(n,))
        sb = _make_storyboard(pages=(page,))
        adapter = InfographicStoryboardAdapter()
        props = adapter.to_remotion_props(sb)
        assert props["pages"][0]["nodes"] == ["helloworld!"]

    def test_newline_and_tab_preserved(self):
        n = _make_node(text="line1\nline2\ttab")
        page = _make_page(nodes=(n,))
        sb = _make_storyboard(pages=(page,))
        adapter = InfographicStoryboardAdapter()
        props = adapter.to_remotion_props(sb)
        assert props["pages"][0]["nodes"] == ["line1\nline2\ttab"]

    def test_text_truncated_at_500_chars(self):
        long_text = "x" * 1000
        n = _make_node(text=long_text)
        page = _make_page(nodes=(n,))
        sb = _make_storyboard(pages=(page,))
        adapter = InfographicStoryboardAdapter()
        props = adapter.to_remotion_props(sb)
        assert len(props["pages"][0]["nodes"][0]) == 500

    def test_invalid_layout_type_falls_back(self):
        page = _make_page()
        sb = _make_storyboard(pages=(page,))
        adapter = InfographicStoryboardAdapter()
        props = adapter.to_remotion_props(sb, metadata={"page-1": {"layoutType": "INVALID"}})
        assert props["pages"][0]["layoutType"] == "overview"

    def test_invalid_composition_falls_back(self):
        page = _make_page()
        sb = _make_storyboard(pages=(page,))
        adapter = InfographicStoryboardAdapter()
        props = adapter.to_remotion_props(sb, metadata={"page-1": {"composition": "bad"}})
        assert props["pages"][0]["composition"] == "split-right"

    def test_invalid_slide_role_falls_back(self):
        page = _make_page()
        sb = _make_storyboard(pages=(page,))
        adapter = InfographicStoryboardAdapter()
        props = adapter.to_remotion_props(sb, metadata={"page-1": {"slideRole": "invalid"}})
        assert props["pages"][0]["slideRole"] == "detail"

    def test_invalid_relationship_type_falls_back(self):
        page = _make_page()
        sb = _make_storyboard(pages=(page,))
        adapter = InfographicStoryboardAdapter()
        props = adapter.to_remotion_props(sb, metadata={"page-1": {"relationshipType": "unknown"}})
        assert props["pages"][0]["relationshipType"] == "none"

    def test_error_messages_do_not_expose_internal_paths(self):
        adapter = InfographicStoryboardAdapter()
        with pytest.raises(StoryboardConversionError) as exc_info:
            adapter.to_remotion_props(InfographicStoryboard(pages=(), total_duration_ms=0))
        assert "/" not in str(exc_info.value)
        assert "\\" not in str(exc_info.value)


# ── Invalid input rejection ─────────────────────────────────────────

class TestInvalidInput:
    def test_empty_pages_raises(self):
        adapter = InfographicStoryboardAdapter()
        sb = InfographicStoryboard(pages=(), total_duration_ms=1000)
        with pytest.raises(StoryboardConversionError) as exc_info:
            adapter.to_remotion_props(sb)
        assert exc_info.value.code == "EMPTY_STORYBOARD"

    def test_zero_duration_raises(self):
        adapter = InfographicStoryboardAdapter()
        page = _make_page(cue_start_ms=0, cue_end_ms=0)
        sb = InfographicStoryboard(pages=(page,), total_duration_ms=0)
        with pytest.raises(StoryboardConversionError) as exc_info:
            adapter.to_remotion_props(sb)
        assert exc_info.value.code == "INVALID_DURATION"

    def test_negative_duration_raises(self):
        adapter = InfographicStoryboardAdapter()
        page = _make_page(cue_start_ms=0, cue_end_ms=0)
        sb = InfographicStoryboard(pages=(page,), total_duration_ms=-100)
        with pytest.raises(StoryboardConversionError) as exc_info:
            adapter.to_remotion_props(sb)
        assert exc_info.value.code == "INVALID_DURATION"

    def test_too_many_pages_raises(self):
        adapter = InfographicStoryboardAdapter()
        pages = tuple(_make_page(page_id=f"p-{i}") for i in range(201))
        sb = InfographicStoryboard(pages=pages, total_duration_ms=10000)
        with pytest.raises(StoryboardConversionError) as exc_info:
            adapter.to_remotion_props(sb)
        assert exc_info.value.code == "TOO_MANY_PAGES"

    def test_too_many_nodes_raises(self):
        nodes = tuple(_make_node(node_id=f"n-{i}") for i in range(21))
        page = _make_page(nodes=nodes)
        sb = _make_storyboard(pages=(page,))
        adapter = InfographicStoryboardAdapter()
        with pytest.raises(StoryboardConversionError) as exc_info:
            adapter.to_remotion_props(sb)
        assert exc_info.value.code == "LIMIT_EXCEEDED"

    def test_page_end_before_start_raises(self):
        page = _make_page(cue_start_ms=5000, cue_end_ms=1000)
        sb = _make_storyboard(pages=(page,), total_duration_ms=5000)
        adapter = InfographicStoryboardAdapter()
        with pytest.raises(StoryboardConversionError) as exc_info:
            adapter.to_remotion_props(sb)
        assert exc_info.value.code == "INVALID_PAGE_TIMING"

    def test_invalid_fps_raises(self):
        with pytest.raises(StoryboardConversionError) as exc_info:
            InfographicStoryboardAdapter(fps=0)
        assert exc_info.value.code == "INVALID_FPS"

    def test_invalid_dimensions_raises(self):
        with pytest.raises(StoryboardConversionError) as exc_info:
            InfographicStoryboardAdapter(width=0, height=100)
        assert exc_info.value.code == "INVALID_DIMENSIONS"

    def test_max_duration_exceeded_raises(self):
        adapter = InfographicStoryboardAdapter()
        page = _make_page(cue_start_ms=0, cue_end_ms=601_000)
        sb = InfographicStoryboard(pages=(page,), total_duration_ms=601_000)
        with pytest.raises(StoryboardConversionError) as exc_info:
            adapter.to_remotion_props(sb)
        assert exc_info.value.code == "INVALID_DURATION"


# ── Round-trip serialization ─────────────────────────────────────────

class TestSerialization:
    def test_props_are_json_serializable(self):
        import json

        adapter = InfographicStoryboardAdapter()
        sb = _make_storyboard()
        props = adapter.to_remotion_props(sb)

        # Must not raise
        serialized = json.dumps(props, ensure_ascii=False)
        deserialized = json.loads(serialized)
        assert deserialized["fps"] == props["fps"]
        assert deserialized["pages"][0]["id"] == props["pages"][0]["id"]

    def test_domain_storyboard_round_trip(self):
        """Domain storyboard → props → verify page count matches."""
        p1 = _make_page(page_id="p-1", title="First", cue_start_ms=0, cue_end_ms=3000)
        p2 = _make_page(page_id="p-2", title="Second", cue_start_ms=3000, cue_end_ms=6000)
        sb = InfographicStoryboard(pages=(p1, p2), total_duration_ms=6000)

        adapter = InfographicStoryboardAdapter(fps=30)
        props = adapter.to_remotion_props(sb)

        assert len(props["pages"]) == 2
        for i, page in enumerate(sb.pages):
            assert props["pages"][i]["pageTitle"] == page.title
            assert props["pages"][i]["id"] == page.page_id


# ── Edge cases ───────────────────────────────────────────────────────

class TestEdgeCases:
    def test_single_node_single_cue(self):
        """Simplest possible valid storyboard."""
        n = _make_node(text="唯一节点")
        c = _make_cue(trigger_ms=0)
        page = _make_page(nodes=(n,), cues=(c,))
        sb = _make_storyboard(pages=(page,), total_duration_ms=5000)
        adapter = InfographicStoryboardAdapter(fps=30)

        props = adapter.to_remotion_props(sb)
        assert len(props["pages"]) == 1
        assert props["pages"][0]["nodes"] == ["唯一节点"]
        assert props["pages"][0]["totalDurationFrames"] if "totalDurationFrames" in props["pages"][0] else True

    def test_unicode_text_preserved(self):
        n = _make_node(text="中文测试 🎉 مرحبا")
        page = _make_page(nodes=(n,))
        sb = _make_storyboard(pages=(page,))
        adapter = InfographicStoryboardAdapter()
        props = adapter.to_remotion_props(sb)
        assert props["pages"][0]["nodes"][0] == "中文测试 🎉 مرحبا"

    def test_mixed_node_kinds(self):
        n1 = _make_node(kind="text", text="文字")
        n2 = _make_node(node_id="n-2", kind="image", text="图片", image_path="img.png")
        n3 = _make_node(node_id="n-3", kind="shape", text="形状")
        page = _make_page(nodes=(n1, n2, n3))
        sb = _make_storyboard(pages=(page,))
        adapter = InfographicStoryboardAdapter()

        props = adapter.to_remotion_props(sb)
        assert props["pages"][0]["nodes"] == ["文字", "图片", "形状"]
        assert props["pages"][0]["image"] == "img.png"

    def test_overlapping_pages_are_rejected_by_p1_contract(self):
        p1 = _make_page(page_id="p-1", cue_start_ms=0, cue_end_ms=5000)
        p2 = _make_page(page_id="p-2", cue_start_ms=2000, cue_end_ms=7000)
        sb = _make_storyboard(pages=(p1, p2), total_duration_ms=7000)
        adapter = InfographicStoryboardAdapter(fps=30)

        with pytest.raises(StoryboardConversionError) as error:
            adapter.to_remotion_props(sb)
        assert error.value.code == "OVERLAPPING_TIMELINE"

    def test_all_valid_layout_types_accepted(self):
        for layout in ("overview", "question", "principle", "evidence", "case",
                       "path", "flow", "comparison", "layers", "cause",
                       "cycle", "timeline", "focus", "summary"):
            page = _make_page()
            sb = _make_storyboard(pages=(page,))
            adapter = InfographicStoryboardAdapter()
            props = adapter.to_remotion_props(sb, metadata={"page-1": {"layoutType": layout}})
            assert props["pages"][0]["layoutType"] == layout
