"""M07 PR-1a 验收测试：/api/v1 端点。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from webapp.server import app


@pytest.fixture()
def tmp_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """临时目录注入。"""
    state = tmp_path / ".webapp"
    state.mkdir()
    monkeypatch.setattr("webapp.server.STATE_DIR", state)
    monkeypatch.setattr("webapp.server.JOBS_DIR", state / "jobs")
    monkeypatch.setattr("webapp.server.CONFIG_PATH", state / "config.json")
    monkeypatch.setattr("webapp.server.PREFERENCES_PATH", state / "preferences.json")
    return state


@pytest.fixture()
def client(tmp_state: Path) -> TestClient:
    """TestClient 注入。"""
    return TestClient(app, raise_server_exceptions=False)


# ── 基础路由测试 ──────────────────────────────────────────────────────


def test_v1_capabilities(client: TestClient) -> None:
    """GET /api/v1/capabilities 返回支持的组合列表。"""
    response = client.get("/api/v1/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body.get("items"), list)
    assert len(body["items"]) >= 1
    first = body["items"][0]
    assert "engine" in first
    assert "visual_source" in first
    assert "supported" in first


def test_v1_health(client: TestClient) -> None:
    """GET /api/v1/health 返回服务健康状态。"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert "providers" in body


# ── 项目生命周期测试 ──────────────────────────────────────────────────


