# CCF-TASK-CREATE-SIX-TAB-18 实际交付回执

## 起点与范围

- starting HEAD：`cecb540`（执行前确认 clean）。
- 实现提交：`acf4dbd feat(mountain-web): align six-tab Task creation flow`。
- 仅修改正式 `/tasks/new` 的 CreateTaskPage、API client/types 与 create-task 行为测试；未修改后端、工作台、Gate、资产管理或设置页面。
- 未推送，未触发 pos-magents、队列或自动派工。

## Preview-first 检查点

六 Tab 已可浏览，顺序为：任务介绍 → 视频文案 → 声音生成 → 输出类型 → 视觉设置 → 成片设置。切换 Tab 保留内存表单；提供上一步/下一步、完整句子切分只读预览、实时字数和最终汇总。

预览命令：

```bash
npm --prefix web-v2 run dev -- --host 0.0.0.0 --port 5181 --strictPort
```

地址：`http://127.0.0.1:5181/tasks/new`。`curl --noproxy '*' -I` 返回 `HTTP/1.1 200 OK`；页面可见证据由 11 个 CreateTaskPage 行为测试覆盖。5175 当时已有 listener，未覆盖或终止其他会话，改用 5181 并使用 `--strictPort`。

真实资产通过 `/api/v1/assets/voices`、`/api/v1/assets/styles` 读取；可用音色提供真实 content URL，风格提供真实 preview URL，加载中、空列表、读取失败和禁用资产均有可见状态。create-options 不可达时页面真实显示错误并保持预览可浏览、提交按钮禁用。

## 行为测试

`web-v2/tests/create-task.test.tsx` 共 11 项通过，覆盖：

- 六 Tab 顺序、Tab 键盘语义、上一步/下一步和跨 Tab 字段保持；
- 中文句号/问号/感叹号边界切分、实时字数、target chars 与“非权威 script_preparation”提示；
- 真实 voice/style client 调用、试听/预览 URL、加载/空/错误/禁用状态；
- engine 与 visual source 独立选择、不可用组合和服务端 reason；
- 最终 JSON `title/summary/engine/pipeline_id/submission_id` 与 multipart `script/target_chars/voice_source/voice_asset_id/visual_source/style_asset_id/shots_per_image/line_density/brand_text/visual_anchor_enabled/include_subtitles`；
- 双击仅一次 create；create 失败保留表单；inputs 失败显示 task_id/run_id，重试只调用 inputs；成功只导航，不调用 start；
- 卸载中的迟到保存不产生 warning 或导航；无浏览器存储依赖。

## 门禁结果

- `npm --prefix web-v2 run build`：通过。
- `npm --prefix web-v2 test -- --run`：15 个文件、361 项测试全部通过。
- `/tmp/ccf-task-create-six-tab-18-test.log` warning scan：React act、Router Future Flag、Unhandled/unhandled rejection、unmounted state update 均 0 命中。
- `npm --prefix web-v2 run test:contract-checker`：48 项通过。
- 禁止 Project/project_id、策略词、浏览器存储和 `Math.random` 静态扫描：0 命中。
- `git diff --check cecb540...HEAD`：提交前通过。

## Questions / Contract Gaps

1. 当前真实后端 `GET http://127.0.0.1:8000/api/v1/tasks/create-options` 返回 `404 Not Found`；因此正式页面不猜测能力，显示“仅可预览，暂不可提交”。需要 CCB 提供 §17.3 冻结的 engines、visual_sources、voice_sources、limits、defaults 响应后才能进行真实最终提交联调。
2. 当前后端输入回写仍以历史 `style/pen_text/stroke_detail/min_chars/max_chars` 为主；本页已按 §17.4 发送正式字段，需 CCB 落地并回读 `voice_asset_id/style_asset_id/visual_source/shots_per_image/line_density/brand_text` 及稳定 `submission_id`。
3. 当前实现只在服务端 create-options 与真实资产接口成功且组合可用时允许提交；未用 fixture、mock、localStorage 或假能力绕过缺口。

## 审核边界

本回执只证明六 Tab WebUI 预览、客户端契约和自动化行为测试；不代表真实后端联调完成，不代表 PM 审核通过，也不进入 `USER_ACCEPTANCE`。
