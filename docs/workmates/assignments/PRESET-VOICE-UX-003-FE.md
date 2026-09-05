# PRESET-VOICE-UX-003-FE — 5182 预置音色可见体验整改

`worker_frontend`，用户已否决 `PRESET-VOICE-UX-001` 的 WebUI 验收。请直接核对并整改当前 5182 实际服务中的“音色管理 → 预置音色”页面；本工单完成前绝不得声称或记录 ACCEPTED。

工作目录：`/mnt/d/Workstation/Projects/cs-board`

回执写入：`docs/workmates/receipts/PRESET-VOICE-UX-003-FE.md`

允许范围：`web-v2/src/pages/VoiceManagementPage.tsx`、直接相关的前端 API/样式/测试文件及本回执。不得修改后端、`docs/Mountain/` 动态信息图规划、服务数据或无关页面；非必要不重启 5182/8000，不提交、不推送。

必须以当前 `http://127.0.0.1:5182` 实际服务完成浏览器级验证，或等效的真实 5182 DOM 交互验证（不得只读源码、只跑 unit test 或只查 API）：

1. 打开路由并进入“音色管理 → 预置音色”；页面的列表、选中态和详情编辑结构必须与同页“音色库”结构一致。回执逐项列出可见标题、列表/卡片、选中指示、详情/表单控件。
2. 在可见 UI 实际操作添加和编辑保存；记录触发控件、表单字段、保存后的可见状态。不得以调用 API 或 mock 代替。
3. Provider 下拉的可见选项只能来自“设置 → 模型服务”中声明音频或 TTS/语音合成能力的 enabled 服务；没有硬编码厂家。回执记录实际候选项和被排除的非音频服务（若当前数据不足，使用等效 DOM 交互 fixture，并明确说明）。
4. 每张音色卡片和编辑区均不得有播放器；整个页面底部只能有一个独立试听区域。回执记录 DOM/audio 元素数及其所在区域。
5. 上方选择音色后，底部试听区显示/绑定该音色；默认输入文案必须精确为 `这是一个语音测试，我会用清晰的语音提醒你，我就是你知心的助手。`，且可编辑。回执记录选中音色、绑定文本和输入交互。
6. 通过页面生成试听后，在真实 Provider preview API 成功时可播放；必须记录加载、成功 audio 元素和错误态。切换至另一音色时旧 audio 立即消失/暂停，延迟旧响应不得重新出现。若当前 5182 环境没有可用 Provider，记录真实错误态和 DOM 交互证据，不得伪造成功；仍须使用等效 DOM 测试覆盖成功和过期响应失效。

测试要求：补足覆盖上述可见交互的直接测试，运行 focused test、`cd web-v2 && npm test`、`cd web-v2 && npm run build`。回执记录命令、退出码、pass/fail/skip、耗时，并把 5182 的路由、交互步骤、逐项可见元素与结果独立列出。

交付出口：`READY_FOR_INDEPENDENT_VISUAL_VERIFICATION` 或 `BLOCKED`，不可写 ACCEPTED；不得自行验收。
