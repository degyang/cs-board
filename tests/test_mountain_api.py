"""Tests for Mountain API endpoints.

NOTE: These tests cover the legacy /api/mountain/ endpoints which are being
isolated from the new product. The legacy API calls MountainCommands.segment_script
which has been removed as part of the generate-visual-anchors migration.
These tests will be moved to tests/legacy/ or removed when the legacy API
is fully decommissioned.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from csboard.adapters.filesystem import FilesystemArtifactStore, FilesystemTaskRepository
from csboard.domain.enums import Engine, Entrypoint, TaskStatus, RunStatus
from csboard.domain.models import Task, Run
from webapp.mountain_api import mountain_router
from webapp.mountain_server import create_app


def _create_test_app(tmpdir: Path) -> tuple[FastAPI, FilesystemTaskRepository]:
    """Create a test FastAPI app with mountain router."""
    app = FastAPI()
    router = mountain_router(tmpdir)
    app.include_router(router)
    return app, FilesystemTaskRepository(tmpdir)


def _setup_task(repo: FilesystemTaskRepository, task_id: str = "proj-1", run_id: str = "run-1"):
    """Create a test task and run."""
    task = Task(
        task_id=task_id,
        title="Test Task",
        pipeline_id="mountain-av-v1",
        engine=Engine.WHITEBOARD,
        status=TaskStatus.READY,
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        active_run_id=run_id,
    )
    run = Run(
        run_id=run_id,
        task_id=task_id,
        trace_id="trace-1",
        entrypoint=Entrypoint.WEB,
        command_ids=["cmd-1"],
        status=RunStatus.PENDING,
        target_stage="compose-video",
        started_at="2025-01-01T00:00:00Z",
    )
    repo.create_task(task)
    repo.create_run(run)
    return task, run


class TestCapabilitiesEndpoint(unittest.TestCase):
    """Test capabilities endpoint."""

    def test_capabilities_returns_items(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app, _ = _create_test_app(Path(tmpdir))
            client = TestClient(app)
            response = client.get("/api/mountain/capabilities")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("items", data)
            self.assertTrue(len(data["items"]) > 0)


class TestTaskEndpoints(unittest.TestCase):
    """Test task CRUD endpoints."""

    def test_create_task(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app, _ = _create_test_app(Path(tmpdir))
            client = TestClient(app)
            response = client.post("/api/mountain/tasks", json={"title": "Test Task"})
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["ok"])
            self.assertIn("task_id", data)
            self.assertIn("run_id", data)

    def test_list_tasks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app, repo = _create_test_app(Path(tmpdir))
            _setup_task(repo)
            client = TestClient(app)
            response = client.get("/api/mountain/tasks")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("items", data)
            self.assertEqual(len(data["items"]), 1)

    def test_get_task(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app, repo = _create_test_app(Path(tmpdir))
            _setup_task(repo)
            client = TestClient(app)
            response = client.get("/api/mountain/tasks/proj-1")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("task", data)
            self.assertIn("active_run", data)

    def test_get_task_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app, _ = _create_test_app(Path(tmpdir))
            client = TestClient(app)
            response = client.get("/api/mountain/tasks/nonexistent")
            self.assertEqual(response.status_code, 404)


class TestStageEndpoints(unittest.TestCase):
    """Executable current `/api/v1` stage and pipeline boundaries."""

    @staticmethod
    def _client(tmpdir: Path) -> TestClient:
        return TestClient(create_app(tmpdir))

    @staticmethod
    def _task(client: TestClient) -> tuple[str, str]:
        response = client.post("/api/v1/tasks", json={"title": "Stage boundary"})
        assert response.status_code == 200
        payload = response.json()
        return payload["task_id"], payload["run_id"]

    def test_generate_visual_anchors(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            client = self._client(Path(tmpdir))
            response = client.post("/api/v1/tasks/missing/runs/missing/stages/generate-visual-anchors/run")
            self.assertEqual(response.status_code, 404)
            data = response.json()
            self.assertEqual(data["error"]["code"], "NOT_FOUND")

    def test_plan_storyboard(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            client = self._client(Path(tmpdir))
            task_id, run_id = self._task(client)
            response = client.post(f"/api/v1/tasks/{task_id}/runs/{run_id}/stages/plan-storyboard/run")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertFalse(data["ok"])
            self.assertEqual(data["results"][0]["error"]["code"], "VALIDATION_ERROR")

    def test_pipeline_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            client = self._client(Path(tmpdir))
            task_id, run_id = self._task(client)
            response = client.post(
                f"/api/v1/tasks/{task_id}/runs/{run_id}/pipeline/run",
                params={"policy": "targeted", "target_stage": "plan-storyboard"},
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertFalse(data["ok"])
            self.assertEqual(data["results"][0]["error"]["code"], "VALIDATION_ERROR")

    def test_stage_retry_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            client = self._client(Path(tmpdir))
            response = client.post("/api/v1/tasks/nonexistent/runs/run-1/stages/generate-visual-anchors/retry")
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["error"]["code"], "NOT_FOUND")


class TestArtifactEndpoints(unittest.TestCase):
    """Test artifact endpoints."""

    def test_list_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app, repo = _create_test_app(Path(tmpdir))
            _setup_task(repo)
            # 创建 artifact index
            run_dir = repo.run_dir("proj-1", "run-1")
            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            index = {
                "schema_version": 1,
                "artifacts": {
                    "planning.av-plan": {
                        "artifact_key": "planning.av-plan",
                        "relative_path": "planning/av-plan.json",
                        "status": "succeeded",
                    }
                },
            }
            (artifacts_dir / "index.json").write_text(json.dumps(index))

            client = TestClient(app)
            response = client.get("/api/mountain/tasks/proj-1/runs/run-1/artifacts")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("items", data)
            self.assertEqual(len(data["items"]), 1)

    def test_artifact_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app, repo = _create_test_app(Path(tmpdir))
            _setup_task(repo)
            # 创建 artifact
            run_dir = repo.run_dir("proj-1", "run-1")
            artifacts_dir = run_dir / "artifacts"
            planning_dir = artifacts_dir / "planning"
            planning_dir.mkdir(parents=True, exist_ok=True)
            av_plan = {"test": "data"}
            (planning_dir / "av-plan.json").write_text(json.dumps(av_plan))
            index = {
                "schema_version": 1,
                "artifacts": {
                    "planning.av-plan": {
                        "artifact_key": "planning.av-plan",
                        "relative_path": "planning/av-plan.json",
                        "status": "succeeded",
                    }
                },
            }
            (artifacts_dir / "index.json").write_text(json.dumps(index))

            client = TestClient(app)
            response = client.get("/api/mountain/tasks/proj-1/runs/run-1/artifacts/planning.av-plan/content")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["artifact_key"], "planning.av-plan")
            self.assertEqual(data["content"], av_plan)


class TestDiagnosticsEndpoints(unittest.TestCase):
    """Test diagnostics endpoints."""

    def test_get_trace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app, repo = _create_test_app(Path(tmpdir))
            _setup_task(repo)
            client = TestClient(app)
            response = client.get("/api/mountain/tasks/proj-1/runs/run-1/trace")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("trace_id", data)
            self.assertIn("command_ids", data)

    def test_get_events(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app, repo = _create_test_app(Path(tmpdir))
            _setup_task(repo)
            # 写入一些事件
            from csboard.adapters.observability import JsonlTelemetry
            telemetry = JsonlTelemetry(repo)
            telemetry.append_event("proj-1", "run-1", {"event_type": "TestEvent"})

            client = TestClient(app)
            response = client.get("/api/mountain/tasks/proj-1/runs/run-1/events")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("items", data)
            self.assertTrue(len(data["items"]) > 0)


if __name__ == "__main__":
    unittest.main()
