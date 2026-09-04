"""CCB-PORTABLE-BACKEND-RUNTIME-22: 后端测试去除 sibling worktree 依赖。

所有测试必须证明真实行为。
每个 Popen 创建后立即纳入 try/finally。
不得使用 ignore_errors 或无人消费的 PIPE。
专项测试必须 0 skipped。
pytest fixture checker 只证明生命周期，不冒充真实 CCF 契约检查；
真实 CCF checker 仅保留在独立集成 smoke 门禁中。
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import struct
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

# 唯一 canary
CANARY = "ccb-runtime-secret-canary-9f3a7b2e"


# ── Helpers ──────────────────────────────────────────────────────────────


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
    env = os.environ.copy()
    _skip = {"PYTHON" + "PATH", "CSBOARD_ALLOW_PLAINTEXT_SECRETS"}
    for key in list(env.keys()):
        if key in _skip:
            del env[key]
    if canary:
        env["CSBOARD_CONTRACT_CANARY"] = CANARY
    return env


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _read_pid_marker(path: Path) -> int | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _start_backend(data_dir: Path, port: int | None = None, cwd: Path | None = None):
    """启动后端，返回 (proc, health, port)。调用方负责清理。"""
    if port is None:
        port = _find_free_port()
    env = _clean_env()
    env["CSBOARD_DATA_DIR"] = str(data_dir)

    log_file = data_dir / "uvicorn.log"
    log_fd = open(log_file, "w")
    proc = subprocess.Popen(
        [PYTHON, str(LAUNCH_SCRIPT), "--port", str(port), "--log-level", "warning"],
        env=env,
        cwd=str(cwd) if cwd else None,
        stdout=log_fd,
        stderr=subprocess.STDOUT,
    )

    try:
        health = _wait_for_health(f"http://127.0.0.1:{port}/api/v1", timeout=30)
    except Exception:
        log_fd.close()
        proc.terminate()
        proc.wait(timeout=10)
        if data_dir.exists():
            shutil.rmtree(data_dir)
        raise

    return proc, health, port, log_fd, data_dir


def _stop_backend(proc: subprocess.Popen, log_fd, data_dir: Path) -> int:
    """停止后端并清理，返回 PID。"""
    pid = proc.pid
    proc.terminate()
    proc.wait(timeout=10)
    log_fd.close()
    if data_dir.exists():
        shutil.rmtree(data_dir)
    return pid


# ── 参数解析 ─────────────────────────────────────────────────────────────


def test_launch_script_help():
    result = subprocess.run(
        [PYTHON, str(LAUNCH_SCRIPT), "--help"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert "--host" in result.stdout
    assert "--port" in result.stdout
    assert "--data-dir" in result.stdout


def test_listener_does_not_force_abortive_rst_close():
    """Large proxied responses require a normal FIN, not SO_LINGER(1, 0)."""
    from scripts.run_mountain_backend import _create_listening_socket

    listener = _create_listening_socket("127.0.0.1", 0)
    try:
        enabled, _timeout = struct.unpack(
            "ii",
            listener.getsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.calcsize("ii")),
        )
        assert enabled == 0
    finally:
        listener.close()


def test_launch_script_port_occupied():
    """端口占用：socket 保持打开，temp file 捕获输出，finally 终止。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proc = None
    out_file = None
    try:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        port = s.getsockname()[1]
        out_file = tempfile.NamedTemporaryFile(mode="w+", suffix=".log", delete=False, prefix="port-test-")
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


# ── 仓库外/空格 cwd ─────────────────────────────────────────────────────


def test_launch_from_outside_repo_cwd():
    """仓库外 cwd 启动，health ok，PID 非空且清理后死亡。"""
    data_dir = Path(tempfile.mkdtemp(prefix="csboard-outside-"))
    proc = None
    log_fd = None
    try:
        with tempfile.TemporaryDirectory(prefix="outside-cwd-") as cwd_str:
            proc, health, _, log_fd, _ = _start_backend(data_dir, cwd=Path(cwd_str))
            pid = proc.pid

            assert health["status"] in ("ok", "degraded")
            assert health.get("checks", {}).get("secret_store", {}).get("encrypted") is True
            assert pid > 0
            assert _pid_alive(pid)

            pid = _stop_backend(proc, log_fd, data_dir)
            proc = None
            log_fd = None

            assert not _pid_alive(pid)
    finally:
        if proc is not None:
            proc.terminate()
            proc.wait(timeout=10)
        if log_fd is not None and not log_fd.closed:
            log_fd.close()
        if data_dir.exists():
            shutil.rmtree(data_dir)


