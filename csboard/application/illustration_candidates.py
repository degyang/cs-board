"""External illustration candidate import, validation, and acceptance."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image

from csboard.adapters.filesystem import FilesystemArtifactStore
from csboard.adapters.filesystem.work_orders import FilesystemWorkOrderRepository
from csboard.application.av_artifacts import illustration_manifest_document, json_bytes
from csboard.domain.errors import DomainError
from csboard.domain.models import StageState
from csboard.domain.enums import StageStatus
from csboard.domain.validation import validate_relative_path


class IllustrationCandidateService:
    """Close the external Codex-image gate without pretending it is a provider."""

    STAGE = "generate-illustrations"

    def __init__(self, tasks) -> None:
        self.tasks = tasks
        self.work_orders = FilesystemWorkOrderRepository(tasks)
        self.artifacts = FilesystemArtifactStore(tasks)

    def import_manifest(
        self, task_id: str, run_id: str, work_order_id: str, manifest_path: str
    ) -> dict[str, Any]:
        work_order = self._current(task_id, run_id, work_order_id, {"waiting-external-output"})
        validate_relative_path(manifest_path)
        expected_prefix = work_order.output_directory.rstrip("/") + "/"
        if not manifest_path.startswith(expected_prefix):
            raise DomainError("VALIDATION_ERROR", "候选 manifest 必须位于工作单输出目录")
        path = self.tasks.run_dir(task_id, run_id) / manifest_path
        output_root = (self.tasks.run_dir(task_id, run_id) / work_order.output_directory).resolve()
        if path.is_symlink() or not path.resolve().is_relative_to(output_root) or not path.is_file():
            raise DomainError("VALIDATION_ERROR", "候选 manifest 不存在")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raise DomainError("VALIDATION_ERROR", "候选 manifest 不是有效 JSON")
        self._validate_envelope(payload, work_order_id)
        self._save_payload(task_id, run_id, "candidate-import.json", payload)
        self._save_state(work_order.transition("validating"))
        return {"ok": True, "work_order_id": work_order_id, "status": "validating",
                "candidate_id": payload["candidate_id"], "item_count": len(payload["items"])}

    def validate(self, task_id: str, run_id: str, work_order_id: str) -> dict[str, Any]:
        work_order = self._current(task_id, run_id, work_order_id, {"validating"})
        payload = self._load_payload(task_id, run_id, "candidate-import.json")
        storyboard = self._artifact_json(task_id, run_id, "planning.storyboard")
        expected = {str(item["visual_id"]) for item in storyboard.get("visuals", [])}
        received = [str(item.get("visual_id", "")) for item in payload["items"]]
        errors: list[dict[str, str]] = []
        if len(received) != len(set(received)):
            errors.append({"code": "DUPLICATE_VISUAL_ID", "message": "visual_id 重复"})
        missing, unexpected = sorted(expected - set(received)), sorted(set(received) - expected)
        if missing:
            errors.append({"code": "VISUAL_COVERAGE_MISSING", "message": ",".join(missing)})
        if unexpected:
            errors.append({"code": "VISUAL_COVERAGE_UNEXPECTED", "message": ",".join(unexpected)})

        checked: list[dict[str, Any]] = []
        prefix = work_order.output_directory.rstrip("/") + "/"
        for item in payload["items"]:
            relative_path = item.get("path")
            try:
                if not isinstance(relative_path, str):
                    raise ValueError
                validate_relative_path(relative_path)
                if not relative_path.startswith(prefix):
                    raise ValueError
                image_path = self.tasks.run_dir(task_id, run_id) / relative_path
                output_root = (self.tasks.run_dir(task_id, run_id) / work_order.output_directory).resolve()
                if (image_path.is_symlink() or not image_path.resolve().is_relative_to(output_root)
                        or not image_path.is_file() or image_path.stat().st_size > 32 * 1024 * 1024):
                    raise FileNotFoundError
                digest = hashlib.sha256(image_path.read_bytes()).hexdigest()
                declared = str(item.get("sha256", "")).removeprefix("sha256:")
                if declared and declared != digest:
                    errors.append({"code": "HASH_MISMATCH", "message": str(item.get("visual_id", ""))})
                    continue
                with Image.open(image_path) as image:
                    image.verify()
                with Image.open(image_path) as image:
                    width, height = image.size
                    fmt = image.format
                if (fmt not in {"PNG", "JPEG", "WEBP"} or width < 512 or height < 512
                        or width > 4096 or height > 4096):
                    errors.append({"code": "IMAGE_SPEC_INVALID", "message": str(item.get("visual_id", ""))})
                    continue
                checked.append({**item, "sha256": digest, "width": width, "height": height,
                                "format": fmt.lower()})
            except (OSError, ValueError, FileNotFoundError):
                errors.append({"code": "IMAGE_INVALID", "message": str(item.get("visual_id", ""))})

        result = {"ok": not errors, "work_order_id": work_order_id,
                  "candidate_id": payload["candidate_id"], "items": checked, "errors": errors}
        self._save_payload(task_id, run_id, "candidate-validation.json", result)
        next_status = "waiting-acceptance" if not errors else "waiting-external-output"
        self._save_state(work_order.transition(next_status))
        return {**result, "status": next_status}

    def accept(self, task_id: str, run_id: str, work_order_id: str) -> dict[str, Any]:
        work_order = self._current(task_id, run_id, work_order_id, {"waiting-acceptance"})
        validation = self._load_payload(task_id, run_id, "candidate-validation.json")
        if not validation.get("ok"):
            raise DomainError("VALIDATION_ERROR", "候选尚未通过校验")
        storyboard = self._artifact_json(task_id, run_id, "planning.storyboard")
        prompt_by_id = {str(item["visual_id"]): str(item.get("prompt", "")) for item in storyboard.get("visuals", [])}
        run_dir = self.tasks.run_dir(task_id, run_id)
        destination = run_dir / "media" / "images"
        destination.mkdir(parents=True, exist_ok=True)
        illustrations: list[dict[str, Any]] = []
        for item in validation["items"]:
            source = run_dir / item["path"]
            suffix = source.suffix.lower() if source.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} else ".png"
            target = destination / f"{item['visual_id']}{suffix}"
            target.write_bytes(source.read_bytes())
            illustrations.append({
                "visual_id": item["visual_id"], "unit_id": item.get("unit_id", ""),
                "image_path": str(target.relative_to(run_dir)), "sha256": "sha256:" + item["sha256"],
                "width": item["width"], "height": item["height"], "model": "codex-imagegen",
                "attempt": int(item.get("attempt", 1)),
                "source_prompt": prompt_by_id.get(item["visual_id"], "")[:200],
                "candidate_id": validation["candidate_id"],
            })
        task = self.tasks.get_task(task_id)
        document = illustration_manifest_document(task_id, run_id, illustrations, task.engine)
        artifact = self.artifacts.commit_bytes(
            task_id, run_id, "illustrations.manifest", "planning/illustration-manifest.json",
            json_bytes(document), self.STAGE,
        )
        run = self.tasks.get_run(task_id, run_id)
        run.stages[self.STAGE] = StageState(StageStatus.SUCCEEDED, 1)
        self.tasks.save_run(run)
        self._save_state(work_order.transition("succeeded"))
        return {"ok": True, "command": "work-order.accept", "task_id": task_id,
                "run_id": run_id, "trace_id": run.trace_id, "stage": self.STAGE,
                "result": "succeeded", "artifacts": [artifact.artifact_key],
                "candidate_id": validation["candidate_id"], "image_count": len(illustrations),
                "next_stage": "render-visuals"}

    def reject(self, task_id: str, run_id: str, work_order_id: str, reason: str) -> dict[str, Any]:
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
            raise DomainError("VALIDATION_ERROR", "拒绝原因无效")
        work_order = self._current(task_id, run_id, work_order_id, {"waiting-acceptance"})
        self._save_payload(task_id, run_id, "candidate-rejection.json", {"reason": reason.strip()})
        self._save_state(work_order.transition("waiting-external-output"))
        return {"ok": True, "work_order_id": work_order_id, "status": "waiting-external-output"}

    def _current(self, task_id: str, run_id: str, work_order_id: str, statuses: set[str]):
        work_order = self.work_orders.get(task_id, run_id, self.STAGE)
        if work_order is None or work_order.work_order_id != work_order_id:
            raise DomainError("WORK_ORDER_STALE", "工作单不存在或已过期")
        if work_order.status not in statuses:
            raise DomainError("INVALID_STATE", f"工作单当前状态为 {work_order.status}")
        return work_order

    def _validate_envelope(self, payload: Any, work_order_id: str) -> None:
        if not isinstance(payload, dict) or set(payload) - {"schema_version", "work_order_id", "candidate_id", "items"}:
            raise DomainError("VALIDATION_ERROR", "候选 manifest 字段无效")
        if payload.get("schema_version") != "1.0" or payload.get("work_order_id") != work_order_id:
            raise DomainError("VALIDATION_ERROR", "候选 manifest 身份无效")
        if not isinstance(payload.get("candidate_id"), str) or not payload["candidate_id"].strip():
            raise DomainError("VALIDATION_ERROR", "candidate_id 无效")
        if not isinstance(payload.get("items"), list) or not payload["items"]:
            raise DomainError("VALIDATION_ERROR", "候选图片列表为空")
        allowed = {"visual_id", "unit_id", "path", "sha256", "attempt"}
        if any(not isinstance(item, dict) or set(item) - allowed or not isinstance(item.get("visual_id"), str)
               for item in payload["items"]):
            raise DomainError("VALIDATION_ERROR", "候选图片条目无效")

    def _directory(self, task_id: str, run_id: str) -> Path:
        return self.tasks.run_dir(task_id, run_id) / "work-orders" / self.STAGE

    def _save_payload(self, task_id: str, run_id: str, name: str, payload: dict[str, Any]) -> None:
        self.tasks.write_json(self._directory(task_id, run_id) / name, payload)

    def _load_payload(self, task_id: str, run_id: str, name: str) -> dict[str, Any]:
        path = self._directory(task_id, run_id) / name
        if not path.is_file():
            raise DomainError("INVALID_STATE", f"{name} 不存在")
        return self.tasks.read_json(path)

    def _save_state(self, work_order) -> None:
        task_id, run_id, stage = (work_order.identity[key] for key in ("task_id", "run_id", "stage"))
        directory = self.work_orders.directory(task_id, run_id, stage)
        parameters = self.tasks.read_json(directory / "parameters.json")
        instructions = (directory / "instructions.md").read_text(encoding="utf-8")
        self.work_orders.save(work_order, parameters, instructions)

    def _artifact_json(self, task_id: str, run_id: str, key: str) -> dict[str, Any]:
        ref = self.artifacts.get(task_id, run_id, key)
        if not ref:
            raise DomainError("DEPENDENCY_NOT_READY", f"Artifact 不存在: {key}")
        path = self.tasks.run_dir(task_id, run_id) / "artifacts" / ref["relative_path"]
        return json.loads(path.read_text(encoding="utf-8"))
