from __future__ import annotations

from enum import StrEnum


class Engine(StrEnum):
    WHITEBOARD = "whiteboard"
    INFOGRAPHIC_REMOTION = "infographic-remotion"


class Entrypoint(StrEnum):
    WEB = "web"
    DESKTOP = "desktop"
    CLI = "cli"
    SKILL = "skill"


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STALE = "stale"
    SKIPPED = "skipped"


class TimingSource(StrEnum):
    WHISPER = "whisper"
    EQUAL_FALLBACK = "equal_fallback"
