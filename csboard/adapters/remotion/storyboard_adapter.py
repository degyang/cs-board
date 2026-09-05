"""InfographicStoryboardAdapter — domain storyboard → Remotion props.

Converts an ``InfographicStoryboard`` (pure domain) into the
``InfographicVideoProps`` dict that ``video_renderer/render.mjs`` consumes.
No Remotion import, no subprocess, no network, no legacy webapp coupling.

The adapter is a pure function: given the same inputs it always produces the
same output.  All I/O (reading illustrations, audio) is the caller's job;
this adapter receives already-resolved data.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from csboard.domain.infographic import (
    InfographicContractError,
    InfographicCue,
    InfographicPage,
    InfographicStoryboard,
    duration_frames,
    milliseconds_to_frame,
    validate_infographic_storyboard,
)

# ── Constants ────────────────────────────────────────────────────────

_VALID_LAYOUT_TYPES = frozenset({
    "overview", "question", "principle", "evidence", "case",
    "path", "flow", "comparison", "layers", "cause", "cycle",
    "timeline", "focus", "summary",
})

_VALID_COMPOSITIONS = frozenset({
    "split-right", "split-left", "center-stage", "top-bottom", "full-width",
})

_VALID_SLIDE_ROLES = frozenset({"overview", "detail", "transition", "summary"})

_VALID_RELATIONSHIP_TYPES = frozenset({"none", "sequence", "cause", "comparison", "hierarchy"})

_DEFAULT_FPS = 30
_DEFAULT_WIDTH = 1920
_DEFAULT_HEIGHT = 1080
_MAX_NODES_PER_PAGE = 20
_MAX_PAGES = 200
_MAX_DURATION_MS = 600_000  # 10 minutes


# ── Errors ───────────────────────────────────────────────────────────

class StoryboardConversionError(Exception):
    """Raised when the storyboard cannot be converted to valid Remotion props."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


# ── Adapter ──────────────────────────────────────────────────────────

