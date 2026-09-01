"""CCB-TASK-INPUT-TRANSACTION-12: 输入事务并发与真实故障注入纠偏测试。

测试矩阵：
- 测试子类只覆盖生产 checkpoint hook，不复制 _install_target 或 rollback
- 首次无 reference：request/task after_install 故障后恢复空状态
- 首次有 reference：request/task/reference after_install 故障后恢复空状态
- 已有同扩展 reference：after_backup/after_install 故障后 sha256 不变
- 已有跨扩展 reference：after_backup/after_install 故障后只存在旧扩展
- 并发测试：B 不能在 A 释放前进入同一 Task 提交区
- A 上传新 reference、B 不上传 reference：B 保留 A 最新 reference
- 不同 Task 可并行
- HTTP 404、大小上限、/mnt/d 上传和 INTERNAL_ERROR 脱敏
"""

from __future__ import annotations

import contextvars
import hashlib
import io
import os
import threading
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


def _count_task_artifacts(task_dir: Path) -> int:
    """扫描 task 目录中的 *.bak 文件数量。"""
    count = 0
    for f in task_dir.iterdir():
        if f.name.endswith(".bak"):
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
    assert resp.status_code == 200
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
    assert resp.status_code == 200
    return resp.json()


# ── 故障注入 Repository ──────────────────────────────────────────────────


class CheckpointFaultRepository(FilesystemTaskRepository):
    """只覆盖生产 checkpoint hook 的 Repository。

    不复制 _install_target 或 rollback 算法。
    """

    def __init__(self, root: Path):
        super().__init__(root)
        self._fault_checkpoint: str | None = None

    def set_fault(self, checkpoint_name: str | None):
        """设置要注入故障的 checkpoint 名称。None 表示不注入。"""
        self._fault_checkpoint = checkpoint_name

    def _input_txn_checkpoint(self, name: str, context: dict) -> None:
        if self._fault_checkpoint and name == self._fault_checkpoint:
            raise IOError(f"INJECTED FAULT at checkpoint: {name}")


def _create_app_with_checkpoint_fault(tmp_path: Path):
    """创建带 checkpoint 故障注入能力的 app。"""
    from webapp.mountain_server import create_app
    repo = CheckpointFaultRepository(tmp_path)
    app = create_app(tmp_path, repository=repo)
    return app, repo


# ── 测试：不存在 Task 上传 ────────────────────────────────────────────────


def test_nonexistent_task_upload_returns_404(tmp_path: Path):
    """不存在 Task 上传：404，磁盘无该 task 目录。"""
    from webapp.mountain_server import create_app

    app = create_app(tmp_path)
    client = TestClient(app)

    fake_task_id = "task-nonexistent-12345"
    resp = client.post(
        f"/api/v1/tasks/{fake_task_id}/inputs",
        data={"script": "这是一个测试文案，用于验证不存在任务的上传处理。"},
    )
    assert resp.status_code == 404
    error = resp.json()["error"]
    assert error["code"] == "NOT_FOUND"

    task_dir = tmp_path / "tasks" / fake_task_id
    assert not task_dir.exists()


# ── 测试：首次无 reference 故障注入 ────────────────────────────────────────


def test_first_save_without_ref_request_after_install_fault(tmp_path: Path):
    """首次无 reference：request.after_install 故障后恢复空状态。"""
    app, repo = _create_app_with_checkpoint_fault(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    repo.set_fault("request.after_install")

    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "这是一个测试文案，用于验证故障注入功能。"},
    )
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "INTERNAL_ERROR"

    repo.set_fault(None)

    task_dir = tmp_path / "tasks" / task_id
    assert not (task_dir / "request.json").exists()
    assert _count_staging_artifacts(task_dir) == 0
    assert _count_task_artifacts(task_dir) == 0