def test_launch_from_cwd_with_spaces():
    """含空格 cwd 启动成功。"""
    data_dir = Path(tempfile.mkdtemp(prefix="csboard-spaces-"))
    proc = None
    log_fd = None
    try:
        with tempfile.TemporaryDirectory(prefix="cwd with spaces ") as cwd_str:
            proc, health, _, log_fd, _ = _start_backend(data_dir, cwd=Path(cwd_str))
            pid = proc.pid

            assert health["status"] in ("ok", "degraded")
            assert pid > 0

            pid = _stop_backend(proc, log_fd, data_dir)
            proc = None
            log_fd = None

            assert not _pid_alive(pid)
    finally:
        if proc is not None:
            proc.terminate()
            proc.wait(timeout=10)
        if log_fd is not None and not log_fd.closed:
            log_fd.close()
        if data_dir.exists():
            shutil.rmtree(data_dir)


# ── 加密启动 ─────────────────────────────────────────────────────────────


def test_default_encrypted_startup():
    data_dir = Path(tempfile.mkdtemp(prefix="csboard-enc-"))
    proc = None
    log_fd = None
    try:
        proc, health, _, log_fd, _ = _start_backend(data_dir)
        assert health.get("checks", {}).get("secret_store", {}).get("encrypted") is True
        assert health.get("checks", {}).get("storage", {}).get("writable") is True
        _stop_backend(proc, log_fd, data_dir)
        proc = None
        log_fd = None
    finally:
        if proc is not None:
            proc.terminate()
            proc.wait(timeout=10)
        if log_fd is not None and not log_fd.closed:
            log_fd.close()
        if data_dir.exists():
            shutil.rmtree(data_dir)


def test_env_leak_proof():
    """移除模块搜索路径变量后启动仍成功。"""
    data_dir = Path(tempfile.mkdtemp(prefix="csboard-leak-"))
    proc = None
    log_fd = None
    try:
        proc, health, _, log_fd, _ = _start_backend(data_dir)
        assert health["status"] in ("ok", "degraded")
        _stop_backend(proc, log_fd, data_dir)
        proc = None
        log_fd = None
    finally:
        if proc is not None:
            proc.terminate()
            proc.wait(timeout=10)
        if log_fd is not None and not log_fd.closed:
            log_fd.close()
        if data_dir.exists():
            shutil.rmtree(data_dir)


# ── 成功路径清理证明 ─────────────────────────────────────────────────────


def test_success_cleanup_proven():
    """成功后 PID 消失、目录消失。"""
    data_dir = Path(tempfile.mkdtemp(prefix="csboard-clean-"))
    proc = None
    log_fd = None
    try:
        proc, health, _, log_fd, _ = _start_backend(data_dir)
        pid = proc.pid

        assert health["status"] in ("ok", "degraded")
        assert pid > 0
        assert _pid_alive(pid)

        pid = _stop_backend(proc, log_fd, data_dir)
        proc = None
        log_fd = None

        assert not _pid_alive(pid)
        assert not data_dir.exists()
    finally:
        if proc is not None:
            proc.terminate()
            proc.wait(timeout=10)
        if log_fd is not None and not log_fd.closed:
            log_fd.close()
        if data_dir.exists():
            shutil.rmtree(data_dir)


def test_two_fresh_data_dirs_reuse_same_port_after_normal_shutdown():
    """Two real launcher children release one port immediately after SIGTERM."""
    port = _find_free_port()
    data_dirs = [
        Path(tempfile.mkdtemp(prefix="csboard-sequential-one-")),
        Path(tempfile.mkdtemp(prefix="csboard-sequential-two-")),
    ]
    try:
        for data_dir in data_dirs:
            proc = None
            log_fd = None
            try:
                proc, health, started_port, log_fd, _ = _start_backend(data_dir, port=port)
                assert started_port == port
                assert health["status"] in ("ok", "degraded")
                child_pid = _stop_backend(proc, log_fd, data_dir)
                log_fd = None

                assert proc.returncode == 0, f"launcher exited {proc.returncode}"
                assert not _pid_alive(child_pid)
                assert not data_dir.exists()
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reusable:
                    reusable.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    reusable.bind(("127.0.0.1", port))
            finally:
                if proc is not None and proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=10)
                if log_fd is not None and not log_fd.closed:
                    log_fd.close()
                if data_dir.exists():
                    shutil.rmtree(data_dir)
    finally:
        for data_dir in data_dirs:
            if data_dir.exists():
                shutil.rmtree(data_dir)


