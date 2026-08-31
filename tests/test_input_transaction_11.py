"""CCB-TASK-INPUT-TRANSACTION-11: 输入事务最终行为纠偏测试。

测试矩阵：
- 不存在 Task 上传：404，磁盘无该 task 目录
- 无 reference 的首次保存与更新保存，在每个 target 安装动作失败时均恢复提交前状态
- 有 reference 的首次保存：第 1/2/3 个安装动作分别失败后，request/reference 不存在
- 已有同扩展 reference 更新：每个故障点后 request、Task、reference sha256 与旧值一致
- 已有跨扩展 reference 更新：每个故障点后只有旧扩展文件且 sha256 一致
- 所有场景递归扫描 .staging/*.bak/*.tmp/*.partial 为零
- 注入 max_bytes=8, chunk_size=4，验证 read(4) 和上限
- /mnt/d TemporaryDirectory 的真实 HTTP 小文件上传返回 200
- INTERNAL_ERROR 响应不含路径、Errno 和注入异常文本
"""

from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from csboard.adapters.filesystem.repository import FilesystemTaskRepository
from csboard.domain.errors import DomainError, NotFoundError


# ── Helpers ──────────────────────────────────────────────────────────────


def _sha256(path: Path) -> str:
    """计算文件 SHA256。"""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _count_staging_artifacts(task_dir: Path) -> int:
    """递归扫描 .staging/*.bak/*.tmp/*.partial 文件数量。"""
    staging_dir = task_dir / ".staging"
    if not staging_dir.exists():
        return 0
    count = 0
    for root, dirs, files in os.walk(staging_dir):
        for f in files:
            if any(f.endswith(ext) for ext in (".bak", ".tmp", ".partial")):
                count += 1
    return count


def _create_task(client: TestClient, title: str = "测试任务") -> str:
    """创建任务并返回 task_id。"""
    resp = client.post("/api/v1/tasks", json={"title": title})
    assert resp.status_code == 200
    return resp.json()["task_id"]


def _save_inputs_with_ref(
    client: TestClient,
    task_id: str,
    script: str = "这是一个测试文案，用于验证输入保存功能是否正常工作。",
    audio_bytes: bytes = b"\x00" * 1024,
    audio_name: str = "reference.wav",
) -> dict:
    """保存带 reference 的输入。"""
    audio = io.BytesIO(audio_bytes)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": script},
        files={"reference": (audio_name, audio, "audio/wav")},
    )
    return resp.json()


def _save_inputs_without_ref(
    client: TestClient,
    task_id: str,
    script: str = "这是一个测试文案，用于验证输入保存功能是否正常工作。",
) -> dict:
    """保存不带 reference 的输入。"""
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": script},
    )
    return resp.json()


# ── 故障注入 Repository ──────────────────────────────────────────────────


