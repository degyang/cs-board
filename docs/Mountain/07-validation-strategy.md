# 测试与验收策略

## 1. 质量目标

Mountain 的主要风险是跨入口行为漂移、中断后重复收费、错误复用旧产物、文字/Voice/图片/视频失配，以及日志无法定位或泄露敏感内容。测试必须围绕契约、依赖、运行事实和真实媒体，而不只验证 HTTP 状态码。

## 2. 测试层次

### 2.1 Domain 单元测试

- Stage 状态机和 pipeline graph；
- Voice Unit/Visual Item 范围、顺序、覆盖率和父子关系；
- Timeline 连续性、Whisper 校验和等分公式；
- Artifact fingerprint 和失效依赖；
- stable error/reason code；
- `trace_id/command_id/span_id/parent_span_id` 传播规则；
- Redactor 的字段、文本模式和路径脱敏。

不访问网络、文件系统或子进程。

### 2.2 Contract 测试

- 所有业务 Artifact JSON Schema 的最小、完整和错误 fixture；
- Domain Event、Diagnostic Log、Audit Record、Trace View Schema；
- CLI JSON/JSONL、API View、Provider/Renderer fake adapter；
- legacy adapter View。

Schema 变化必须升级 `schema_version` 或提供兼容读取测试。

### 2.3 Repository / Artifact / Telemetry 集成测试

- 临时文件原子提交、hash、revision、并发写保护和损坏检测；
- stale 传播和服务重启恢复；
- Event cursor 单调、断点续读、投影重建和重复事件幂等；
- Log 轮转、筛选、保留和有界字段；
- Audit append-only 行为；
- 观测写入失败不能伪造业务成功，降级策略必须产生可见告警；
- 日志设置变化不改变业务 fingerprint。

### 2.4 Stage 集成测试

使用 fake Provider 与小型真实媒体：

- `segment-script` → AV Plan；
- `clone-voice` → Unit WAV、Whisper/fallback Timeline 和母带；
- `plan-storyboard` → Visual planning/prompt hash；
- `generate-illustrations` → source/final image；
- `render-visuals` → clip/silent master；
- `compose-video` → final manifest；
- 每个 Stage 的事件、span、指标、错误和日志脱敏。

### 2.5 Pipeline E2E

M06 先用短文案、固定 fake 图片、短 WAV 和 fake Whisper 跑通 `whiteboard + preset`，不调用收费服务，覆盖 Whisper 成功和 fallback、完整目录、状态、顺序、时长、最终 MP4 和 Trace。M09 再为 `custom-reference` 与信息图引擎增加同等 E2E 覆盖。

### 2.6 真实服务 Smoke Test

受控运行：

- IndexTTS 的语气连续性、最大单请求和并发音色；
- Whisper 中文标点/数字/同音词的覆盖率与失败路径；
- OpenAI-compatible Chat Completions、可选 Responses 和 Images；
- Windows、WSL、macOS 的 FFmpeg、字体和 PyInstaller sidecar；
- Remotion 与白板 renderer；
- Provider request id、延迟和重试字段是否可追踪且已脱敏。

不进入默认 CI。

## 3. 跨入口一致性矩阵

| 场景 | Web/API | CLI/Skills | 必须一致 |
| --- | --- | --- | --- |
| 创建同配置项目 | form | request JSON | 归一化 settings |
| 执行 Stage | API command | CLI command | fingerprint、Artifact Schema |
| 查看项目 | Project View | `project show --json` | 状态、Stage、Artifact keys |
| 查看运行 | 活动/诊断面板 | events/trace/logs | 同一 `run_id/trace_id` 和事件事实 |
| 失败重试 | 页面按钮 | `stage retry` | attempt、复用范围、Error |
| 单图重生成 | Visual 工作区 | `--visual` | 只失效对应 clip/final |
| 取消 | 取消 Run | `pipeline cancel` | 不调度后续 Unit，记录相同结果 |
| 恢复 | 重开页面 | `pipeline resume` | 不重复有效 Provider 调用 |
| 诊断导出 | 下载诊断包 | `diagnostics export` | 相同 bundle schema 和脱敏规则 |
| 最终交付 | 下载 | artifact show/path | 同一 final hash |

分别新建两个项目并调用随机模型时不要求字节相同；精确一致性针对同一 Project/Run 或 deterministic fake。

## 4. 关键不变量

### 4.1 文案与规划

- `source_text[source_range.start:source_range.end] == unit.text/visual.text`；
- Unit 完整覆盖有效原文且互不重叠；
- 每个 Unit 至少一个 Visual，Visual 完整覆盖父 Unit；
- 2–3 句话、1–2 张图允许合理偏离；
- Storyboard 不改变 Unit/Visual 原文、范围、数量或顺序。

### 4.2 Voice 与 Timeline