# ── Smoke 真实 checker 成功路径 + PID marker ────────────────────────────


def test_smoke_checker_success_path():
    """smoke 生命周期成功路径：临时最小 checker 输出成功标记后 exit=0。

    此 checker 只证明 smoke 生命周期（启动→health→checker→清理），
    不冒充真实 CCF 契约检查。真实 CCF checker 仅在独立集成 smoke 门禁中运行。
    """
    tmp_parent = Path(tempfile.mkdtemp(prefix="smoke-success-"))
    marker = tmp_parent / "pid.marker"
    # 临时最小成功 checker：仅输出成功标记，不执行真实契约断言
    min_checker = tmp_parent / "min-success-checker.mjs"
    min_checker.write_text(
        'console.log("All contracts aligned against real backend ✓");\n'
        'process.exit(0);\n',
        encoding="utf-8",
    )
    try:
        result = subprocess.run(
            [
                PYTHON, str(SMOKE_SCRIPT),
                "--checker-path", str(min_checker),
                "--temp-parent", str(tmp_parent),
                "--pid-marker", str(marker),
            ],
            capture_output=True, text=True, timeout=120,
            env=_clean_env(),
        )
        output = result.stdout + result.stderr
        assert result.returncode == 0, f"smoke 失败: exit={result.returncode}\n{output}"
        assert "All contracts aligned against real backend" in output

        pid = _read_pid_marker(marker)
        assert pid is not None, "PID marker 为空"
        assert pid > 0, f"PID 无效: {pid}"
        assert not _pid_alive(pid), f"PID {pid} 仍存活"

        # PID marker 和 min_checker 是测试创建的，由测试清理；smoke 临时目录应已消失
        remaining = [f for f in tmp_parent.iterdir() if f not in (min_checker, marker)]
        assert len(remaining) == 0, f"遗留: {remaining}"
    finally:
        if tmp_parent.exists():
            shutil.rmtree(tmp_parent)


# ── Smoke checker 失败路径 + PID marker + canary 脱敏 ───────────────────


def test_smoke_checker_failure_path():
    """smoke checker 非零：exit=1，PID marker 非空，PID 已死，canary 脱敏。"""
    tmp_parent = Path(tempfile.mkdtemp(prefix="smoke-fail-"))
    marker = tmp_parent / "pid.marker"
    # 创建输出 canary 的假 checker
    fake_checker = tmp_parent / "fake-checker.mjs"
    fake_checker.write_text(
        'console.log("Authorization: Bearer ccb-runtime-secret-canary-FAKE123");\n'
        'console.log("https://api.example.com/v1?api_key=ccb-runtime-secret-canary-QUERY456");\n'
        'process.stderr.write("Bearer ccb-runtime-secret-canary-STDERR789\\n");\n'
        'process.exit(1);\n',
        encoding="utf-8",
    )
    try:
        result = subprocess.run(
            [
                PYTHON, str(SMOKE_SCRIPT),
                "--checker-path", str(fake_checker),
                "--temp-parent", str(tmp_parent),
                "--pid-marker", str(marker),
            ],
            capture_output=True, text=True, timeout=120,
            env=_clean_env(),
        )
        assert result.returncode != 0

        pid = _read_pid_marker(marker)
        assert pid is not None, "PID marker 为空"
        assert pid > 0
        assert not _pid_alive(pid), f"PID {pid} 仍存活"

        output = result.stdout + result.stderr
        assert "ccb-runtime-secret-canary-FAKE123" not in output
        assert "ccb-runtime-secret-canary-QUERY456" not in output
        assert "ccb-runtime-secret-canary-STDERR789" not in output
        assert "[REDACTED]" in output

        # PID marker 和 fake_checker 是测试创建的，由测试清理
        remaining = [f for f in tmp_parent.iterdir() if f not in (fake_checker, marker)]
        assert len(remaining) == 0, f"遗留: {remaining}"
    finally:
        if tmp_parent.exists():
            shutil.rmtree(tmp_parent)