def test_first_save_without_ref_task_after_install_fault(tmp_path: Path):
    """首次无 reference：task.after_install 故障后恢复空状态。"""
    app, repo = _create_app_with_checkpoint_fault(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    repo.set_fault("task.after_install")

    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "这是一个测试文案，用于验证故障注入功能。"},
    )
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "INTERNAL_ERROR"

    repo.set_fault(None)

    task_dir = tmp_path / "tasks" / task_id
    assert not (task_dir / "request.json").exists()
    assert _count_staging_artifacts(task_dir) == 0
    assert _count_task_artifacts(task_dir) == 0


# ── 测试：首次有 reference 故障注入 ────────────────────────────────────────


def test_first_save_with_ref_request_after_install_fault(tmp_path: Path):
    """首次有 reference：request.after_install 故障后恢复空状态。"""
    app, repo = _create_app_with_checkpoint_fault(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    repo.set_fault("request.after_install")

    audio = io.BytesIO(b"\x00" * 1024)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "这是一个测试文案，用于验证带参考音频的故障注入功能。"},
        files={"reference": ("reference.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "INTERNAL_ERROR"

    repo.set_fault(None)

    task_dir = tmp_path / "tasks" / task_id
    assert not (task_dir / "request.json").exists()
    assert not (task_dir / "inputs" / "reference.wav").exists()
    assert _count_staging_artifacts(task_dir) == 0
    assert _count_task_artifacts(task_dir) == 0


def test_first_save_with_ref_task_after_install_fault(tmp_path: Path):
    """首次有 reference：task.after_install 故障后恢复空状态。"""
    app, repo = _create_app_with_checkpoint_fault(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    repo.set_fault("task.after_install")

    audio = io.BytesIO(b"\x00" * 1024)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "这是一个测试文案，用于验证带参考音频的故障注入功能。"},
        files={"reference": ("reference.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "INTERNAL_ERROR"

    repo.set_fault(None)

    task_dir = tmp_path / "tasks" / task_id
    assert not (task_dir / "request.json").exists()
    assert not (task_dir / "inputs" / "reference.wav").exists()
    assert _count_staging_artifacts(task_dir) == 0
    assert _count_task_artifacts(task_dir) == 0


def test_first_save_with_ref_reference_after_install_fault(tmp_path: Path):
    """首次有 reference：reference.after_install 故障后恢复空状态。"""
    app, repo = _create_app_with_checkpoint_fault(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    repo.set_fault("reference.after_install")

    audio = io.BytesIO(b"\x00" * 1024)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "这是一个测试文案，用于验证带参考音频的故障注入功能。"},
        files={"reference": ("reference.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "INTERNAL_ERROR"

    repo.set_fault(None)

    task_dir = tmp_path / "tasks" / task_id
    assert not (task_dir / "request.json").exists()
    assert not (task_dir / "inputs" / "reference.wav").exists()
    assert _count_staging_artifacts(task_dir) == 0
    assert _count_task_artifacts(task_dir) == 0


# ── 测试：已有同扩展 reference 故障注入 ────────────────────────────────────


def test_same_ext_ref_request_after_backup_fault(tmp_path: Path):
    """同扩展 reference：request.after_backup 故障后 sha256 不变。"""
    app, repo = _create_app_with_checkpoint_fault(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    _save_inputs_with_ref(client, task_id, audio_bytes=b"\x00" * 1024)

    task_dir = tmp_path / "tasks" / task_id
    old_request_sha = _sha256(task_dir / "request.json")
    old_task_sha = _sha256(task_dir / "task.json")
    old_ref_sha = _sha256(task_dir / "inputs" / "reference.wav")

    repo.set_fault("request.after_backup")

    audio = io.BytesIO(b"\x01" * 1024)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "更新后的文案用于测试同扩展参考音频更新功能。"},
        files={"reference": ("reference.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 500

    repo.set_fault(None)

    assert _sha256(task_dir / "request.json") == old_request_sha
    assert _sha256(task_dir / "task.json") == old_task_sha
    assert _sha256(task_dir / "inputs" / "reference.wav") == old_ref_sha
    assert _count_staging_artifacts(task_dir) == 0
    assert _count_task_artifacts(task_dir) == 0


def test_same_ext_ref_request_after_install_fault(tmp_path: Path):
    """同扩展 reference：request.after_install 故障后 sha256 不变。"""
    app, repo = _create_app_with_checkpoint_fault(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    _save_inputs_with_ref(client, task_id, audio_bytes=b"\x00" * 1024)

    task_dir = tmp_path / "tasks" / task_id
    old_request_sha = _sha256(task_dir / "request.json")
    old_task_sha = _sha256(task_dir / "task.json")
    old_ref_sha = _sha256(task_dir / "inputs" / "reference.wav")

    repo.set_fault("request.after_install")

    audio = io.BytesIO(b"\x01" * 1024)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "更新后的文案用于测试同扩展参考音频更新功能。"},
        files={"reference": ("reference.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 500

    repo.set_fault(None)

    assert _sha256(task_dir / "request.json") == old_request_sha
    assert _sha256(task_dir / "task.json") == old_task_sha
    assert _sha256(task_dir / "inputs" / "reference.wav") == old_ref_sha
    assert _count_staging_artifacts(task_dir) == 0
    assert _count_task_artifacts(task_dir) == 0


def test_same_ext_ref_task_after_install_fault(tmp_path: Path):
    """同扩展 reference：task.after_install 故障后 sha256 不变。"""
    app, repo = _create_app_with_checkpoint_fault(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    _save_inputs_with_ref(client, task_id, audio_bytes=b"\x00" * 1024)

    task_dir = tmp_path / "tasks" / task_id
    old_request_sha = _sha256(task_dir / "request.json")
    old_task_sha = _sha256(task_dir / "task.json")
    old_ref_sha = _sha256(task_dir / "inputs" / "reference.wav")

    repo.set_fault("task.after_install")

    audio = io.BytesIO(b"\x01" * 1024)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "更新后的文案用于测试同扩展参考音频更新功能。"},
        files={"reference": ("reference.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 500

    repo.set_fault(None)

    assert _sha256(task_dir / "request.json") == old_request_sha
    assert _sha256(task_dir / "task.json") == old_task_sha
    assert _sha256(task_dir / "inputs" / "reference.wav") == old_ref_sha
    assert _count_staging_artifacts(task_dir) == 0
    assert _count_task_artifacts(task_dir) == 0


def test_same_ext_ref_reference_after_backup_fault(tmp_path: Path):
    """同扩展 reference：reference.after_backup 故障后 sha256 不变。"""
    app, repo = _create_app_with_checkpoint_fault(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    _save_inputs_with_ref(client, task_id, audio_bytes=b"\x00" * 1024)

    task_dir = tmp_path / "tasks" / task_id
    old_request_sha = _sha256(task_dir / "request.json")
    old_task_sha = _sha256(task_dir / "task.json")
    old_ref_sha = _sha256(task_dir / "inputs" / "reference.wav")

    repo.set_fault("reference.after_backup")

    audio = io.BytesIO(b"\x01" * 1024)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "更新后的文案用于测试同扩展参考音频更新功能。"},
        files={"reference": ("reference.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 500

    repo.set_fault(None)

    assert _sha256(task_dir / "request.json") == old_request_sha
    assert _sha256(task_dir / "task.json") == old_task_sha
    assert _sha256(task_dir / "inputs" / "reference.wav") == old_ref_sha
    assert _count_staging_artifacts(task_dir) == 0
    assert _count_task_artifacts(task_dir) == 0


def test_same_ext_ref_reference_after_install_fault(tmp_path: Path):
    """同扩展 reference：reference.after_install 故障后 sha256 不变。"""
    app, repo = _create_app_with_checkpoint_fault(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    _save_inputs_with_ref(client, task_id, audio_bytes=b"\x00" * 1024)

    task_dir = tmp_path / "tasks" / task_id
    old_request_sha = _sha256(task_dir / "request.json")
    old_task_sha = _sha256(task_dir / "task.json")
    old_ref_sha = _sha256(task_dir / "inputs" / "reference.wav")

    repo.set_fault("reference.after_install")

    audio = io.BytesIO(b"\x01" * 1024)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "更新后的文案用于测试同扩展参考音频更新功能。"},
        files={"reference": ("reference.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 500

    repo.set_fault(None)

    assert _sha256(task_dir / "request.json") == old_request_sha
    assert _sha256(task_dir / "task.json") == old_task_sha
    assert _sha256(task_dir / "inputs" / "reference.wav") == old_ref_sha
    assert _count_staging_artifacts(task_dir) == 0
    assert _count_task_artifacts(task_dir) == 0


# ── 测试：已有跨扩展 reference 故障注入 ────────────────────────────────────


def test_cross_ext_ref_after_backup_fault(tmp_path: Path):
    """跨扩展 reference：after_backup 故障后只存在旧扩展且 sha256 不变。"""
    app, repo = _create_app_with_checkpoint_fault(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    _save_inputs_with_ref(client, task_id, audio_bytes=b"\x00" * 1024, audio_name="reference.wav")

    task_dir = tmp_path / "tasks" / task_id
    old_request_sha = _sha256(task_dir / "request.json")
    old_task_sha = _sha256(task_dir / "task.json")
    old_ref_sha = _sha256(task_dir / "inputs" / "reference.wav")

    for checkpoint in ["request.after_backup", "task.after_backup", "reference.after_backup"]:
        repo.set_fault(checkpoint)

        audio = io.BytesIO(b"\x01" * 1024)
        resp = client.post(
            f"/api/v1/tasks/{task_id}/inputs",
            data={"script": "更新后的文案用于测试跨扩展参考音频更新功能。"},
            files={"reference": ("reference.mp3", audio, "audio/mpeg")},
        )
        assert resp.status_code == 500, f"checkpoint {checkpoint} should fail"

        repo.set_fault(None)

        assert _sha256(task_dir / "request.json") == old_request_sha, f"checkpoint {checkpoint}"
        assert _sha256(task_dir / "task.json") == old_task_sha, f"checkpoint {checkpoint}"
        assert (task_dir / "inputs" / "reference.wav").exists(), f"checkpoint {checkpoint}"
        assert not (task_dir / "inputs" / "reference.mp3").exists(), f"checkpoint {checkpoint}"
        assert _sha256(task_dir / "inputs" / "reference.wav") == old_ref_sha, f"checkpoint {checkpoint}"
        assert _count_staging_artifacts(task_dir) == 0
        assert _count_task_artifacts(task_dir) == 0


def test_cross_ext_ref_after_install_fault(tmp_path: Path):
    """跨扩展 reference：after_install 故障后只存在旧扩展且 sha256 不变。"""
    app, repo = _create_app_with_checkpoint_fault(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    _save_inputs_with_ref(client, task_id, audio_bytes=b"\x00" * 1024, audio_name="reference.wav")

    task_dir = tmp_path / "tasks" / task_id
    old_request_sha = _sha256(task_dir / "request.json")
    old_task_sha = _sha256(task_dir / "task.json")
    old_ref_sha = _sha256(task_dir / "inputs" / "reference.wav")

    for checkpoint in ["request.after_install", "task.after_install", "reference.after_install"]:
        repo.set_fault(checkpoint)

        audio = io.BytesIO(b"\x01" * 1024)
        resp = client.post(
            f"/api/v1/tasks/{task_id}/inputs",
            data={"script": "更新后的文案用于测试跨扩展参考音频更新功能。"},
            files={"reference": ("reference.mp3", audio, "audio/mpeg")},
        )
        assert resp.status_code == 500, f"checkpoint {checkpoint} should fail"

        repo.set_fault(None)

        assert _sha256(task_dir / "request.json") == old_request_sha, f"checkpoint {checkpoint}"
        assert _sha256(task_dir / "task.json") == old_task_sha, f"checkpoint {checkpoint}"
        assert (task_dir / "inputs" / "reference.wav").exists(), f"checkpoint {checkpoint}"
        assert not (task_dir / "inputs" / "reference.mp3").exists(), f"checkpoint {checkpoint}"
        assert _sha256(task_dir / "inputs" / "reference.wav") == old_ref_sha, f"checkpoint {checkpoint}"
        assert _count_staging_artifacts(task_dir) == 0
        assert _count_task_artifacts(task_dir) == 0


# ── 测试：并发串行化 ──────────────────────────────────────────────────────


def test_same_task_lock_serializes(tmp_path: Path):
    """同一 Task 并发保存被锁串行化：A 持有锁时 B 无法进入 checkpoint。

    使用 Event + contextvars 同步，证明 A 在 checkpoint 内（锁持有）时 B 被阻塞。
    注意：upload_inputs 是 async def，Starlette TestClient 在 asyncio portal 线程中执行，
    因此用 contextvars.ContextVar 而非 threading.current_thread().name 来区分逻辑线程。
    """
    from webapp.mountain_server import create_app

    # Context variable for logical thread identification
    logical_thread = contextvars.ContextVar("logical_thread", default="unknown")

    # 同步原语
    a_entered = threading.Event()  # A 进入 checkpoint 后设置
    a_release = threading.Event()  # 主线程通知 A 释放
    b_entered = threading.Event()  # B 进入 checkpoint 后设置（不应在 A 释放前发生）
    b_started = threading.Event()  # B 紧邻真实 POST 前设置，排除未调度假象
    results: dict[str, int | BaseException] = {}

    class SyncRepo(FilesystemTaskRepository):
        """只在 request.after_install 处注入同步点。"""

        def _input_txn_checkpoint(self, name: str, context: dict) -> None:
            if name == "request.after_install":
                current = logical_thread.get()
                if current == "thread-a":
                    a_entered.set()
                    a_release.wait(timeout=10)
                elif current == "thread-b":
                    b_entered.set()

    repo = SyncRepo(tmp_path)
    app = create_app(tmp_path, repository=repo)

    # 先用 TestClient 创建任务
    setup_client = TestClient(app)
    task_id = _create_task(setup_client, "并发串行化测试")

    def thread_a():
        """A：上传 reference，保存输入。"""
        try:
            logical_thread.set("thread-a")
            client = TestClient(app)
            audio = io.BytesIO(b"\xAA" * 512)
            results["a"] = client.post(
                f"/api/v1/tasks/{task_id}/inputs",
                data={"script": "A 的文案：带参考音频的首次保存，需要足够长的文案内容。"},
                files={"reference": ("ref_a.wav", audio, "audio/wav")},
            ).status_code
        except BaseException as exc:
            results["a"] = exc

    def thread_b():
        """B：不上传 reference，保存不同 script。"""
        try:
            logical_thread.set("thread-b")
            client = TestClient(app)
            b_started.set()
            results["b"] = client.post(
                f"/api/v1/tasks/{task_id}/inputs",
                data={"script": "B 的文案：不带参考音频的更新保存，需要足够长的文案内容。"},
            ).status_code
        except BaseException as exc:
            results["b"] = exc

    # 启动 A
    t_a = threading.Thread(target=thread_a, name="thread-a")
    t_a.start()

    # 等待 A 进入 checkpoint（在锁内）
    assert a_entered.wait(timeout=15), "A 未在超时内进入 checkpoint"

    # 启动 B（A 仍持有锁）
    t_b = threading.Thread(target=thread_b, name="thread-b")
    t_b.start()

    assert b_started.wait(timeout=15), "B 未在超时内开始真实 POST"
    # 有界观察：等待 1 秒确认 B 被锁阻塞（不得用 is_set() 代替等待窗口）
    assert not b_entered.wait(timeout=1.0), "B 在 A 持有锁期间进入了 checkpoint，串行化失败"

    # 释放 A
    a_release.set()

    # 等待两个线程完成
    t_a.join(timeout=15)
    t_b.join(timeout=15)

    # 验证两者都成功
    assert not t_a.is_alive(), "A 线程超时未完成"
    assert not t_b.is_alive(), "B 线程超时未完成"
    assert b_entered.is_set(), "B 在线程结束后未经过同一生产 checkpoint"
    assert not isinstance(results.get("a"), BaseException), f"A 线程异常: {results.get('a')}"
    assert not isinstance(results.get("b"), BaseException), f"B 线程异常: {results.get('b')}"
    assert results.get("a") == 200, f"A 线程状态码: {results.get('a')}"
    assert results.get("b") == 200, f"B 线程状态码: {results.get('b')}"


def test_concurrent_ref_preservation(tmp_path: Path):
    """A 上传新 reference 并停止在 checkpoint（锁内），B 不上传 reference 并提交不同 script。

    释放后两者都成功：最终 script 是 B 的，reference 是 A 上传的文件。
    """
    from webapp.mountain_server import create_app

    # Context variable for logical thread identification
    logical_thread = contextvars.ContextVar("logical_thread", default="unknown")

    # 同步原语
    a_entered = threading.Event()
    a_release = threading.Event()
    b_entered = threading.Event()
    b_started = threading.Event()

    # 用于记录线程结果
    results: dict[str, int] = {}

    class SyncRepo(FilesystemTaskRepository):
        """只在 request.after_install 处注入同步点。"""

        def _input_txn_checkpoint(self, name: str, context: dict) -> None:
            if name == "request.after_install":
                current = logical_thread.get()
                if current == "thread-a":
                    a_entered.set()
                    a_release.wait(timeout=10)
                elif current == "thread-b":
                    b_entered.set()

    repo = SyncRepo(tmp_path)
    app = create_app(tmp_path, repository=repo)

    # 先用 TestClient 创建任务
    setup_client = TestClient(app)
    task_id = _create_task(setup_client, "并发 reference 保留测试")

    audio_a_content = b"\xAA" * 512  # A 上传的 reference 内容

    def thread_a():
        """A：上传 reference，带 script。"""
        try:
            logical_thread.set("thread-a")
            client = TestClient(app)
            audio = io.BytesIO(audio_a_content)
            results["a"] = client.post(
                f"/api/v1/tasks/{task_id}/inputs",
                data={"script": "A 的文案：首次带参考音频保存，需要足够长的文案内容。"},
                files={"reference": ("reference.wav", audio, "audio/wav")},
            ).status_code
        except BaseException as exc:
            results["a"] = exc

    def thread_b():
        """B：不上传 reference，不同 script。"""
        try:
            logical_thread.set("thread-b")
            client = TestClient(app)
            b_started.set()
            results["b"] = client.post(
                f"/api/v1/tasks/{task_id}/inputs",
                data={"script": "B 的文案：更新文案不带参考音频，需要足够长的文案内容。"},
            ).status_code
        except BaseException as exc:
            results["b"] = exc

    # 启动 A
    t_a = threading.Thread(target=thread_a, name="thread-a")
    t_a.start()

    # 等待 A 进入 checkpoint（在锁内）
    assert a_entered.wait(timeout=15), "A 未在超时内进入 checkpoint"

    # 启动 B（A 仍持有锁）
    t_b = threading.Thread(target=thread_b, name="thread-b")
    t_b.start()

    assert b_started.wait(timeout=15), "B 未在超时内开始真实 POST"
    # 有界观察：等待 1 秒确认 B 被锁阻塞（不得用 is_set() 代替等待窗口）
    assert not b_entered.wait(timeout=1.0), "B 在 A 持有锁期间进入了 checkpoint"

    # 释放 A
    a_release.set()

    # 等待两个线程完成
    t_a.join(timeout=15)
    t_b.join(timeout=15)

    # 两者都应成功
    assert b_entered.is_set(), "B 在线程结束后未经过同一生产 checkpoint"
    assert not isinstance(results.get("a"), BaseException), f"A 线程异常: {results.get('a')}"
    assert not isinstance(results.get("b"), BaseException), f"B 线程异常: {results.get('b')}"
    assert results.get("a") == 200, f"A 线程状态码: {results.get('a')}"
    assert results.get("b") == 200, f"B 线程状态码: {results.get('b')}"

    # 验证最终状态
    task_dir = tmp_path / "tasks" / task_id
    repo2 = FilesystemTaskRepository(tmp_path)
    request_data = repo2._read_json(task_dir / "request.json")
    task_data = repo2._read_json(task_dir / "task.json")

    # script 是 B 的（后获取锁者胜出）
    expected_script = "B 的文案：更新文案不带参考音频，需要足够长的文案内容。"
    assert request_data.get("script") == expected_script
    voice_units = task_data["script_preparation"]["voice_units"]
    reconstructed_script = "".join(unit["text"] for unit in voice_units)
    assert reconstructed_script == expected_script
    cursor = 0
    for unit in voice_units:
        source_range = unit["source_range"]
        assert source_range["start"] == cursor
        assert unit["text"] == expected_script[source_range["start"]:source_range["end"]]
        cursor = source_range["end"]
    assert cursor == len(expected_script)

    # reference 是 A 上传的（B 没上传，preserve_reference=True 保留了 A 的）
    assert request_data.get("reference_audio") == "inputs/reference.wav"
    ref_path = task_dir / "inputs" / "reference.wav"
    assert ref_path.exists(), "reference 文件应存在"
    assert _sha256(ref_path) == hashlib.sha256(audio_a_content).hexdigest(), \
        "reference 文件 sha256 应等于 A 上传的内容"

    # staging 清零
    assert _count_staging_artifacts(task_dir) == 0
    assert _count_task_artifacts(task_dir) == 0


def test_different_tasks_can_parallel(tmp_path: Path):
    """不同 Task 可并行，不退化为全局锁。"""
    from webapp.mountain_server import create_app

    app = create_app(tmp_path)
    client = TestClient(app)

    task_id_a = _create_task(client, "任务 A")
    task_id_b = _create_task(client, "任务 B")

    barrier = threading.Barrier(2, timeout=10)
    results: dict[str, int] = {}
    entered: list[str] = []

    class BarrierCheckpointRepository(FilesystemTaskRepository):
        """在 request.after_install 处同步。"""

        def _input_txn_checkpoint(self, name: str, context: dict) -> None:
            if name == "request.after_install":
                entered.append(context["task_id"])
                barrier.wait()

    repo = BarrierCheckpointRepository(tmp_path)
    app2 = create_app(tmp_path, repository=repo)
    client2 = TestClient(app2)

    def save_a():
        resp = client2.post(
            f"/api/v1/tasks/{task_id_a}/inputs",
            data={"script": "任务 A 的文案内容，用于测试不同任务并行功能。"},
        )
        results["a"] = resp.status_code

    def save_b():
        resp = client2.post(
            f"/api/v1/tasks/{task_id_b}/inputs",
            data={"script": "任务 B 的文案内容，用于测试不同任务并行功能。"},
        )
        results["b"] = resp.status_code

    t_a = threading.Thread(target=save_a)
    t_b = threading.Thread(target=save_b)
    t_a.start()
    t_b.start()
    t_a.join(timeout=10)
    t_b.join(timeout=10)

    # 两个保存都应该成功
    assert results.get("a") == 200
    assert results.get("b") == 200

    # 两个任务都进入了 checkpoint（证明并行，不是全局锁）
    assert len(entered) == 2
    assert task_id_a in entered
    assert task_id_b in entered


# ── 测试：上传上限和 chunk size 注入 ──────────────────────────────────────


def test_upload_limit_injection(tmp_path: Path):
    """注入 max_bytes=8, chunk_size=4，验证 8 字节成功、9 字节失败。"""
    from webapp.mountain_server import create_app

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
    """注入 chunk_size=4，验证文件大小正确。"""
    from webapp.mountain_server import create_app

    app = create_app(tmp_path, max_upload_bytes=100, chunk_size=4)
    client = TestClient(app)
    task_id = _create_task(client)

    audio = io.BytesIO(b"\x00" * 8)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "这是一个测试文案，用于验证分块读取功能。"},
        files={"reference": ("reference.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 200

    resp = client.get(f"/api/v1/tasks/{task_id}/inputs")
    assert resp.status_code == 200
    assert resp.json()["reference_audio"]["size_bytes"] == 8


# ── 测试：/mnt/d 真实 HTTP 上传 ──────────────────────────────────────────


def test_real_http_upload_mnt_d():
    """在 /mnt/d 下运行真实 HTTP 小文件上传测试。"""
    import tempfile

    mnt_d = Path("/mnt/d")
    if not mnt_d.exists():
        pytest.skip("/mnt/d 不存在")

    with tempfile.TemporaryDirectory(dir=mnt_d) as tmp_dir:
        from webapp.mountain_server import create_app

        data_dir = Path(tmp_dir)
        app = create_app(data_dir)
        client = TestClient(app)

        task_id = _create_task(client, "真实上传测试")

        audio = io.BytesIO(b"\x00" * 256)
        resp = client.post(
            f"/api/v1/tasks/{task_id}/inputs",
            data={"script": "这是一个测试文案，用于验证在真实数据盘上的上传功能。"},
            files={"reference": ("reference.wav", audio, "audio/wav")},
        )
        assert resp.status_code == 200

        task_dir = data_dir / "tasks" / task_id
        assert (task_dir / "request.json").exists()
        assert (task_dir / "inputs" / "reference.wav").exists()
        assert _count_staging_artifacts(task_dir) == 0


# ── 测试：INTERNAL_ERROR 脱敏 ────────────────────────────────────────────


def test_internal_error_no_path_leak(tmp_path: Path):
    """INTERNAL_ERROR 响应不含路径、Errno 和注入异常文本。"""
    app, repo = _create_app_with_checkpoint_fault(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    repo.set_fault("request.after_install")

    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "这是一个测试文案，用于验证错误信息脱敏功能。"},
    )
    assert resp.status_code == 500
    error = resp.json()["error"]
    assert error["code"] == "INTERNAL_ERROR"

    repo.set_fault(None)

    message = error["message"]
    assert "/tmp" not in message
    assert "/mnt" not in message
    assert "Errno" not in message
    assert "INJECTED FAULT" not in message
    assert "Traceback" not in message


# ── 测试：成功后 staging/backup 清零 ──────────────────────────────────────


def test_success_cleanup_no_artifacts(tmp_path: Path):
    """成功后所有 staging、backup、tmp、partial 清零。"""
    from webapp.mountain_server import create_app

    app = create_app(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    _save_inputs_with_ref(client, task_id)

    task_dir = tmp_path / "tasks" / task_id
    assert _count_staging_artifacts(task_dir) == 0
    assert _count_task_artifacts(task_dir) == 0

    # 同扩展更新
    _save_inputs_with_ref(
        client, task_id,
        script="更新后的文案用于验证成功后清理功能。",
        audio_bytes=b"\x01" * 1024,
    )
    assert _count_staging_artifacts(task_dir) == 0
    assert _count_task_artifacts(task_dir) == 0

    # 跨扩展更新
    _save_inputs_with_ref(
        client, task_id,
        script="再次更新文案用于验证跨扩展更新后的清理功能。",
        audio_bytes=b"\x02" * 1024,
        audio_name="reference.mp3",
    )
    assert _count_staging_artifacts(task_dir) == 0
    assert _count_task_artifacts(task_dir) == 0

    assert (task_dir / "inputs" / "reference.mp3").exists()
    assert not (task_dir / "inputs" / "reference.wav").exists()


# ── 测试：所有保存走同一事务 ──────────────────────────────────────────────


def test_all_saves_use_transaction(tmp_path: Path):
    """所有保存（有无 reference）都走同一事务。"""
    from webapp.mountain_server import create_app

    app = create_app(tmp_path)
    client = TestClient(app)
    task_id = _create_task(client)

    resp = _save_inputs_without_ref(client, task_id)
    assert resp["ok"] is True

    task_dir = tmp_path / "tasks" / task_id
    assert _count_staging_artifacts(task_dir) == 0

    resp = _save_inputs_with_ref(client, task_id)
    assert resp["ok"] is True
    assert _count_staging_artifacts(task_dir) == 0

    resp = _save_inputs_without_ref(client, task_id, "更新文案用于验证事务一致性。")
    assert resp["ok"] is True
    assert _count_staging_artifacts(task_dir) == 0
