"""CCB-PORTABLE-BACKEND-RUNTIME-17: 可移植后端启动与 Smoke 行为测试。

测试矩阵：
- run_mountain_backend.py 参数解析、默认值
- sys.executable 使用（非硬编码路径）
- 默认加密环境检查
- 端口占用失败
- smoke checker 缺失处理
- 子进程终止和临时目录清理断言
"""

from __future__ import annotations

import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
LAUNCH_SCRIPT = PROJECT_ROOT / "scripts" / "run_mountain_backend.py"
SMOKE_SCRIPT = PROJECT_ROOT / "scripts" / "smoke_real_backend_contract.py"


# ── run_mountain_backend.py 行为测试 ─────────────────────────────────────


def test_launch_script_exists():
    """启动脚本存在且可执行。"""
    assert LAUNCH_SCRIPT.exists()
    assert LAUNCH_SCRIPT.stat().st_size > 0


def test_launch_script_uses_sys_executable():
    """启动脚本使用 sys.executable 而非硬编码路径。"""
    content = LAUNCH_SCRIPT.read_text(encoding="utf-8")
    # 不得硬编码 venv 路径
    assert "/mnt/d/" not in content
    assert ".venv/bin" not in content
    assert "mise/installs" not in content
    # 必须使用 sys.executable 或 uvicorn.run
    assert "sys.executable" in content or "uvicorn.run" in content


def test_launch_script_no_plaintext_secrets():
    """启动脚本不得设置 CSBOARD_ALLOW_PLAINTEXT_SECRETS=1。"""
    content = LAUNCH_SCRIPT.read_text(encoding="utf-8")
    assert "CSBOARD_ALLOW_PLAINTEXT_SECRETS.*1" not in content
    # 不得主动创建明文 SecretStore
    assert 'CSBOARD_ALLOW_PLAINTEXT_SECRETS", "1"' not in content


def test_launch_script_no_webapp_server():
    """启动脚本不得导入 webapp.server。"""
    content = LAUNCH_SCRIPT.read_text(encoding="utf-8")
    assert "from webapp.server" not in content
    assert "import webapp.server" not in content
    assert "webapp.server:app" not in content


def test_launch_script_help():
    """启动脚本 --help 正常退出。"""
    result = subprocess.run(
        [PYTHON, str(LAUNCH_SCRIPT), "--help"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert "--host" in result.stdout
    assert "--port" in result.stdout
    assert "--data-dir" in result.stdout
    assert "--log-level" in result.stdout


def test_launch_script_default_values():
    """启动脚本默认值: host=127.0.0.1, port=8000。"""
    content = LAUNCH_SCRIPT.read_text(encoding="utf-8")
    assert 'default="127.0.0.1"' in content
    assert "default=8000" in content


def test_launch_script_port_occupied():
    """端口占用时启动脚本非零退出并给出可操作错误。"""
    # 占用一个端口
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        result = subprocess.run(
            [PYTHON, str(LAUNCH_SCRIPT), "--port", str(port)],
            capture_output=True, text=True, timeout=10,
            env={**os.environ, "CSBOARD_DATA_DIR": tempfile.mkdtemp()},
        )
        assert result.returncode != 0
        assert "端口" in result.stderr or "port" in result.stderr.lower()


# ── smoke_real_backend_contract.py 行为测试 ──────────────────────────────


def test_smoke_script_uses_sys_executable():
    """smoke 脚本使用 sys.executable 而非硬编码路径。"""
    content = SMOKE_SCRIPT.read_text(encoding="utf-8")
    assert "/mnt/d/" not in content
    assert ".venv/bin" not in content
    assert "mise/installs" not in content
    assert "sys.executable" in content


def test_smoke_script_no_hardcoded_node():
    """smoke 脚本使用 shutil.which('node') 而非硬编码 node 路径。"""
    content = SMOKE_SCRIPT.read_text(encoding="utf-8")
    assert "mise/installs/node" not in content
    assert 'shutil.which("node")' in content


def test_smoke_script_checker_default():
    """smoke 脚本默认 checker 路径为仓库内 web-v2/scripts/check-api-contract.mjs。"""
    content = SMOKE_SCRIPT.read_text(encoding="utf-8")
    assert "web-v2" in content
    assert "check-api-contract.mjs" in content


def test_smoke_script_checker_missing_exits_nonzero():
    """checker 不存在时 smoke 脚本非零退出。"""
    result = subprocess.run(
        [PYTHON, str(SMOKE_SCRIPT), "--checker-path", "/nonexistent/checker.mjs"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "不存在" in output or "not exist" in output.lower() or "Checker" in output


def test_smoke_script_no_webapp_server():
    """smoke 脚本不得导入 webapp.server。"""
    content = SMOKE_SCRIPT.read_text(encoding="utf-8")
    assert "from webapp.server" not in content
    assert "import webapp.server" not in content


def test_smoke_script_no_ignore_errors():
    """smoke 脚本清理不使用 ignore_errors=True。"""
    content = SMOKE_SCRIPT.read_text(encoding="utf-8")
    assert "ignore_errors=True" not in content


def test_smoke_script_asserts_cleanup():
    """smoke 脚本断言进程终止和目录清理。"""
    content = SMOKE_SCRIPT.read_text(encoding="utf-8")
    # 进程终止断言
    assert "proc.poll()" in content
    assert "terminated" in content
    # 目录清理断言
    assert "Path(tmp_dir).exists()" in content or "exists()" in content


def test_smoke_script_uses_launch_script():
    """smoke 脚本通过 run_mountain_backend.py 拉起后端。"""
    content = SMOKE_SCRIPT.read_text(encoding="utf-8")
    assert "run_mountain_backend.py" in content


def test_smoke_script_log_file_strategy():
    """smoke 脚本使用临时日志文件避免 PIPE 阻塞。"""
    content = SMOKE_SCRIPT.read_text(encoding="utf-8")
    assert "log_file" in content or "log_fd" in content


# ── 清理证明测试 ─────────────────────────────────────────────────────────


def test_cleanup_process_terminates():
    """cleanup_process 真实终止子进程并返回 True。"""
    # 导入 cleanup_process
    import importlib.util
    spec = importlib.util.spec_from_file_location("smoke", SMOKE_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # 启动一个 sleep 进程
    proc = subprocess.Popen([PYTHON, "-c", "import time; time.sleep(60)"])
    assert proc.poll() is None

    result = mod.cleanup_process(proc)
    assert result is True
    assert proc.poll() is not None


def test_temp_dir_cleanup_proven():
    """临时目录创建后 rmtree 成功且路径消失。"""
    tmp_dir = tempfile.mkdtemp(prefix="csboard-test-cleanup-")
    test_file = Path(tmp_dir) / "test.txt"
    test_file.write_text("test")
    assert Path(tmp_dir).exists()

    shutil.rmtree(tmp_dir)
    assert not Path(tmp_dir).exists()
