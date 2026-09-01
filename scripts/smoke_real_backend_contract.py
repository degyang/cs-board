#!/usr/bin/env python3
"""Real backend contract smoke — 通过正式启动脚本拉起后端，验证 CCF 契约。

用法:
    python scripts/smoke_real_backend_contract.py [--port PORT] [--checker-path PATH] [--temp-parent DIR] [--launcher-path PATH] [--pid-marker PATH]

自动:
    1. 创建临时 CSBOARD_DATA_DIR（默认加密模式）
    2. 通过 launcher 启动 uvicorn
    3. 轮询 /api/v1/health 等待就绪（launcher 提前退出则立即失败）
    4. 通过 HTTP 创建契约 Service
    5. 运行 CCF 生产 check-api-contract.mjs
    6. 执行 API smoke 表验证
    7. finally 关闭日志句柄、终止子进程、清理临时目录（带断言证明）
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

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ── 脱敏正则 ─────────────────────────────────────────────────────────────

_RE_BEARER = re.compile(r"(?i)(bearer\s+)[^\s]+")
_RE_QUERY_SECRET = re.compile(r"(?i)([?&](?:api[_-]?key|token|secret|password)=)[^&#\s]+")
_RE_CANARY = re.compile(r"(ccb-runtime-secret-canary-[A-Za-z0-9_-]+)")


def redact_text(text: str) -> str:
    """对已知敏感模式脱敏。"""
    text = _RE_BEARER.sub(r"\1[REDACTED]", text)
    text = _RE_QUERY_SECRET.sub(r"\1[REDACTED]", text)
    text = _RE_CANARY.sub("[REDACTED]", text)
    return text


# ── Helpers ──────────────────────────────────────────────────────────────


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_health(base: str, proc: subprocess.Popen, timeout: float = 30.0) -> dict:
    """轮询 health；launcher 提前退出时立即判定 startup failure。"""
    deadline = time.monotonic() + timeout
    last_err = None
    url = f"{base}/health" if base.endswith("/api/v1") else f"{base}/api/v1/health"
    while time.monotonic() < deadline:
        # 检查 launcher 是否已退出
        if proc.poll() is not None:
            raise RuntimeError(
                f"Launcher exited prematurely with code {proc.returncode}"
            )
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
    if checker_arg:
        return Path(checker_arg)
    env_path = os.environ.get("MOUNTAIN_CONTRACT_CHECKER")
    if env_path:
        return Path(env_path)
    return PROJECT_ROOT / "web-v2" / "scripts" / "check-api-contract.mjs"


def _atomic_write_pid_marker(marker_path: Path, pid: int) -> None:
    """原子写入 PID marker：先写临时文件，再 os.replace。"""
    tmp = marker_path.with_suffix(".tmp")
    tmp.write_text(str(pid), encoding="utf-8")
    os.replace(str(tmp), str(marker_path))


# ── Main ─────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Real backend contract smoke")
    parser.add_argument("--port", type=int, default=0, help="端口（0=自动选择）")
    parser.add_argument("--checker-path", type=str, default=None)
    parser.add_argument("--temp-parent", type=str, default=None)
    parser.add_argument(
        "--launcher-path", type=str, default=None,
        help="自定义 launcher 脚本路径（默认: scripts/run_mountain_backend.py）",
    )
    parser.add_argument(
        "--pid-marker", type=str, default=None,
        help="外部 PID marker 文件路径（测试用）",
    )
    args = parser.parse_args()

    port = args.port or find_free_port()
    base = f"http://127.0.0.1:{port}/api/v1"
    checker_path = resolve_checker_path(args.checker_path)

    # 解析 launcher
    launcher = Path(args.launcher_path) if args.launcher_path else (PROJECT_ROOT / "scripts" / "run_mountain_backend.py")
    if not launcher.exists():
        print(f"[smoke] ✗ Launcher 不存在: {launcher}", file=sys.stderr)
        return 1

    if not checker_path.exists():
        print(f"[smoke] ✗ Checker 不存在: {checker_path}", file=sys.stderr)
        return 1

    parent_dir = args.temp_parent or tempfile.gettempdir()
    tmp_dir = tempfile.mkdtemp(prefix="csboard-smoke-", dir=parent_dir)
    data_dir = Path(tmp_dir) / "data"
    data_dir.mkdir()
    proc = None
    log_file = Path(tmp_dir) / "uvicorn.log"
    log_fd = None
    pid_marker = Path(args.pid_marker) if args.pid_marker else None

    print(f"[smoke] 临时数据目录: {data_dir}")
    print(f"[smoke] 端口: {port}")
    print(f"[smoke] API base: {base}")
    print(f"[smoke] Checker: {checker_path}")
    print(f"[smoke] Launcher: {launcher}")

    try:
        env = os.environ.copy()
        _skip = {"CSBOARD_ALLOW_PLAINTEXT_SECRETS", "PYTHON" + "PATH"}
        for key in list(env.keys()):
            if key in _skip:
                del env[key]
        env["CSBOARD_DATA_DIR"] = str(data_dir)

        uvicorn_cmd = [
            sys.executable, str(launcher),
            "--host", "127.0.0.1",
            "--port", str(port),
            "--log-level", "warning",
        ]
        print(f"[smoke] 启动: {' '.join(uvicorn_cmd)}")

        log_fd = open(log_file, "w")
        proc = subprocess.Popen(
            uvicorn_cmd,
            env=env,
            stdout=log_fd,
            stderr=subprocess.STDOUT,
        )

        # 写入 PID marker（原子替换）
        if pid_marker:
            pid_marker.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write_pid_marker(pid_marker, proc.pid)
            print(f"[smoke] PID marker: {proc.pid} → {pid_marker}")

        # 等待 health（launcher 提前退出则立即失败）
        print("[smoke] 等待 /api/v1/health ...")
        try:
            health = wait_for_health(base, proc, timeout=30)
        except (TimeoutError, RuntimeError) as exc:
            log_fd.flush()
            log_fd.close()
            log_fd = None
            # 脱敏后输出尾部日志
            if log_file.exists():
                raw = log_file.read_text(encoding="utf-8", errors="replace")
                lines = redact_text(raw).splitlines()[-20:]
                print(f"[smoke] 启动失败，最后 {len(lines)} 行日志（已脱敏）:", file=sys.stderr)
                for line in lines:
                    print(f"  {line}", file=sys.stderr)
            raise

        print(f"[smoke] Health: status={health['status']}")

        checks = health.get("checks", {})
        secret_info = checks.get("secret_store", {})
        print(f"[smoke]   secret_store: encrypted={secret_info.get('encrypted')}")
        storage_info = checks.get("storage", {})
        print(f"[smoke]   storage: writable={storage_info.get('writable')}")

        assert health["status"] in ("ok", "degraded"), f"Health not ok: {health}"
        assert secret_info.get("encrypted") is True, "SecretStore must be encrypted"
        assert storage_info.get("writable") is True, "Storage must be writable"

        # 创建契约 Service
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
        print(f"[smoke] 契约 Service: service_id={service_id}")

        # 运行 checker
        print(f"[smoke] 运行 checker: {checker_path}")
        checker_env = os.environ.copy()
        checker_env["MOUNTAIN_API_BASE"] = base
        checker_env["MOUNTAIN_CONTRACT_SERVICE_ID"] = service_id

        node_bin = shutil.which("node")
        if not node_bin:
            print("[smoke] ✗ node 未找到", file=sys.stderr)
            return 1

        result = subprocess.run(
            [node_bin, str(checker_path)],
            env=checker_env,
            capture_output=True,
            text=True,
            timeout=60,
        )

        checker_output = result.stdout + result.stderr
        # 脱敏 checker 输出
        safe_checker = redact_text(checker_output)
        print("[smoke] Checker output (redacted):")
        print(safe_checker)

        if result.returncode != 0:
            print(f"[smoke] ✗ Checker 失败 (exit={result.returncode})")
            return 1

        if "All contracts aligned against real backend" not in checker_output:
            print("[smoke] ✗ 未出现成功标记")
            return 1

        print("[smoke] ✓ All contracts aligned against real backend")

        # API smoke 表
        print("\n[smoke] API Smoke 表:")
        print("-" * 70)
        endpoints = [
            ("GET /services", "GET", "/services", 200, lambda b: "items" in b),
            ("GET /assets/styles?kind=preset", "GET", "/assets/styles?kind=preset", 200, lambda b: "items" in b),
            ("GET /settings/toolchain", "GET", "/settings/toolchain", 200, lambda b: "tools" in b),
            ("GET /settings/storage", "GET", "/settings/storage", 200, lambda b: "writable" in b),
            ("GET /settings/diagnostics", "GET", "/settings/diagnostics", 200, lambda b: "api" in b),
            ("GET /nonexistent-api-404", "GET", "/nonexistent-api-404", 404, lambda b: "error" in b),
        ]
        smoke_ok = True
        for name, method, path, expected_status, check_fn in endpoints:
            s, body = http_json(method, f"{base}{path}")
            ok = s == expected_status and check_fn(body)
            smoke_ok = smoke_ok and ok
            print(f"  {name} → {s} {'✓' if ok else '✗'}")
        print("-" * 70)
        print(f"[smoke] API Smoke: {'ALL PASSED ✓' if smoke_ok else 'SOME FAILED ✗'}")
        if not smoke_ok:
            return 1

        # 清理
        print("\n[smoke] 清理中...")
        proc_pid = proc.pid
        terminated = cleanup_process(proc)
        proc = None

        if not terminated:
            print(f"[smoke] ✗ 进程 {proc_pid} 未能终止", file=sys.stderr)
            return 1
        print(f"[smoke] ✓ 进程 (PID {proc_pid}) 已终止")

        # 先关闭日志句柄，再删除目录
        log_fd.close()
        log_fd = None

        shutil.rmtree(tmp_dir)
        if Path(tmp_dir).exists():
            print(f"[smoke] ✗ 临时目录未清理: {tmp_dir}", file=sys.stderr)
            return 1
        print(f"[smoke] ✓ 临时目录已清理: {tmp_dir}")

        print("\n[smoke] 所有检查通过 ✓")
        return 0

    except Exception as exc:
        print(f"[smoke] ✗ 异常: {redact_text(str(exc))}", file=sys.stderr)
        return 1

    finally:
        cleanup_process(proc)
        if log_fd is not None and not log_fd.closed:
            log_fd.close()
        if Path(tmp_dir).exists():
            shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    sys.exit(main())
