# MEDIA-PREFLIGHT-004：真实媒体依赖 fail-closed 预检

- Owner: MEDIA
- Status: REVIEW_READY
- Priority: P0
- Depends on: `MEDIA-SKILLS-003=APPROVED`
- Worktree: `/mnt/d/workstation/projects/cs-board-media`
- Branch: `feat/mountain-media-work-orders`
- Base commit: `6fc2924ee82442d49aa61dfe6c9893709f417832`

## Goal

在不运行六阶段链、不生成付费内容的前提下，为后续 `MEDIA-E2E-003` 建立机器可运行的真实 preflight：
检查 FFmpeg/ffprobe、Node/Whisper 本地入口、配置的 IndexTTS/Whisper 服务、所需模型/目录和临时工件目录，
明确区分 ready/unavailable/misconfigured，并在必需依赖缺失、无响应或输出不可写时 fail closed、清理干净。
同时确认当前 Codex Worker 能访问项目七个 Skills 与 Codex image generation 能力，冻结后续人工
`generate-illustrations` gate 的唯一图片生成路径；本任务不实际生成图片。

## Allowed surfaces

- 新增 `scripts/check_media_preflight.py` 或等价单一 CLI，以及必要的纯 helper；
- `tests/` 中聚焦真实 subprocess、受控本地 HTTP 服务、配置/模型路径、临时工件和清理的测试；
- 只有预检无法通过既有公开接口实现时，才可最小修改 `csboard/runtime/toolchain.py`、
  `csboard/application/service_resolver.py` 或媒体 adapter 的 probe/cleanup 边界，报告必须给出复现；
- `docs/agents/reports/MEDIA-PREFLIGHT-004.md` 和 ignored runtime 下的脱敏 JSON 结果。

## Forbidden surfaces

- `web-v2`、backend API/DTO、Stage Work Order、stage run/retry、Pipeline 编排或 `MEDIA-E2E-003`；
- 实际 TTS 合成、Whisper 转写、imagegen/LLM 调用、渲染或视频合成；自动启动/停止用户的外部服务；
- Fake/placeholder 作为最终 live 可用性证据，联网安装依赖，或把 Secret、完整 URL 凭据、用户素材、
  绝对用户路径写入日志/报告；
- 将 unavailable 降级为 warning 后 exit 0，依赖测试 timeout/skip，或遗留 HTTP server、child、临时文件。

## Acceptance

1. 单一 CLI 输出稳定、脱敏、机器可读 JSON，并以进程退出码表达整体 readiness；必需项 unavailable、
   timeout、版本命令失败、模型/入口缺失、目录不可写均非零退出；
2. 对实际解析到的 `ffmpeg`、`ffprobe`、`node` 执行有界只读版本子进程；验证可执行文件与所需
   renderer/alignment 入口真实存在，不以 `shutil.which()` 单独冒充可运行；
3. 对持久化配置中启用的 IndexTTS/Whisper 服务执行有界健康/元数据探测，只发送无素材的只读请求；
   required/optional 配置、连接拒绝、silent server、HTTP 4xx/5xx、畸形响应形成明确 reason code；
4. 模型/工作目录只验证存在、类型、可读/可写和安全边界；preflight 在独立临时目录完成原子
   write→rename→readback→cleanup，失败注入后也无 staging/partial 残留；
5. 测试使用真实本地子进程与受控 HTTP server 同时证明 ready exit 0 和各类 fail-closed 非零退出，断言
   child `signal=null` 或明确清理路径；外层 watchdog 只能清理失败测试，不能作为成功判据；
6. 在当前机器实际运行 live preflight 并记录每项 ready/unavailable 与版本摘要。若外部服务当前未启动，
   如实保留 nonzero readiness 结果，但只要检测器的正负门禁均通过可进入评审；`MEDIA-E2E-003` 在 live
   readiness 全绿前仍不得派发；
7. 实际 Codex Worker 会话必须确认七个项目 `SKILL.md` 可读、`validate_skill_contracts.py` 正常退出，
   且会话暴露 Codex image generation 能力；报告记录能力名称和后续人工调用/gate 边界，不调用生成，
   不允许配置脚本、Fake/PIL 或其他 provider 作为 `generate-illustrations` 替代路径；
8. 报告不得包含 Secret 值、Authorization、完整用户路径或素材；清理后无 preflight HTTP/Node/Python
   child、监听端口或临时工件残留。

## Gates

```bash
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q tests/test_media_preflight.py
/mnt/d/workstation/projects/cs-board/.venv/bin/python scripts/validate_skill_contracts.py
/mnt/d/workstation/projects/cs-board/.venv/bin/python scripts/check_media_preflight.py --json
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
git diff --check 6fc2924...HEAD
! rg -n 'Authorization|api[_-]?key\s*[:=]\s*[^[:space:]]{8}|/home/|/mnt/|/tmp/' \
  docs/agents/reports/MEDIA-PREFLIGHT-004.md
```

第二个 live gate 的 nonzero 只表示环境 readiness 尚未满足，必须原样记录 reason code；不得把它改写成
检测器失败。聚焦测试、全量测试、diff 和脱敏门禁必须正常 exit 0 且无 skip。

## Stop condition

提交并推送当前 MEDIA 分支，报告给出实现门禁与 live readiness 两类结果并清理所有 probe 资源；置为
`REVIEW_READY` 后通知 PM。不得自行批准、启动外部服务或进入 `MEDIA-E2E-003`。

本任务只为 `docs/agents/milestone-m1-manual-skills-closure.md` 的人工闭环做前置验证，不授权自动或
selective 编排。

## Review handoff

- Implementation: `d9f3a41`
- Delivery: `8532302`
- Report: `docs/agents/reports/MEDIA-PREFLIGHT-004.md`
- State: `REVIEW_READY`

stale recovery 已核验 MEDIA 分支与远端一致、工作树干净且报告已提交；本节只恢复已完成的 Worker
handoff，不代表 CEO 批准。live readiness 仍为非零环境结果，`MEDIA-E2E-003` 不得派发。
