#!/usr/bin/env python3
"""Mountain Server 前台启动入口。

用法:
    python scripts/run_mountain_backend.py [--host HOST] [--port PORT] [--data-dir DIR] [--log-level LEVEL]

默认:
    host=127.0.0.1, port=8000, data-dir=$CSBOARD_DATA_DIR 或 ~/.csboard, log-level=info

仅使用 webapp.mountain_server 组合根，默认加密 SecretStore，不负责 daemon/浏览器/WebUI。
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import sys


def _check_port_available(host: str, port: int) -> None:
    """检查端口是否可用，不可用时给出可操作错误。"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
    except OSError as exc:
        print(f"错误: 端口 {port} 不可用 ({exc})", file=sys.stderr)
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


def _check_app_creatable(data_dir: str | None) -> None:
    """检查 webapp.mountain_server:app 可创建（非 None）。"""
    env = os.environ.copy()
    if data_dir:
        env["CSBOARD_DATA_DIR"] = data_dir
    allow_plaintext = env.get("CSBOARD_ALLOW_PLAINTEXT_SECRETS", "")
    if allow_plaintext != "1":
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

    # 不允许明文 SecretStore 时的检查
    _plaintext_env = os.environ.get("CSBOARD_ALLOW_PLAINTEXT_SECRETS", "")
    if _plaintext_env != "1":
        _check_app_creatable(args.data_dir)

    _check_dependencies()
    _check_port_available(args.host, args.port)

    # 设置 CSBOARD_DATA_DIR（如果指定）
    if args.data_dir:
        os.environ["CSBOARD_DATA_DIR"] = args.data_dir

    import uvicorn
    uvicorn.run(
        "webapp.mountain_server:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
