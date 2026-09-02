# CCF-TASK-CREATE-VISUAL-RECOVERY-19 实际交付报告

## 范围

- 仅修改新建任务 WebUI、共享 Tabs 样式/键盘兼容、API DTO/client、专项测试和浏览器证据；未修改后端、Gate、资产/设置业务页面。
- 六 Tab 已按原型补齐响应式布局：文案双栏与中英文/换行句界、超长句硬切；声音选择列表＋单一试听区；风格真实缩略图选择卡；输出能力禁用原因；成片开关及最终汇总。
- 提交身份使用 URL `submission_id/task_id/run_id` 恢复；无业务浏览器存储、无 Task 创建脚本、无用户真实输入。创建成功后失败重试只保存输入，并提供进入工作台入口；恢复时提示文件需重新选择。

## 门禁结果

| 门禁 | 结果 |
|---|---|
| `npm --prefix web-v2 run build` | PASS |
| 全量前端测试 | PASS，15 files / 364 tests |
| warning/unhandled 扫描 | PASS，日志无 act、Router Future Flag、Unhandled、unmounted warning |
| contract checker | PASS，48 tests |
| 禁止词/浏览器存储/随机数静态扫描 | PASS |
| `git diff --check bb3fbad...HEAD` | PASS |

## 浏览器证据

浏览器使用既有 Chromium：`/home/ubuntu/.cache/ms-playwright/chromium-1187/chrome-linux/chrome`。桌面 1440×1100 六图及移动 390×844 三图均为非空 PNG，人工确认没有 404 页面、loading 空态或错误白屏；真实后端的 `create-options` 404 以页面内可见错误提示呈现，提交保持禁用。

桌面六图 SHA-256：

| 文件 | SHA-256 |
|---|---|
| `create-intro.png` | `0149aa282aff4b4f9dbdf52d612b78e800a458e2940bdfc0638f56b7e1ce8399` |
| `create-script.png` | `50a6a8e797393e206f30076288527c977a4935d7fa3c22909d215014ff5d6413` |
| `create-voice.png` | `5f03e6c8057df25a08672b3a7a94a0a554fe558e6d2cfaaa5f639b18f7f3d5cf` |
| `create-output.png` | `60828454866cc0df16d8dcbd83d9fdd914764cc2842648b25619c0e197cd4249` |
| `create-visual.png` | `63d8d8d428e803f68d78bc5ab001ca6792dfd787bba8e0fca071929e289dc69e` |
| `create-final.png` | `33eb93a860a03c78b52489c0cce55963f267b962602dfb38161fb6f6810f27fe` |

移动证据：`create-mobile-intro.png`、`create-mobile-script.png`、`create-mobile-final.png`，尺寸均为 390×844；SHA-256 分别为 `93f4281694975d83bc06921e4bf0c472ffd0028cf1fad4fa29c4f871d09b7f8f`、`4be8e3a5fa0a875b0674145eaef972373d7174a6fa30e1947c2a17d09f84a29d`、`9b06dc9dc7de10db83992f6b0647e74e39e342dff9cdbe9f43219f8e2c7e0522`。

证据索引见 `docs/Mountain/evidence/ccf-task-create-19/README.md`。

## Contract Gaps / Questions

1. 当前真实后端尚未提供 `GET /api/v1/tasks/create-options`（8000 返回 404），因此本轮保留六 Tab 预览与真实错误态，提交按钮安全禁用；需要 CCB 确认正式选项契约后再启用持久化联调。
2. 旧后端 `GET /tasks/{task_id}/inputs` 的 readback 仍以 `style/pen_text/stroke_detail` 为主；前端兼容读取新字段并保留旧字段回退，音频文件刷新后需用户重新选择。

## 提交

- 实现提交：`cb30e31 fix(mountain-web): align Task creation preview and recovery`
- 回执提交：`docs(mountain): report Task creation visual recovery`
- 当前仅本地提交，未推送；待 PM 复审。
