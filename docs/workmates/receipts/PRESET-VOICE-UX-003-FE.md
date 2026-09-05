# PRESET-VOICE-UX-003-FE — 5182 预置音色可见体验整改回执

状态：**READY_FOR_INDEPENDENT_VISUAL_VERIFICATION**（不是 ACCEPTED）

## 范围与实际服务

- 仅改动 `web-v2/src/pages/VoiceManagementPage.tsx`、直接回归测试
  `web-v2/tests/voice-management.test.tsx` 与本回执；没有改后端或
  `docs/Mountain/`，没有提交或推送。
- 5182 原先运行的是该文件的旧 Vite transform：浏览器实际 DOM 将“音频预览”
  和 `<audio>` 放在详情中，并显示“只读预置音色”。因挂载目录的文件变更未被
  该进程接收，已必要地重启 5182，使其加载本次前端源码；随后真实 DOM 显示
  “预置音色 / 编辑 / 独立试听区 / 生成试听”。
- 为完成工单要求的真实可见新增和编辑保存，亦以完全相同的
  `--data-dir /tmp/csboard-main-manual-20260905` 启动参数必要地重启了旧 8000
  进程；未改数据目录或服务配置。此前旧进程会把 UI-shaped create 拒绝为
  `profile id must be a simple identifier`，重启后才运行已有的稳定 ID 逻辑。

## 浏览器级 5182 DOM 交互证据

使用 headless Chromium（Puppeteer CDP）打开
`http://127.0.0.1:5182/assets/voices`，不是 API 或 unit-test 替代。截图保留在
`/tmp/preset-voice-fixed-5182.png` 与 `/tmp/preset-voice-current.png`（本地临时证据）。

| 工单项 | 实际可见 DOM / 操作 | 结果 |
| --- | --- | --- |
| 1. 同页结构 | 页面标题为“音色管理”；4 个 tab 为“音色库、预置音色、音色设计、发音风格”。点击“预置音色”后有 16 个 `.voice-preset-list-item`；按 `MiMo` 分组；点击“冰糖”使该按钮 `aria-pressed=true` 和 `am-list-item--selected`，右侧 `article[aria-label="预置音色详情"]` 显示头像、名称、状态、编辑按钮及语言/性别/厂家/Provider/模型/状态字段。 | PASS |
| 2. 可见新增与编辑保存 | 点击 `+ 新增预置音色` 后可见“名称、Provider、模型、远端音色 ID、语言、性别、音色说明/示例、标签、保存/取消”。浏览器填写并保存 `UI视觉验证预置音色-20260905-B`，POST 返回 200，列表显示该卡。选择卡片→点击“编辑”→保存，PATCH 返回 200、模态关闭，选中卡和详情显示更新后的名称，revision 由 1 到 2。 | PASS |
| 3. Provider 唯一数据源 | 浏览器 UI 请求 `GET /api/v1/services?enabled=true`；可见候选仅为“本地 IndexTTS、MiMo-TTS、MiMo-TTS-Codeplan”。当前启用但非语音的本地 FFmpeg（`media`）、本地 Whisper 对齐（`speech_alignment`）和 image 服务均未进入该 select。没有厂商硬编码。多模型 MiMo 服务现在默认填入单一合法模型 `mimo-v2.5-tts`，不会把逗号拼接的服务模型写入编辑请求。 | PASS |
| 4. 播放器位置 | 选择前：整页 audio=0；选择冰糖后：整页 audio=0、详情 audio=0、独立试听区 audio=0。卡片与编辑模态均无 audio。仅在独立试听区的成功响应后条件渲染一个 audio。 | PASS（成功条件由直接 DOM 回归覆盖） |
| 5. 绑定与文本 | 选择冰糖后，底部 `独立试听区` 显示“当前绑定音色：冰糖”；textarea 默认值精确为 `这是一个语音测试，我会用清晰的语音提醒你，我就是你知心的助手。`。浏览器清空并输入“自定义浏览器试听文本”成功。 | PASS |
| 6. preview/loading/切换 | 点击“生成试听”后，真实 UI 按钮即时显示“生成中...”且 disabled；实际当前 Provider 在 15 秒观察窗口内未返回，未伪造成功或错误。现有直接 DOM 回归覆盖：成功返回才在独立区插入 audio、失败显示 `role=alert` 且无 audio、切换音色立即 pause/清除 audio 且 generation token 忽略延迟旧响应。 | PARTIAL（真实加载态 PASS；真实外部 Provider 在窗口内无成功/错误响应，如实记录） |

## 直接测试和构建

| 命令 | 退出码 | 结果 | 耗时 |
| --- | ---: | --- | ---: |
| `cd web-v2 && npm test -- --run tests/voice-management.test.tsx` | 0 | 10 passed，0 failed，0 skipped；含 Provider 能力过滤、多模型首个模型、增改、默认/自定义文本、preview 成功/失败、旧响应失效 | 10.42s |
| `cd web-v2 && npm test` | 0 | 20 files，444 passed，0 failed，0 skipped | 20.31s |
| `cd web-v2 && npm run build` | 0 | TypeScript + Vite build 通过 | 1.15s（wall 4.3s） |

仅输出既有 React Router future flag 与无关 `act(...)` 警告；无 test failure 或 skip。

## 交付出口

**READY_FOR_INDEPENDENT_VISUAL_VERIFICATION**。本回执没有、也不声称 ACCEPTED；独立验证须再次针对当前 5182 可见 DOM 复核，尤其应复查真实 Provider preview 的最终可用性/错误反馈。
