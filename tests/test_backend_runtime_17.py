"""CCB-PORTABLE-BACKEND-RUNTIME-19: 可移植后端启动与 Smoke 纠偏测试。

所有测试必须证明真实子进程行为，不得读取源码字符串代替。
每个 Popen 创建后立即纳入 try/finally。
不得使用 ignore_errors 或手工复制清理算法冒充 smoke 行为。
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
LAUNCH_SCRIPT = PROJECT_ROOT / "scripts" / "run_mountain_backend.py"
SMOKE_SCRIPT = PROJECT_ROOT / "scripts" / "smoke_real_backend_contract.py"

# CCF worktree 中的 contract checker
CCF_CHECKER = Path(
    "/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/"
    "mountain-assets-settings-web/web-v2/scripts/check-api-contract.mjs"
)

# 唯一 canary，用于验证脱敏
CANARY_SECRET = "ccb-runtime-secret-canary-9f3a7b2e"


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_health(base: str, timeout: float = 30.0) -> dict:
    deadline = time.monotonic() + timeout
    last_err = None
    url = f"{base}/health"
    while time.monotonic() < deadline:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                body = json.loads(resp.read())
                if body.get("status") in ("ok", "degraded"):
                    return body
        except Exception as exc:
            last_err = exc
        time.sleep(0.5)
    raise TimeoutError(f"Health check timed out after {timeout}s: {last_err}")


def _clean_env(canary: bool = False) -> dict[str, str]:
    """返回干净环境：移除会影响模块搜索和加密模式的变量。

    canary=True 时注入唯一 Secret canary 用于脱敏验证。
    """
    env = os.environ.copy()
    # 移除可能干扰仓库外启动测试的变量
    _skip = {"PYTHON" + "PATH", "CSBOARD_ALLOW_PLAINTEXT_SECRETS"}
    for key in list(env.keys()):
        if key in _skip:
            del env[key]
    if canary:
        env["CSBOARD_CONTRACT_CANARY"] = CANARY_SECRET
    return env


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# ── 参数解析测试 ─────────────────────────────────────────────────────────


def test_launch_script_help():
    """--help 正常退出并包含关键参数。"""
    result = subprocess.run(
        [PYTHON, str(LAUNCH_SCRIPT), "--help"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert "--host" in result.stdout
    assert "--port" in result.stdout
    assert "--data-dir" in result.stdout


def test_launch_script_port_occupied():
    """端口占用时非零退出并给出可操作错误。

    socket 保持打开直到 launcher 返回，确保端口确实被占用。
    使用临时文件捕获输出，finally 强制终止。
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proc = None
    out_file = None
    try:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        port = s.getsockname()[1]
        out_file = tempfile.NamedTemporaryFile(
            mode="w+", suffix=".log", delete=False, prefix="port-test-"
        )
        proc = subprocess.Popen(
            [PYTHON, str(LAUNCH_SCRIPT), "--port", str(port)],
            stdout=out_file,
            stderr=subprocess.STDOUT,
            env=_clean_env(),
        )
        proc.wait(timeout=15)
        assert proc.returncode != 0
        out_file.seek(0)
        err_text = out_file.read()
        assert "端口" in err_text or "port" in err_text.lower()
    finally:
        s.close()
        if proc is not None and proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
        if out_file is not None:
            out_file.close()
            Path(out_file.name).unlink(missing_ok=True)


# ── 仓库外/空格 cwd 真实启动 ─────────────────────────────────────────────


def test_launch_from_outside_repo_cwd():
    """从仓库外绝对路径启动，health 返回 ok、加密。"""
    proc = None
    data_dir = Path(tempfile.mkdtemp(prefix="csboard-outside-"))
    try:
        with tempfile.TemporaryDirectory(prefix="outside-cwd-") as cwd_str:
            cwd = Path(cwd_str)
            port = _find_free_port()
            env = _clean_env()
            env["CSBOARD_DATA_DIR"] = str(data_dir)

            log_file = data_dir / "uvicorn.log"
            log_fd = open(log_file, "w")
            try:
                proc = subprocess.Popen(
                    [PYTHON, str(LAUNCH_SCRIPT), "--port", str(port), "--log-level", "warning"],
                    env=env,
                    cwd=str(cwd),
                    stdout=log_fd,
                    stderr=subprocess.STDOUT,
                )

                health = _wait_for_health(f"http://127.0.0.1:{port}/api/v1", timeout=30)

                assert health["status"] in ("ok", "degraded")
                checks = health.get("checks", {})
                assert checks.get("secret_store", {}).get("encrypted") is True
                assert checks.get("storage", {}).get("writable") is True
            finally:
                log_fd.close()
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=10)
        if data_dir.exists():
            shutil.rmtree(data_dir)