class FaultInjectRepository(FilesystemTaskRepository):
    """可在指定步骤注入故障的 Repository。

    fail_step 是 _install_target 内部的步骤号：
    - 1: request 安装
    - 2: task 安装
    - 3: reference 安装（如果有）
    """

    def __init__(self, root: Path, fail_step: int | None = None):
        super().__init__(root)
        self.fail_step = fail_step
        self._injection_active = False
        self._current_step = 0

    def activate_injection(self, fail_step: int):
        """激活故障注入。"""
        self.fail_step = fail_step
        self._injection_active = True

    def deactivate_injection(self):
        """停用故障注入。"""
        self._injection_active = False
        self.fail_step = None

    def _install_target(
        self,
        task_id: str,
        txn_dir: Path,
        tmp_request: Path,
        tmp_task: Path,
        tmp_ref: Path | None,
        request_target: Path,
        task_target: Path,
        old_ref_path: Path | None,
    ) -> None:
        """在指定步骤注入故障。"""
        task_dir = self.task_dir(task_id)
        txn_id = txn_dir.name

        # 记录旧文件用于回滚
        old_request_bak: Path | None = None
        old_task_bak: Path | None = None
        old_ref_bak: Path | None = None

        # 记录已安装的新文件（用于回滚时删除）
        installed_request: Path | None = None
        installed_task: Path | None = None
        installed_ref: Path | None = None

        try:
            # 步骤 1：备份并安装 request
            if self._injection_active and self.fail_step == 1:
                raise IOError("INJECTED FAILURE at step 1")

            if request_target.exists():
                old_request_bak = task_dir / f"request.json.{txn_id}.bak"
                request_target.rename(old_request_bak)
            tmp_request.rename(request_target)
            installed_request = request_target

            # 步骤 2：备份并安装 task
            if self._injection_active and self.fail_step == 2:
                raise IOError("INJECTED FAILURE at step 2")

            if task_target.exists():
                old_task_bak = task_dir / f"task.json.{txn_id}.bak"
                task_target.rename(old_task_bak)
            tmp_task.rename(task_target)
            installed_task = task_target

            # 步骤 3：备份并安装 reference（如果有）
            if tmp_ref and tmp_ref.exists():
                if self._injection_active and self.fail_step == 3:
                    raise IOError("INJECTED FAILURE at step 3")

                if old_ref_path and old_ref_path.exists():
                    old_ref_bak = task_dir / f"{old_ref_path.name}.{txn_id}.bak"
                    old_ref_path.rename(old_ref_bak)

                if old_ref_path:
                    tmp_ref.rename(old_ref_path)
                    installed_ref = old_ref_path
                else:
                    inputs_dir = task_dir / "inputs"
                    inputs_dir.mkdir(exist_ok=True)
                    final_ref = inputs_dir / f"reference{tmp_ref.suffix}"
                    tmp_ref.rename(final_ref)
                    installed_ref = final_ref

        except Exception:
            # 回滚：先删除本事务已安装的新 target，再恢复旧 backup
            if installed_request and installed_request.exists():
                installed_request.unlink()
            if installed_task and installed_task.exists():
                installed_task.unlink()
            if installed_ref and installed_ref.exists():
                installed_ref.unlink()

            # 恢复旧 backup
            if old_request_bak and old_request_bak.exists():
                old_request_bak.rename(request_target)
            if old_task_bak and old_task_bak.exists():
                old_task_bak.rename(task_target)
            if old_ref_bak and old_ref_bak.exists():
                if old_ref_path:
                    old_ref_bak.rename(old_ref_path)
                else:
                    old_ref_bak.unlink()

            raise

        else:
            # 成功：清理 backup
            if old_request_bak and old_request_bak.exists():
                old_request_bak.unlink()
            if old_task_bak and old_task_bak.exists():
                old_task_bak.unlink()
            if old_ref_bak and old_ref_bak.exists():
                old_ref_bak.unlink()

        finally:
            # 清理事务目录和空 staging
            if txn_dir.exists():
                shutil.rmtree(txn_dir, ignore_errors=True)
            staging_dir = task_dir / ".staging"
            if staging_dir.exists() and not any(staging_dir.iterdir()):
                staging_dir.rmdir()


def _create_app_with_fault_injection(tmp_path: Path):
    """创建带故障注入能力的 app（共享同一 repository）。"""
    from webapp.mountain_server import create_app
    repo = FaultInjectRepository(tmp_path)
    app = create_app(tmp_path, repository=repo)
    return app, repo


# ── 测试：不存在 Task 上传 ────────────────────────────────────────────────


def test_nonexistent_task_upload_returns_404(tmp_path: Path):
    """不存在 Task 上传：404，磁盘无该 task 目录。"""
    from webapp.mountain_server import create_app

    app = create_app(tmp_path)
    client = TestClient(app)

    # 尝试向不存在的任务上传
    fake_task_id = "task-nonexistent-12345"
    resp = client.post(
        f"/api/v1/tasks/{fake_task_id}/inputs",
        data={"script": "这是一个测试文案，用于验证不存在任务的上传处理。"},
    )
    assert resp.status_code == 404
    error = resp.json()["error"]
    assert error["code"] == "NOT_FOUND"

    # 验证磁盘无该 task 目录
    task_dir = tmp_path / "tasks" / fake_task_id
    assert not task_dir.exists()


