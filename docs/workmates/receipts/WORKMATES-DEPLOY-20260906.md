# Workmates 部署验收回执

## For future agent

2026-09-06，本次任务实现 POS Workmates 的配置驱动工具，并部署到 cs-board。用户要求配置先进入 EnvOps 映射目录，再软链到项目。本回执只验收协作工具接入，不推进旧产品看板或宣称视频生产链完成。

## 配置归属

- 通用技能与 runner：POS `00-System/Skills/skills-pos-workmates/`。
- 项目配置、AGENTS 入口、认知 agent、topology 与包装入口：EnvOps `Projects/cs-board/`。
- `.managed-files` 通过 EnvOps `scripts/project-links.py` 映射到本项目；13 项映射检查为 linked。
- 用户 `config.toml` 未修改，模型、推理与权限沿用已有默认。项目只明确启用 multi_agent。
- 本机映射链接及 `.workmates-runtime/` 加入 Git 本地 exclude。该仓库的 worktree 共享 exclude；不影响已跟踪文件，不提交本机链接到产品仓库。

## 实现与验证

| 验收项 | 实际证据 | 结果 |
| --- | --- | --- |
| 配置驱动与独立工作区检查 | core `scripts/test_workmates.py -v`：15 tests，全部通过 | PASS |
| 安全映射与重复部署 | EnvOps `scripts/test_project_links.py -v`：4 tests，全部通过 | PASS |
| 四技能结构与链接 | quick_validate 四个入口通过；相对文档链接检查 | PASS |
| 项目启动与恢复 | `scripts/tmux_start --session cs-board-workmates` 后 `--resume` 返回相同 role/pane | PASS |
| 当前客户端发现 | Codex CLI 0.153.4 的独立只读 exec 会话确认四个 skill 与四个 wm_* custom agent 已暴露 | PASS |
| 项目真实验证命令 | `.venv/bin/python -m pytest -q tests/test_workmates_release_guard.py tests/test_runtime_paths.py` | 12 passed，0.58s，exit 0 |

项目验证在 `cs-board-workmates` 的 `deployment-evidence` tmux 窗口执行。原始证据位于本机 `.workmates-runtime/deployment-verification.json`，记录 UTC 04:09:26–04:09:31、argv、退出码、输出、代码状态及配置摘要。目标 HEAD 前后均为 `e34ba6e83ef1a6c3ec3ad5274485505379ce0a21`。

源码标识（未提交改动，以哈希识别）：

- `workmates.py` SHA256：`7cf114766766bee96c01dcab7be23ec137bb18c18dba80b559a80b3a0769e898`
- `project-links.py` SHA256：`668688863689d7909abf57b256575c754b38e5f97d9de2fb269214a0a6c8a9e7`

## 覆盖边界

- launch 的窗口与输入保留测试使用测试替身，不声称启动了真实产品 worker。真实 Codex CLI 发现测试是短暂只读会话，已退出；四类子代理未逐个执行任务。
- 当前 session 保留 application、verification shell 和证据窗口，没有模型 agent 常驻。status 明确显示 zsh，不把它们计作在线 agent。
- config/role/write_scope 声明不等于 OS 隔离。资源冲突检查只检查声明，不代替实际服务健康检查。
- 当前自动 launch 支持 Codex，Claude 需显式人工启动。macOS 与 Windows 原生未实测；本次为 Linux/WSL。
- 未运行完整产品后端/前端/E2E 门禁，未调用图片/TTS/视频服务，未修改旧业务任务或验收标准。
- 未修改既有 main、worker tmux 会话，未提交或推送任何仓库。

## 交付

协作工具部署与本地验证通过。后续从项目目录启动 Codex，可通过 `$pos-workmates-core` 派发真实有界任务；初始化/重配置用 `$pos-workmates-bootstrap`。操作入口见 `docs/workmates/workmates-runtime.md`。
