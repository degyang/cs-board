# PRESET-VOICE-UX-003-V — 5182 预置音色独立可视验证回执

状态：**FAIL**（不得据此标记 `ACCEPTED`）

## 验证边界与方法

- 独立验证时间：2026-09-05；直接访问当前运行的
  `http://127.0.0.1:5182/assets/voices`，以临时 headless Chromium 操作真实 Vite
  页面和 DOM。没有以 API、源码或 unit test 代替可见性结论。
- 未改产品代码、后端、动态信息图规划或服务配置；未重启 5182/8000；未提交、推送或执行 real render。
- 截图证据留在本机临时路径：
  `/tmp/preset-voice-independent-initial.png`、
  `/tmp/preset-voice-independent-selected-form.png`、
  `/tmp/preset-voice-independent-create-edit.png`、
  `/tmp/preset-voice-independent-preview-20s.png`、
  `/tmp/preset-voice-independent-switch.png`、
  `/tmp/preset-voice-independent-error.png`、
  `/tmp/preset-voice-independent-settings.png`。

## 逐项真实 5182 DOM 结果

| 项 | 实际可见元素、交互与网络证据 | 结论 |
| --- | --- | --- |
| 1. 同页结构 | 页面含 tabs `音色库 / 预置音色 / 音色设计 / 发音风格`。点击 `预置音色` 后，`.voice-preset-list-item` 以 `MIMO` 分组显示；点选 `冰糖` 后该卡 `aria-pressed="true"`。右侧 `article[aria-label="预置音色详情"]` 显示 `冰糖`、状态、`编辑`，以及语言、性别、厂家、Provider、模型、状态字段；布局为同页列表—选中—详情编辑结构。 | PASS |
| 2. 可见新增、编辑与保存 | 真实点击 `+ 新增预置音色`，表单可见 `名称 * / Provider * / 模型 * / 远端音色 ID * / 语言 / 性别 / 音色说明/示例 / 标签` 与 `保存/取消`。实际填写并保存 `独立UI验证音色-681479`：`POST /api/v1/voice-profiles` 为 **200**，卡片可见。选择该卡并点 `编辑`，把名称改为 `独立UI验证音色-681479-编辑` 后点保存：真实 `PATCH /api/v1/voice-profiles/preset-4d23a72137bd524e1fbfc039f74ea15f722f7f7b02878a88c298ea673d3bfb29` 为 **400**；编辑表单仍开着，选中卡和详情仍为旧名称。 | **FAIL** |
| 3. Provider 可见过滤 | 新增表单的 `select#preset-provider` 只有 `本地 IndexTTS`、`MiMo-TTS`、`MiMo-TTS-Codeplan`。同一真实 5182 设置页 `设置 → 模型服务` 可见两项 MiMo 均标为 `音频`；`设置 → 本地服务` 可见 `本地 IndexTTS`，能力为 `语音合成 (TTS)`。同页设置中可见的 `OpenAI 兼容图片模型`（图片）和 `OpenAI 兼容文本模型`（文本）未出现于下拉。页面 DOM 仅呈现上述服务名称，没有额外厂商预置项。 | PASS（当前可见候选仅为启用音频/TTS 服务） |
| 4. 播放器位置 | 切换到预置音色且未生成时整页 `audio=0`；选中 `冰糖` 后整页和 `预置音色详情` 均 `audio=0`，卡片、详情和新增/编辑表单内均无播放器。真实成功 preview 后整页 `audio=1`，该唯一元素位于页面底部 `试听区`。 | PASS |
| 5. 选择绑定与文本 | 选中 `冰糖` 时试听区可见 `当前绑定音色：冰糖`。`textarea#preset-preview-text` 默认值精确为 `这是一个语音测试，我会用清晰的语音提醒你，我就是你知心的助手。`；该 textarea 可在浏览器中输入自定义文字。切换到 `Chloe` 后绑定文本实时变为 `当前绑定音色：Chloe`。 | PASS |
| 6. 真实 preview、成功/错误及旧音频失效 | 对 `冰糖` 点 `生成试听` 后，按钮立即变为禁用的 `生成中...`，随后真实 `POST .../model-service-268dbca4-bingtang/preview` 为 **200**、`GET` 音频为 **206**，试听区出现且仅出现一个 `audio`。选择另一音色 `Chloe` 后 100ms，整页 `audio=0`，试听区 `audio=0`；等待 7 秒仍为 0，旧结果没有回流。另对真实新建的不可用本地 IndexTTS 音色点生成，出现 `role=alert`：`预览生成失败：VOICE_PROFILE_MODEL_UNAVAILABLE`，且 `audio=0`；未使用 mock。 | PASS |

## 不通过原因与处理要求

验收主体第 2 项要求“添加和编辑必须在可见 UI 中可操作”。虽新增成功，但当前 5182 的编辑保存有可复现的 400，用户可见表单无法成功关闭和展示更新结果。因此总体为 **FAIL**；preview 的真实成功、真实错误和旧音频失效均不能覆盖该缺陷。

PM 应保持任务 reopened，派发仅针对实际 5182 编辑保存 400 的有界整改及再次独立可视验证；在修复后的真实 UI 编辑保存成功前，不得标记 `ACCEPTED`。