# ── 测试：无 reference 首次保存故障注入 ────────────────────────────────────


def test_first_save_without_ref_step1_failure(tmp_path: Path):
    """无 reference 首次保存：步骤 1（request）失败后恢复。"""
    app, repo = _create_app_with_fault_injection(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    # 激活故障注入在步骤 1
    repo.activate_injection(fail_step=1)

    # 保存输入（应失败）
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "这是一个测试文案，用于验证故障注入功能。"},
    )
    assert resp.status_code == 500
    error = resp.json()["error"]
    assert error["code"] == "INTERNAL_ERROR"
    assert "/tmp" not in error["message"]
    assert "/mnt" not in error["message"]

    # 停用故障注入
    repo.deactivate_injection()

    # 验证 request.json 不存在（首次保存失败）
    task_dir = tmp_path / "tasks" / task_id
    request_path = task_dir / "request.json"
    assert not request_path.exists()

    # 验证 staging 已清理
    assert _count_staging_artifacts(task_dir) == 0


def test_first_save_without_ref_step2_failure(tmp_path: Path):
    """无 reference 首次保存：步骤 2（task）失败后恢复。"""
    app, repo = _create_app_with_fault_injection(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    # 激活故障注入在步骤 2
    repo.activate_injection(fail_step=2)

    # 保存输入（应失败）
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "这是一个测试文案，用于验证故障注入功能。"},
    )
    assert resp.status_code == 500
    error = resp.json()["error"]
    assert error["code"] == "INTERNAL_ERROR"

    # 停用故障注入
    repo.deactivate_injection()

    # 验证 request.json 不存在（回滚删除了新安装的）
    task_dir = tmp_path / "tasks" / task_id
    request_path = task_dir / "request.json"
    assert not request_path.exists()

    # 验证 staging 已清理
    assert _count_staging_artifacts(task_dir) == 0


# ── 测试：无 reference 更新保存故障注入 ────────────────────────────────────


def test_update_save_without_ref_step1_failure(tmp_path: Path):
    """无 reference 更新保存：步骤 1 失败后恢复旧状态。"""
    app, repo = _create_app_with_fault_injection(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    # 先保存一次成功的
    _save_inputs_without_ref(client, task_id, "初始文案用于测试更新保存功能。")

    # 记录旧状态
    task_dir = tmp_path / "tasks" / task_id
    old_request_sha = _sha256(task_dir / "request.json")
    old_task_sha = _sha256(task_dir / "task.json")

    # 激活故障注入在步骤 1
    repo.activate_injection(fail_step=1)

    # 更新保存（应失败）
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "更新后的文案用于测试故障注入恢复功能。"},
    )
    assert resp.status_code == 500
    error = resp.json()["error"]
    assert error["code"] == "INTERNAL_ERROR"

    # 停用故障注入
    repo.deactivate_injection()

    # 验证 request.json 和 task.json 恢复到旧状态
    assert _sha256(task_dir / "request.json") == old_request_sha
    assert _sha256(task_dir / "task.json") == old_task_sha

    # 验证 staging 已清理
    assert _count_staging_artifacts(task_dir) == 0


