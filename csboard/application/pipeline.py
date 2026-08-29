"""Pipeline orchestrator for multi-stage video production.

Supports three execution policies:
- ``auto``: run to target stage or completion
- ``gated``: pause after each successful stage
- ``targeted``: run only the specified stage and its dependencies
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from csboard.application.context import CommandContext, new_id, utc_now
from csboard.domain.enums import Entrypoint, RunStatus, StageStatus
from csboard.domain.errors import DomainError


# Stage dependency graph for mountain-av-v1 (linear pipeline).
STAGE_ORDER: list[str] = [
    "segment-script",
    "clone-voice",
    "plan-storyboard",
    "generate-illustrations",
    "render-visuals",
    "compose-video",
]

# Type alias for stage executor functions.
# Signature: (project_id, run_id, context) -> result dict
StageExecutor = Callable[[str, str, CommandContext], dict[str, Any]]


@dataclass
class PipelineOrchestrator:
    """Orchestrate stage execution with dependency resolution.

    Parameters
    ----------
    get_run:
        Callable that returns a Run-like object with ``stages`` dict.
    save_run:
        Callable to persist the run after status changes.
    append_event:
        Callable to append a telemetry event.
    """

    get_run: Callable[[str, str], Any]
    save_run: Callable[[Any], None]
    append_event: Callable[[str, str, dict[str, Any]], dict[str, Any]]

    _executors: dict[str, StageExecutor] = field(default_factory=dict)

    def register_stage(self, name: str, executor: StageExecutor) -> None:
        """Register a stage executor."""
        self._executors[name] = executor

    def get_next_stage(self, run: Any) -> str | None:
        """Return the next pending or failed stage, or None if all complete."""
        for stage in STAGE_ORDER:
            state = run.stages.get(stage)
            if state is None or state.status in (StageStatus.PENDING, StageStatus.FAILED, StageStatus.STALE):
                return stage
        return None

    def get_pending_stages(self, run: Any, target: str | None = None) -> list[str]:
        """Return stages that need to run to reach *target* (or complete)."""
        if target and target not in STAGE_ORDER:
            raise DomainError("VALIDATION_ERROR", f"未知阶段: {target}")
        end_idx = STAGE_ORDER.index(target) if target else len(STAGE_ORDER) - 1
        pending: list[str] = []
        for stage in STAGE_ORDER[: end_idx + 1]:
            state = run.stages.get(stage)
            if state is None or state.status in (StageStatus.PENDING, StageStatus.FAILED, StageStatus.STALE):
                pending.append(stage)
        return pending

    def run_pipeline(
        self,
        project_id: str,
        run_id: str,
        policy: str = "auto",
        target_stage: str | None = None,
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        """Run the pipeline with the given policy.

        Parameters
        ----------
        project_id:
            Project identifier.
        run_id:
            Run identifier.
        policy:
            ``auto``, ``gated``, or ``targeted``.
        target_stage:
            For ``targeted`` policy: the stage to run (with its dependencies).
        context:
            Command context for telemetry correlation.
        """
        if policy not in ("auto", "gated", "targeted"):
            raise DomainError("VALIDATION_ERROR", f"未知策略: {policy}")
        if policy == "targeted" and not target_stage:
            raise DomainError("VALIDATION_ERROR", "targeted 策略需要 --stage 参数")

        context = context or CommandContext(entrypoint=Entrypoint.CLI)
        run = self.get_run(project_id, run_id)

        # For targeted policy, only run the target stage (skip deps check for now)
        if policy == "targeted":
            pending = [target_stage] if self._needs_run(run, target_stage) else []
        else:
            pending = self.get_pending_stages(run, target_stage)

        if not pending:
            return {
                "ok": True,
                "command": "pipeline.run",
                "project_id": project_id,
                "run_id": run_id,
                "trace_id": run.trace_id,
                "command_id": context.command_id,
                "policy": policy,
                "stages_executed": [],
                "status": "completed",
                "message": "所有阶段已完成",
            }

        # Update run status
        run.status = RunStatus.RUNNING
        self.save_run(run)

        self.append_event(project_id, run_id, {
            "event_type": "PipelineStarted",
            "policy": policy,
            "target_stage": target_stage,
            "pending_stages": pending,
        })

        results: list[dict[str, Any]] = []
        for stage in pending:
            result = self._execute_stage(project_id, run_id, stage, context)
            results.append(result)

            if not result.get("ok"):
                # Stage failed — stop pipeline
                run = self.get_run(project_id, run_id)
                run.status = RunStatus.FAILED
                self.save_run(run)
                self.append_event(project_id, run_id, {
                    "event_type": "PipelineFailed",
                    "failed_stage": stage,
                    "error": result.get("error"),
                })
                break

            if policy == "gated":
                # Gated: pause after first successful stage
                self.append_event(project_id, run_id, {
                    "event_type": "PipelineGated",
                    "completed_stage": stage,
                    "next_stage": self._next_stage_after(stage),
                })
                break
        else:
            # All stages completed
            run = self.get_run(project_id, run_id)
            run.status = RunStatus.SUCCEEDED
            self.save_run(run)
            self.append_event(project_id, run_id, {
                "event_type": "PipelineSucceeded",
                "stages_executed": [r.get("stage") for r in results],
            })

        executed = [r.get("stage") for r in results]
        last_ok = results[-1] if results else {}
        return {
            "ok": all(r.get("ok") for r in results),
            "command": "pipeline.run",
            "project_id": project_id,
            "run_id": run_id,
            "trace_id": run.trace_id,
            "command_id": context.command_id,
            "policy": policy,
            "stages_executed": executed,
            "results": results,
            "next_stage": self._next_stage_after(executed[-1]) if executed else None,
        }

    def resume_pipeline(
        self,
        project_id: str,
        run_id: str,
        policy: str = "auto",
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        """Resume pipeline from the last successful stage."""
        context = context or CommandContext(entrypoint=Entrypoint.CLI)
        run = self.get_run(project_id, run_id)

        if run.status == RunStatus.SUCCEEDED:
            return {
                "ok": True,
                "command": "pipeline.resume",
                "project_id": project_id,
                "run_id": run_id,
                "trace_id": run.trace_id,
                "command_id": context.command_id,
                "policy": policy,
                "stages_executed": [],
                "status": "completed",
                "message": "流水线已完成，无需恢复",
            }

        # Reset failed run to running
        if run.status == RunStatus.FAILED:
            run.status = RunStatus.RUNNING
            self.save_run(run)

        return self.run_pipeline(project_id, run_id, policy, context=context)

    def _execute_stage(
        self,
        project_id: str,
        run_id: str,
        stage: str,
        context: CommandContext,
    ) -> dict[str, Any]:
        """Execute a single stage using the registered executor."""
        executor = self._executors.get(stage)
        if executor is None:
            return {
                "ok": False,
                "command": "stage.run",
                "project_id": project_id,
                "run_id": run_id,
                "stage": stage,
                "error": {
                    "code": "CAPABILITY_NOT_AVAILABLE",
                    "message": f"阶段 {stage} 将在后续 Mountain PR 提供",
                    "retryable": False,
                },
            }
        try:
            return executor(project_id, run_id, context)
        except Exception as exc:
            return {
                "ok": False,
                "command": "stage.run",
                "project_id": project_id,
                "run_id": run_id,
                "stage": stage,
                "error": {
                    "code": getattr(exc, "code", "STAGE_EXECUTION_ERROR"),
                    "message": str(exc)[:500],
                    "retryable": getattr(exc, "retryable", False),
                },
            }

    def _needs_run(self, run: Any, stage: str) -> bool:
        """Check if a stage needs to be executed."""
        state = run.stages.get(stage)
        return state is None or state.status in (StageStatus.PENDING, StageStatus.FAILED, StageStatus.STALE)

    @staticmethod
    def _next_stage_after(stage: str) -> str | None:
        """Return the stage that follows *stage*, or None if it's the last."""
        try:
            idx = STAGE_ORDER.index(stage)
            return STAGE_ORDER[idx + 1] if idx + 1 < len(STAGE_ORDER) else None
        except ValueError:
            return None
