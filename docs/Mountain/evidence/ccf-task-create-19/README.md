# CCF-TASK-CREATE-VISUAL-RECOVERY-19 浏览器证据

浏览器：现有 Chromium `/home/ubuntu/.cache/ms-playwright/chromium-1187/chrome-linux/chrome`。前端预览地址：`http://127.0.0.1:5181/tasks/new`；`tab` 查询参数仅用于证据选择页面，不保存业务状态。

## 桌面六 Tab（1440×1100）

| Tab | 文件 | 页面状态 |
|---|---|---|
| 任务介绍 | `create-intro.png` | 表单、选项失败提示、导航完整 |
| 视频文案 | `create-script.png` | 双栏原文/切分预览、长度边界 |
| 声音生成 | `create-voice.png` | 真实资产列表、单一试听区、禁用项 |
| 输出类型 | `create-output.png` | 服务端能力卡片、不可用原因 |
| 视觉设置 | `create-visual.png` | 真实风格缩略图、选择卡、禁用项 |
| 成片设置 | `create-final.png` | 选项开关与最终汇总 |

## 移动三页（390×844）

`create-mobile-intro.png`、`create-mobile-script.png`、`create-mobile-final.png`。三图均显示响应式单列布局、横向 Tab 条和真实 `create-options` 错误提示；未创建 Task、未使用用户真实制作输入。

接口错误来自当前真实后端：`GET /api/v1/tasks/create-options` 返回 404；页面保留可浏览状态并禁用提交，不以 mock 绕过。
