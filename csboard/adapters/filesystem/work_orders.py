from __future__ import annotations

from csboard.domain.work_order import StageWorkOrder
from csboard.domain.validation import validate_relative_path

from .repository import FilesystemTaskRepository


class FilesystemWorkOrderRepository:
    """Auditable current + revision-history storage under a Run root."""

    def __init__(self, tasks: FilesystemTaskRepository) -> None:
        self.tasks = tasks

    def directory(self, task_id: str, run_id: str, stage: str) -> object:
        return self.tasks.run_dir(task_id, run_id) / "work-orders" / stage

    def get(self, task_id: str, run_id: str, stage: str) -> StageWorkOrder | None:
        path = self.directory(task_id, run_id, stage) / "work-order.json"
        return None if not path.is_file() else StageWorkOrder.from_dict(self.tasks.read_json(path))

    def save(self, work_order: StageWorkOrder, parameters: dict, instructions: str) -> None:
        task_id, run_id, stage = (work_order.identity[key] for key in ("task_id", "run_id", "stage"))
        directory = self.directory(task_id, run_id, stage)
        with self.tasks.task_lock(task_id):
            directory.mkdir(parents=True, exist_ok=True)
            revision_dir = directory / "revisions" / str(work_order.revision)
            revision_dir.mkdir(parents=True, exist_ok=True)
            for path in (work_order.parameters_path, work_order.instructions_path, work_order.output_directory):
                validate_relative_path(path)
            self.tasks.write_json(directory / "parameters.json", parameters)
            (directory / "instructions.md").write_text(instructions, encoding="utf-8")
            self.tasks.write_json(directory / "work-order.json", work_order.to_dict())
            self.tasks.write_json(revision_dir / "work-order.json", work_order.to_dict())
