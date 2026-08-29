"""Tests for Mountain API endpoints."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from csboard.adapters.filesystem import FilesystemArtifactStore, FilesystemProjectRepository
from csboard.domain.enums import Engine, Entrypoint, ProjectStatus, RunStatus
from csboard.domain.models import Project, Run
from webapp.mountain_api import mountain_router


def _create_test_app(tmpdir: Path) -> tuple[FastAPI, FilesystemProjectRepository]:
    """Create a test FastAPI app with mountain router."""
    app = FastAPI()
    router = mountain_router(tmpdir)
    app.include_router(router)
    return app, FilesystemProjectRepository(tmpdir)


def _setup_project(repo: FilesystemProjectRepository, project_id: str = "proj-1", run_id: str = "run-1"):
    """Create a test project and run."""
    project = Project(
        project_id=project_id,
        title="Test Project",
        pipeline_id="mountain-av-v1",
        engine=Engine.WHITEBOARD,
        status=ProjectStatus.READY,
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        active_run_id=run_id,
    )
    run = Run(
        run_id=run_id,
        project_id=project_id,
        trace_id="trace-1",
        entrypoint=Entrypoint.WEB,
        command_ids=["cmd-1"],
        status=RunStatus.PENDING,
        target_stage="compose-video",
        started_at="2025-01-01T00:00:00Z",
    )
    repo.create_project(project)
    repo.create_run(run)
    return project, run


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


class TestProjectEndpoints(unittest.TestCase):
    """Test project CRUD endpoints."""

    def test_create_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app, _ = _create_test_app(Path(tmpdir))
            client = TestClient(app)
            response = client.post("/api/mountain/projects", json={"title": "Test Project"})
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["ok"])
            self.assertIn("project_id", data)
            self.assertIn("run_id", data)

    def test_list_projects(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app, repo = _create_test_app(Path(tmpdir))
            _setup_project(repo)
            client = TestClient(app)
            response = client.get("/api/mountain/projects")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("items", data)
            self.assertEqual(len(data["items"]), 1)

    def test_get_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app, repo = _create_test_app(Path(tmpdir))
            _setup_project(repo)
            client = TestClient(app)
            response = client.get("/api/mountain/projects/proj-1")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("project", data)
            self.assertIn("active_run", data)

    def test_get_project_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app, _ = _create_test_app(Path(tmpdir))
            client = TestClient(app)
            response = client.get("/api/mountain/projects/nonexistent")
            self.assertEqual(response.status_code, 404)


class TestStageEndpoints(unittest.TestCase):
    """Test stage operation endpoints."""

    def test_segment_script(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app, repo = _create_test_app(Path(tmpdir))
            _setup_project(repo)
            client = TestClient(app)
            response = client.post(
                "/api/mountain/projects/proj-1/runs/run-1/stages/segment-script",
                json={"script": "第一句话。第二句话。"},
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["ok"])
            self.assertEqual(data["stage"], "segment-script")

    def test_plan_storyboard(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app, repo = _create_test_app(Path(tmpdir))
            _setup_project(repo)
            # 先运行 segment-script
            run_dir = repo.run_dir("proj-1", "run-1")
            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            av_plan = {
                "voice_units": [
                    {
                        "unit_id": "u1",
                        "order": 0,
                        "source_range": {"start": 0, "end": 10},
                        "text": "测试文案",
                        "visual_items": [
                            {
                                "visual_id": "v1",
                                "order": 0,
                                "source_range": {"start": 0, "end": 10},
                                "text": "测试文案",
                            }
                        ],
                    }
                ],
            }
            (artifacts_dir / "planning" / "av-plan.json").parent.mkdir(parents=True, exist_ok=True)
            (artifacts_dir / "planning" / "av-plan.json").write_text(json.dumps(av_plan))
            timeline = {
                "units": [
                    {
                        "unit_id": "u1",
                        "duration_ms": 5000,
                        "timing_source": "equal_fallback",
                        "visual_timings": [{"visual_id": "v1", "start_ms": 0, "end_ms": 5000}],
                    }
                ],
            }
            (artifacts_dir / "timing" / "timeline.json").parent.mkdir(parents=True, exist_ok=True)
            (artifacts_dir / "timing" / "timeline.json").write_text(json.dumps(timeline))
            store = FilesystemArtifactStore(repo)
            store.commit_bytes("proj-1", "run-1", "planning.av-plan", "planning/av-plan.json", json.dumps(av_plan).encode(), "segment-script")
            store.commit_bytes("proj-1", "run-1", "timing.timeline", "timing/timeline.json", json.dumps(timeline).encode(), "clone-voice")

            client = TestClient(app)
            response = client.post("/api/mountain/projects/proj-1/runs/run-1/stages/plan-storyboard")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["ok"])
            self.assertEqual(data["stage"], "plan-storyboard")

    def test_pipeline_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app, repo = _create_test_app(Path(tmpdir))
            _setup_project(repo)
            # 保存 request.json
            project_dir = repo.project_dir("proj-1")
            request_path = project_dir / "request.json"
            request_path.write_text(json.dumps({"script": "测试文案用于分割。"}))

            client = TestClient(app)
            response = client.post(
                "/api/mountain/projects/proj-1/runs/run-1/pipeline/run",
                params={"policy": "gated"},
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("stages_executed", data)

    def test_stage_retry_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app, _ = _create_test_app(Path(tmpdir))
            client = TestClient(app)
            response = client.post("/api/mountain/projects/nonexistent/runs/run-1/stages/segment-script/retry")
            self.assertEqual(response.status_code, 404)


class TestArtifactEndpoints(unittest.TestCase):
    """Test artifact endpoints."""

    def test_list_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app, repo = _create_test_app(Path(tmpdir))
            _setup_project(repo)
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
            response = client.get("/api/mountain/projects/proj-1/runs/run-1/artifacts")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("items", data)
            self.assertEqual(len(data["items"]), 1)

    def test_artifact_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app, repo = _create_test_app(Path(tmpdir))
            _setup_project(repo)
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
            response = client.get("/api/mountain/projects/proj-1/runs/run-1/artifacts/planning.av-plan/content")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["artifact_key"], "planning.av-plan")
            self.assertEqual(data["content"], av_plan)


class TestDiagnosticsEndpoints(unittest.TestCase):
    """Test diagnostics endpoints."""

    def test_get_trace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app, repo = _create_test_app(Path(tmpdir))
            _setup_project(repo)
            client = TestClient(app)
            response = client.get("/api/mountain/projects/proj-1/runs/run-1/trace")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("trace_id", data)
            self.assertIn("command_ids", data)

    def test_get_events(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app, repo = _create_test_app(Path(tmpdir))
            _setup_project(repo)
            # 写入一些事件
            from csboard.adapters.observability import JsonlTelemetry
            telemetry = JsonlTelemetry(repo)
            telemetry.append_event("proj-1", "run-1", {"event_type": "TestEvent"})

            client = TestClient(app)
            response = client.get("/api/mountain/projects/proj-1/runs/run-1/events")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("items", data)
            self.assertTrue(len(data["items"]) > 0)


if __name__ == "__main__":
    unittest.main()
