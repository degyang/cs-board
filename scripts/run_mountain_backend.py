#!/usr/bin/env python3
"""Mountain Server 前台启动入口。

用法:
    python /absolute/path/to/run_mountain_backend.py [--host HOST] [--port PORT] [--data-dir DIR] [--log-level LEVEL]

默认:
    host=127.0.0.1, port=8000, data-dir=$CSBOARD_DATA_DIR 或 ~/.csboard, log-level=info

可从任意 cwd 启动：脚本自行解析仓库根目录并加入 sys.path。
仅使用 webapp.mountain_server 组合根，默认加密 SecretStore。
"""

from __future__ import annotations

import argparse
import asyncio
import os
import signal
import socket
import struct
import sys
from pathlib import Path


def _resolve_repo_root() -> Path:
    """解析仓库根目录（scripts/ 的父目录）。"""
    return Path(__file__).resolve().parents[1]


def _ensure_importable(repo_root: Path) -> None:
    """确保仓库根在 sys.path 中，使 webapp 可导入。"""
    root_str = str(repo_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def _create_listening_socket(host: str, port: int) -> socket.socket:
    """Bind the server socket with immediate-reuse shutdown semantics.

    The launcher is repeatedly started by fresh-data-dir smoke tests.  Passing
    this socket to uvicorn makes the bind lifecycle explicit and ensures a
    normal SIGTERM shutdown cannot leave recently handled localhost connections
    holding the test port in TIME_WAIT.
    """
    try:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
        listener.bind((host, port))
        listener.listen(socket.SOMAXCONN)
        return listener
    except OSError:
        print(f"错误: 端口 {port} 不可用", file=sys.stderr)
        print(f"解决: 使用 --port 指定其他端口，或终止占用 {port} 的进程", file=sys.stderr)
        sys.exit(1)


def _check_dependencies() -> None:
    """检查 uvicorn 依赖是否可用。"""
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        print("错误: uvicorn 未安装", file=sys.stderr)
        print("解决: pip install uvicorn", file=sys.stderr)
        sys.exit(1)


def _check_encryption_available() -> None:
    """检查加密依赖可用（非明文模式）。"""
    try:
        import cryptography  # noqa: F401
    except ImportError:
        print("错误: cryptography 未安装且未允许明文 Secret", file=sys.stderr)
        print("解决: pip install cryptography", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mountain Server 前台启动入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               "  python scripts/run_mountain_backend.py\n"
               "  python scripts/run_mountain_backend.py --port 9000 --log-level debug\n",
    )
    parser.add_argument("--host", default="127.0.0.1", help="绑定地址 (默认 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="端口 (默认 8000)")
    parser.add_argument("--data-dir", default=None, help="数据目录 (默认 $CSBOARD_DATA_DIR 或 ~/.csboard)")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error", "critical"],
                        help="日志级别 (默认 info)")
    args = parser.parse_args()

    # 1. 解析仓库根并确保可导入
    repo_root = _resolve_repo_root()
    _ensure_importable(repo_root)

    # 2. 设置 data-dir 环境变量（必须在导入 app 之前）
    if args.data_dir:
        os.environ["CSBOARD_DATA_DIR"] = args.data_dir

    # 3. 检查加密依赖（非明文模式）
    if os.environ.get("CSBOARD_ALLOW_PLAINTEXT_SECRETS") != "1":
        _check_encryption_available()

    # 4. 验证 app 可创建（非 None）
    try:
        from webapp.mountain_server import app  # noqa: F401
        if app is None:
            print("错误: webapp.mountain_server:app 为 None", file=sys.stderr)
            print("解决: 检查依赖是否完整安装", file=sys.stderr)
            sys.exit(1)
    except Exception:
        print("错误: 无法导入 webapp.mountain_server", file=sys.stderr)
        print("解决: 确认在仓库根目录或已正确安装依赖", file=sys.stderr)
        sys.exit(1)

    # 5. 检查 uvicorn 并创建受 launcher 管理的监听 socket
    _check_dependencies()
    listener = _create_listening_socket(args.host, args.port)

    # 6. 启动 uvicorn（传入 app 对象与已绑定 socket，避免二次导入问题）
    import uvicorn
    server = uvicorn.Server(uvicorn.Config(app, log_level=args.log_level))
    previous_sigterm = signal.getsignal(signal.SIGTERM)

    def request_graceful_shutdown(_signum, _frame) -> None:
        server.should_exit = True

    try:
        signal.signal(signal.SIGTERM, request_graceful_shutdown)
        server.config.setup_event_loop()
        asyncio.run(server._serve(sockets=[listener]))
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)
        listener.close()


if __name__ == "__main__":
    main()
