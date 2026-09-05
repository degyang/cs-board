"""Versioned renderer-neutral contracts for infographic-remotion (P1)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import PurePosixPath
import re
from typing import Any, Mapping

from csboard.domain.enums import Engine

INFOGRAPHIC_SCHEMA_VERSION = 1
RENDER_MANIFEST_SCHEMA_VERSION = 1
REMOTION_EVIDENCE_SCHEMA_VERSION = 1
MAX_PAGES, MAX_NODES_PER_PAGE, MAX_CUES_PER_PAGE, MAX_DURATION_MS = 200, 20, 100, 600_000
INFOGRAPHIC_NODE_KINDS = frozenset({"text", "shape", "image", "chart"})
INFOGRAPHIC_CUE_ACTIONS = frozenset({"enter", "exit", "emphasize"})
# V1 deliberately chooses the fixed end of the former "1–2 pages per Voice
# Unit" design space.  A Voice Unit is exactly one page; multiple visuals are
# nodes/cues on that page.  Splitting is a future schema-version change, never
# a renderer-side guess.
VOICE_UNIT_PAGE_STRATEGY = "exactly_one_page_per_voice_unit"
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_HASH = re.compile(r"[a-f0-9]{64}")
_SECRET = re.compile(r"(?:api[_-]?key|secret|token|password|authorization)", re.I)
_URI_OR_WINDOWS_DRIVE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_SECRET_VALUE = re.compile(
    r"""(?ix)
    \b(?:api[ _-]?key|access[ _-]?key|private[ _-]?key|secret|password)\b\s*[:=]\s*\S+
    |\b(?:token|key)\b\s*[:=]\s*(?:[A-Za-z0-9._~+/=-]*[0-9._~+/=-][A-Za-z0-9._~+/=-]{7,})
    |\bbearer\s+(?:[A-Za-z0-9._~+/=-]*[0-9._~+/=-][A-Za-z0-9._~+/=-]{7,})
    """
)


class InfographicContractError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _id(value: str, label: str) -> None:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise InfographicContractError("INVALID_ID", f"{label} 必须是稳定安全标识")


def _relative(value: str, label: str) -> None:
    path = PurePosixPath(value) if isinstance(value, str) else PurePosixPath("")
    if (not isinstance(value, str) or not value or "\\" in value or
            _URI_OR_WINDOWS_DRIVE.match(value) or path.is_absolute() or
            ".." in path.parts or value.startswith("./")):
        raise InfographicContractError("ABSOLUTE_PATH_FORBIDDEN", f"{label} 必须是 run-relative POSIX 路径")


def _no_secret(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if _SECRET.search(str(key)):
                raise InfographicContractError("SECRET_FORBIDDEN", "信息图契约不得包含 secret")
            _no_secret(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _no_secret(nested)
    elif isinstance(value, str) and _SECRET_VALUE.search(value):
        # Values are scanned only for an explicit credential syntax. Ordinary
        # narrative such as "token economics" remains portable content.
        raise InfographicContractError("SECRET_FORBIDDEN", "信息图契约不得包含 secret")


def milliseconds_to_frame(milliseconds: int, fps: int) -> int:
    """Map an absolute millisecond cue to its zero-based frame coordinate.

    Frame intervals are start-inclusive/end-exclusive.  Cue starts use floor
    conversion; a total-duration frame count must use ``duration_frames`` so
    a non-frame-aligned tail is not silently dropped.
    """
    if not isinstance(milliseconds, int) or milliseconds < 0 or not isinstance(fps, int) or fps <= 0:
        raise InfographicContractError("INVALID_FRAME_COORDINATE", "毫秒和 fps 必须为非负/正整数")
    return milliseconds * fps // 1000


def duration_frames(duration_ms: int, fps: int) -> int:
    """Return the number of frames covering a positive millisecond interval."""
    if not isinstance(duration_ms, int) or duration_ms <= 0 or not isinstance(fps, int) or fps <= 0:
        raise InfographicContractError("INVALID_FRAME_COORDINATE", "时长和 fps 必须为正整数")
    return (duration_ms * fps + 999) // 1000


@dataclass(frozen=True, slots=True)
class InfographicCue:
    cue_id: str
    trigger_ms: int
    action: str
    def to_dict(self) -> dict[str, Any]: return asdict(self)
    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "InfographicCue":
        return cls(str(value["cue_id"]), int(value["trigger_ms"]), str(value["action"]))


@dataclass(frozen=True, slots=True)
class InfographicNode:
    node_id: str
    kind: str
    props: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self) -> None:
        if self.kind not in INFOGRAPHIC_NODE_KINDS:
            raise InfographicContractError("UNKNOWN_NODE_KIND", "不支持的信息图节点类型")
    def to_dict(self) -> dict[str, Any]: return asdict(self)
    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "InfographicNode":
        return cls(str(value["node_id"]), str(value["kind"]), dict(value.get("props", {})))


@dataclass(frozen=True, slots=True)
class InfographicPage:
    page_id: str
    title: str
    nodes: tuple[InfographicNode, ...]
    cues: tuple[InfographicCue, ...]
    cue_start_ms: int
    cue_end_ms: int
    def to_dict(self) -> dict[str, Any]:
        return {"page_id": self.page_id, "title": self.title, "nodes": [x.to_dict() for x in self.nodes], "cues": [x.to_dict() for x in self.cues], "cue_start_ms": self.cue_start_ms, "cue_end_ms": self.cue_end_ms}
    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "InfographicPage":
        return cls(str(value["page_id"]), str(value["title"]), tuple(InfographicNode.from_dict(x) for x in value.get("nodes", [])), tuple(InfographicCue.from_dict(x) for x in value.get("cues", [])), int(value["cue_start_ms"]), int(value["cue_end_ms"]))


@dataclass(frozen=True, slots=True)
class InfographicStoryboard:
    """V1: every page and cue uses absolute milliseconds."""
    pages: tuple[InfographicPage, ...]
    total_duration_ms: int
    engine: str = Engine.INFOGRAPHIC_REMOTION.value
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = INFOGRAPHIC_SCHEMA_VERSION
    def to_dict(self) -> dict[str, Any]:
        validate_infographic_storyboard(self)
        return {"schema_version": self.schema_version, "engine": self.engine, "pages": [x.to_dict() for x in self.pages], "total_duration_ms": self.total_duration_ms, "metadata": dict(self.metadata)}
    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "InfographicStoryboard":
        result = cls(tuple(InfographicPage.from_dict(x) for x in value.get("pages", [])), int(value["total_duration_ms"]), str(value.get("engine", Engine.INFOGRAPHIC_REMOTION.value)), dict(value.get("metadata", {})), int(value.get("schema_version", INFOGRAPHIC_SCHEMA_VERSION)))
        validate_infographic_storyboard(result)
        return result


def validate_infographic_storyboard(storyboard: InfographicStoryboard) -> None:
    if storyboard.schema_version != INFOGRAPHIC_SCHEMA_VERSION: raise InfographicContractError("UNSUPPORTED_SCHEMA_VERSION", "不支持的 storyboard schema 版本")
    if storyboard.engine != Engine.INFOGRAPHIC_REMOTION.value: raise InfographicContractError("INVALID_ENGINE", "storyboard engine 无效")
    if not storyboard.pages: raise InfographicContractError("EMPTY_STORYBOARD", "storyboard 不可为空")
    if len(storyboard.pages) > MAX_PAGES: raise InfographicContractError("TOO_MANY_PAGES", "页面数超过上限")
    if not 0 < storyboard.total_duration_ms <= MAX_DURATION_MS: raise InfographicContractError("INVALID_DURATION", "总时长无效")
    _no_secret(storyboard.metadata)
    last_page_end, page_ids = 0, set()
    for page in storyboard.pages:
        _id(page.page_id, "page_id")
        if page.page_id in page_ids: raise InfographicContractError("DUPLICATE_ID", "page_id 不可重复")
        page_ids.add(page.page_id)
        if page.cue_start_ms < 0 or page.cue_end_ms <= page.cue_start_ms: raise InfographicContractError("INVALID_PAGE_TIMING", "页面必须有非零正向绝对时间区间")
        if page.cue_start_ms < last_page_end: raise InfographicContractError("OVERLAPPING_TIMELINE", "页面时间不可重叠")
        if page.cue_end_ms > storyboard.total_duration_ms: raise InfographicContractError("DURATION_MISMATCH", "页面超过总时长")
        last_page_end = page.cue_end_ms
        if not page.nodes: raise InfographicContractError("EMPTY_PAGE", "页面不可为空")
        if len(page.nodes) > MAX_NODES_PER_PAGE or len(page.cues) > MAX_CUES_PER_PAGE: raise InfographicContractError("LIMIT_EXCEEDED", "页面元素超过上限")
        node_ids, cue_ids, last_cue = set(), set(), page.cue_start_ms - 1
        for node in page.nodes:
            _id(node.node_id, "node_id")
            if node.node_id in node_ids: raise InfographicContractError("DUPLICATE_ID", "node_id 不可重复")
            node_ids.add(node.node_id); _no_secret(node.props)
            for key in ("image_path", "asset_path"):
                if key in node.props: _relative(str(node.props[key]), key)
        for cue in page.cues:
            _id(cue.cue_id, "cue_id")
            if cue.cue_id in cue_ids: raise InfographicContractError("DUPLICATE_ID", "cue_id 不可重复")
            cue_ids.add(cue.cue_id)
            if cue.action not in INFOGRAPHIC_CUE_ACTIONS: raise InfographicContractError("INVALID_CUE_ACTION", "cue action 无效")
            if not page.cue_start_ms <= cue.trigger_ms < page.cue_end_ms or cue.trigger_ms < last_cue: raise InfographicContractError("INVALID_CUE_TIMING", "cue 时间无效")
            last_cue = cue.trigger_ms
    if last_page_end != storyboard.total_duration_ms: raise InfographicContractError("DURATION_MISMATCH", "总时长必须等于最后页面结束")


def voice_units_to_pages(voice_units: list[dict[str, Any]], timeline_units: list[dict[str, Any]], storyboard_visuals: list[dict[str, Any]], default_node_kind: str = "image") -> InfographicStoryboard:
    """Pure V1 conversion using ``exactly_one_page_per_voice_unit``.

    A declared visual must have exactly one non-overlapping timing record and
    exactly one catalog record.  The resulting page and its cues remain in
    absolute milliseconds; translation to frames belongs at the props edge.
    """
    if not voice_units: raise InfographicContractError("EMPTY_VOICE_UNITS", "voice_units 不可为空")
    if default_node_kind not in INFOGRAPHIC_NODE_KINDS: raise InfographicContractError("UNKNOWN_NODE_KIND", "节点类型无效")
    visuals = {str(x.get("visual_id", "")): x for x in storyboard_visuals}
    if len(visuals) != len(storyboard_visuals):
        raise InfographicContractError("DUPLICATE_ID", "visual_id 不可重复")
    timelines = {str(x.get("unit_id", "")): x for x in timeline_units}
    if len(timelines) != len(timeline_units):
        raise InfographicContractError("DUPLICATE_ID", "unit_id 不可重复")
    pages: list[InfographicPage] = []
    for unit in voice_units:
        unit_id = str(unit.get("unit_id", "")); _id(unit_id, "unit_id")
        declared = [str(x.get("visual_id", "")) for x in unit.get("visual_items", [])]
        if len(set(declared)) != len(declared):
            raise InfographicContractError("DUPLICATE_ID", "Voice Unit visual_id 不可重复")
        for visual_id in declared:
            _id(visual_id, "visual_id")
        timing = timelines.get(unit_id)
        if not declared: raise InfographicContractError("EMPTY_VISUALS", "Voice Unit 缺少 visual")
        if timing is None: raise InfographicContractError("MISSING_TIMELINE", "Voice Unit 缺少 timeline")
        records = list(timing.get("visual_timings", []))
        if not records: raise InfographicContractError("EMPTY_TIMELINE", "Voice Unit 缺少 visual timing")
        if len(records) != len(declared):
            raise InfographicContractError("MISSING_VISUAL_REF", "每个 Voice Unit visual 必须恰有一条 timing")
        nodes: list[InfographicNode] = []; cues: list[InfographicCue] = []; prior_end: int | None = None; timed_visual_ids: set[str] = set()
        for index, record in enumerate(records):
            visual_id = str(record.get("visual_id", "")); start, end = int(record.get("start_ms", -1)), int(record.get("end_ms", -1))
            if visual_id in timed_visual_ids or visual_id not in declared or visual_id not in visuals: raise InfographicContractError("MISSING_VISUAL_REF", "缺少或重复 visual ref")
            timed_visual_ids.add(visual_id)
            if start < 0 or end <= start: raise InfographicContractError("INVALID_VISUAL_TIMING", "visual timing 无效")
            if prior_end is not None and start < prior_end: raise InfographicContractError("OVERLAPPING_TIMELINE", "visual timing 不可重叠")
            prior_end = end; visual = visuals[visual_id]
            props: dict[str, Any] = {"text": visual.get("prompt", unit.get("text", "")), "order": index, "visual_id": visual_id}
            if "image_path" in visual: props["image_path"] = visual["image_path"]
            nodes.append(InfographicNode(f"{unit_id}-{visual_id}", str(visual.get("node_kind", default_node_kind)), props)); cues.append(InfographicCue(f"enter-{visual_id}", start, "enter"))
        if timed_visual_ids != set(declared):
            raise InfographicContractError("MISSING_VISUAL_REF", "Voice Unit visual 缺少 timing")
        pages.append(InfographicPage(f"page-{unit_id}", str(unit.get("text", ""))[:80], tuple(nodes), tuple(cues), int(records[0]["start_ms"]), int(records[-1]["end_ms"])))
    storyboard = InfographicStoryboard(tuple(pages), pages[-1].cue_end_ms); validate_infographic_storyboard(storyboard); return storyboard


@dataclass(frozen=True, slots=True)
class RenderManifestV1:
    output_relative_path: str; output_sha256: str; size_bytes: int; duration_ms: int; frames: int; probe_sha256: str
    schema_version: int = RENDER_MANIFEST_SCHEMA_VERSION; engine: str = Engine.INFOGRAPHIC_REMOTION.value
    def to_dict(self) -> dict[str, Any]: validate_render_manifest(self); return asdict(self)


def validate_render_manifest(value: RenderManifestV1) -> None:
    if value.schema_version != RENDER_MANIFEST_SCHEMA_VERSION or value.engine != Engine.INFOGRAPHIC_REMOTION.value: raise InfographicContractError("MANIFEST_INVALID", "manifest schema 或 engine 无效")
    _relative(value.output_relative_path, "output_relative_path")
    if not all(_HASH.fullmatch(x) for x in (value.output_sha256, value.probe_sha256)) or min(value.size_bytes, value.duration_ms, value.frames) <= 0: raise InfographicContractError("MANIFEST_INVALID", "manifest 输出或 hash 无效")


@dataclass(frozen=True, slots=True)
class RemotionEvidenceV1:
    verified_at: str; renderer_sha256: str; lockfile_sha256: str; props_sha256: str; tool_versions: dict[str, str]; service_probe_sha256: str; artifact_index_sha256: str; render_manifest_sha256: str; mp4_sha256: str
    schema_version: int = REMOTION_EVIDENCE_SCHEMA_VERSION
    def to_dict(self) -> dict[str, Any]: validate_remotion_evidence(self); return asdict(self)


def validate_remotion_evidence(value: RemotionEvidenceV1) -> None:
    hashes = (value.renderer_sha256, value.lockfile_sha256, value.props_sha256, value.service_probe_sha256, value.artifact_index_sha256, value.render_manifest_sha256, value.mp4_sha256)
    if value.schema_version != REMOTION_EVIDENCE_SCHEMA_VERSION or not value.verified_at.endswith("Z") or not all(_HASH.fullmatch(x) for x in hashes): raise InfographicContractError("EVIDENCE_INVALID", "evidence schema、UTC 时间或 hash 无效")
    if not value.tool_versions or any(not key or not version for key, version in value.tool_versions.items()): raise InfographicContractError("EVIDENCE_INVALID", "evidence 缺少工具版本")
    _no_secret(value.tool_versions)