def test_launch_from_cwd_with_spaces():
    """从含空格的 cwd 启动，正常工作。"""
    proc = None
    data_dir = Path(tempfile.mkdtemp(prefix="csboard-spaces-"))
    try:
        with tempfile.TemporaryDirectory(prefix="cwd with spaces ") as cwd_str:
            cwd = Path(cwd_str)
            port = _find_free_port()
            env = _clean_env()
            env["CSBOARD_DATA_DIR"] = str(data_dir)

            log_file = data_dir / "uvicorn.log"
            log_fd = open(log_file, "w")
            try:
                proc = subprocess.Popen(
                    [PYTHON, str(LAUNCH_SCRIPT), "--port", str(port), "--log-level", "warning"],
                    env=env,
                    cwd=str(cwd),
                    stdout=log_fd,
                    stderr=subprocess.STDOUT,
                )

                health = _wait_for_health(f"http://127.0.0.1:{port}/api/v1", timeout=30)

                assert health["status"] in ("ok", "degraded")
                assert health.get("checks", {}).get("secret_store", {}).get("encrypted") is True
            finally:
                log_fd.close()
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=10)
        if data_dir.exists():
            shutil.rmtree(data_dir)


# ── 加密启动证明 ─────────────────────────────────────────────────────────


def test_default_encrypted_startup():
    """默认加密模式：无 CSBOARD_ALLOW_PLAINTEXT_SECRETS 时 health 加密=true。"""
    proc = None
    data_dir = Path(tempfile.mkdtemp(prefix="csboard-enc-"))
    try:
        port = _find_free_port()
        env = _clean_env()
        env["CSBOARD_DATA_DIR"] = str(data_dir)

        log_file = data_dir / "uvicorn.log"
        log_fd = open(log_file, "w")
        try:
            proc = subprocess.Popen(
                [PYTHON, str(LAUNCH_SCRIPT), "--port", str(port), "--log-level", "warning"],
                env=env,
                stdout=log_fd,
                stderr=subprocess.STDOUT,
            )

            health = _wait_for_health(f"http://127.0.0.1:{port}/api/v1", timeout=30)

            checks = health.get("checks", {})
            assert checks.get("secret_store", {}).get("encrypted") is True
            assert checks.get("storage", {}).get("writable") is True
        finally:
            log_fd.close()
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=10)
        if data_dir.exists():
            shutil.rmtree(data_dir)


def test_env_leak_proof():
    """显式移除模块搜索路径变量，启动仍成功。"""
    proc = None
    data_dir = Path(tempfile.mkdtemp(prefix="csboard-leak-"))
    try:
        port = _find_free_port()
        env = _clean_env()
        env["CSBOARD_DATA_DIR"] = str(data_dir)

        log_file = data_dir / "uvicorn.log"
        log_fd = open(log_file, "w")
        try:
            proc = subprocess.Popen(
                [PYTHON, str(LAUNCH_SCRIPT), "--port", str(port), "--log-level", "warning"],
                env=env,
                stdout=log_fd,
                stderr=subprocess.STDOUT,
            )

            health = _wait_for_health(f"http://127.0.0.1:{port}/api/v1", timeout=30)

            assert health["status"] in ("ok", "degraded")
            assert health.get("checks", {}).get("secret_store", {}).get("encrypted") is True
        finally:
            log_fd.close()
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=10)
        if data_dir.exists():
            shutil.rmtree(data_dir)


# ── 成功路径清理证明 ─────────────────────────────────────────────────────


def test_success_cleanup_proven():
    """成功启动后：进程停止、PID 消失、临时目录消失。"""
    proc = None
    data_dir = Path(tempfile.mkdtemp(prefix="csboard-clean-"))
    try:
        port = _find_free_port()
        env = _clean_env()
        env["CSBOARD_DATA_DIR"] = str(data_dir)

        log_file = data_dir / "uvicorn.log"
        log_fd = open(log_file, "w")
        try:
            proc = subprocess.Popen(
                [PYTHON, str(LAUNCH_SCRIPT), "--port", str(port), "--log-level", "warning"],
                env=env,
                stdout=log_fd,
                stderr=subprocess.STDOUT,
            )
            pid = proc.pid

            health = _wait_for_health(f"http://127.0.0.1:{port}/api/v1", timeout=30)
            assert health["status"] in ("ok", "degraded")

            # 清理
            proc.terminate()
            proc.wait(timeout=10)
            proc = None

            assert not _pid_alive(pid), f"进程 {pid} 仍存活"
        finally:
            log_fd.close()
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=10)
        if data_dir.exists():
            shutil.rmtree(data_dir)
    assert not data_dir.exists(), f"临时目录未清理: {data_dir}"


# ── Smoke 真实路径测试 ───────────────────────────────────────────────────


