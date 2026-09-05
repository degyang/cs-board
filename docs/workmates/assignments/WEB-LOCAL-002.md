# WEB-LOCAL-002 — 本地服务 WebUI 收口

`worker_frontend`，请接手本地服务 WebUI 收口。

工作目录：`/mnt/d/Workstation/Projects/cs-board`

遵照：`docs/workmates/team-contract.md` 的 Stage goal 与 Definition of done；参考 `web-v2/src/pages/VoiceManagementPage.tsx` 的预置音色列表/详情模式。

回执写入：`docs/workmates/receipts/WEB-LOCAL-002.md`

本轮动作：

- 审查并完成当前未提交的 `web-v2/src/pages/VoiceAlignmentPage.tsx`。
- 页面标题/导航必须为“本地服务”；Whisper 不得出现在本页或模型服务，仍可出现在工具链。
- 左侧列表、右侧详情/预览状态、新增、编辑、保存与真实探测必须可操作。
- “预览”在本工单指右侧详情预览/编辑切换，不要求新建语音合成 API。
- 增补本页面的直接测试，覆盖列表、Whisper 过滤、新增、编辑、探测和详情预览。

完成门槛：

- `cd web-v2 && npm test` 正常退出且 0 failed、0 skipped。
- `cd web-v2 && npm run build` 正常退出。
- 5182 实际加载当前源码，访问 `/settings/voice-alignment` 可见上述交互。

注意事项：

- 仅修改 `web-v2` 的直接相关文件与本回执；不得修改后端、动态信息图或其他基准页面。
- 不删除断言、不增加 skip、不提交。
- 若发现真实 API 缺口，写明具体复现，不用 mock 冒充成功。
