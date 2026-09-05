# M09-INFRA-PLAN-001-V 独立验证回执

结论：**FAIL**。未修改产品代码、测试、配置、服务或既有规划；未创建任务、未执行 real render、未启动服务。失败仅在规划依赖/派工顺序存在不可执行的环与自相矛盾，见第 3、7 项。

## 检查范围与命令

- 读取：`docs/workmates/assignments/M09-INFRA-PLAN-001.md`、两份既有 29 计划、目标执行计划、实施回执，以及相关 domain/application/adapters/repository/renderer/test 路径。
- `git status --short`、`git diff --stat`、`git diff --check`：exit 0（`git diff --check`）。未提交的 M09 代码/测试存在，但其 mtime 为 10:42–12:32；规划和实施回执为 17:44，支持规划没有引入这些产品文件的事实。
- `rg`/`nl` 静态核验了 `capabilities.py`、`commands.py`、`legacy_bridge.py`、filesystem repository/artifact store、Remotion adapter/domain 和 `video_renderer`。未运行测试，避免任何超出指定回执的写入。
- `find` 核验：没有 M09 Remotion MP4、probe JSON 或 smoke evidence；唯一已有 MP4 属于 `engine=whiteboard`（`outputs/task-02b3a76b491445bfaf594b02c75cd70e/task.json`），不能作为 M09 real-render 证据。

## 七项核验

1. **PASS** — 执行计划 §1（行 16–43）逐项区分已具备、缺失/冲突/待澄清，并明确未提交 M09 代码只是“待审实现”。静态事实吻合：`Engine.INFOGRAPHIC_REMOTION` 在 `csboard/domain/enums.py:8`；legacy 判断和 v8 投影在 `legacy_bridge.py:82,120-121`；现有 capability 的工具探测仅为 PATH/少量 Windows 路径（`capabilities.py:47-77`）。
2. **PASS** — §2（行 47–67）定义 delivery → application → domain/ports 的方向，并明确 storyboard adapter、Remotion adapter、capability、Task/API/CLI、输出/恢复、错误与 secret 脱敏责任；禁止 domain/application/adapters 反向依赖 legacy/webapp。
3. **FAIL** — P1–P6 都列出目标、边界、I/O、测试、entry/exit、证据和禁止项（行 70–125），但有序依赖图不可执行：P3 entry 要求“P2 的 renderer prerequisites”和 P6 evidence schema，P3 exit 又要求 smoke evidence（行 92–94）；P6 entry 要求 P1–P5 exit（行 115–121），其中包含 P3。因此 P3 需要 P6 evidence 才能 exit，而 P6 不能在 P3 exit 前开始。图（行 127–130）也遗漏了 P2 → P3 的明示边。
4. **PASS** — §§4、P6（行 115–121、135–139）将 Node/锁定依赖、browser、FFmpeg/ffprobe、服务 probe、图像 gate、真实非空 MP4 与 probe 设为门禁；fake E2E 和 real E2E 分层，失败保持 `supported=false`。规划 §1 明确尚无真实 MP4/probe；静态扫描亦未发现 M09 evidence，未把草案或 mock 当成 real render。
5. **PASS** — §5（行 143–147）定义 legacy 识别键、只读且不迁移的默认策略、未来迁移决策点，以及阻止 `WhiteboardRendererAdapter`/legacy import 回落的 spy、AST、路由测试。与 `legacy_bridge.py:82,94,120-121` 的现状一致。
6. **PASS** — §6（行 151–163）规定 `outputs/<task>/runs/<run>/artifacts`、artifact key/元数据、index 原子提交、状态/错误、stale/retry、evidence、清理保留及 secret/绝对路径限制，并持续禁止 WebUI submission。与 `repository.py:169`、`artifacts.py:37-69` 的现有任务包机制一致。
7. **FAIL** — §7 每张票有独立验证角色，且正确声明规划不授权实现；但 next queue 与包 gate 冲突：CAP-003 只依赖 CONTRACT-001、可与 ADAPTER-002 并行（行 171、177），而 P3 自己规定 P2 prerequisites 为 entry gate（行 94）。再加第 3 项的 P3/P6 环，表中“严格依赖/推荐顺序”不能实际满足，故不是可分派的最小队列。

## 附加只读边界核验

**PASS（规划文档范围）** — 实施回执关于未执行 real render、未开放 WebUI、且未把现存未提交 M09 代码当完成的陈述，与计划 §0–§1、静态工作树和文件时间一致。规划本身为两份 17:44 新增 Markdown；所见 M09 产品代码/测试均早于它。不存在 M09 Remotion real-render 产物或 evidence。实施回执的“115 passed”是历史自述，未在本验证中重跑或当作 real-render 证据。

精确失败定位：`docs/Mountain/29-m09-dynamic-infographic-execution-plan.md:92-94,115-121,127-130,171,177`。在消除 P3/P6 环、把 P2 → P3 与 CAP-003 的依赖关系统一前，计划不得交付为可执行 implementation queue；本结论不授权任何实现。
