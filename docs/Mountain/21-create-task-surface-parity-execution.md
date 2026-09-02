# M07 WebUI 新建任务表面对齐执行单

## 1. 当前结论

`docs/Mountain/20-task-queue-surface-parity-execution.md` 已通过最终验收。真实验收后端当时为 0 个 Task，因此三张队列证据如实覆盖全量空态、失败筛选空态和待执行筛选空态；mixed 数据的浏览器证据暂缺，但其 DTO、筛选和渲染行为已有自动化测试覆盖。

本文件是 CCF 下一项工作的唯一需求来源。实现范围仅限新建任务页，不进入任务工作台，不修改 Python 后端。

## 2. 工作目录与基线

- 工作目录：`/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-webui-surface-parity`
- 分支：`feat/mountain-webui-surface-parity`
- 开始前：`git pull --ff-only`
- 产品原型：`prototypes/webui/src/pages/CreateProjectPage.tsx`
- 生产页面：`web-v2/src/pages/CreateTaskPage.tsx`
- 真实 API：`POST /api/v1/tasks`、`POST /api/v1/tasks/{task_id}/inputs`

原型中的 `Project/project_id/project.save` 是旧语义和 mock 调用，只参考布局、文案、Tab 和交互层次；生产代码必须继续使用 `Task/task_id` 与真实 API。

## 3. 本轮目标

将 `/tasks/new` 的表面结构对齐为原型的六个 Tab：

1. 任务介绍
2. 视频文案
3. 声音生成
4. 输出类型
5. 视觉设置
6. 成片设置

保持现有可靠事务：先创建 Task，再上传 inputs；上传失败只能重试同一 `task_id`，不得重复创建 Task；本轮“创建任务”只保存，不自动启动 Run。

## 4. 字段与真实契约

### 4.1 必须可编辑并真实提交

| 页面区域 | UI 字段 | API 字段 |
|---|---|---|
| 任务介绍 | 任务名称 | `POST /tasks.title` |
| 视频文案 | 原始文案 | multipart `script` |
| 视频文案 | 最小/目标/最大字数 | `min_chars/target_chars/max_chars` |
| 声音生成 | 参考音频文件 | multipart `reference` |
| 成片设置 | 画面锚定文字 | `visual_anchor_enabled` |
| 成片设置 | 生成字幕 | `include_subtitles` |
| 成片设置 | 笔身文字 | `pen_text`，最长 12 字符 |
| 成片设置 | 线条绘制量 | `stroke_detail`：`light/standard/detailed/full` |

分段预览必须与后端规则语义一致。不得继续使用只接受单一 `segLen` 的原型算法冒充后端结果；允许在前端提供明确标注为“提交前预估”的确定性预览，并必须覆盖最小/目标/最大三个参数。若不能复用同算法，则只显示字符统计和预计规则，不伪称服务端结果。

### 4.2 资产联动

- 声音生成页通过真实 `GET /api/v1/assets/voices` 展示可用音色；选择已有音色不能假装已满足 `/inputs` 当前要求的 `reference` 文件。
- 视觉设置页通过真实 `GET /api/v1/assets/styles` 展示预置/自定义风格。
- 当前 `/inputs` 只接受 `style` 文本，不接受 `style_id`/`voice_id`。因此选择风格时只可提交其真实名称到 `style`；音色资产若无法通过 API 转成上传文件，应显示明确契约缺口，并仍要求用户上传参考音频。
- 空资产、加载、失败均有独立状态；禁止 localStorage、硬编码资产和 mock DTO。

### 4.3 未被后端支持的原型项

- 输出类型仅展示并选中“白板动画”；动态信息图显示“尚未开放”且不可选择。
- 视觉来源可展示预置/自定义分类，但只提交后端当前支持的 `style` 名称；不得提交不存在的字段。
- 每张图分镜数、执行策略 auto/manual/selective 尚无 `/inputs` 持久化字段。本轮以只读“后端契约待接入”或禁用控件呈现，不得伪保存，不得调用 start。
- 任务摘要没有真实字段，本轮不渲染可编辑假控件。

## 5. 页面行为

- Tab 切换不得丢失表单状态；顶部视频文案 Tab 显示实时字符数。
- 底部主操作固定为“创建并保存”，副操作为“取消”；文案明确说明不会启动运行。
- 未通过当前 Tab 的校验时，点击下一步或最终提交应定位到对应 Tab，并在字段附近显示错误。
- 文案不足 10 字、字数规则非法、首次未选择参考音频时，前端必须阻止提交；规则为 `1 ≤ min ≤ target ≤ max ≤ 500`。
- 双击/重复提交只允许发出一次 `POST /tasks`。
- `POST /tasks` 成功但 `/inputs` 失败：保留 `task_id`，显示安全错误、重试保存和进入工作台；重试不再创建 Task。
- API 错误不得显示本地路径、Secret、token、traceback 或音频内容。
- 页面不直接启动 Run，不因 capability loading 放行任何启动行为。