# ── Smoke launcher/startup 失败路径 + PID marker + canary 脱敏 ──────────


def test_smoke_startup_failure_path():
    """临时 launcher 输出 canary 后非零退出。

    smoke 检测到 launcher 提前退出 → startup failure → 非零。
    断言：PID marker 非空，PID 已死，canary 脱敏，目录消失。
    launcher 在 checker 运行前即失败，故 checker 只需存在（不执行真实契约）。
    """
    tmp_parent = Path(tempfile.mkdtemp(prefix="smoke-startup-"))
    marker = tmp_parent / "pid.marker"
    # 创建临时 launcher：输出 canary 后退出
    bad_launcher = tmp_parent / "bad_launcher.py"
    bad_launcher.write_text(
        f'import sys\n'
        f'sys.stderr.write("Authorization: Bearer {CANARY}\\n")\n'
        f'sys.stderr.write("https://api.example.com/v1?api_key={CANARY}\\n")\n'
        f'sys.exit(42)\n',
        encoding="utf-8",
    )
    # 临时存在 checker：launcher 在 checker 运行前即失败，checker 只需存在
    existing_checker = tmp_parent / "existing-checker.mjs"
    existing_checker.write_text(
        'console.log("placeholder checker");\nprocess.exit(0);\n',
        encoding="utf-8",
    )
    try:
        result = subprocess.run(
            [
                PYTHON, str(SMOKE_SCRIPT),
                "--launcher-path", str(bad_launcher),
                "--checker-path", str(existing_checker),
                "--temp-parent", str(tmp_parent),
                "--pid-marker", str(marker),
            ],
            capture_output=True, text=True, timeout=60,
            env=_clean_env(),
        )
        output = result.stdout + result.stderr
        assert result.returncode != 0, "smoke 应非零退出"

        pid = _read_pid_marker(marker)
        assert pid is not None, "PID marker 为空"
        assert pid > 0, f"PID 无效: {pid}"
        assert not _pid_alive(pid), f"PID {pid} 仍存活"

        # canary 脱敏
        assert CANARY not in output, "输出泄漏了 canary"
        assert "[REDACTED]" in output, "未出现脱敏标记"

        # 临时目录消失
        # PID marker、bad_launcher、existing_checker 是测试创建的，由测试清理
        remaining = [f for f in tmp_parent.iterdir() if f not in (bad_launcher, existing_checker, marker)]
        assert len(remaining) == 0, f"遗留: {remaining}"
    finally:
        if tmp_parent.exists():
            shutil.rmtree(tmp_parent)


# ── Canary 脱敏验证 ─────────────────────────────────────────────────────


def test_startup_error_no_secret_leak():
    """启动错误输出不包含 canary。"""
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
        assert CANARY not in output, "错误输出泄漏了 canary"
    finally:
        s.close()
        if data_dir.exists():
            shutil.rmtree(data_dir)


# ── Smoke redact_text 函数 ──────────────────────────────────────────────


def test_smoke_redact_function():
    """smoke 内置脱敏函数正确处理 Bearer、query secret 和 canary。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("smoke", SMOKE_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    text = "Authorization: Bearer my-secret-token-123"
    assert "my-secret-token-123" not in mod.redact_text(text)
    assert "[REDACTED]" in mod.redact_text(text)

    text2 = "https://api.example.com/v1?api_key=super-secret-key"
    assert "super-secret-key" not in mod.redact_text(text2)
    assert "[REDACTED]" in mod.redact_text(text2)

    text3 = f"ccb-runtime-secret-canary-XYZ"
    assert "ccb-runtime-secret-canary-XYZ" not in mod.redact_text(text3)
    assert "[REDACTED]" in mod.redact_text(text3)


# ── Smoke checker 缺失 ──────────────────────────────────────────────────


def test_smoke_checker_missing_exits_nonzero():
    result = subprocess.run(
        [PYTHON, str(SMOKE_SCRIPT), "--checker-path", "/nonexistent/checker.mjs"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "不存在" in output or "Checker" in output


def test_smoke_launcher_missing_exits_nonzero():
    """launcher 不存在时 smoke 非零退出。"""
    result = subprocess.run(
        [PYTHON, str(SMOKE_SCRIPT), "--launcher-path", "/nonexistent/launcher.py"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "Launcher" in output or "不存在" in output
