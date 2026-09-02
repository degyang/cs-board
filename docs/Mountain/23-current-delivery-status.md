# Mountain 当前交付状态

状态日期：2026-09-02  
权威集成分支：`integration/mountain-v2`  
本文只记录已由PM核查的当前事实；目标设计不等于已实现。

## 1. 当前产品目标

近期只打通一条主线：

```text
用户在WebUI新建Task
→ 保存真实文案、参考音频、风格和成片设置
→ 生成六阶段工作条件与工作单
→ Codex按六个能力Skills执行
→ 外部图片等成果回存并验收
→ 渲染与合成final.mp4
→ 用户验收
```

动态信息图、自定义参考、Desktop和Legacy兼容均不在当前主线。

## 2. 分支和人员状态

| 责任方 | 分支/工作树 | 当前状态 | PM结论 |
|---|---|---|---|
| 集成 | `integration/mountain-v2` | 设置、资产、Task基础、服务启动等已集成 | 稳定基线 |
| CCF | `feat/mountain-webui-surface-parity` | 新建任务六Tab生产页面已编码；测试和真实浏览器证据正在纠偏 | `CORRECTION REQUIRED` |
| CCB | `feat/mountain-assets-settings-backend` | execution plan领域/API/持久化初版已编码；测试矩阵和全量挂起正在纠偏 | `CORRECTION REQUIRED` |
| 用户 | 不操作开发分支 | 等待可用WebUI后提供真实文案、音频、风格和验收判断 | 尚未进入真实制作验收 |
| PM | 集成工作树 | 维护契约、指令、审核与合并 | 当前进行文档收口 |

## 3. 已实现并通过阶段验收

- Task/Run/Stage/Artifact、文件仓储、Telemetry、脱敏和诊断基础；
- OpenAI-compatible动态服务配置、加密Secret、Probe与默认服务；
- 预置/自定义风格和音色资产API；
- 设置页面与资产页面真实API接入；
- Task队列真实API、状态筛选、搜索、cursor和空态；
- IndexTTS、Whisper alignment/fallback、FFmpeg和白板渲染适配器代码；
- 六阶段Application Commands和基础CLI命令；
- 7个Skill文件的初版职责说明；
- 可移植后端启动器和真实前后端contract checker。

以上“实现”不代表六阶段已经用一个真实用户Task完整跑通。

## 4. 当前正在纠偏

### 4.1 CCF：新建任务

已编码：六Tab、Task创建、inputs multipart保存、真实styles/voices读取、首次reference校验、style名称、字幕、锚定、笔身文字和线条量。

未通过：

- 现有全量前端结果为`329 passed / 16 failed`；
- 存在React act warning；
- 六张新建任务浏览器证据缺失；
- 真实后端contract checker尚未作为本切片证据通过。

当前指令：CCF分支 `docs/Mountain/21-create-task-surface-parity-execution.md` 的最新PM纠偏段落。

### 4.2 CCB：Task execution plan

已编码：`auto/selective`领域对象、multipart字段、request持久化、GET/task show readback、selective 409保护。

未通过：

- 只有3个专项测试；
- 缺事务故障、并发、CLI subprocess、旧数据和脱敏矩阵；
- selective无副作用证明范围不足；
- canonical阶段顺序存在重复来源；
-全量测试中的`test_inputs_and_start_boundary`持续挂起。

当前指令：CCB分支 `docs/Mountain/16-agent-execution-ledger.md` 第4T节。

## 5. 尚未实现

以下能力不得在页面、文档或报告中描述为可用：

- 六阶段统一Stage Work Order文件；
- 每阶段参数文件、Codex指令文件、规范输出目录和预期Artifact清单；
- Work Order的API/CLI查询；
- 外部/Codex图片候选的import、validate、accept、reject和retry；
- selective自动运行到人工门禁并在确认后继续；
- 任务工作台展示完整工作单、外部成果和人工控制；
- 六个能力Skill完全基于工作单执行；
- 使用真实用户输入从新建Task跑到最终MP4；
- 用户对最终视频的验收。

## 6. 已知Skills偏差

- `skills/script-segmenter/`的Skill名称已改成visual anchor，但目录尚未重命名；
- Skill示例仍存在废弃`--script`、直接传`tts-url`或旧Project文字；
- 当前Skill没有统一读取Stage Work Order；
- illustration Skill默认假设图片Provider自动生成，Codex人工出图回存未闭环；
- `video-workflow`中的产品策略仍混用内部`gated/targeted`；
- 目前不能声称“Codex可无隐含上下文完成六阶段”。

## 7. 预计四轮交付

| 轮次 | CCF | CCB/核心 | 完成标志 |
|---|---|---|---|
| 1（当前） | 新建任务纠偏 | execution plan纠偏 | WebUI可可靠保存当前完整Task输入 |
| 2 | 展示初始化阶段条件 | 六阶段Work Order与外部成果命令 | Task创建后有确定性六阶段工作包 |
| 3 | 工作台呈现输入/指令/输出/成果 | Skills和CLI按工作单实跑 | Codex可顺序执行六阶段 |
| 4 | 真实状态、预览、重做和最终视频 | 联合E2E与质量验证 | 用户输入真实内容并得到final.mp4 |

轮次完成必须通过PM复验，不以开发者自报或测试数量替代。

## 8. 文档权威顺序

1. 本文当前状态；
2. `22-delivery-roles-and-document-handoff.md`角色与交接；
3. `24-codex-six-stage-execution-contract.md`当前执行契约；
4. PM明确点名的本轮指令及最新审核段落；
5. `02/03/07/09/12/14/15`专题设计；
6. 其他设计作为目标或阶段基线；
7. `m*-report/audit`仅为历史证据。

若文档与当前代码冲突，执行者记录Contract Gap，由PM裁决并同步本文；不得自行选择较方便的旧文档。
