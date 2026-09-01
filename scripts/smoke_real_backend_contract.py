#!/usr/bin/env python3
"""Real backend contract smoke — 通过正式启动脚本拉起后端，验证 CCF 契约。

用法:
    python scripts/smoke_real_backend_contract.py [--port PORT] [--checker-path PATH]

自动:
    1. 创建临时 CSBOARD_DATA_DIR（默认加密模式）
    2. 通过 scripts/run_mountain_backend.py 启动 uvicorn
    3. 轮询 /api/v1/health 等待就绪
    4. 通过 HTTP 创建契约 Service
    5. 运行 CCF 生产 check-api-contract.mjs
    6. 执行 API smoke 表验证
    7. finally 终止子进程并清理临时目录（带断言证明）
"""

from __future__ import annotations

import argparse
import json
import os
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
    args = parser.parse_args()

    port = args.port or find_free_port()
    base = f"http://127.0.0.1:{port}/api/v1"
    checker_path = resolve_checker_path(args.checker_path)

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

    print(f"[smoke] 临时数据目录: {data_dir}")
    print(f"[smoke] 端口: {port}")
    print(f"[smoke] API base: {base}")
    print(f"[smoke] Checker: {checker_path}")

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

        # ── 3. 等待 health ───────────────────────────────────────────────
        print("[smoke] 等待 /api/v1/health ...")
        try:
            health = wait_for_health(base, timeout=30)
        except TimeoutError:
            # 启动失败：输出最后几行日志
            log_fd.flush()
            if log_file.exists():
                lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()[-20:]
                print(f"[smoke] 启动失败，最后 {len(lines)} 行日志:", file=sys.stderr)
                for line in lines:
                    print(f"  {line}", file=sys.stderr)
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

        safe_fields = {
            k: v for k, v in created.items()
            if k not in ("config", "required_secrets", "optional_secrets")
        }
        print(f"[smoke]   非敏感字段: {json.dumps(safe_fields, ensure_ascii=False, indent=2)}")

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

        print("[smoke] Checker stdout:")
        print(result.stdout)
        if result.stderr:
            print("[smoke] Checker stderr:")
            print(result.stderr)

        checker_output = result.stdout + result.stderr

        if result.returncode != 0:
            print(f"[smoke] ✗ Checker 失败 (exit={result.returncode})")
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
        proc = None

        if not terminated:
            print(f"[smoke] ✗ 进程 {proc_pid} 未能终止", file=sys.stderr)
            return 1
        print(f"[smoke] ✓ uvicorn 进程 (PID {proc_pid}) 已终止")

        # 关闭日志文件句柄
        log_fd.close()

        # 清理临时目录并断言
        shutil.rmtree(tmp_dir)
        if Path(tmp_dir).exists():
            print(f"[smoke] ✗ 临时目录未清理: {tmp_dir}", file=sys.stderr)
            return 1
        print(f"[smoke] ✓ 临时目录已清理: {tmp_dir}")

        print("\n[smoke] 所有检查通过 ✓")
        return 0

    except Exception as exc:
        print(f"[smoke] ✗ 异常: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    finally:
        cleanup_process(proc)
        # 清理临时目录（不使用 ignore_errors，失败时报错）
        if Path(tmp_dir).exists():
            shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    sys.exit(main())
