# WEB-LOCAL-003 — 本地服务 Whisper 排除回归修复

`worker_frontend`，请只完成此处列出的纠正。

工作目录：`/mnt/d/Workstation/Projects/cs-board`

输入：`docs/workmates/receipts/WEB-LOCAL-002-V.md`。

回执写入：`docs/workmates/receipts/WEB-LOCAL-003.md`

本轮动作：

- 在 `web-v2/src/pages/VoiceAlignmentPage.tsx` 的本地服务筛选中，除能力条件外，按结构化的 `adapter_type` 和 `service_id` 明确排除 Whisper；不得依赖显示名称或中文/英文文本匹配。
- 在 `web-v2/tests/voice-alignment-page.test.tsx` 增加回归测试。fixture 必须采用实时返回的形状，并包含 `service_id: 'local-whisper'`、`adapter_type: 'whisper'`、`capability: 'speech_alignment'`；断言该服务不显示，同时正常的 `speech_alignment` 本地服务仍显示。
- 运行该页面的 focused test、`cd web-v2 && npm test` 与 `cd web-v2 && npm run build`；回执记录每条命令、退出码、通过/失败/skip 数量和耗时。

边界：

- 只可修改上述页面、上述测试和本回执；不得修改后端、服务数据、动态信息图、其他页面或工单。
- 不删除断言、不加 skip、不提交或推送。
- 不扩大 Whisper 规则：本修复仅用于“本地服务”页面，Whisper 仍属于工具链。

完成后：更新回执并将工单交回独立验证；不得自行验收。
