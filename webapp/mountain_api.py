from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from csboard.adapters.filesystem import FilesystemProjectRepository
from csboard.adapters.observability import JsonlTelemetry
from csboard.domain.errors import NotFoundError


def mountain_router(data_dir: Path) -> APIRouter:
    repository = FilesystemProjectRepository(data_dir)
    telemetry = JsonlTelemetry(repository)
    router = APIRouter(prefix="/api/mountain", tags=["mountain"])

    @router.get("/projects")
    def projects(limit: int = 50):
        items = []
        for path in sorted((data_dir / "projects").glob("*/project.json"), reverse=True)[:max(1, min(limit, 100))]:
            try:
                items.append(repository.get_project(path.parent.name).to_dict())
            except NotFoundError:
                continue
        return {"items": items}

    @router.get("/projects/{project_id}")
    def project(project_id: str):
        try:
            value = repository.get_project(project_id)
            run = repository.get_run(project_id, value.active_run_id) if value.active_run_id else None
            return {"project": value.to_dict(), "active_run": run.to_dict() if run else None}
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    @router.get("/projects/{project_id}/runs/{run_id}/events")
    def events(project_id: str, run_id: str, after: int = 0):
        try:
            items = telemetry.read_events(project_id, run_id, after)
            return {"items": items, "next_cursor": items[-1]["sequence"] if items else after}
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    @router.get("/projects/{project_id}/runs/{run_id}/logs")
    def logs(project_id: str, run_id: str):
        try:
            path = repository.run_dir(project_id, run_id) / "observability" / "logs.jsonl"
            repository.get_run(project_id, run_id)
            import json
            return {"items": [] if not path.exists() else [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]}
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    @router.post("/projects/{project_id}/runs/{run_id}/diagnostics")
    def diagnostics(project_id: str, run_id: str):
        try:
            return {"bundle": str(telemetry.export_diagnostic_bundle(project_id, run_id))}
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    return router