class InfographicStoryboardAdapter:
    """Convert an ``InfographicStoryboard`` to Remotion ``InfographicVideoProps``.

    Parameters
    ----------
    fps:
        Frames per second for the Remotion composition.
    width:
        Canvas width in pixels.
    height:
        Canvas height in pixels.
    style:
        Visual style name (maps to a palette in ``video.tsx``).
    subtitles_enabled:
        Whether to render subtitle overlay.
    """

    def __init__(
        self,
        fps: int = _DEFAULT_FPS,
        width: int = _DEFAULT_WIDTH,
        height: int = _DEFAULT_HEIGHT,
        style: str = "极简粗线简笔白板风",
        subtitles_enabled: bool = False,
    ) -> None:
        if fps < 1:
            raise StoryboardConversionError("INVALID_FPS", "fps 必须大于 0")
        if width < 1 or height < 1:
            raise StoryboardConversionError("INVALID_DIMENSIONS", "width 和 height 必须大于 0")
        self._fps = fps
        self._width = width
        self._height = height
        self._style = style
        self._subtitles_enabled = subtitles_enabled

    # ── Public API ───────────────────────────────────────────────────

    def to_remotion_props(
        self,
        storyboard: InfographicStoryboard,
        illustrations: dict[str, str] | None = None,
        audio_paths: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Convert a domain storyboard to Remotion ``InfographicVideoProps``.

        Parameters
        ----------
        storyboard:
            Domain storyboard with pages, nodes, and cues.
        illustrations:
            Mapping of ``visual_id`` → image path (run-relative or absolute).
            Used to populate each page's ``image`` field.
        audio_paths:
            Audio file paths to include in the output (for the renderer).
        metadata:
            Optional per-page metadata overrides.  Keys are ``page_id``; values
            are dicts with fields like ``seriesTitle``, ``chapterTitle``,
            ``layoutType``, ``composition``, ``slideRole``, ``relationshipType``,
            ``coreIdea``, ``visualStrategy``, ``narrativeLink``, ``conclusion``,
            ``seriesPersistent``, ``chapterPersistent``.

        Returns
        -------
        dict
            A dict matching the ``InfographicVideoProps`` TypeScript type.

        Raises
        ------
        StoryboardConversionError
            If the storyboard is empty, has invalid timing, or exceeds limits.
        """
        illustrations = illustrations or {}
        metadata = metadata or {}

        try:
            validate_infographic_storyboard(storyboard)
        except InfographicContractError as exc:
            raise StoryboardConversionError(exc.code, "storyboard 不符合 P1 契约") from exc
        self._validate_storyboard(storyboard)
        self._validate_relative_refs(illustrations, audio_paths)

        total_duration_ms = storyboard.total_duration_ms
        total_duration_frames = duration_frames(total_duration_ms, self._fps)

        pages: list[dict[str, Any]] = []
        for page in storyboard.pages:
            page_meta = metadata.get(page.page_id, {})
            pages.append(self._convert_page(page, illustrations, page_meta))

        props: dict[str, Any] = {
            "schemaVersion": 1,
            "fps": self._fps,
            "width": self._width,
            "height": self._height,
            "totalDurationMs": total_duration_ms,
            "totalDurationFrames": total_duration_frames,
            "style": self._style,
            "pages": pages,
        }
        if self._subtitles_enabled:
            props["subtitlesEnabled"] = True
        if audio_paths:
            props["audioPaths"] = list(audio_paths)
        return props

    # ── Page conversion ──────────────────────────────────────────────

    def _convert_page(
        self,
        page: InfographicPage,
        illustrations: dict[str, str],
        meta: dict[str, Any],
    ) -> dict[str, Any]:
        start_frame = self._ms_to_frames(page.cue_start_ms)
        end_frame = start_frame + duration_frames(page.cue_end_ms - page.cue_start_ms, self._fps)

        node_texts = self._extract_node_texts(page)
        image = self._resolve_image(page, illustrations)

        cues = [self._convert_cue(cue, start_frame) for cue in page.cues]

        result: dict[str, Any] = {
            "id": page.page_id,
            "image": image,
            "startFrame": start_frame,
            "endFrame": end_frame,
            "seriesTitle": str(meta.get("seriesTitle", "")),
            "chapterTitle": str(meta.get("chapterTitle", "")),
            "pageTitle": page.title,
            "layoutType": self._sanitize_layout(meta.get("layoutType", "overview")),
            "composition": self._sanitize_composition(meta.get("composition", "split-right")),
            "slideRole": self._sanitize_slide_role(meta.get("slideRole", "detail")),
            "relationshipType": self._sanitize_relationship(meta.get("relationshipType", "none")),
            "coreIdea": str(meta.get("coreIdea", "")),
            "visualStrategy": str(meta.get("visualStrategy", "")),
            "narrativeLink": str(meta.get("narrativeLink", "")),
            "nodes": node_texts,
            "conclusion": str(meta.get("conclusion", "")),
            "cues": cues,
            "seriesPersistent": bool(meta.get("seriesPersistent", False)),
            "chapterPersistent": bool(meta.get("chapterPersistent", False)),
        }
        return result

    def _extract_node_texts(self, page: InfographicPage) -> list[str]:
        """Extract display text from each node, preserving order."""
        texts: list[str] = []
        for node in page.nodes:
            text = node.props.get("text", "")
            if not isinstance(text, str):
                text = str(text)
            # Sanitize: limit length, strip control characters
            text = self._sanitize_text(text, max_chars=500)
            texts.append(text)
        return texts

    def _resolve_image(
        self,
        page: InfographicPage,
        illustrations: dict[str, str],
    ) -> str:
        """Find the image path for this page from illustrations or node props."""
        # Try illustration mapping by visual_id from first image node
        for node in page.nodes:
            if node.kind == "image":
                visual_id = node.props.get("visual_id", "")
                if visual_id and visual_id in illustrations:
                    return illustrations[visual_id]
                image_path = node.props.get("image_path", "")
                if image_path:
                    return str(image_path)

        # Try any node with image_path
        for node in page.nodes:
            image_path = node.props.get("image_path", "")
            if image_path:
                return str(image_path)

        # Fallback: use page_id as placeholder
        return f"pages/{page.page_id}.png"

    # ── Cue conversion ───────────────────────────────────────────────

    def _convert_cue(self, cue: InfographicCue, page_start_frame: int) -> dict[str, Any]:
        """Convert a domain InfographicCue to a Remotion TimedCue."""
        trigger_frame = self._ms_to_frames(cue.trigger_ms)
        # Cue frames are absolute in the domain; Remotion expects page-relative
        # but the video.tsx component handles this by subtracting page.startFrame.
        # So we keep absolute frames here.
        return {
            "id": cue.cue_id,
            "anchorText": "",
            "startFrame": trigger_frame,
            "endFrame": trigger_frame + max(1, self._fps),  # default 1s duration
            "spokenStartMs": cue.trigger_ms,
            "spokenEndMs": cue.trigger_ms + 1000,
            "enterIds": [cue.cue_id.replace("enter-", "node-")] if cue.action == "enter" else [],
            "focusId": "",
            "alignmentCoverage": 1.0,
            "alignmentConfidence": 1.0,
        }

    # ── Validation ───────────────────────────────────────────────────

    def _validate_storyboard(self, storyboard: InfographicStoryboard) -> None:
        if not storyboard.pages:
            raise StoryboardConversionError("EMPTY_STORYBOARD", "Storyboard 必须至少包含一个页面")
        if len(storyboard.pages) > _MAX_PAGES:
            raise StoryboardConversionError(
                "TOO_MANY_PAGES",
                f"页面数 {len(storyboard.pages)} 超过上限 {_MAX_PAGES}",
            )
        if storyboard.total_duration_ms <= 0:
            raise StoryboardConversionError(
                "INVALID_DURATION",
                "total_duration_ms 必须大于 0",
            )
        if storyboard.total_duration_ms > _MAX_DURATION_MS:
            raise StoryboardConversionError(
                "DURATION_EXCEEDED",
                f"总时长 {storyboard.total_duration_ms}ms 超过上限 {_MAX_DURATION_MS}ms",
            )
        for page in storyboard.pages:
            if len(page.nodes) > _MAX_NODES_PER_PAGE:
                raise StoryboardConversionError(
                    "TOO_MANY_NODES",
                    f"页面 {page.page_id} 节点数 {len(page.nodes)} 超过上限 {_MAX_NODES_PER_PAGE}",
                )
            if page.cue_end_ms < page.cue_start_ms:
                raise StoryboardConversionError(
                    "INVALID_PAGE_TIMING",
                    f"页面 {page.page_id} cue_end_ms({page.cue_end_ms}) < cue_start_ms({page.cue_start_ms})",
                )

    @staticmethod
    def _validate_relative_refs(illustrations: dict[str, str], audio_paths: list[str] | None) -> None:
        for value in [*illustrations.values(), *(audio_paths or [])]:
            path = PurePosixPath(value)
            if not isinstance(value, str) or not value or "\\" in value or path.is_absolute() or ".." in path.parts or ":" in value:
                raise StoryboardConversionError("ABSOLUTE_PATH_FORBIDDEN", "renderer asset 必须为 run-relative POSIX 路径")

    # ── Sanitization ─────────────────────────────────────────────────

    @staticmethod
    def _sanitize_text(text: str, max_chars: int = 500) -> str:
        """Remove control characters and limit length."""
        # Strip control chars except newline/tab
        cleaned = "".join(
            ch for ch in text
            if ch in "\n\t" or (ord(ch) >= 32 and ch != "\x7f")
        )
        return cleaned[:max_chars]

    @staticmethod
    def _sanitize_layout(value: str) -> str:
        return value if value in _VALID_LAYOUT_TYPES else "overview"

    @staticmethod
    def _sanitize_composition(value: str) -> str:
        return value if value in _VALID_COMPOSITIONS else "split-right"

    @staticmethod
    def _sanitize_slide_role(value: str) -> str:
        return value if value in _VALID_SLIDE_ROLES else "detail"

    @staticmethod
    def _sanitize_relationship(value: str) -> str:
        return value if value in _VALID_RELATIONSHIP_TYPES else "none"

    # ── Frame math ───────────────────────────────────────────────────

    def _ms_to_frames(self, ms: int) -> int:
        """Convert milliseconds to Remotion frame number."""
        return milliseconds_to_frame(ms, self._fps)
