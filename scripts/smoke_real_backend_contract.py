#!/usr/bin/env python3
"""Real backend contract smoke — 通过正式启动脚本拉起后端，验证 CCF 契约。

用法:
    python scripts/smoke_real_backend_contract.py [--port PORT] [--checker-path PATH] [--pid-marker FILE]

自动:
    1. 创建临时 CSBOARD_DATA_DIR（默认加密模式）
    2. 通过 scripts/run_mountain_backend.py 启动 uvicorn
    3. 轮询 /api/v1/health 等待就绪
    4. 通过 HTTP 创建契约 Service
    5. 运行 CCF 生产 check-api-contract.mjs
    6. 执行 API smoke 表验证
    7. finally 终止子进程并清理临时目录（带断言证明）

PID 观测:
    --pid-marker FILE  启动成功后将 PID 写入该文件（位于 smoke 临时目录之外）。
                       smoke 不负责删除调用者提供的 marker。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ── Redaction ────────────────────────────────────────────────────────────

_BEARER = re.compile(r"(?i)(bearer\s+)[^\s]+")
_QUERY_SECRET = re.compile(r"(?i)([?&](?:api[_-]?key|token|secret|password)=)[^&#\s]+")
_SECRET_VALUE = re.compile(r"(ccb-runtime-secret-canary-[A-Za-z0-9_-]+)")


def redact_text(text: str) -> str:
    """对文本进行脱敏：Bearer token、query secret、已知 canary。"""
    text = _BEARER.sub(r"\1[REDACTED]", text)
    text = _QUERY_SECRET.sub(r"\1[REDACTED]", text)
    text = _SECRET_VALUE.sub("[REDACTED]", text)
    return text


# ── Helpers ──────────────────────────────────────────────────────────────


def find_free_port() -> int:
    """获取一个未占用的端口。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_health(base: str, timeout: float = 30.0) -> dict:
    """轮询 /api/v1/health 直到就绪或超时。"""
    deadline = time.monotonic() + timeout
    last_err = None
    url = f"{base}/health" if base.endswith("/api/v1") else f"{base}/api/v1/health"
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