- 每个 Unit 恰有一个规范 Voice 文件；
- 母带时长等于 Unit 累计时长（容差内）；
- 每个 Unit 恰有一个 `timing_source`；
- Whisper 时间单调、合法并覆盖实际 Voice 时长；
- 对齐无效时整个 Unit 使用 `floor(i*D/N)` 等分，不混用精确边界；
- fallback 产生 `alignment.fallback`、warning、reason code 和指标，但 Run 可继续；
- Unit N 失败只重做 N，取消后 N+1 不启动。

### 4.3 图片

- 每个 Visual 恰有一个 source/final item；
- prompt hash 与 Storyboard 一致；
- key text 开关只影响 final image；
- 单图 revision 和失效范围正确；
- 自定义人物 ID 稳定。

### 4.4 渲染与合成

- clip 顺序等于 AV Plan/Timeline；
- clip 目标时长只来自 Timeline；
- 开场不提前露图、结尾保留完整画面；
- silent master 包含全部 clip；
- A/V duration delta 在容差内；
- 字幕 cue 不跨 Voice Unit；
- final 可 seek，编码策略符合目标平台；
- `validation.passed=false` 时 Run 不能 succeeded。

### 4.5 事件、日志和 Trace

- Run 创建一个 `trace_id`，跨 Web/Skill/Desktop 恢复不变；
- 每次用户/入口动作创建新 `command_id`；
- Stage/Provider/进程 span 的父子关系无环且闭合；
- 每个 terminal Stage 恰有一条对应 terminal Domain Event；
- Event cursor 单调，重新订阅不丢关键状态；
- Diagnostic Log 不被状态恢复读取；
- fallback、retry、cancel、process exit 和 Provider error 都可由 Trace 定位到 Unit/Visual；
- Event/Log/Audit 时间统一为带时区 ISO 8601，持续时间使用单调时钟测量。

## 5. 恢复与失效场景

自动覆盖：

1. AV Plan 成功后服务重启；
2. 第三个 Unit 配音写完 partial 前退出；
3. Voice 提交后、Timeline 提交前退出；
4. Whisper 超时、低覆盖、非单调和缺少可执行文件；
5. 第 N 张图片损坏或第 N 个 clip 时长不符；
6. silent master 存在但输入 hash 变化；
7. final 存在但字幕设置变化；
8. 用户修改风格、参考音色、Whisper profile 或原文；
9. 旧任务无 Mountain manifest；
10. Web 启动的 Run 由 Skill 取消/恢复；
11. Skill 启动的 Run 由 Web 重试；
12. Log 写满/轮转、事件订阅断线和 cursor 过期；
13. 诊断包导出过程中 Run 继续写日志。

## 6. Golden Projects

至少两组无隐私 Golden：

- `golden-whisper`：3 个 Voice Unit，至少一个 Unit 有 3 个 Visual，Whisper 边界成功；
- `golden-fallback`：至少一个 Unit 模拟对齐失败，验证整个 Unit 等分和 warning。

每组包含固定短 WAV、16:9 图片、字幕、短 clip、final、Event/Log/Audit 和 Trace fixture。Golden 不锁定有损 MP4 全字节 hash，锁定 JSON canonical hash、映射、codec、分辨率、fps、时长容差和关键帧感知差异。

## 7. 性能与资源

- 20 个排队项目公平性，一个长任务不能占满 Unit 队列；
- 项目内 1/2 路 TTS 的音色和墙钟对比；
- 图片并发和本地渲染不超过策略；
- 大项目 View 不读取二进制；
- 10 万 Event/Log 条目下 cursor 查询、筛选和 UI 首屏延迟；
- Log 轮转与诊断包不阻塞 Stage 提交；
- `/mnt/*` 等慢文件系统的原子操作和性能 warning；
- 日志采样开启/关闭不显著影响媒体吞吐。

## 8. 安全与隐私

- API key/Authorization/Secret 不出现在 Project、Artifact、Event、Log、Audit、CLI、API、错误和诊断包；
- 用唯一 canary Secret 扫描所有输出文件和压缩包；
- 默认不记录完整正文、prompt、Provider 响应、参考音频内容；
- 用户名、绝对路径和局域网地址按诊断包策略脱敏；
- 下载只能访问注册 Artifact，路径不能逃逸 Project 根；
- 上传类型、大小和媒体有效性；
- prompt、错误、任务名不能形成命令注入；
- CLI 不通过命令行参数传 Secret；
- 局域网 client 标识不作为授权依据。

## 9. 发布门槛

`mountain-av-v1` 成为 Web 默认前必须满足：

- contract、integration、双 engine E2E 全部通过；
- 真实长短文案、IndexTTS 和 Whisper 成功/fallback 验证；
- Voice/Visual 边界、最终 A/V 和字幕验收通过；
- 失败、取消、重启、轮转和跨入口接管通过；
- Web、Skills、CLI、Desktop（若随版本发布）对同一 Run 展示同一 Trace 事实；
- legacy 查看/下载回归通过；
- 无已知重复收费路径；
- Secret canary、诊断包脱敏和保留清理测试通过；
- 运维、故障排查和数据迁移说明已更新。
