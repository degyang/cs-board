"""Tests for infographic domain models and voice_units_to_pages conversion."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from csboard.domain.enums import Engine
from csboard.domain.infographic import (
    INFOGRAPHIC_SCHEMA_VERSION,
    InfographicCue,
    InfographicContractError,
    InfographicNode,
    InfographicPage,
    InfographicStoryboard,
    RemotionEvidenceV1,
    RenderManifestV1,
    VOICE_UNIT_PAGE_STRATEGY,
    duration_frames,
    milliseconds_to_frame,
    validate_infographic_storyboard,
    voice_units_to_pages,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "infographic"


def _storyboard_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


# ── Round-trip serialization ────────────────────────────────────────

def test_infographic_cue_round_trip():
    original = InfographicCue(cue_id="c1", trigger_ms=1500, action="enter")
    restored = InfographicCue.from_dict(original.to_dict())
    assert restored == original


def test_infographic_node_round_trip():
    original = InfographicNode(
        node_id="n1", kind="image",
        props={"text": "hello", "image_path": "illustrations/v1.png"},
    )
    restored = InfographicNode.from_dict(original.to_dict())
    assert restored == original


def test_infographic_node_rejects_unknown_kind():
    with pytest.raises(InfographicContractError) as error:
        InfographicNode(node_id="n1", kind="video")
    assert error.value.code == "UNKNOWN_NODE_KIND"


def test_infographic_page_round_trip():
    page = InfographicPage(
        page_id="p1", title="First Page",
        nodes=(InfographicNode("n1", "text", {"text": "hi"}),),
        cues=(InfographicCue("c1", 0, "enter"),),
        cue_start_ms=0, cue_end_ms=5000,
    )
    restored = InfographicPage.from_dict(page.to_dict())
    assert restored == page


def test_infographic_storyboard_round_trip():
    sb = InfographicStoryboard(
        pages=(
            InfographicPage(
                "p1", "Page 1",
                nodes=(InfographicNode("n1", "text", {"text": "hi"}),),
                cues=(InfographicCue("c1", 0, "enter"),),
                cue_start_ms=0, cue_end_ms=1000,
            ),
        ),
        total_duration_ms=1000,
        metadata={"source": "test"},
    )
    restored = InfographicStoryboard.from_dict(sb.to_dict())
    assert restored == sb
    assert restored.engine == Engine.INFOGRAPHIC_REMOTION.value
    assert restored.schema_version == INFOGRAPHIC_SCHEMA_VERSION


def test_v1_golden_storyboard_fixtures_round_trip_and_reject_empty():
    single = InfographicStoryboard.from_dict(_storyboard_fixture("storyboard-single-visual-v1.json"))
    multi = InfographicStoryboard.from_dict(_storyboard_fixture("storyboard-multi-visual-v1.json"))
    assert InfographicStoryboard.from_dict(single.to_dict()) == single
    assert InfographicStoryboard.from_dict(multi.to_dict()) == multi
    assert [len(page.nodes) for page in multi.pages] == [2, 1]
    with pytest.raises(InfographicContractError) as error:
        InfographicStoryboard.from_dict(_storyboard_fixture("storyboard-empty-v1.json"))
    assert error.value.code == "EMPTY_STORYBOARD"


def test_v1_frame_coordinate_contract_is_zero_based_and_end_exclusive():
    assert milliseconds_to_frame(0, 30) == 0
    assert milliseconds_to_frame(1000, 30) == 30
    assert duration_frames(1000, 30) == 30
    assert duration_frames(1050, 30) == 32
    with pytest.raises(InfographicContractError) as error:
        duration_frames(0, 30)
    assert error.value.code == "INVALID_FRAME_COORDINATE"


def test_v1_dynamic_props_golden_fixture_has_run_relative_assets_and_frame_math():
    props = _storyboard_fixture("dynamic-infographic-props-v1.json")
    assert props["schemaVersion"] == 1
    assert props["totalDurationFrames"] == duration_frames(props["totalDurationMs"], props["fps"])
    assert all(not path.startswith("/") and ".." not in path.split("/") for path in props["audioPaths"])
    for page in props["pages"]:
        assert page["startFrame"] < page["endFrame"] <= props["totalDurationFrames"]
        assert not page["image"].startswith("/")


# ── voice_units_to_pages conversion ────────────────────────────────

def _make_voice_unit(unit_id: str, text: str, visual_ids: list[str]) -> dict:
    return {
        "unit_id": unit_id,
        "order": 0,
        "text": text,
        "visual_items": [{"visual_id": vid, "order": i} for i, vid in enumerate(visual_ids)],
    }


def _make_timeline_unit(unit_id: str, timings: list[tuple[str, int, int]]) -> dict:
    return {
        "unit_id": unit_id,
        "visual_timings": [
            {"visual_id": vid, "start_ms": s, "end_ms": e}
            for vid, s, e in timings
        ],
    }


def _make_visual(visual_id: str, prompt: str = "test prompt") -> dict:
    return {"visual_id": visual_id, "prompt": prompt}


def test_voice_units_to_pages_single_unit_single_visual():
    units = [_make_voice_unit("u1", "Hello world", ["v1"])]
    timeline = [_make_timeline_unit("u1", [("v1", 0, 3000)])]
    visuals = [_make_visual("v1", "A greeting")]

    sb = voice_units_to_pages(units, timeline, visuals)

    assert sb.total_duration_ms == 3000
    assert len(sb.pages) == 1
    page = sb.pages[0]
    assert page.page_id == "page-u1"
    assert page.cue_start_ms == 0
    assert page.cue_end_ms == 3000
    assert len(page.nodes) == 1
    assert page.nodes[0].kind == "image"
    assert page.nodes[0].props["text"] == "A greeting"
    assert len(page.cues) == 1
    assert page.cues[0].trigger_ms == 0


def test_voice_units_to_pages_multiple_visuals():
    units = [_make_voice_unit("u1", "Two pictures", ["v1", "v2"])]
    timeline = [_make_timeline_unit("u1", [("v1", 0, 2000), ("v2", 2000, 5000)])]
    visuals = [_make_visual("v1"), _make_visual("v2")]

    sb = voice_units_to_pages(units, timeline, visuals)

    assert sb.total_duration_ms == 5000
    page = sb.pages[0]
    assert len(page.nodes) == 2
    assert len(page.cues) == 2
    assert page.cues[0].trigger_ms == 0
    assert page.cues[1].trigger_ms == 2000
    assert VOICE_UNIT_PAGE_STRATEGY == "exactly_one_page_per_voice_unit"


def test_voice_units_to_pages_multiple_units():
    units = [
        _make_voice_unit("u1", "First", ["v1"]),
        _make_voice_unit("u2", "Second", ["v2"]),
    ]
    timeline = [
        _make_timeline_unit("u1", [("v1", 0, 3000)]),
        _make_timeline_unit("u2", [("v2", 3000, 6000)]),
    ]
    visuals = [_make_visual("v1"), _make_visual("v2")]

    sb = voice_units_to_pages(units, timeline, visuals)

    assert len(sb.pages) == 2
    assert sb.total_duration_ms == 6000
    assert sb.pages[0].cue_end_ms == 3000
    assert sb.pages[1].cue_start_ms == 3000


def test_voice_units_to_pages_empty_input():
    with pytest.raises(InfographicContractError, match="voice_units") as error:
        voice_units_to_pages([], [], [])
    assert error.value.code == "EMPTY_VOICE_UNITS"


def test_voice_units_to_pages_missing_visual_timing():
    """Missing timing is a deterministic contract failure, never a zero page."""
    units = [_make_voice_unit("u1", "Orphan", ["v1"])]
    timeline = []  # no timing for u1
    visuals = [_make_visual("v1")]

    with pytest.raises(InfographicContractError) as error:
        voice_units_to_pages(units, timeline, visuals)
    assert error.value.code == "MISSING_TIMELINE"


def test_voice_units_to_pages_rejects_missing_or_duplicate_visual_timing():
    units = [_make_voice_unit("u1", "Two", ["v1", "v2"])]
    visuals = [_make_visual("v1"), _make_visual("v2")]
    with pytest.raises(InfographicContractError) as error:
        voice_units_to_pages(units, [_make_timeline_unit("u1", [("v1", 0, 1000)])], visuals)
    assert error.value.code == "MISSING_VISUAL_REF"
    with pytest.raises(InfographicContractError) as error:
        voice_units_to_pages(units, [_make_timeline_unit("u1", [("v1", 0, 1000), ("v1", 1000, 2000)])], visuals)
    assert error.value.code == "MISSING_VISUAL_REF"


def test_voice_units_to_pages_preserves_image_path():
    units = [_make_voice_unit("u1", "Text", ["v1"])]
    timeline = [_make_timeline_unit("u1", [("v1", 0, 1000)])]
    visuals = [{"visual_id": "v1", "prompt": "p", "image_path": "illustrations/v1.png"}]

    sb = voice_units_to_pages(units, timeline, visuals)
    assert sb.pages[0].nodes[0].props["image_path"] == "illustrations/v1.png"


def test_voice_units_to_pages_default_node_kind():
    units = [_make_voice_unit("u1", "Text", ["v1"])]
    timeline = [_make_timeline_unit("u1", [("v1", 0, 1000)])]
    visuals = [_make_visual("v1")]

    sb = voice_units_to_pages(units, timeline, visuals, default_node_kind="text")
    assert sb.pages[0].nodes[0].kind == "text"


def test_v1_rejects_absolute_asset_path_and_secret():
    page = InfographicPage("p1", "P", (InfographicNode("n1", "image", {"image_path": "/tmp/a.png"}),), (InfographicCue("c1", 0, "enter"),), 0, 1000)
    with pytest.raises(InfographicContractError) as error:
        validate_infographic_storyboard(InfographicStoryboard((page,), 1000))
    assert error.value.code == "ABSOLUTE_PATH_FORBIDDEN"


@pytest.mark.parametrize("path", [
    "C:/render/infographic.mp4",
    "C:render/infographic.mp4",
    "file:///render/infographic.mp4",
    "render\\infographic.mp4",
    "render/../infographic.mp4",
])
def test_v1_rejects_non_posix_or_escaping_asset_path_matrix(path: str):
    page = InfographicPage("p1", "P", (InfographicNode("n1", "image", {"image_path": path}),), (InfographicCue("c1", 0, "enter"),), 0, 1000)
    with pytest.raises(InfographicContractError) as error:
        validate_infographic_storyboard(InfographicStoryboard((page,), 1000))
    assert error.value.code == "ABSOLUTE_PATH_FORBIDDEN"


@pytest.mark.parametrize("nested_value", [
    {"nested": ["api_key=sk-live-12345678"]},
    {"nested": {"value": "password: not-for-artifact"}},
    {"nested": "token=abc-12345678"},
    {"nested": "Bearer sk-live-12345678"},
])
def test_v1_rejects_explicit_secret_value_matrix(nested_value: dict):
    page = InfographicPage("p1", "P", (InfographicNode("n1", "text", nested_value),), (InfographicCue("c1", 0, "enter"),), 0, 1000)
    with pytest.raises(InfographicContractError) as error:
        validate_infographic_storyboard(InfographicStoryboard((page,), 1000))
    assert error.value.code == "SECRET_FORBIDDEN"


def test_v1_allows_ordinary_narrative_token_text():
    page = InfographicPage("p1", "P", (InfographicNode("n1", "text", {"text": "Token economics and bearer market dynamics."}),), (InfographicCue("c1", 0, "enter"),), 0, 1000)
    validate_infographic_storyboard(InfographicStoryboard((page,), 1000))


def test_v1_rejects_overlap_zero_duration_and_missing_visual_ref():
    page1 = InfographicPage("p1", "P", (InfographicNode("n1", "text", {}),), (InfographicCue("c1", 0, "enter"),), 0, 1000)
    page2 = InfographicPage("p2", "P", (InfographicNode("n2", "text", {}),), (InfographicCue("c2", 500, "enter"),), 500, 1500)
    with pytest.raises(InfographicContractError) as error:
        validate_infographic_storyboard(InfographicStoryboard((page1, page2), 1500))
    assert error.value.code == "OVERLAPPING_TIMELINE"
    zero = InfographicPage("p3", "P", (InfographicNode("n3", "text", {}),), (InfographicCue("c3", 0, "enter"),), 0, 0)
    with pytest.raises(InfographicContractError) as error:
        validate_infographic_storyboard(InfographicStoryboard((zero,), 1))
    assert error.value.code == "INVALID_PAGE_TIMING"
    with pytest.raises(InfographicContractError) as error:
        voice_units_to_pages([_make_voice_unit("u1", "x", ["v1"])], [_make_timeline_unit("u1", [("missing", 0, 1)])], [_make_visual("v1")])
    assert error.value.code == "MISSING_VISUAL_REF"


def test_v1_render_manifest_and_evidence_are_portable_hash_only():
    digest = "a" * 64
    manifest = RenderManifestV1("render/infographic.mp4", digest, 1, 1, 1, digest)
    assert manifest.to_dict()["output_relative_path"] == "render/infographic.mp4"
    evidence = RemotionEvidenceV1("2026-09-05T00:00:00Z", digest, digest, digest, {"node": "24"}, digest, digest, digest, digest)
    assert evidence.to_dict()["verified_at"].endswith("Z")
