"""Stable interfaces used by the shared application core."""

from csboard.ports.providers import (
    AlignmentPort,
    ImageModelPort,
    MediaPort,
    RendererPort,
    TextModelPort,
    TextToSpeechPort,
)
from csboard.ports.repositories import ArtifactStore, TaskRepository
from csboard.ports.telemetry import AuditSink, DiagnosticLogSink, DomainEventSink, Redactor

__all__ = [
    "AlignmentPort",
    "ArtifactStore",
    "AuditSink",
    "DiagnosticLogSink",
    "DomainEventSink",
    "ImageModelPort",
    "MediaPort",
    "TaskRepository",
    "Redactor",
    "RendererPort",
    "TextModelPort",
    "TextToSpeechPort",
]
