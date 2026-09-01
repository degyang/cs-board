#!/usr/bin/env python3
"""Real backend contract smoke — 启动真实 uvicorn，验证 CCF 契约。

用法:
    python scripts/smoke_real_backend_contract.py [--port PORT] [--checker-path PATH]

自动:
    1. 创建临时 CSBOARD_DATA_DIR（默认加密模式）
    2. 启动 uvicorn 子进程
    3. 轮询 /api/v1/health 等待就绪
    4. 通过 HTTP 创建契约 Service
    5. 运行 CCF 生产 check-api-contract.mjs
    6. 执行 API smoke 表验证
    7. finally 终止子进程并清理临时目录
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


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


def cleanup_process(proc: subprocess.Popen | None) -> None:
    """终止子进程，确保无残留。"""
    if proc is None or proc.poll() is not None:
        return
    try:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


# ── Main ─────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Real backend contract smoke")
    parser.add_argument("--port", type=int, default=0, help="端口（0=自动选择）")
    parser.add_argument(
        "--checker-path",
        type=str,
        default=str(
            Path("/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/"
                 "mountain-assets-settings-web/web-v2/scripts/check-api-contract.mjs")
        ),
        help="CCF contract checker 绝对路径",
    )
    args = parser.parse_args()

    port = args.port or find_free_port()
    base = f"http://127.0.0.1:{port}/api/v1"
    checker_path = Path(args.checker_path)
    venv_python = "/mnt/d/workstation/projects/cs-board/.venv/bin/python"

    # ── 1. 创建临时数据目录 ──────────────────────────────────────────────
    tmp_dir = tempfile.mkdtemp(prefix="csboard-smoke-")
    data_dir = Path(tmp_dir) / "data"
    data_dir.mkdir()
    proc = None

    print(f"[smoke] 临时数据目录: {data_dir}")
    print(f"[smoke] 端口: {port}")
    print(f"[smoke] API base: {base}")

    try:
        # ── 2. 启动 uvicorn ──────────────────────────────────────────────
        env = os.environ.copy()
        env.pop("CSBOARD_ALLOW_PLAINTEXT_SECRETS", None)
        env["CSBOARD_DATA_DIR"] = str(data_dir)
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])

        uvicorn_cmd = [
            venv_python, "-m", "uvicorn",
            "webapp.mountain_server:app",
            "--host", "127.0.0.1",
            "--port", str(port),
            "--log-level", "warning",
        ]
        print(f"[smoke] 启动: {' '.join(uvicorn_cmd)}")

        proc = subprocess.Popen(
            uvicorn_cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # ── 3. 等待 health ───────────────────────────────────────────────
        print("[smoke] 等待 /api/v1/health ...")
        health = wait_for_health(base, timeout=30)
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

        # 打印非敏感字段
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

        # 确保 node 可用
        node_bin = "/home/ubuntu/.local/share/mise/installs/node/22.19.0/bin/node"
        if not Path(node_bin).exists():
            node_bin = "node"

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

        # /api/v1/services
        status, body = http_json("GET", f"{base}/services")
        ok = status == 200 and "items" in body
        smoke_results.append(("GET /services", status, ok))
        print(f"  GET /services → {status} {'✓' if ok else '✗'}")

        # /api/v1/assets/styles?kind=preset
        status, body = http_json("GET", f"{base}/assets/styles?kind=preset")
        ok = status == 200 and "items" in body
        smoke_results.append(("GET /assets/styles?kind=preset", status, ok))
        print(f"  GET /assets/styles?kind=preset → {status} {'✓' if ok else '✗'}")

        # /api/v1/settings/toolchain
        status, body = http_json("GET", f"{base}/settings/toolchain")
        ok = status == 200 and "tools" in body
        smoke_results.append(("GET /settings/toolchain", status, ok))
        print(f"  GET /settings/toolchain → {status} {'✓' if ok else '✗'}")

        # /api/v1/settings/storage
        status, body = http_json("GET", f"{base}/settings/storage")
        ok = status == 200 and "writable" in body
        smoke_results.append(("GET /settings/storage", status, ok))
        print(f"  GET /settings/storage → {status} {'✓' if ok else '✗'}")

        # /api/v1/settings/diagnostics
        status, body = http_json("GET", f"{base}/settings/diagnostics")
        ok = status == 200 and "api" in body
        smoke_results.append(("GET /settings/diagnostics", status, ok))
        print(f"  GET /settings/diagnostics → {status} {'✓' if ok else '✗'}")

        # 不存在的 API
        status, body = http_json("GET", f"{base}/nonexistent-api-404")
        ok = status == 404 and "error" in body
        smoke_results.append(("GET /nonexistent-api-404", status, ok))
        print(f"  GET /nonexistent-api-404 → {status} {'✓' if ok else '✗'}")

        print("-" * 70)
        all_ok = all(ok for _, _, ok in smoke_results)
        print(f"[smoke] API Smoke: {'ALL PASSED ✓' if all_ok else 'SOME FAILED ✗'}")

        if not all_ok:
            return 1

        # ── 7. 进程和临时目录清理 ────────────────────────────────────────
        print("\n[smoke] 清理中...")
        cleanup_process(proc)
        proc = None

        # 验证进程已终止
        if proc is not None:
            assert proc.poll() is not None, "进程未终止"

        print(f"[smoke] ✓ uvicorn 进程已终止")
        print(f"[smoke] ✓ 临时目录将由系统清理: {tmp_dir}")
        print("\n[smoke] 所有检查通过 ✓")
        return 0

    except Exception as exc:
        print(f"[smoke] ✗ 异常: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    finally:
        cleanup_process(proc)
        # 清理临时目录
        import shutil
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            print(f"[smoke] 临时目录已清理: {tmp_dir}")
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
