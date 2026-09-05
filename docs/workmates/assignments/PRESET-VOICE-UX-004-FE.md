# PRESET-VOICE-UX-004-FE — 预置音色桌面布局与试听终态修复

`worker_frontend`（可见 tmux worker），用户人工审查已判定 `PRESET-VOICE-UX-003-FE` 视觉 **FAIL**。请只修复当前 5182“音色管理 → 预置音色”的桌面可见体验；本工单完成前不得标记 ACCEPTED。

交接：此前内部子任务已被 PM 停止，以避免并发文件写入。此后只有可见 tmux `worker_frontend` 可执行本工单；PM 只消费回执，不实施。

工作目录：`/mnt/d/Workstation/Projects/cs-board`

输入视觉证据：`/tmp/preset-voice-fixed-5182.png`、`/tmp/preset-voice-current.png`。两图均显示右侧详情列过窄、预置音色及字段逐字/竖行断行，且未清晰展示页面下方独立试听区。

已确认可复用浏览器路径（不得全盘搜索环境）：

- Puppeteer Chromium：`/home/ubuntu/.cache/puppeteer/chrome/linux-152.0.7977.54/chrome-linux64/chrome`
- Playwright Chromium 备用：`/home/ubuntu/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome`

回执写入：`docs/workmates/receipts/PRESET-VOICE-UX-004-FE.md`

允许范围：`web-v2/src/pages/VoiceManagementPage.tsx`、直接关联的前端样式/API/测试文件及本回执。不得修改后端、动态信息图规划、服务数据或无关页面；非必要不重启 5182/8000，不提交、不推送。

必须完成：

1. 在正常桌面视口（至少 1440×900；也记录实际 viewport）使预置音色成为真正可用的双栏页面：左侧完整列表，右侧详情/编辑列具有足够最小宽度；不得让名称、标签、Provider、模型、状态或字段值逐字、单字或异常竖行断开。必要时改为合理的 grid/flex 比例、`min-width`、文本换行/溢出策略；窄屏可另行响应，但不能牺牲桌面布局。
2. 保持可见 UI 新增、选择、编辑和保存路径；详情列的编辑入口、字段与保存控件必须在全页截图可辨认。
3. 全页面底部的独立试听区必须在同一张桌面全页截图中清晰可见，展示当前绑定音色、精确默认文本输入和生成试听控件；卡片/详情/编辑区仍无播放器。
4. 修复真实试听长期停留“生成中...”的无终态：真实 preview 请求只能以成功的可播放 audio、真实可见错误，或明确的前端超时错误终态结束。超时必须取消/忽略过期请求、解除 loading、无旧 audio 回流且不伪造成功；切换音色仍立即清除旧 audio。
5. 使用当前 5182 的浏览器级验证（不能仅靠 DOM 存在或 unit test）在桌面视口完成新增/选择/编辑入口、布局、试听区和试听终态交互；生成并在回执链接/列出全页截图路径。截图必须同时包含完整列表、详情编辑入口和页面下方独立试听区；必要时使用浏览器 full-page screenshot。
6. 添加直接回归测试：桌面布局关键 class/结构、preview timeout/terminal error、成功/错误/切换失效；运行 focused、`cd web-v2 && npm test`、`cd web-v2 && npm run build`，记录退出码、pass/fail/skip 和耗时。

人工复核追加硬门禁（优先于交付）：

7. 先用上述 Chromium 对当前 5182 的编辑保存操作捕获 Network 中 PATCH 400 的 response body/稳定 error code，并在回执中记录精确 contract；必须以该事实修复，禁止猜测。修复后同一真实浏览器路径的编辑保存 PATCH 必须成功、表单关闭且卡片/详情显示新值。
8. 目录/UI 按规范化 `vendor_id + remote_voice_id` 去重：同一厂家的多个可用 Provider 不得复制整套预置音色。Provider 字段仍是用户可选的、可用音频/TTS模型服务绑定，不能用 Provider ID 作为目录展示身份。增加非 mock 或浏览器级回归，覆盖同 vendor 同 remote voice 的多 Provider 只展示一项、不同 vendor 或 remote voice 不被误合并。
9. 全页截图必须从页面顶端开始，在正常桌面宽度中同时可见页头、tabs、`+ 新增预置音色`、完整列表、详情编辑入口和页面下方独立试听区。若一个浏览器 full-page 截图无法清晰展示上述区域，使用同一会话、同一 viewport 的合规拼接证据，并说明方法；不得从中间滚动位置开始截取。

交付出口只能为 `READY_FOR_INDEPENDENT_VISUAL_VERIFICATION` 或 `BLOCKED`。不得把元素存在、API 返回或测试通过写成视觉 PASS/ACCEPTED；须逐项记录截图中可见的布局与试听终态。未完成追加 7–9 项不得交回执。