## 6. 表面对齐要求

- 1440×900 下与原型保持相同页面宽度、标题、说明、六 Tab、内容分栏、选择卡、开关卡和底部 action bar 的视觉层次。
- 使用现有共享样式和组件；不复制原型的 mock store/API。
- 文案统一为“任务”，生产源码中不得新增 `Project/project_id/projects`。
- 响应式窄屏不横向溢出，Tab 允许横向滚动或合理换行。

## 7. 自动化测试

至少覆盖：

1. 六 Tab 存在、切换保持数据。
2. 三字数规则和不足 10 字校验。
3. 首次参考音频必填与合法文件 FormData。
4. 真实 styles/voices loading、empty、error、success。
5. 风格名称进入 `style`，不提交 `style_id/voice_id/execution_strategy/shots_per_image`。
6. 动态信息图和未支持设置不可选/不可伪保存。
7. 单次创建、上传失败后同 Task 重试。
8. 安全错误渲染。
9. 测试 stderr 无 React warning、act warning、unhandled rejection。

## 8. 浏览器证据

扩展 `web-v2/scripts/capture-parity-evidence.mjs`，使用真实后端、1440×900，保存：

```text
docs/Mountain/webui-parity-evidence/tasks/create-intro.png
docs/Mountain/webui-parity-evidence/tasks/create-script.png
docs/Mountain/webui-parity-evidence/tasks/create-voice.png
docs/Mountain/webui-parity-evidence/tasks/create-visual.png
docs/Mountain/webui-parity-evidence/tasks/create-final.png
docs/Mountain/webui-parity-evidence/tasks/create-validation.png
```

截图脚本不得创建 Task。填写表单仅用于展示；validation 图通过前端校验产生。资产页截图必须等待真实 styles/voices 响应。更新 evidence README，记录 API、状态、时间和 SHA-256；Playwright console error/warning 和失败 API 均为 0（预期验证请求除外，并须说明）。

## 9. 门禁与提交

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 test -- --run
MOUNTAIN_API_BASE=http://127.0.0.1:8000 node web-v2/scripts/check-api-contract.mjs
git diff --check origin/integration/mountain-v2...HEAD
! rg -n 'Project|project_id|/projects' web-v2/src
git status --short
```

实现、测试、证据和报告分别形成易审计提交并推送。完成后在本文件末尾追加“CCF 实际交付报告”，只记录真实 commit、文件、门禁数字、截图哈希、已知契约缺口；不得只写“已完成”。

## Questions / Contract Gaps

1. 当前 `POST /api/v1/tasks/{task_id}/inputs` 仅接受 `reference` 音频文件，不接受 `voice_id`；`GET /api/v1/assets/voices` 返回的音色资产无法转换为该文件。因此页面仅展示真实音色并明确要求上传 reference，未伪造音色提交。
2. 本工作树执行 contract checker 时 `http://127.0.0.1:8000` 未提供响应，命令在 10 秒超时；需要真实后端启动后复验。

## CCF 实际交付报告

- 实现 commits：`ec160bb`、`c721646`（`web-v2/src/pages/CreateTaskPage.tsx`、`web-v2/src/styles/app.css`）。新增六 Tab（任务介绍、视频文案、声音生成、输出类型、视觉设置、成片设置），真实 styles/voices loading/empty/error/success 状态，`style` 名称提交，reference multipart 校验，字数与 10 字校验，双提交保护、创建后同 task 重试及安全错误渲染；底部 action bar sticky；未调用 start、未提交未冻结字段。
- 证据脚本 commit：`9e79aa2`（扩展 `web-v2/scripts/capture-parity-evidence.mjs`，加入六张 create surface/validation 路径；脚本不创建 Task）。因真实后端不可达，本轮未生成或伪造截图，故无 SHA-256 可报告。
- 门禁摘要：`npm --prefix web-v2 run build` 通过（TypeScript + Vite）；`git diff --check` 通过；`! rg -n 'Project|project_id|/projects' web-v2/src` 通过。`MOUNTAIN_API_BASE=http://127.0.0.1:8000 node web-v2/scripts/check-api-contract.mjs` 在 10 秒内无响应并超时。既有 `tests/create-task.test.tsx` 仍针对旧单页表面/可选 reference 假设，运行结果为 16 failed、1 passed，需按本执行单补写六 Tab 测试后复验。
- 截止报告时工作树状态：见同提交后的 `git status --short`；未推送。