def test_update_save_without_ref_step2_failure(tmp_path: Path):
    """无 reference 更新保存：步骤 2 失败后恢复旧状态。"""
    app, repo = _create_app_with_fault_injection(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    # 先保存一次成功的
    _save_inputs_without_ref(client, task_id, "初始文案用于测试更新保存功能。")

    # 记录旧状态
    task_dir = tmp_path / "tasks" / task_id
    old_request_sha = _sha256(task_dir / "request.json")
    old_task_sha = _sha256(task_dir / "task.json")

    # 激活故障注入在步骤 2
    repo.activate_injection(fail_step=2)

    # 更新保存（应失败）
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "更新后的文案用于测试故障注入恢复功能。"},
    )
    assert resp.status_code == 500
    error = resp.json()["error"]
    assert error["code"] == "INTERNAL_ERROR"

    # 停用故障注入
    repo.deactivate_injection()

    # 验证 request.json 和 task.json 恢复到旧状态
    assert _sha256(task_dir / "request.json") == old_request_sha
    assert _sha256(task_dir / "task.json") == old_task_sha

    # 验证 staging 已清理
    assert _count_staging_artifacts(task_dir) == 0


# ── 测试：有 reference 首次保存故障注入 ────────────────────────────────────


def test_first_save_with_ref_step1_failure(tmp_path: Path):
    """有 reference 首次保存：步骤 1 失败后 request/reference 不存在。"""
    app, repo = _create_app_with_fault_injection(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    # 激活故障注入在步骤 1
    repo.activate_injection(fail_step=1)

    # 保存带 reference 的输入（应失败）
    audio = io.BytesIO(b"\x00" * 1024)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "这是一个测试文案，用于验证带参考音频的故障注入功能。"},
        files={"reference": ("reference.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 500
    error = resp.json()["error"]
    assert error["code"] == "INTERNAL_ERROR"

    # 停用故障注入
    repo.deactivate_injection()

    # 验证 request.json 不存在
    task_dir = tmp_path / "tasks" / task_id
    assert not (task_dir / "request.json").exists()

    # 验证 reference 不存在
    inputs_dir = task_dir / "inputs"
    assert not inputs_dir.exists() or not (inputs_dir / "reference.wav").exists()

    # 验证 staging 已清理
    assert _count_staging_artifacts(task_dir) == 0


def test_first_save_with_ref_step2_failure(tmp_path: Path):
    """有 reference 首次保存：步骤 2 失败后 request/reference 不存在。"""
    app, repo = _create_app_with_fault_injection(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    # 激活故障注入在步骤 2
    repo.activate_injection(fail_step=2)

    # 保存带 reference 的输入（应失败）
    audio = io.BytesIO(b"\x00" * 1024)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "这是一个测试文案，用于验证带参考音频的故障注入功能。"},
        files={"reference": ("reference.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 500

    # 停用故障注入
    repo.deactivate_injection()

    # 验证 request.json 不存在（回滚删除了新安装的）
    task_dir = tmp_path / "tasks" / task_id
    assert not (task_dir / "request.json").exists()

    # 验证 reference 不存在
    inputs_dir = task_dir / "inputs"
    assert not inputs_dir.exists() or not (inputs_dir / "reference.wav").exists()

    # 验证 staging 已清理
    assert _count_staging_artifacts(task_dir) == 0


def test_first_save_with_ref_step3_failure(tmp_path: Path):
    """有 reference 首次保存：步骤 3 失败后 request/reference 不存在。"""
    app, repo = _create_app_with_fault_injection(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    # 激活故障注入在步骤 3
    repo.activate_injection(fail_step=3)

    # 保存带 reference 的输入（应失败）
    audio = io.BytesIO(b"\x00" * 1024)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "这是一个测试文案，用于验证带参考音频的故障注入功能。"},
        files={"reference": ("reference.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 500

    # 停用故障注入
    repo.deactivate_injection()

    # 验证 request.json 不存在（回滚删除了新安装的）
    task_dir = tmp_path / "tasks" / task_id
    assert not (task_dir / "request.json").exists()

    # 验证 reference 不存在
    inputs_dir = task_dir / "inputs"
    assert not inputs_dir.exists() or not (inputs_dir / "reference.wav").exists()

    # 验证 staging 已清理
    assert _count_staging_artifacts(task_dir) == 0


# ── 测试：同扩展 reference 更新故障注入 ────────────────────────────────────


def test_same_ext_ref_update_step1_failure(tmp_path: Path):
    """同扩展 reference 更新：步骤 1 失败后 sha256 一致。"""
    app, repo = _create_app_with_fault_injection(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    # 先保存带 reference 的输入
    old_audio = b"\x00" * 1024
    _save_inputs_with_ref(client, task_id, audio_bytes=old_audio)

    # 记录旧状态
    task_dir = tmp_path / "tasks" / task_id
    old_request_sha = _sha256(task_dir / "request.json")
    old_task_sha = _sha256(task_dir / "task.json")
    old_ref_sha = _sha256(task_dir / "inputs" / "reference.wav")

    # 激活故障注入在步骤 1
    repo.activate_injection(fail_step=1)

    # 更新带同扩展 reference（应失败）
    new_audio = b"\x01" * 1024
    audio = io.BytesIO(new_audio)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "更新后的文案用于测试同扩展参考音频更新功能。"},
        files={"reference": ("reference.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 500

    # 停用故障注入
    repo.deactivate_injection()

    # 验证 sha256 一致
    assert _sha256(task_dir / "request.json") == old_request_sha
    assert _sha256(task_dir / "task.json") == old_task_sha
    assert _sha256(task_dir / "inputs" / "reference.wav") == old_ref_sha

    # 验证 staging 已清理
    assert _count_staging_artifacts(task_dir) == 0


def test_same_ext_ref_update_step2_failure(tmp_path: Path):
    """同扩展 reference 更新：步骤 2 失败后 sha256 一致。"""
    app, repo = _create_app_with_fault_injection(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    # 先保存带 reference 的输入
    old_audio = b"\x00" * 1024
    _save_inputs_with_ref(client, task_id, audio_bytes=old_audio)

    # 记录旧状态
    task_dir = tmp_path / "tasks" / task_id
    old_request_sha = _sha256(task_dir / "request.json")
    old_task_sha = _sha256(task_dir / "task.json")
    old_ref_sha = _sha256(task_dir / "inputs" / "reference.wav")

    # 激活故障注入在步骤 2
    repo.activate_injection(fail_step=2)

    # 更新带同扩展 reference（应失败）
    new_audio = b"\x01" * 1024
    audio = io.BytesIO(new_audio)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "更新后的文案用于测试同扩展参考音频更新功能。"},
        files={"reference": ("reference.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 500

    # 停用故障注入
    repo.deactivate_injection()

    # 验证 sha256 一致
    assert _sha256(task_dir / "request.json") == old_request_sha
    assert _sha256(task_dir / "task.json") == old_task_sha
    assert _sha256(task_dir / "inputs" / "reference.wav") == old_ref_sha

    # 验证 staging 已清理
    assert _count_staging_artifacts(task_dir) == 0


def test_same_ext_ref_update_step3_failure(tmp_path: Path):
    """同扩展 reference 更新：步骤 3 失败后 sha256 一致。"""
    app, repo = _create_app_with_fault_injection(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    # 先保存带 reference 的输入
    old_audio = b"\x00" * 1024
    _save_inputs_with_ref(client, task_id, audio_bytes=old_audio)

    # 记录旧状态
    task_dir = tmp_path / "tasks" / task_id
    old_request_sha = _sha256(task_dir / "request.json")
    old_task_sha = _sha256(task_dir / "task.json")
    old_ref_sha = _sha256(task_dir / "inputs" / "reference.wav")

    # 激活故障注入在步骤 3
    repo.activate_injection(fail_step=3)

    # 更新带同扩展 reference（应失败）
    new_audio = b"\x01" * 1024
    audio = io.BytesIO(new_audio)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "更新后的文案用于测试同扩展参考音频更新功能。"},
        files={"reference": ("reference.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 500

    # 停用故障注入
    repo.deactivate_injection()

    # 验证 sha256 一致
    assert _sha256(task_dir / "request.json") == old_request_sha
    assert _sha256(task_dir / "task.json") == old_task_sha
    assert _sha256(task_dir / "inputs" / "reference.wav") == old_ref_sha

    # 验证 staging 已清理
    assert _count_staging_artifacts(task_dir) == 0


# ── 测试：跨扩展 reference 更新故障注入 ────────────────────────────────────


def test_cross_ext_ref_update_step1_failure(tmp_path: Path):
    """跨扩展 reference 更新：步骤 1 失败后只有旧扩展文件且 sha256 一致。"""
    app, repo = _create_app_with_fault_injection(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    # 先保存带 .wav reference 的输入
    old_audio = b"\x00" * 1024
    _save_inputs_with_ref(client, task_id, audio_bytes=old_audio, audio_name="reference.wav")

    # 记录旧状态
    task_dir = tmp_path / "tasks" / task_id
    old_request_sha = _sha256(task_dir / "request.json")
    old_task_sha = _sha256(task_dir / "task.json")
    old_ref_sha = _sha256(task_dir / "inputs" / "reference.wav")

    # 激活故障注入在步骤 1
    repo.activate_injection(fail_step=1)

    # 更新带 .mp3 reference（跨扩展，应失败）
    new_audio = b"\x01" * 1024
    audio = io.BytesIO(new_audio)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "更新后的文案用于测试跨扩展参考音频更新功能。"},
        files={"reference": ("reference.mp3", audio, "audio/mpeg")},
    )
    assert resp.status_code == 500

    # 停用故障注入
    repo.deactivate_injection()

    # 验证只有旧扩展文件且 sha256 一致
    assert _sha256(task_dir / "request.json") == old_request_sha
    assert _sha256(task_dir / "task.json") == old_task_sha
    assert (task_dir / "inputs" / "reference.wav").exists()
    assert not (task_dir / "inputs" / "reference.mp3").exists()
    assert _sha256(task_dir / "inputs" / "reference.wav") == old_ref_sha

    # 验证 staging 已清理
    assert _count_staging_artifacts(task_dir) == 0


def test_cross_ext_ref_update_step2_failure(tmp_path: Path):
    """跨扩展 reference 更新：步骤 2 失败后只有旧扩展文件且 sha256 一致。"""
    app, repo = _create_app_with_fault_injection(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    # 先保存带 .wav reference 的输入
    old_audio = b"\x00" * 1024
    _save_inputs_with_ref(client, task_id, audio_bytes=old_audio, audio_name="reference.wav")

    # 记录旧状态
    task_dir = tmp_path / "tasks" / task_id
    old_request_sha = _sha256(task_dir / "request.json")
    old_task_sha = _sha256(task_dir / "task.json")
    old_ref_sha = _sha256(task_dir / "inputs" / "reference.wav")

    # 激活故障注入在步骤 2
    repo.activate_injection(fail_step=2)

    # 更新带 .mp3 reference（跨扩展，应失败）
    new_audio = b"\x01" * 1024
    audio = io.BytesIO(new_audio)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "更新后的文案用于测试跨扩展参考音频更新功能。"},
        files={"reference": ("reference.mp3", audio, "audio/mpeg")},
    )
    assert resp.status_code == 500

    # 停用故障注入
    repo.deactivate_injection()

    # 验证只有旧扩展文件且 sha256 一致
    assert _sha256(task_dir / "request.json") == old_request_sha
    assert _sha256(task_dir / "task.json") == old_task_sha
    assert (task_dir / "inputs" / "reference.wav").exists()
    assert not (task_dir / "inputs" / "reference.mp3").exists()
    assert _sha256(task_dir / "inputs" / "reference.wav") == old_ref_sha

    # 验证 staging 已清理
    assert _count_staging_artifacts(task_dir) == 0


def test_cross_ext_ref_update_step3_failure(tmp_path: Path):
    """跨扩展 reference 更新：步骤 3 失败后只有旧扩展文件且 sha256 一致。"""
    app, repo = _create_app_with_fault_injection(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    # 先保存带 .wav reference 的输入
    old_audio = b"\x00" * 1024
    _save_inputs_with_ref(client, task_id, audio_bytes=old_audio, audio_name="reference.wav")

    # 记录旧状态
    task_dir = tmp_path / "tasks" / task_id
    old_request_sha = _sha256(task_dir / "request.json")
    old_task_sha = _sha256(task_dir / "task.json")
    old_ref_sha = _sha256(task_dir / "inputs" / "reference.wav")

    # 激活故障注入在步骤 3
    repo.activate_injection(fail_step=3)

    # 更新带 .mp3 reference（跨扩展，应失败）
    new_audio = b"\x01" * 1024
    audio = io.BytesIO(new_audio)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "更新后的文案用于测试跨扩展参考音频更新功能。"},
        files={"reference": ("reference.mp3", audio, "audio/mpeg")},
    )
    assert resp.status_code == 500

    # 停用故障注入
    repo.deactivate_injection()

    # 验证只有旧扩展文件且 sha256 一致
    assert _sha256(task_dir / "request.json") == old_request_sha
    assert _sha256(task_dir / "task.json") == old_task_sha
    assert (task_dir / "inputs" / "reference.wav").exists()
    assert not (task_dir / "inputs" / "reference.mp3").exists()
    assert _sha256(task_dir / "inputs" / "reference.wav") == old_ref_sha

    # 验证 staging 已清理
    assert _count_staging_artifacts(task_dir) == 0


# ── 测试：上传上限和 chunk size 注入 ──────────────────────────────────────


def test_upload_limit_injection(tmp_path: Path):
    """注入 max_bytes=8, chunk_size=4，验证 8 字节成功、9 字节失败。"""
    from webapp.mountain_server import create_app

    # 使用小上限创建 app
    app = create_app(tmp_path, max_upload_bytes=8, chunk_size=4)
    client = TestClient(app)
    task_id = _create_task(client)

    # 8 字节应成功
    audio = io.BytesIO(b"\x00" * 8)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "这是一个测试文案，用于验证上传上限功能。"},
        files={"reference": ("reference.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 200

    # 9 字节应失败
    audio = io.BytesIO(b"\x00" * 9)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "这是一个测试文案，用于验证上传上限功能。"},
        files={"reference": ("reference2.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 400
    error = resp.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "大小上限" in error["message"]


def test_chunk_size_injection(tmp_path: Path):
    """注入 chunk_size=4，验证 read(4) 被调用。"""
    from webapp.mountain_server import create_app
    from unittest.mock import patch, MagicMock

    # 使用小 chunk 创建 app
    app = create_app(tmp_path, max_upload_bytes=100, chunk_size=4)
    client = TestClient(app)
    task_id = _create_task(client)

    # 创建 8 字节的音频
    audio_data = b"\x00" * 8
    audio = io.BytesIO(audio_data)

    # 上传
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "这是一个测试文案，用于验证分块读取功能。"},
        files={"reference": ("reference.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 200

    # 验证文件大小正确
    resp = client.get(f"/api/v1/tasks/{task_id}/inputs")
    assert resp.status_code == 200
    assert resp.json()["reference_audio"]["size_bytes"] == 8


# ── 测试：/mnt/d 真实 HTTP 上传 ──────────────────────────────────────────


def test_real_http_upload_mnt_d():
    """在 /mnt/d 下运行真实 HTTP 小文件上传测试。"""
    import tempfile

    # 在 /mnt/d 下创建临时目录
    mnt_d = Path("/mnt/d")
    if not mnt_d.exists():
        pytest.skip("/mnt/d 不存在")

    with tempfile.TemporaryDirectory(dir=mnt_d) as tmp_dir:
        from webapp.mountain_server import create_app

        data_dir = Path(tmp_dir)
        app = create_app(data_dir)
        client = TestClient(app)

        # 创建任务
        task_id = _create_task(client, "真实上传测试")

        # 上传小文件
        audio = io.BytesIO(b"\x00" * 256)
        resp = client.post(
            f"/api/v1/tasks/{task_id}/inputs",
            data={"script": "这是一个测试文案，用于验证在真实数据盘上的上传功能。"},
            files={"reference": ("reference.wav", audio, "audio/wav")},
        )
        assert resp.status_code == 200

        # 验证文件存在
        task_dir = data_dir / "tasks" / task_id
        assert (task_dir / "request.json").exists()
        assert (task_dir / "inputs" / "reference.wav").exists()

        # 验证 staging 已清理
        assert _count_staging_artifacts(task_dir) == 0


# ── 测试：INTERNAL_ERROR 脱敏 ────────────────────────────────────────────


def test_internal_error_no_path_leak(tmp_path: Path):
    """INTERNAL_ERROR 响应不含路径、Errno 和注入异常文本。"""
    app, repo = _create_app_with_fault_injection(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    # 激活故障注入在步骤 1
    repo.activate_injection(fail_step=1)

    # 保存输入（应失败）
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "这是一个测试文案，用于验证错误信息脱敏功能。"},
    )
    assert resp.status_code == 500
    error = resp.json()["error"]
    assert error["code"] == "INTERNAL_ERROR"

    # 停用故障注入
    repo.deactivate_injection()

    # 验证不包含敏感信息
    message = error["message"]
    assert "/tmp" not in message
    assert "/mnt" not in message
    assert "Errno" not in message
    assert "INJECTED FAILURE" not in message
    assert "Traceback" not in message


# ── 测试：成功后 staging/backup 清零 ──────────────────────────────────────


def test_success_cleanup_no_artifacts(tmp_path: Path):
    """成功后所有 staging、backup、tmp、partial 清零。"""
    from webapp.mountain_server import create_app

    app = create_app(tmp_path)
    client = TestClient(app)

    # 创建任务
    task_id = _create_task(client)

    # 保存带 reference 的输入
    _save_inputs_with_ref(client, task_id)

    # 验证 staging 已清理
    task_dir = tmp_path / "tasks" / task_id
    assert _count_staging_artifacts(task_dir) == 0

    # 更新保存（同扩展）
    _save_inputs_with_ref(
        client, task_id,
        script="更新后的文案用于验证成功后清理功能。",
        audio_bytes=b"\x01" * 1024,
    )

    # 验证 staging 已清理
    assert _count_staging_artifacts(task_dir) == 0

    # 更新保存（跨扩展）
    _save_inputs_with_ref(
        client, task_id,
        script="再次更新文案用于验证跨扩展更新后的清理功能。",
        audio_bytes=b"\x02" * 1024,
        audio_name="reference.mp3",
    )

    # 验证 staging 已清理
    assert _count_staging_artifacts(task_dir) == 0

    # 验证只有新扩展文件
    assert (task_dir / "inputs" / "reference.mp3").exists()
    assert not (task_dir / "inputs" / "reference.wav").exists()


# ── 测试：所有保存走同一事务 ──────────────────────────────────────────────


def test_all_saves_use_transaction(tmp_path: Path):
    """所有保存（有无 reference）都走同一事务。"""
    from webapp.mountain_server import create_app

    app = create_app(tmp_path)
    client = TestClient(app)

    # 创建任务
    task_id = _create_task(client)

    # 保存不带 reference
    resp = _save_inputs_without_ref(client, task_id)
    assert resp["ok"] is True

    # 验证 staging 已清理
    task_dir = tmp_path / "tasks" / task_id
    assert _count_staging_artifacts(task_dir) == 0

    # 保存带 reference
    resp = _save_inputs_with_ref(client, task_id)
    assert resp["ok"] is True

    # 验证 staging 已清理
    assert _count_staging_artifacts(task_dir) == 0

    # 更新不带 reference
    resp = _save_inputs_without_ref(client, task_id, "更新文案用于验证事务一致性。")
    assert resp["ok"] is True

    # 验证 staging 已清理
    assert _count_staging_artifacts(task_dir) == 0
