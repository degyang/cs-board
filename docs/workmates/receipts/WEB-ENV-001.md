---
ticket: WEB-ENV-001
role: worker_env
status: PASS
timestamp: 2026-09-05T17:10+08:00
---

# WEB-ENV-001 — 5182 单实例部署验收回执

## 后端 8000

| 项目 | 值 |
| --- | --- |
| PID | 678187 |
| 监听 | `0.0.0.0:8000` (single instance) |
| 命令行 | `.venv/bin/python scripts/run_mountain_backend.py --host 127.0.0.1 --port 8000 --data-dir /tmp/csboard-main-manual-20260905 --log-level info` |
| Python | 项目 `.venv` → `/home/ubuntu/.local/share/mise/installs/python/3.12.14/bin/python3.12` |
| `/api/v1/health` | HTTP 200 `{"status":"ok"}` |
| 启动日志 | `/tmp/csboard-logs/backend-8000.log` |

## 前端 5182

| 项目 | 值 |
| --- | --- |
| PID | 702514 |
| 监听 | `0.0.0.0:5182` (single instance) |
| 命令行 | `node ./node_modules/vite/bin/vite.js --host 0.0.0.0 --port 5182 --strictPort --force` |
| cwd | `/mnt/d/Workstation/Projects/cs-board/web-v2` |
| 根页面 `/` | HTTP 200 |
| `/settings/voice-alignment` | HTTP 200 |
| 启动日志 | `/tmp/cs-board-web-v2-vite.log` |

## 验证总结

- 8000 单进程(PID 678187 不变)、5182 单进程(PID 更新为 702514)，无叠加版本。
- 三个端点均 HTTP 200。
- 模块验证：`VoiceAlignmentPage.tsx` 已包含 `isWhisperService` 和 `local-whisper`（WEB-LOCAL-003 source 变更后重启生效）。
- 未修改产品代码，未创建第二套服务，未提交。
