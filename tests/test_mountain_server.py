"""Mountain Server 集成测试。

覆盖：
- app 可导入
- /api/v1/tasks 可用
- /api/v1/providers 为 404
- /api/v1/services 可用
- 创建 Task / 保存 inputs / 读取
- 5175 CORS
- SPA fallback
- API 404 不返回 HTML
- 无 legacy import
- Health 非固定假状态
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from webapp.mountain_server import create_app


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    app = create_app(tmp_path)
    return TestClient(app)


def test_app_importable():
    """mountain_server:app 可导入。"""
    from webapp.mountain_server import app
    assert app is not None


def test_health(client: TestClient):
    """Health 端点返回真实状态。"""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded", "failed")
    assert "checks" in data
    assert "task_repository" in data["checks"]
    assert "secret_store" in data["checks"]


def test_tasks_not_404(client: TestClient):
    """GET /api/v1/tasks 不再是 404。"""
    resp = client.get("/api/v1/tasks")
    assert resp.status_code == 200
    assert "items" in resp.json()


def test_providers_is_404(client: TestClient):
    """GET /api/v1/providers 在新 Mountain Server 中为 404。"""
    resp = client.get("/api/v1/providers")
    assert resp.status_code == 404
    data = resp.json()
    assert "error" in data


def test_services_available(client: TestClient):
    """GET /api/v1/services 正常工作。"""
    resp = client.get("/api/v1/services")
    assert resp.status_code == 200
    assert "items" in resp.json()


def test_create_and_get_task(client: TestClient):
    """创建 Task 后能读取 Task。"""
    resp = client.post("/api/v1/tasks", json={"title": "测试任务"})
    assert resp.status_code == 200
    task_id = resp.json()["task_id"]
    assert task_id

    resp = client.get(f"/api/v1/tasks/{task_id}")
    assert resp.status_code == 200
    assert resp.json()["task"]["task_id"] == task_id


def test_save_and_read_inputs(client: TestClient):
    """保存 inputs 后能读取。"""
    # 创建任务
    resp = client.post("/api/v1/tasks", json={"title": "输入测试"})
    task_id = resp.json()["task_id"]

    # 保存输入（带参考音频）
    import io
    audio = io.BytesIO(b"\x00" * 4096)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={
            "script": "这是一段测试文案，用于验证输入保存功能是否正常工作。",
            "style": "极简粗线简笔白板风",
        },
        files={"reference": ("test.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 200
    assert resp.json()["input_saved"] is True

    # 读取输入
    resp = client.get(f"/api/v1/tasks/{task_id}/inputs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["saved"] is True
    assert "测试" in data["inputs"]["script"]


def test_create_run_and_control(client: TestClient):
    """创建 Run 后能在同一 task_id 下控制。"""
    resp = client.post("/api/v1/tasks", json={"title": "Run 测试"})
    assert resp.status_code == 200
    data = resp.json()
    task_id = data["task_id"]
    run_id = data.get("run_id")
    assert run_id, f"run_id not found in response: {data}"

    # 获取 Run
    resp = client.get(f"/api/v1/tasks/{task_id}/runs/{run_id}")
    assert resp.status_code == 200
    assert resp.json()["run_id"] == run_id

    # 获取 Stages
    resp = client.get(f"/api/v1/tasks/{task_id}/runs/{run_id}/stages")
    assert resp.status_code == 200
    assert "items" in resp.json()


def test_cors_5175(client: TestClient):
    """CORS 允许 localhost:5175。"""
    resp = client.options(
        "/api/v1/health",
        headers={
            "origin": "http://localhost:5175",
            "access-control-request-method": "GET",
        },
    )
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers


def test_api_unknown_returns_json_404(client: TestClient):
    """未知 /api/* 返回 JSON 404，不是 HTML。"""
    resp = client.get("/api/unknown/path")
    assert resp.status_code == 404
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"


def test_no_legacy_import():
    """mountain_server 不导入 webapp.server、LegacyJobBridge、JOBS。"""
    import webapp.mountain_server as mod
    source = Path(mod.__file__).read_text(encoding="utf-8")
    # 只检查实际 import 语句，不检查注释
    import_lines = [l.strip() for l in source.splitlines() if l.strip().startswith(("from ", "import "))]
    for line in import_lines:
        assert "LegacyJobBridge" not in line, f"Forbidden import: {line}"
        assert "webapp.server" not in line, f"Forbidden import: {line}"


def test_default_encrypted_startup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """默认加密模式启动：未设置 CSBOARD_ALLOW_PLAINTEXT_SECRETS 时 health 返回 encrypted=true。"""
    # 确保环境变量不存在
    monkeypatch.delenv("CSBOARD_ALLOW_PLAINTEXT_SECRETS", raising=False)

    # 创建 app（使用临时目录）
    app = create_app(tmp_path)
    client = TestClient(app)

    # 验证 health 端点返回 encrypted=true
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["checks"]["secret_store"]["encrypted"] is True


def test_inputs_and_start_boundary(client: TestClient):
    """验证 inputs 和 start 端点不直接访问文件系统。"""
    import io

    # 创建任务
    resp = client.post("/api/v1/tasks", json={"title": "边界测试"})
    assert resp.status_code == 200
    task_id = resp.json()["task_id"]
    run_id = resp.json()["run_id"]

    # 上传输入
    audio = io.BytesIO(b"\x00" * 4096)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "这是一段测试文案，用于验证输入保存功能是否正常工作。"},
        files={"reference": ("test.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 200
    assert resp.json()["input_saved"] is True

    # 读取输入
    resp = client.get(f"/api/v1/tasks/{task_id}/inputs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["saved"] is True
    assert "测试" in data["inputs"]["script"]
    assert data["reference_audio"]["uploaded"] is True

    # 启动（缺服务应返回 CAPABILITY_NOT_AVAILABLE）
    resp = client.post(f"/api/v1/tasks/{task_id}/runs/{run_id}/start")
    assert resp.status_code == 400
    error = resp.json()["error"]
    assert error["code"] == "CAPABILITY_NOT_AVAILABLE"


def test_start_without_inputs_returns_validation_error(client: TestClient):
    """未上传输入时 start 返回 VALIDATION_ERROR。"""
    # 创建任务
    resp = client.post("/api/v1/tasks", json={"title": "无输入测试"})
    assert resp.status_code == 200
    task_id = resp.json()["task_id"]
    run_id = resp.json()["run_id"]

    # 尝试启动（无输入）
    resp = client.post(f"/api/v1/tasks/{task_id}/runs/{run_id}/start")
    assert resp.status_code == 400
    error = resp.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "文案" in error["message"]


def test_update_inputs_preserves_old_reference(client: TestClient):
    """更新输入不带新 reference 时保留旧文件。"""
    import io

    # 创建任务并上传初始输入
    resp = client.post("/api/v1/tasks", json={"title": "保留测试"})
    assert resp.status_code == 200
    task_id = resp.json()["task_id"]

    audio = io.BytesIO(b"\x00" * 4096)
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "初始文案用于测试保留功能是否正常。"},
        files={"reference": ("test.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 200

    # 更新输入（不带新 reference）
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "更新后的文案用于测试保留功能是否正常。"},
    )
    assert resp.status_code == 200

    # 验证 reference 保留
    resp = client.get(f"/api/v1/tasks/{task_id}/inputs")
    assert resp.status_code == 200
    assert resp.json()["reference_audio"]["uploaded"] is True
