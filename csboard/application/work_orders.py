from __future__ import annotations

import hashlib
import json
from typing import Any

from csboard.adapters.filesystem.work_orders import FilesystemWorkOrderRepository
from csboard.domain.errors import DomainError
from csboard.domain.execution_plan import CANONICAL_STAGES, ExecutionPlan
from csboard.domain.work_order import STAGE_SKILLS, StageWorkOrder, fingerprint


STAGE_INPUTS = {
    "generate-visual-anchors": (),
    "clone-voice": ("planning.av-plan",),
    "plan-storyboard": ("planning.av-plan", "timing.timeline"),
    "generate-illustrations": ("planning.storyboard",),
    "render-visuals": ("timing.timeline", "planning.storyboard", "illustrations.manifest"),
    "compose-video": ("audio.voice-manifest", "timing.timeline", "render.manifest"),
}
STAGE_OUTPUTS = {
    "generate-visual-anchors": "planning.av-plan",
    "clone-voice": "audio.voice-manifest",
    "plan-storyboard": "planning.storyboard",
    "generate-illustrations": "illustrations.manifest",
    "render-visuals": "render.manifest",
    "compose-video": "output.final-manifest",
}


class WorkOrderService:
    def __init__(self, tasks) -> None:
        self.tasks = tasks
        self.repository = FilesystemWorkOrderRepository(tasks)

    def show(self, task_id: str, run_id: str, stage: str) -> dict[str, Any]:
        if stage not in CANONICAL_STAGES:
            raise DomainError("VALIDATION_ERROR", "未知工作单 Stage")
        task = self.tasks.get_task(task_id)
        run = self.tasks.get_run(task_id, run_id)
        if run.task_id != task.task_id:
            raise DomainError("NOT_FOUND", "运行记录不存在")
        with self.tasks.task_lock(task_id):
            payload, parameters = self._payload(task, run, stage)
            current = self.repository.get(task_id, run_id, stage)
            if current and current.input_fingerprint == payload["input_fingerprint"]:
                return current.to_dict()
            if current:
                self.repository.save(current.transition("stale"), {}, "stale: input fingerprint changed\n")
            revision = (current.revision + 1) if current else 1
            work_order = StageWorkOrder(
                **{**payload, "revision": revision,
                   "work_order_id": "wo-" + hashlib.sha256(
                       f"{task_id}:{run_id}:{stage}:{payload['input_fingerprint']}".encode()).hexdigest()[:24]}
            )
            instructions = (
                f"# {stage}\n\nRead parameters from `{work_order.parameters_path}`. "
                "Use only structured commands from this work order. External candidate commands are not implemented.\n"
            )
            self.repository.save(work_order, parameters, instructions)
            return work_order.to_dict()

    def _payload(self, task: Any, run: Any, stage: str) -> tuple[dict[str, Any], dict[str, Any]]:
        task_id, run_id = task.task_id, run.run_id
        request = self.tasks.get_request(task_id) or {}
        plan = ExecutionPlan.from_dict(request.get("execution_plan", {}))
        index_path = self.tasks.run_dir(task_id, run_id) / "artifacts" / "index.json"
        index = self.tasks.read_json(index_path).get("artifacts", {})
        inputs = []
        for key in STAGE_INPUTS[stage]:
            item = index.get(key)
            if item and item.get("status", "succeeded") == "succeeded":
                inputs.append({"artifact_key": key, "revision": int(item.get("revision", 1)),
                               "sha256": "sha256:" + str(item["sha256"]), "status": "succeeded",
                               "relative_path": str(item["relative_path"])})
        safe_request = {
            "script_sha256": hashlib.sha256(str(request.get("script", "")).encode()).hexdigest(),
            "style": str(request.get("style", "")), "include_subtitles": bool(request.get("include_subtitles", True)),
            "stroke_detail": str(request.get("stroke_detail", "detailed")),
            "visual_anchor_enabled": bool(request.get("visual_anchor_enabled", True)),
            "execution_plan": plan.to_dict(),
        }
        parameters = {"schema_version": "1.0", "stage": stage, "input_summary": safe_request,
                      "input_artifacts": inputs}
        value = {"identity": {"task_id": task_id, "run_id": run_id, "stage": stage,
                                "skill": STAGE_SKILLS[stage], "pipeline_id": task.pipeline_id,
                                "engine": task.engine.value}, "scope": {"kind": "stage"},
                 "input_artifacts": inputs, "parameters": parameters}
        work_id_hint = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:24]
        output = (f"manual/illustrations/candidates/wo-{work_id_hint}"
                  if stage == "generate-illustrations" else f"work-orders/{stage}/output")
        status = "waiting-manual-trigger" if stage in plan.manual_stages else "ready"
        return ({"schema_version": "1.0", "identity": value["identity"],
                 "input_fingerprint": fingerprint(value), "status": status, "scope": value["scope"],
                 "input_artifacts": inputs, "parameters_path": f"work-orders/{stage}/parameters.json",
                 "instructions_path": f"work-orders/{stage}/instructions.md", "output_directory": output,
                 "expected_outputs": [{"artifact_key": STAGE_OUTPUTS[stage], "status": "succeeded"}],
                 "commands": {action: [] for action in ("run", "import", "validate", "accept", "reject", "retry")},
                 "next_action": {"code": "CAPABILITY_NOT_AVAILABLE", "message": "外部 Work Order command 尚未实现"}}, parameters)
