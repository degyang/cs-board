# PRESET-VOICE-UX-003-V — 5182 预置音色独立可视验证

`tester_frontend`（Codex medium），请对 `PRESET-VOICE-UX-003-FE` 进行独立的 current-5182 可视验证。

工作目录：`/mnt/d/Workstation/Projects/cs-board`

输入：`PRESET-VOICE-UX-003-FE.md`、其回执与相关前端 diff。

回执写入：`docs/workmates/receipts/PRESET-VOICE-UX-003-V.md`

必须用浏览器级验证或等效真实 5182 DOM 交互访问音色管理→预置音色；不得只用 API、源码检查或 unit test 代替。逐项记录可见选择器/文本/交互和截图或等价证据：

1. 与音色库一致的列表、选中、详情编辑结构。
2. UI 内真实新增及编辑保存后的可见状态。
3. Provider 下拉只出现 enabled 音频/TTS能力的模型服务，不含非音频服务或厂商硬编码结果。
4. 卡片/详情/编辑区没有播放器，全页底部仅一个独立试听区域；记录 audio DOM 个数和位置。
5. 选择音色后底部绑定正确 profile；默认文案精确匹配且可编辑。
6. 点击生成后的 loading、成功可播放 audio 和错误状态；切换音色时旧 audio 立刻消失/暂停，迟到结果不得恢复。

第 6 项不可用 mock 成功或 unit test 代替实际 5182 观察。若外部 Provider 在合理等待时间内无法成功，验证者必须尝试记录可见错误态；若既无成功 audio 也无可见错误的终态，该项为 FAIL/BLOCKED，不得 PASS 或 ACCEPTED。

可复跑 focused/full frontend tests 和 build 作为补充，但它们不能覆盖可见性结论。不得修改实现、后端、动态信息图规划或服务配置；不重启 5182/8000，除非先在回执记录不可避免的具体原因；不提交、不推送、不执行 real render。出口仅 PASS / FAIL / BLOCKED，PM 在 PASS 前不得重新 ACCEPTED。
