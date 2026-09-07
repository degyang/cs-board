"""Safe task-package persistence for asset generation provenance."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from csboard.domain.errors import DomainError, NotFoundError

from .repository import FilesystemTaskRepository


class FilesystemGenerationRecordStore:
    """Persist and read generation records without writing media binaries.

    This store owns only ``generation.json`` and immutable attempt documents.
    Binary replacement and regeneration deliberately remain outside this first
    provenance slice.
    """

    def __init__(self, repository: FilesystemTaskRepository) -> None:
        self.repository = repository
        schema_path = Path(__file__).parents[3] / "schemas" / "artifacts" / "generation-record.schema.json"
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
        except (OSError, ValueError) as error:
            raise RuntimeError("generation-record schema is unavailable") from error
        self._validator = Draft202012Validator(schema, format_checker=FormatChecker())

    def save_current(self, task_id: str, run_id: str, asset_id: str, record: dict[str, Any]) -> None:
        """Validate fully before atomically replacing only ``generation.json``."""
        self._validate_record(task_id, run_id, asset_id, record, expected_scope="current")
        target = self._asset_dir(task_id, run_id, asset_id) / "generation.json"
        with self.repository.task_lock(task_id):
            self.repository.write_json(target, record)

    def save_attempt(self, task_id: str, run_id: str, asset_id: str, record: dict[str, Any]) -> None:
        """Atomically save a non-current attempt without changing current state."""
        self._validate_record(task_id, run_id, asset_id, record, expected_scope="attempt")
        attempt_id = str(record["attempt"]["attempt_id"])
        target = self._asset_dir(task_id, run_id, asset_id) / "attempts" / f"{attempt_id}.json"
        with self.repository.task_lock(task_id):
            self.repository.write_json(target, record)

    def read_current(self, task_id: str, run_id: str, asset_id: str) -> dict[str, Any]:
        target = self._asset_dir(task_id, run_id, asset_id) / "generation.json"
        if not target.is_file():
            raise NotFoundError("资产生成记录不存在")
        try:
            record = self.repository.read_json(target)
        except (OSError, ValueError, TypeError) as error:
            raise DomainError("GENERATION_RECORD_INVALID", "资产生成记录无效") from error
        self._validate_record(task_id, run_id, asset_id, record, expected_scope="current")
        return record

    def list_current(self, task_id: str, run_id: str) -> list[dict[str, Any]]:
        """Return every valid current record in a run in stable asset-id order.

        Directories without a current document are deliberately not assets yet.
        A present document, however, is always read through ``read_current`` so
        corruption and identity/path violations remain visible to callers.
        """
        self._validate_route_identity(task_id, run_id, "asset-placeholder")
        self.repository.get_run(task_id, run_id)
        assets_dir = self.repository.run_dir(task_id, run_id) / "assets"
        if not assets_dir.is_dir():
            return []
        records: list[dict[str, Any]] = []
        for asset_dir in sorted(assets_dir.iterdir(), key=lambda item: item.name):
            if not asset_dir.is_dir() or not (asset_dir / "generation.json").is_file():
                continue
            records.append(self.read_current(task_id, run_id, asset_dir.name))
        return records

    def media_path(self, task_id: str, run_id: str, asset_id: str) -> tuple[Path, str]:
        """Return a verified task-local current media path and MIME type."""
        record = self.read_current(task_id, run_id, asset_id)
        output = record["output"]
        assert isinstance(output, dict)  # guaranteed by current-record validation
        path = self._resolve_project_output_path(str(output["relative_path"]), task_id, run_id, asset_id)
        if not path.is_file():
            raise NotFoundError("资产媒体不存在")
        return path, str(output["mime_type"])

    def _asset_dir(self, task_id: str, run_id: str, asset_id: str) -> Path:
        self._validate_route_identity(task_id, run_id, asset_id)
        self.repository.get_run(task_id, run_id)
        return self.repository.run_dir(task_id, run_id) / "assets" / asset_id

    @staticmethod
    def _validate_route_identity(task_id: str, run_id: str, asset_id: str) -> None:
        for value in (task_id, run_id, asset_id):
            if not isinstance(value, str) or not value or Path(value).is_absolute() or any(part in {".", ".."} for part in Path(value).parts):
                raise DomainError("GENERATION_RECORD_ROUTE_INVALID", "资产记录身份无效")

    def _validate_record(self, task_id: str, run_id: str, asset_id: str, record: object, *, expected_scope: str) -> None:
        self._validate_route_identity(task_id, run_id, asset_id)
        if not isinstance(record, dict):
            raise DomainError("GENERATION_RECORD_INVALID", "资产生成记录无效")
        errors = list(self._validator.iter_errors(record))
        if errors:
            raise DomainError("GENERATION_RECORD_INVALID", "资产生成记录无效")
        identity = record.get("identity")
        if (
            record.get("record_scope") != expected_scope
            or record.get("asset_id") != asset_id
            or not isinstance(identity, dict)
            or identity.get("task_id") != task_id
            or identity.get("run_id") != run_id
        ):
            raise DomainError("GENERATION_RECORD_IDENTITY_MISMATCH", "资产生成记录身份不匹配")
        output = record.get("output")
        if isinstance(output, dict):
            self._resolve_project_output_path(str(output.get("relative_path", "")), task_id, run_id, asset_id)
        for item in record.get("input_assets", []):
            if not isinstance(item, dict):
                raise DomainError("GENERATION_RECORD_INVALID", "资产生成记录无效")
            self._resolve_project_output_path(str(item.get("relative_path", "")), task_id, None, None)

    def _resolve_project_output_path(
        self, relative_path: str, task_id: str, run_id: str | None, asset_id: str | None,
    ) -> Path:
        raw = Path(relative_path)
        if raw.is_absolute() or any(part in {".", ".."} for part in raw.parts):
            raise DomainError("GENERATION_RECORD_PATH_INVALID", "资产记录路径无效")
        expected = ["outputs", task_id]
        if run_id is not None and asset_id is not None:
            expected.extend(["runs", run_id, "assets", asset_id])
        if list(raw.parts[:len(expected)]) != expected or len(raw.parts) <= len(expected):
            raise DomainError("GENERATION_RECORD_PATH_INVALID", "资产记录路径无效")
        candidate = (self.repository.project_root / raw).resolve(strict=False)
        try:
            candidate.relative_to(self.repository.project_root)
        except ValueError as error:
            raise DomainError("GENERATION_RECORD_PATH_INVALID", "资产记录路径无效") from error
        return candidate
