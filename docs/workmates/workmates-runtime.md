# Workmates 项目运行入口

## For future agent

2026-09-06 后续重配置：当前团队以 [team-setup.md](team-setup.md) 为准。PM、frontend、backend、verification 四角色；前后端独立 worktree，测试使用 Claude Code。新 shell 会话为 `cs-board-team`。下文首次部署记录保留供审计，旧 application 单 owner 和旧会话不能当作新团队配置。

2026-09-06 部署。配置源在 EnvOps `Projects/cs-board/`，技能源在 POS `00-System/Skills/skills-pos-workmates/`。项目里的 config、agent、topology 与技能目录通过映射软链使用源文件。不要把本机链接删除提交成源文件删除。

产品需求继续读 `docs/Mountain/README.md` 和已有 `docs/workmates/team-contract.md`、`board.md`；本次仅部署并验证协作运行工具，不推进旧看板产品任务。

## 使用

集成环境统一使用项目根的数据契约：配置与菜单资产在 `settings/`，任务、索引、临时文件和结果在 `outputs/`。`/tmp/csboard-*` 只用于测试夹具，不得作为 8000 长期数据源；`~/.csboard` 与仓库旧产品 dot 目录已迁入 `archive/legacy-runtime/`。启动后检查 `/api/v1/services` 中用户服务仍存在、secret status 未丢失，并核对 `/api/v1/voice-profiles`。当前固定基线见 `team-setup.md`。

从项目目录执行：

```bash
./scripts/workmates check
./scripts/tmux_start --dry-run
./scripts/tmux_start --session cs-board-team
./scripts/tmux_start --session cs-board-team --resume
./scripts/workmates status --session cs-board-team
./scripts/workmates verify --role verification --evidence /tmp/cs-board-workmates-evidence.json
```

证据文件必须不存在；输出路径由本轮任务选择。verify 的成功只证明指定命令通过，产品验收仍需原任务标准。当前入口运行已有 release guard 与 runtime paths 测试，不调用图片/TTS API，也不声称视频生成通过。

## 终端保留与回收（项目试行）

- 固定角色 `frontend`、`backend`、`verification` 的真实客户端在任务完成后进入 `idle`，默认保留 30 分钟；期间若有同角色后续任务，优先继续使用，避免重复冷启动、授权和上下文加载。
- 固定角色只有在连续空闲至少 30 分钟、没有已分配或可立即领取的同角色任务、没有权限/编辑确认等待、且回执已被 PM 消费后才回收。PID 存活或出现提示符本身都不足以判断可回收。
- 一次性诊断、临时 gate、非固定角色和已失效/重复客户端在任务完成并核对回执后立即回收；不会为了保留窗口而留下额外 shell。
- 产品服务窗口按已记录的进程和端口归属管理，不因没有交互输入而视为空闲。回收只针对已现场核实的精确 pane/window/PID，不触碰用户附着的其他 session。
- 回收前记录角色、任务、最后有效活动、回执状态和判定时间；未满足条件时保持 `idle`，不在“立即销毁”和“空壳常驻”之间反复切换。

需要真实 Codex worker 时，先创建项目内任务文件，再检查和启动：

```bash
./scripts/workmates launch --session cs-board-team --role frontend --assignment docs/workmates/assignments/TASK.md --dry-run
./scripts/workmates launch --session cs-board-team --role frontend --assignment docs/workmates/assignments/TASK.md
```

`TASK.md` 是调用示例，必须替换为真实任务文件。launch 使用新窗口，保留原 shell，不向已有会话输入任务。当前自动启动只支持 Codex；Claude 角色仍可人工启动，不使用旧 launcher 的权限绕过默认。

## 角色与范围

- `pm` 维护共享看板与集成；`frontend`、`backend` 为独立产品写入 owner，使用新建工作树。模型固定 Codex `gpt-5.6-terra / medium`。
- `verification` 使用 Claude Code `mimo-v2.5-pro / medium` 做独立代码、视觉/行为与证据验证。允许指定测试缓存和新回执；role 的 read-only 是实现权限声明，实际隔离须核对客户端有效权限。CC 当前需按 team-setup 中的显式新窗口流程启动。
- 已为前后端各建独立 worktree，default/frontend/backend/verify profile 可按任务选择；依赖安装和产品服务启动由后续任务完成，不复用归档 worktree 当作当前实现基线。
- `requires_roles` 只表示需要同时运行的角色；产品任务先后依赖仍在现有看板。
- 旧运行文档中的 coordination/systemd 目录当前不存在，不能据其文字认定旧 PM 仍在线。

## 配置维护

```bash
python3 ~/dotfiles/scripts/project-links.py --source ~/dotfiles/Projects/cs-board --target ~/Projects/cs-board --apply
```

此入口只部署缺失映射，不克隆、清理或更新仓库。用户模型、推理和权限默认保持原样；项目只明确开启 multi_agent 能力，是否委派仍遵循实际任务与运行时授权。

稳定规则：秘密不进入任务证据；配置存在不代表有效权限；未运行的验证必须报告未验证。需要具体验证流程时用 `pos-workmates-verify`，需要调度用 `pos-workmates-core`。共享看板由协调者更新，执行者只写自己的回执。
