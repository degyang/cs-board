# PRESET-VOICE-UX-001-FE — 预置音色前端体验

`worker_frontend`，请只完成前端范围；可与后端工单并行。

工作目录：`/mnt/d/Workstation/Projects/cs-board`

回执写入：`docs/workmates/receipts/PRESET-VOICE-UX-001-FE.md`

范围：`web-v2/src/pages/VoiceManagementPage.tsx`、必要的 `web-v2/src/lib/api/voiceProfiles.ts` 类型/调用调整、以及直接相关的 `web-v2/tests/voice-management.test.tsx` / `web-v2/tests/voice-profiles-api.test.ts`。不要修改后端或其他 WebUI 页面。

交付要求：

1. “预置音色”以现有音色库一致的卡片式视觉/选择模式呈现，支持新增、选择、编辑、保存；不要退化既有音色设计或发音风格能力。
2. 所有 Provider 下拉框以设置→模型服务的 `fetchServices({ enabled: true })` 为唯一数据源，只保留声明音频或 TTS/语音合成能力的服务（兼容当前能力命名）；显示服务自身名称/ID，禁止硬编码厂商、MiMo 或固定 Provider 列表。
3. 移除每张预置卡片及编辑表单内嵌的试听播放器/自动试听；在页面底部建立独立“试听区”。上方选中音色后，试听区明确绑定该 profile；未选择时禁用/提示。
4. 试听区的示例朗读文本可编辑，默认必须完全等于：`这是一个语音测试，我会用清晰的语音提醒你，我就是你知心的助手。`
5. 点击生成试听必须调用真实 `previewVoiceProfile(profile_id, text)` API；展示加载、可播放 audio、错误状态。请求进行中和切换音色时立即清除/停止旧音频，过期响应不得覆盖当前选中 profile；不可用 API 不得伪造 audio。
6. 补足直接测试：Provider 能力过滤且无厂商硬编码；新增/编辑/保存；选中到试听区的联动；默认及自定义文本；preview 参数；音色切换使旧音频失效；加载/错误态和仅成功时可播放。保留并适配既有覆盖，不加 skip 或删除断言。

门槛：先跑 focused voice-management / voice-profiles API tests，再运行 `cd web-v2 && npm test` 与 `cd web-v2 && npm run build`；回执记录命令、退出码、pass/fail/skip 数与耗时。无需且不得为本工单重启 5182/8000。不得自行验收。
