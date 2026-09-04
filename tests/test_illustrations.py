"""Unit tests for IllustrationService.

Uses FakeImageModel to avoid real API calls.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from csboard.adapters.fakes import FakeImageModel
from csboard.adapters.filesystem import FilesystemTaskRepository, FilesystemArtifactStore
from csboard.adapters.filesystem.asset_repository import FilesystemAssetRepository
from csboard.application.av_artifacts import json_bytes, storyboard_document
from csboard.application.context import new_id, utc_now
from csboard.application.illustrations import IllustrationService
from csboard.domain.enums import Engine, Entrypoint, TaskStatus, RunStatus, StageStatus
from csboard.domain.models import Task, Run, StageState


def _setup_project_with_storyboard(root: Path) -> tuple[str, str, FilesystemTaskRepository]:
    """Create a test project with storyboard artifact."""
    repo = FilesystemTaskRepository(root)
    task_id = new_id("project")
    run_id = new_id("run")

    # Create project
    task = Task(
        task_id=task_id,
        title="测试项目",
        pipeline_id="mountain-av-v1",
        engine=Engine.WHITEBOARD,
        status=TaskStatus.READY,
        created_at=utc_now(),
        updated_at=utc_now(),
        active_run_id=run_id,
    )
    repo.create_task(task)

    # Create run
    run = Run(
        run_id=run_id,
        task_id=task_id,
        trace_id=new_id("trace"),
        entrypoint=Entrypoint.CLI,
        command_ids=[new_id("command")],
        status=RunStatus.RUNNING,
        target_stage="compose-video",
        started_at=utc_now(),
        stages={
            "generate-visual-anchors": StageState(StageStatus.SUCCEEDED, 1),
            "clone-voice": StageState(StageStatus.SUCCEEDED, 1),
            "plan-storyboard": StageState(StageStatus.SUCCEEDED, 1),
        },
    )
    repo.create_run(run)

    # Create storyboard artifact
    visuals = [
        {
            "visual_id": "visual-001-01",
            "unit_id": "unit-001",
            "prompt": "简约白板风格，测试画面",
            "negative_prompt": "text, watermark",
            "composition": "centered",
            "overlay_text": [],
            "style_profile": "whiteboard-v1",
        },
        {
            "visual_id": "visual-001-02",
            "unit_id": "unit-001",
            "prompt": "简约白板风格，第二个画面",
            "negative_prompt": "text, watermark",
            "composition": "centered",
            "overlay_text": [],
            "style_profile": "whiteboard-v1",
        },
    ]
    bible = {
        "style": "简约白板手绘风",
        "color_scheme": "黑白为主",
        "composition_rules": ["居中构图"],
        "mood": "专业",
        "visual_metaphors": [],
    }
    storyboard = storyboard_document(task_id, run_id, visuals, bible, Engine.WHITEBOARD)
    store = FilesystemArtifactStore(repo)
    store.commit_bytes(
        task_id, run_id, "planning.storyboard", "planning/storyboard.json",
        json_bytes(storyboard), "plan-storyboard",
    )

    return task_id, run_id, repo


class TestIllustrationService(unittest.TestCase):
    """Test IllustrationService.run()."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.task_id, self.run_id, self.repo = _setup_project_with_storyboard(self.root)
        self.image_model = FakeImageModel()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_returns_illustrations(self) -> None:
        service = IllustrationService(self.image_model, self.repo)
        result = service.run(self.task_id, self.run_id)
        self.assertIn("illustrations", result)

    def test_image_count_matches(self) -> None:
        service = IllustrationService(self.image_model, self.repo)
        result = service.run(self.task_id, self.run_id)
        self.assertEqual(result["image_count"], 2)

    def test_artifact_committed(self) -> None:
        service = IllustrationService(self.image_model, self.repo)
        result = service.run(self.task_id, self.run_id)
        store = FilesystemArtifactStore(self.repo)
        ref = store.get(self.task_id, self.run_id, "illustrations.manifest")
        self.assertIsNotNone(ref)

    def test_images_saved_to_disk(self) -> None:
        service = IllustrationService(self.image_model, self.repo)
        result = service.run(self.task_id, self.run_id)
        images_dir = self.repo.run_dir(self.task_id, self.run_id) / "media" / "images"
        self.assertTrue(images_dir.exists())
        png_files = list(images_dir.glob("*.png"))
        self.assertEqual(len(png_files), 2)

    def test_single_visual_retry(self) -> None:
        service = IllustrationService(self.image_model, self.repo)
        result = service.run(self.task_id, self.run_id, visual_id="visual-001-01")
        self.assertEqual(result["image_count"], 1)
        illustrations = result["illustrations"]["illustrations"]
        self.assertEqual(illustrations[0]["visual_id"], "visual-001-01")

    def test_keyword_route_supplies_real_reference_images_and_records_the_match(self) -> None:
        assets = FilesystemAssetRepository(self.root)
        first = assets.save_asset(b"\x89PNG\r\n\x1a\nfirst", "first.png", "image/png")
        second = assets.save_asset(b"\x89PNG\r\n\x1a\nsecond", "second.png", "image/png")
        self.repo.write_json(self.repo.task_dir(self.task_id) / "request.json", {
            "style_snapshot": {"config": {"reference_routing": {
                "enabled": True, "match_mode": "first", "rules": [{
                    "rule_id": "route-whiteboard", "name": "白板规则", "keywords": ["白板"],
                    "reference_asset_ids": [first.asset_id, second.asset_id], "order": 1,
                }],
            }}},
        })
        service = IllustrationService(self.image_model, self.repo)
        result = service.run(self.task_id, self.run_id, visual_id="visual-001-01")
        self.assertEqual(self.image_model.last_request.reference_images, (
            assets.read_asset_bytes(first.asset_id), assets.read_asset_bytes(second.asset_id),
        ))
        route = result["illustrations"]["illustrations"][0]["reference_route"]
        self.assertEqual(route["rule_id"], "route-whiteboard")
        self.assertEqual(route["reference_asset_ids"], [first.asset_id, second.asset_id])

    def test_missing_visual_id_raises(self) -> None:
        service = IllustrationService(self.image_model, self.repo)
        with self.assertRaises(ValueError):
            service.run(self.task_id, self.run_id, visual_id="nonexistent")

    def test_missing_storyboard_raises(self) -> None:
        # Create a project without storyboard
        task_id = new_id("project")
        run_id = new_id("run")
        task = Task(
            task_id=task_id,
            title="测试项目",
            pipeline_id="mountain-av-v1",
            engine=Engine.WHITEBOARD,
            status=TaskStatus.READY,
            created_at=utc_now(),
            updated_at=utc_now(),
            active_run_id=run_id,
        )
        self.repo.create_task(task)
        run = Run(
            run_id=run_id, task_id=task_id, trace_id=new_id("trace"),
            entrypoint=Entrypoint.CLI, command_ids=[], status=RunStatus.RUNNING,
            target_stage="compose-video", started_at=utc_now(),
        )
        self.repo.create_run(run)

        service = IllustrationService(self.image_model, self.repo)
        with self.assertRaises(ValueError):
            service.run(task_id, run_id)


if __name__ == "__main__":
    unittest.main()