def test_v1_project_lifecycle(client: TestClient, tmp_state: Path) -> None:
    """完整项目生命周期：创建 → 上传 → 启动 → 状态查询。"""
    # 1. 创建项目
    response = client.post("/api/v1/projects", json={"title": "验收测试"})
    assert response.status_code == 200
    body = response.json()
    project_id = body["project_id"]
    assert project_id

    # 2. 上传输入（文案 + 参考音频）
    script = "第一幕：春天来了，花儿开了。第二幕：夏天到了，果实成熟了。"
    reference_content = b"fake-audio-content"
    response = client.post(
        f"/api/v1/projects/{project_id}/inputs",
        data={
            "script": script,
            "style": "极简粗线简笔白板风",
            "include_subtitles": "true",
            "pen_text": "",
            "stroke_detail": "detailed",
        },
        files={"reference": ("reference.wav", reference_content, "audio/wav")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["input_saved"] is True

    # 3. 尝试启动标准流程（Provider 未配置，应返回 CAPABILITY_NOT_AVAILABLE）
    response = client.post(f"/api/v1/projects/{project_id}/runs/{project_id}/start")
    assert response.status_code == 400
    body = response.json()
    assert body["detail"]["code"] == "CAPABILITY_NOT_AVAILABLE"


def test_v1_project_not_found(client: TestClient) -> None:
    """查询不存在的项目返回 404。"""
    response = client.get("/api/v1/projects/nonexistent")
    assert response.status_code == 404


# ── 输入上传测试 ──────────────────────────────────────────────────────


def test_v1_upload_short_script(client: TestClient, tmp_state: Path) -> None:
    """文案过短返回 400。"""
    # 先创建项目
    response = client.post("/api/v1/projects", json={"title": "测试"})
    project_id = response.json()["project_id"]

    # 上传过短文案
    response = client.post(
        f"/api/v1/projects/{project_id}/inputs",
        data={"script": "太短了"},
        files={"reference": ("ref.wav", b"audio", "audio/wav")},
    )
    assert response.status_code == 400
    assert "至少需要 10 个字" in response.text


def test_v1_upload_invalid_audio_format(client: TestClient, tmp_state: Path) -> None:
    """音频格式不支持返回 400。"""
    # 先创建项目
    response = client.post("/api/v1/projects", json={"title": "测试"})
    project_id = response.json()["project_id"]

    # 上传不支持的音频格式
    response = client.post(
        f"/api/v1/projects/{project_id}/inputs",
        data={"script": "这是一个足够长的文案用于测试验证"},
        files={"reference": ("ref.txt", b"not-audio", "text/plain")},
    )
    assert response.status_code == 400
    assert "格式不支持" in response.text


# ── Run 操作测试 ──────────────────────────────────────────────────────


def test_v1_start_without_inputs(client: TestClient, tmp_state: Path) -> None:
    """未上传输入时启动返回 400。"""
    # 先创建项目
    response = client.post("/api/v1/projects", json={"title": "测试"})
    project_id = response.json()["project_id"]

    # 尝试启动（没有 request.json）
    response = client.post(f"/api/v1/projects/{project_id}/runs/{project_id}/start")
    assert response.status_code == 400
    assert "请先上传文案与参考音频" in response.text


def test_v1_cancel_run(client: TestClient, tmp_state: Path) -> None:
    """取消运行。"""
    # 先创建项目
    response = client.post("/api/v1/projects", json={"title": "测试"})
    project_id = response.json()["project_id"]

    # 获取项目详情（这会创建一个 Run）
    response = client.get(f"/api/v1/projects/{project_id}")
    assert response.status_code == 200
    run_id = response.json()["active_run"]["run_id"]

    # 取消运行
    response = client.post(f"/api/v1/projects/{project_id}/runs/{run_id}/cancel")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["status"] == "cancelled"


# ── 产物测试 ──────────────────────────────────────────────────────


def test_v1_list_artifacts_empty(client: TestClient, tmp_state: Path) -> None:
    """没有产物时返回空列表。"""
    # 先创建项目
    response = client.post("/api/v1/projects", json={"title": "测试"})
    project_id = response.json()["project_id"]

    # 列出产物
    response = client.get(f"/api/v1/projects/{project_id}/runs/{project_id}/artifacts")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []


# ── 诊断测试 ──────────────────────────────────────────────────────


def test_v1_export_diagnostics(client: TestClient, tmp_state: Path) -> None:
    """导出诊断包。"""
    # 先创建项目
    response = client.post("/api/v1/projects", json={"title": "测试"})
    project_id = response.json()["project_id"]

    # 获取项目详情（这会创建一个 Run）
    response = client.get(f"/api/v1/projects/{project_id}")
    assert response.status_code == 200
    run_id = response.json()["active_run"]["run_id"]

    # 导出诊断包
    response = client.post(f"/api/v1/projects/{project_id}/runs/{run_id}/diagnostics")
    assert response.status_code == 200
    body = response.json()
    assert "bundle_id" in body
    assert "download_url" in body


# ── 视图完整性测试 ──────────────────────────────────────────────────────


def test_v1_project_detail_view(client: TestClient, tmp_state: Path) -> None:
    """项目详情视图包含所有必要字段。"""
    # 先创建项目
    response = client.post("/api/v1/projects", json={"title": "视图测试"})
    project_id = response.json()["project_id"]

    # 获取详情
    response = client.get(f"/api/v1/projects/{project_id}")
    assert response.status_code == 200
    body = response.json()

    # 验证视图字段
    assert "project" in body
    assert "active_run" in body
    assert "stages" in body
    assert "warnings" in body
    assert "artifacts" in body
    assert "trace" in body


def test_v1_run_view(client: TestClient, tmp_state: Path) -> None:
    """Run 视图包含所有必要字段。"""
    # 先创建项目
    response = client.post("/api/v1/projects", json={"title": "Run视图测试"})
    project_id = response.json()["project_id"]

    # 获取项目详情（这会创建一个 Run）
    response = client.get(f"/api/v1/projects/{project_id}")
    assert response.status_code == 200
    run_id = response.json()["active_run"]["run_id"]

    # 获取 Run
    response = client.get(f"/api/v1/projects/{project_id}/runs/{run_id}")
    assert response.status_code == 200
    body = response.json()

    # 验证视图字段
    assert "run_id" in body
    assert "project_id" in body
    assert "status" in body
    assert "stages" in body
    assert "warnings" in body


# ── 验收测试：完整流程（Provider 未配置场景） ──────────────────────────────


def test_v1_acceptance_flow_with_missing_provider(client: TestClient, tmp_state: Path) -> None:
    """M07 PR-1a 验收：创建项目 → 上传音频 → 启动真实标准流程 → 返回 CAPABILITY_NOT_AVAILABLE。"""
    # 步骤 1: 创建项目
    response = client.post("/api/v1/projects", json={"title": "验收测试项目"})
    assert response.status_code == 200
    project_id = response.json()["project_id"]
    assert project_id

    # 步骤 2: 上传文案和参考音频
    script = "这是一段用于验收测试的文案，足够长以满足最小要求。包含多个句子，用于测试分镜功能。"
    reference_content = b"RIFF" + b"\x00" * 100  # 简单的 WAV 头部
    response = client.post(
        f"/api/v1/projects/{project_id}/inputs",
        data={
            "script": script,
            "style": "极简粗线简笔白板风",
            "include_subtitles": "true",
            "pen_text": "",
            "stroke_detail": "detailed",
        },
        files={"reference": ("reference.wav", reference_content, "audio/wav")},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True

    # 步骤 3: 获取项目详情（这会创建一个 Run）
    response = client.get(f"/api/v1/projects/{project_id}")
    assert response.status_code == 200
    run_id = response.json()["active_run"]["run_id"]

    # 步骤 4: 尝试启动标准流程（Provider 未配置）
    response = client.post(f"/api/v1/projects/{project_id}/runs/{run_id}/start")
    assert response.status_code == 400
    body = response.json()

    # 验证返回 CAPABILITY_NOT_AVAILABLE
    assert body["detail"]["code"] == "CAPABILITY_NOT_AVAILABLE"
    assert "Provider 未配置" in body["detail"]["message"]
    assert isinstance(body["detail"]["missing"], list)
    assert len(body["detail"]["missing"]) > 0


# ── 无 legacy 依赖验证 ──────────────────────────────────────────────────────


def test_v1_no_legacy_references(client: TestClient) -> None:
    """验证 /api/v1 不包含任何 legacy 依赖。"""
    # 这个测试通过代码检查来验证，而不是运行时检查
    # 主要确保：
    # 1. 没有 mountain_stages 导入
    # 2. 没有 legacy_execution_id
    # 3. 没有 127.0.0.1:8000 引用
    # 4. 没有 Fake* 适配器使用

    # 读取 mountain_v1_api.py 源码
    from webapp import mountain_v1_api
    import inspect

    source = inspect.getsource(mountain_v1_api)

    # 验证没有 legacy 依赖（排除注释和文档字符串）
    # 将源码按行分割，只检查非注释行
    lines = source.split('\n')
    code_lines = []
    in_docstring = False
    for line in lines:
        stripped = line.strip()
        # 跳过文档字符串
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if stripped.count('"""') >= 2 or stripped.count("'''") >= 2:
                continue  # 单行文档字符串
            in_docstring = not in_docstring
            continue
        if in_docstring:
            continue
        # 跳过注释
        if stripped.startswith('#'):
            continue
        code_lines.append(line)

    code_only = '\n'.join(code_lines)

    # 验证没有 legacy 依赖
    assert "from webapp.mountain_stages" not in code_only
    assert "import mountain_stages" not in code_only
    assert "legacy_execution_id" not in code_only
    assert "127.0.0.1:8000" not in code_only
    assert "FakeTextModel" not in code_only
    assert "FakeImageModel" not in code_only
    assert "FakeTextToSpeech" not in code_only
    assert "FakeAlignment" not in code_only
    assert "FakeRenderer" not in code_only
    assert "FakeMedia" not in code_only
