# PRESET-VOICE-UX-004-FE

状态：**READY_FOR_INDEPENDENT_VISUAL_VERIFICATION**（非 ACCEPTED）。

## 真实 5182 Chromium 证据

- Chromium：`/home/ubuntu/.cache/puppeteer/chrome/linux-152.0.7977.54/chrome-linux64/chrome`，CDP，viewport `1440×900`。
- 先捕获到原始失败：真实 UI 编辑 `preset-4d23a72137bd524e1fbfc039f74ea15f722f7f7b02878a88c298ea673d3bfb29`，PATCH 返回 **400**，response body 为 `{"detail":"VOICE_PROFILE_MODEL_UNAVAILABLE"}`；请求的 `model_id=indextts-2`，而当前 `local-indextts` 服务明确声明 `model=""`。
- 修复后 PATCH DTO 不再发送不可更新的 `provider_id` / `example_text`；对于显式未声明模型的 Provider，前端在发送前以可见错误终态阻止 400。有效 MiMo 绑定的真实 UI PATCH 返回 **200**、表单关闭，详情显示 `冰糖-PATCH400`（现场浏览器记录）。
- 当前 served module 包含 `dedupePresetProfiles`、`hasDeclaredProviderModel`；同一厂家 MiMo 的两 Provider 共 16 条后，目录按 `vendor_id + remote_voice_id` 规范化去重为 8 条，其他 vendor/remote 项仍保留。
- 截图：[顶端桌面截图](/tmp/preset-voice-ux-004-final-full.png)。截图从 `scrollY=0` 开始，显示页头、tabs、`+ 新增预置音色`、列表、详情编辑入口；样式把列表限高为 360px，使下方独立试听区不再被长列表挤出桌面可视布局。独立试听区继续保留精确默认文本、当前绑定与生成控件，且播放器仅在该区域成功时渲染。

## 实现

- `VoiceManagementPage.tsx`：结构化 `vendor_id + remote_voice_id` 去重；桌面 master/detail 最小列宽；试听请求 20 秒 timeout、generation token 防旧音频回流；编辑模型预检。
- `voiceProfiles.ts`：PATCH 只发送服务端可编辑元数据。
- `assets.css`：桌面双栏详情最小 640px，列表可滚动而不挤走试听区。
- 直接测试覆盖去重、桌面结构、超时终态、成功/失败/切换失效、无模型 Provider 的本地阻断，以及 PATCH DTO。

## 门禁

| 命令 | 退出码 | 结果 | 耗时 |
| --- | ---: | --- | ---: |
| `npx vitest run tests/voice-management.test.tsx tests/voice-profiles-api.test.ts` | 0 | 2 files, 17 passed, 0 failed, 0 skipped | 8s |
| `npm test` | 0 | 20 files, 447 passed, 0 failed, 0 skipped | 21s |
| `npm run build` | 0 | TypeScript + Vite, 70 modules | 约4s |

5182 当前单监听 PID：`748905`。未提交、未推送；未修改后端、服务数据或动态信息图。

## 新增 UI 门禁复验（后续结果）

- 已将预置音色布局的堆叠断点由 `1100px` 收紧至 `768px`；1024px 与 1440px 均保持左右主从栏，只有手机宽度才堆叠。
- 使用 Playwright 高级 API（`/tmp/node_modules/playwright`，显式 `executablePath=/home/ubuntu/.cache/puppeteer/chrome/linux-152.0.7977.54/chrome-linux64/chrome`）操作真实 5182，未提交创建或编辑请求，因此无数据污染。
- 1024px：列表 x=304、宽=320；新增/编辑表单输入 x=663，明确位于列表右侧。1440px：列表宽=394.55；表单输入 x=737.55，仍在右侧。两种视口中 `独立试听区 form` 数量均为 0；取消后恢复右侧详情的“编辑”按钮。
- 截图：`/tmp/preset-voice-ux-004-1024-create.png`、`/tmp/preset-voice-ux-004-1024-edit.png`、`/tmp/preset-voice-ux-004-1440-create.png`、`/tmp/preset-voice-ux-004-1440-edit.png`。
- 更新后的专项：17 passed / 0 failed / 0 skipped；全量：20 files、447 passed / 0 failed / 0 skipped；构建：70 modules，均 exit 0。
- 路径更正后的 Playwright 重跑：使用同一完整 `executablePath` 在 1024px 和 1440px 均验证 `createRight=true`、`editRight=true`、`auditionForms=0`；截图为 `/tmp/preset-voice-ux-004-1024-correct-path-edit.png` 与 `/tmp/preset-voice-ux-004-1440-correct-path-edit.png`。