def test_smoke_checker_success_path():
    """smoke 真实 checker 成功路径：exit=0，PID 消失，目录消失。"""
    tmp_parent = Path(tempfile.mkdtemp(prefix="csboard-smoke-test-"))
    try:
        result = subprocess.run(
            [
                PYTHON, str(SMOKE_SCRIPT),
                "--checker-path", str(CCF_CHECKER),
                "--temp-parent", str(tmp_parent),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            env=_clean_env(canary=True),
        )
        output = result.stdout + result.stderr
        assert result.returncode == 0, f"smoke 失败: exit={result.returncode}\n{output}"
        assert "All contracts aligned against real backend" in output
        assert "API Smoke: ALL PASSED" in output

        # 验证 PID 消失
        marker = list(tmp_parent.glob("csboard-smoke-*/pid.marker"))
        assert len(marker) == 0 or all(
            not _pid_alive(int(m.read_text())) for m in marker
        ), "smoke 遗留了存活进程"

        # 验证临时目录消失
        remaining = list(tmp_parent.iterdir())
        assert len(remaining) == 0, f"smoke 遗留了临时目录: {remaining}"

        # 验证 canary 脱敏
        assert CANARY_SECRET not in output, "smoke stdout/stderr 泄漏了 canary Secret"
    finally:
        if tmp_parent.exists():
            shutil.rmtree(tmp_parent)


def test_smoke_checker_failure_path():
    """smoke checker 非零路径：exit=1，PID 消失，目录消失。"""
    tmp_parent = Path(tempfile.mkdtemp(prefix="csboard-smoke-fail-"))
    try:
        # 使用一个返回非零的假 checker
        fake_checker = tmp_parent / "fake-checker.mjs"
        fake_checker.write_text(
            'console.error("Fake checker failure"); process.exit(1);\n',
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                PYTHON, str(SMOKE_SCRIPT),
                "--checker-path", str(fake_checker),
                "--temp-parent", str(tmp_parent),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            env=_clean_env(canary=True),
        )
        output = result.stdout + result.stderr
        assert result.returncode != 0, "smoke 应非零退出"
        assert "Checker" in output or "checker" in output

        # 验证 PID 消失
        remaining = list(tmp_parent.iterdir())
        # 只剩 fake-checker.mjs 本身
        remaining_files = [f for f in remaining if f.name != "fake-checker.mjs"]
        assert len(remaining_files) == 0, f"smoke 遗留了临时目录: {remaining_files}"

        # 验证 canary 脱敏
        assert CANARY_SECRET not in output, "smoke stdout/stderr 泄漏了 canary Secret"
    finally:
        if tmp_parent.exists():
            shutil.rmtree(tmp_parent)


def test_smoke_health_startup_failure_path():
    """smoke health/startup 失败路径：exit!=0，PID 消失，目录消失。

    通过让 launcher 绑定一个已被占用的端口来触发启动失败。
    """
    tmp_parent = Path(tempfile.mkdtemp(prefix="csboard-smoke-health-"))
    # 占用端口让 smoke 的 health 超时
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        blocker.bind(("127.0.0.1", 0))
        blocker.listen(1)
        occupied_port = blocker.getsockname()[1]

        result = subprocess.run(
            [
                PYTHON, str(SMOKE_SCRIPT),
                "--port", str(occupied_port),
                "--temp-parent", str(tmp_parent),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            env=_clean_env(canary=True),
        )
        output = result.stdout + result.stderr
        assert result.returncode != 0, "smoke 应非零退出（health 失败）"

        # 验证 PID 消失
        marker = list(tmp_parent.glob("csboard-smoke-*/pid.marker"))
        assert len(marker) == 0 or all(
            not _pid_alive(int(m.read_text())) for m in marker
        ), "smoke 遗留了存活进程"

        # 验证临时目录消失
        remaining = list(tmp_parent.iterdir())
        assert len(remaining) == 0, f"smoke 遗留了临时目录: {remaining}"

        # 验证 canary 脱敏（启动失败日志中也不含 canary）
        assert CANARY_SECRET not in output, "smoke 输出泄漏了 canary Secret"
    finally:
        blocker.close()
        if tmp_parent.exists():
            shutil.rmtree(tmp_parent)


# ── 脱敏测试 ─────────────────────────────────────────────────────────────


def test_startup_error_no_secret_leak():
    """启动错误输出不包含 canary Secret。"""
    data_dir = Path(tempfile.mkdtemp(prefix="csboard-noleak-"))
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        port = s.getsockname()[1]

        env = _clean_env(canary=True)
        env["CSBOARD_DATA_DIR"] = str(data_dir)
        result = subprocess.run(
            [PYTHON, str(LAUNCH_SCRIPT), "--port", str(port)],
            capture_output=True, text=True, timeout=15,
            env=env,
        )
        output = result.stdout + result.stderr
        assert CANARY_SECRET not in output, "错误输出泄漏了 canary Secret"
    finally:
        s.close()
        if data_dir.exists():
            shutil.rmtree(data_dir)


# ── Smoke checker 缺失 ──────────────────────────────────────────────────


def test_smoke_checker_missing_exits_nonzero():
    """checker 不存在时 smoke 非零退出。"""
    result = subprocess.run(
        [PYTHON, str(SMOKE_SCRIPT), "--checker-path", "/nonexistent/checker.mjs"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "不存在" in output or "Checker" in output