def http_json(method: str, url: str, data: dict | None = None) -> tuple[int, dict]:
    """发送 HTTP 请求并返回 (status, body)。"""
    body_bytes = json.dumps(data).encode() if data else None
    req = urllib.request.Request(
        url,
        data=body_bytes,
        method=method,
        headers={"Content-Type": "application/json"} if body_bytes else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def cleanup_process(proc: subprocess.Popen | None) -> bool:
    """终止子进程，返回是否成功终止。"""
    if proc is None:
        return True
    if proc.poll() is not None:
        return True
    try:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
    return proc.poll() is not None


def resolve_checker_path(checker_arg: str | None) -> Path:
    """解析 checker 路径：参数 > 环境变量 > 仓库默认。"""
    if checker_arg:
        return Path(checker_arg)

    env_path = os.environ.get("MOUNTAIN_CONTRACT_CHECKER")
    if env_path:
        return Path(env_path)

    # 仓库内默认路径
    default = PROJECT_ROOT / "web-v2" / "scripts" / "check-api-contract.mjs"
    return default


def write_pid_marker(path: Path, pid: int) -> None:
    """原子写入 PID marker 文件。"""
    path.write_text(str(pid), encoding="utf-8")


def read_pid_marker(path: Path) -> int | None:
    """读取 PID marker，返回 PID 或 None。"""
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def pid_alive(pid: int) -> bool:
    """检查 PID 是否仍存活。"""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# ── Lifecycle result ─────────────────────────────────────────────────────

class LifecycleResult:
    """smoke 生命周期结果，供调用方断言。"""
    def __init__(self) -> None:
        self.spawned = False
        self.pid: int | None = None
        self.terminated = False
        self.tmp_dir_cleaned = False
        self.returncode: int = 0


# ── Main ─────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Real backend contract smoke")
    parser.add_argument("--port", type=int, default=0, help="端口（0=自动选择）")
    parser.add_argument(
        "--checker-path",
        type=str,
        default=None,
        help="CCF contract checker 路径（默认: 仓库内 web-v2/scripts/check-api-contract.mjs）",
    )
    parser.add_argument(
        "--pid-marker",
        type=str,
        default=None,
        help="外部 PID marker 文件路径（位于 smoke 临时目录之外）",
    )
    args = parser.parse_args()

    port = args.port or find_free_port()
    base = f"http://127.0.0.1:{port}/api/v1"
    checker_path = resolve_checker_path(args.checker_path)
    pid_marker = Path(args.pid_marker) if args.pid_marker else None

    # 验证 checker 存在
    if not checker_path.exists():
        print(f"[smoke] ✗ Checker 不存在: {checker_path}", file=sys.stderr)
        print(f"[smoke] 解决: 确认 CCF worktree 已检出，或使用 --checker-path 指定路径", file=sys.stderr)
        return 1

    # ── 1. 创建临时数据目录 ──────────────────────────────────────────────
    tmp_dir = tempfile.mkdtemp(prefix="csboard-smoke-")
    data_dir = Path(tmp_dir) / "data"
    data_dir.mkdir()
    proc = None
    log_file = Path(tmp_dir) / "uvicorn.log"
    lifecycle = LifecycleResult()

    print(f"[smoke] 临时数据目录: {data_dir}")
    print(f"[smoke] 端口: {port}")
    print(f"[smoke] API base: {base}")
    print(f"[smoke] Checker: {checker_path}")
    if pid_marker:
        print(f"[smoke] PID marker: {pid_marker}")

    try:
        # ── 2. 通过正式启动脚本拉起后端 ──────────────────────────────────
        env = os.environ.copy()
        env.pop("CSBOARD_ALLOW_PLAINTEXT_SECRETS", None)
        env.pop("PYTHONPATH", None)
        env["CSBOARD_DATA_DIR"] = str(data_dir)

        launch_script = PROJECT_ROOT / "scripts" / "run_mountain_backend.py"
        uvicorn_cmd = [
            sys.executable, str(launch_script),
            "--host", "127.0.0.1",
            "--port", str(port),
            "--log-level", "warning",
        ]
        print(f"[smoke] 启动: {' '.join(uvicorn_cmd)}")

        # 使用临时日志文件避免 PIPE 阻塞
        log_fd = open(log_file, "w")
        proc = subprocess.Popen(
            uvicorn_cmd,
            env=env,
            stdout=log_fd,
            stderr=subprocess.STDOUT,
        )
        lifecycle.spawned = True
        lifecycle.pid = proc.pid

        # 写入外部 PID marker
        if pid_marker:
            write_pid_marker(pid_marker, proc.pid)

        # ── 3. 等待 health ───────────────────────────────────────────────
        print("[smoke] 等待 /api/v1/health ...")
        try:
            health = wait_for_health(base, timeout=30)
        except TimeoutError:
            # 启动失败：输出最后几行日志（脱敏后）
            log_fd.flush()
            if log_file.exists():
                lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()[-20:]
                print(f"[smoke] 启动失败，最后 {len(lines)} 行日志:", file=sys.stderr)
                for line in lines:
                    print(f"  {redact_text(line)}", file=sys.stderr)
            raise

        print(f"[smoke] Health: status={health['status']}")

        checks = health.get("checks", {})
        secret_info = checks.get("secret_store", {})
        print(f"[smoke]   secret_store: encrypted={secret_info.get('encrypted')}")
        storage_info = checks.get("storage", {})
        print(f"[smoke]   storage: writable={storage_info.get('writable')}")
        registry_info = checks.get("service_registry", {})
        print(f"[smoke]   service_registry: status={registry_info.get('status')}")

        assert health["status"] in ("ok", "degraded"), f"Health not ok: {health}"
        assert secret_info.get("encrypted") is True, "SecretStore must be encrypted"
        assert storage_info.get("writable") is True, "Storage must be writable"

        # ── 4. 创建契约 Service ──────────────────────────────────────────
        service_payload = {
            "service_id": "contract-test-svc",
            "display_name": "契约测试服务",
            "capability": "speech_synthesis",
            "adapter_type": "openai_compatible",
            "endpoint": "https://example.invalid/v1",
            "model": "test-model",
            "enabled": True,
            "priority": 100,
            "required_secrets": ["api_key"],
            "optional_secrets": [],
            "config": {"timeout": 30},
        }

        status, created = http_json("POST", f"{base}/services", service_payload)
        assert status == 200, f"Create service failed: {status} {created}"
        service_id = created["service_id"]
        print(f"[smoke] 契约 Service 创建成功: service_id={service_id}")

        # ── 5. 运行 CCF 生产 checker ────────────────────────────────────
        print(f"[smoke] 运行 CCF contract checker: {checker_path}")

        checker_env = os.environ.copy()
        checker_env["MOUNTAIN_API_BASE"] = base
        checker_env["MOUNTAIN_CONTRACT_SERVICE_ID"] = service_id

        # 使用 shutil.which 查找 node
        node_bin = shutil.which("node")
        if not node_bin:
            print("[smoke] ✗ node 未找到，请确保 Node.js 已安装并在 PATH 中", file=sys.stderr)
            return 1

        checker_cmd = [node_bin, str(checker_path)]
        result = subprocess.run(
            checker_cmd,
            env=checker_env,
            capture_output=True,
            text=True,
            timeout=60,
        )

        checker_output = result.stdout + result.stderr

        # 脱敏后输出
        print("[smoke] Checker stdout (redacted):")
        print(redact_text(result.stdout))
        if result.stderr:
            print("[smoke] Checker stderr (redacted):")
            print(redact_text(result.stderr))

        if result.returncode != 0:
            print(f"[smoke] ✗ Checker 失败 (exit={result.returncode})")
            lifecycle.returncode = result.returncode
            return 1

        if "All contracts aligned against real backend" not in checker_output:
            print("[smoke] ✗ 未出现 'All contracts aligned against real backend'")
            return 1

        print("[smoke] ✓ All contracts aligned against real backend")

        # ── 6. API smoke 表 ──────────────────────────────────────────────
        print("\n[smoke] API Smoke 表:")
        print("-" * 70)

        smoke_results = []

        endpoints = [
            ("GET /services", "GET", "/services", 200, lambda b: "items" in b),
            ("GET /assets/styles?kind=preset", "GET", "/assets/styles?kind=preset", 200, lambda b: "items" in b),
            ("GET /settings/toolchain", "GET", "/settings/toolchain", 200, lambda b: "tools" in b),
            ("GET /settings/storage", "GET", "/settings/storage", 200, lambda b: "writable" in b),
            ("GET /settings/diagnostics", "GET", "/settings/diagnostics", 200, lambda b: "api" in b),
            ("GET /nonexistent-api-404", "GET", "/nonexistent-api-404", 404, lambda b: "error" in b),
        ]

        for name, method, path, expected_status, check_fn in endpoints:
            status, body = http_json(method, f"{base}{path}")
            ok = status == expected_status and check_fn(body)
            smoke_results.append((name, status, ok))
            print(f"  {name} → {status} {'✓' if ok else '✗'}")

        print("-" * 70)
        all_ok = all(ok for _, _, ok in smoke_results)
        print(f"[smoke] API Smoke: {'ALL PASSED ✓' if all_ok else 'SOME FAILED ✗'}")

        if not all_ok:
            return 1

        # ── 7. 进程和临时目录清理 ────────────────────────────────────────
        print("\n[smoke] 清理中...")
        proc_pid = proc.pid
        terminated = cleanup_process(proc)
        lifecycle.terminated = terminated
        proc = None

        if not terminated:
            print(f"[smoke] ✗ 进程 {proc_pid} 未能终止", file=sys.stderr)
            return 1
        print(f"[smoke] ✓ uvicorn 进程 (PID {proc_pid}) 已终止")

        # 关闭日志文件句柄
        log_fd.close()

        # 清理临时目录并断言
        shutil.rmtree(tmp_dir)
        lifecycle.tmp_dir_cleaned = not Path(tmp_dir).exists()
        if not lifecycle.tmp_dir_cleaned:
            print(f"[smoke] ✗ 临时目录未清理: {tmp_dir}", file=sys.stderr)
            return 1
        print(f"[smoke] ✓ 临时目录已清理: {tmp_dir}")

        print("\n[smoke] 所有检查通过 ✓")
        lifecycle.returncode = 0
        return 0

    except Exception as exc:
        redacted_msg = redact_text(str(exc))
        print(f"[smoke] ✗ 异常: {redacted_msg}", file=sys.stderr)
        lifecycle.returncode = 1
        return 1

    finally:
        cleanup_process(proc)
        # 清理临时目录
        if Path(tmp_dir).exists():
            shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    sys.exit(main())
