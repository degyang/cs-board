# 音色 Provider 与动态信息图接入计划

状态：已批准规划，尚未开放提交。
日期：2026-09-05

## 1. 范围与顺序

本计划补充两个后续能力，二者都不得通过打开现有禁用按钮或调用旧 `webapp/server.py` 伪装完成：

1. 音色管理升级为多 Provider 的可选音色与合成配置；首个实现为小米 MiMo V2.5 TTS；
2. 动态信息图以 `engine=infographic-remotion` 接入统一 Task/Run/Artifact/Trace 和六阶段流程。

执行顺序：先完成音色 Provider 领域/API/WebUI 和 MiMo 真实合成 smoke test；动态信息图随后按独立 M09 工作包接入。两项均不阻塞当前白板任务的既有读取、下载、恢复与资产选择。

## 2. 音色管理产品边界

音色管理页面保留现有“音色库”页面作为第一个 Tab，并增加两个 Provider 驱动的 Tab：

| Tab | 用途 | 首版行为 |
| --- | --- | --- |
| 音色库 | 已上传/已归档的本地音频音色资产；保留搜索、筛选、试听、启停、上传和编辑 | 现有页面原样迁入，不复制状态逻辑 |
| 预置音色 | 按厂家展示远程预置音色；厂家是产品分类，Provider 只是连接、密钥与模型配置 | 首个厂家为 MiMo，预置项：冰糖、茉莉、苏打、白桦、Mia、Chloe、Milo、Dean；以后 MiniMax、字节等按各自厂家加入 |
| 音色设计 | 以文字创建可复用的音色设计配置 | 创建时选择 Provider、模型和名称；保存音色描述与默认朗读风格，不把 API Key、完整 Provider 响应或临时音频写入资产 View |
| 发音风格 | 管理可复用的朗读风格模板 | 用简短列表呈现风格名称和指令；可选择/编辑/启停，支持基础/复合情绪、语调、音色定位、角色或方言等标签；具体标签由 Provider capability 返回 |

预置音色以与“音色库”一致的左侧列表/右侧详情组织：每项至少显示音色名、语言、性别、厂家、Provider、模型、状态、可播放预览和示例朗读文本。默认示例文本固定为“这是一个语音测试，我会用清晰的语音提醒你，我就是你知心的助手。”；预览音频由真实 TTS 预览接口按该文本生成，不能以假音频、浏览器语音或静态占位文件替代。

页面只罗列必要字段；不把小米文档长说明、认证资料或 Provider 调试参数直接塞入页面。厂家字段由 adapter 的非敏感 catalog 元数据提供，不能从 Provider 显示名猜测；每一项运行时仍绑定一个明确 Provider。音色名称允许使用“冰糖”“茉莉”等用户可读名称，但持久化使用稳定本地 ID 加 `vendor_id + provider_id + remote_voice_id/model`。

## 3. Provider-neutral 领域与安全契约

现有 `VoiceAsset` 是本地音频文件资产，继续用于上传参考音频和已归档媒体，不能承担远程预置音色或音色设计。新增独立、版本化的 `VoiceProfile` 聚合：

```text
VoiceProfile
  profile_id, revision, name, kind, vendor_id, vendor_name, provider_id, model_id
  remote_voice_id?              # 预置音色
  design_prompt?                # 音色设计
  default_style_profile_id?     # 可选发音风格
  language/tags/status/created_at/updated_at
  capability_snapshot           # 非敏感、可审计

VoiceStyleProfile
  style_profile_id, revision, name, provider_id?
  instruction, tags, status
```

`kind` 首版固定为 `uploaded-reference | provider-preset | provider-designed`。后续克隆音色可增加 `provider-cloned`，但不得复用上传文件路径作为远程克隆身份。

任务保存 VoiceProfile 的不可变、非敏感 revision snapshot；Run 只使用 snapshot。API Key 仅由模型服务的 SecretStore 保存，永不进入 VoiceProfile、Task、Artifact、Trace、浏览器响应、错误文本或日志。Provider 名称不是能力判断；Capability API 必须按已配置服务、模型和支持的 `speech.synthesize` 变体返回可用性与稳定错误码。

## 4. MiMo V2.5 首个 Adapter

MiMo 使用 OpenAI-compatible Chat Completions 风格调用，但属于独立的 `speech.synthesize` adapter，不复用文本生成 adapter 的 payload 假设。

| 能力 | MiMo 模型 | VoiceProfile 映射 |
| --- | --- | --- |
| 预置音色合成 | `mimo-v2.5-tts` | `provider-preset`，保存远程 Voice ID 与可选默认风格 |
| 文本设计音色 | `mimo-v2.5-tts-voicedesign` | `provider-designed`，保存设计描述、模型和样例文本，不假定其为可枚举的永久远程 Voice ID |
| 音色复刻 | `mimo-v2.5-tts-voiceclone` | 后续工作包；先保留 capability，不在首版 UI 宣称已经支持 |

适配器输入由领域请求转换为 MiMo 所需的 `user` 风格/设计指令与 `assistant` 合成文本；输出标准化为音频 bytes、格式、采样率、Provider request ID（如有）和脱敏诊断。流式 PCM16 的拼接、WAV 封装和失败清理由 adapter 负责，Stage 不接触 MiMo 协议细节。

模型服务中由用户创建 MiMo Provider：Provider ID、能力 `speech.synthesize`、adapter、Base URL、模型列表与 SecretStore API Key。模型服务 API 只返回 Key 是否已配置，绝不回显其值。

## 5. 动态信息图 M09 工作包

详细工作分解见 [29-m09-infographic-work-breakdown.md](29-m09-infographic-work-breakdown.md)。

动态信息图在完成以下全部条件前保持 `supported=false`：

1. `InfographicStoryboardAdapter` 将统一 Voice Unit/Timeline 转换为页面、节点、Cue 与 Remotion props；
2. `RemotionRendererAdapter` 通过 `RendererPort` 生成统一 `render-manifest`，不导入旧 `webapp.server`；
3. Task、CLI、WebUI、Skills 对同一 `engine=infographic-remotion` 读取同一 Capability、输入 snapshot、Run 与 Trace；
4. 指定的预置风格、Provider、Node/Remotion、FFmpeg、TTS/对齐能力缺失时，Capability 返回稳定原因，而不是执行中途失败；
5. 增加 fake E2E、恢复/重试、旧信息图只读、错误脱敏和一次真实短文案成片验收；
6. 所有输出进入 `outputs/<task_id>/runs/<run_id>/` 的任务包。

只有这些门禁均通过，WebUI 的“动态信息图”才从只读预览改为可提交。它与自定义参考风格可共享 Artifact/Timeline/Trace，但分别拥有 storyboard 与 renderer adapter 测试。

## 6. 验收清单

- [ ] 本地音频、MiMo 预置音色、音色设计与发音风格具有不同且明确的数据模型；
- [ ] MiMo、MiniMax 等 Provider 只通过 adapter/capability 扩展，Domain 和页面不出现厂商分支；
- [ ] MiMo API Key 经 SecretStore 保存、提交后清空且不回显；
- [ ] Provider 未配置、模型不支持、认证失败、限流、超时和不合法音频均有稳定脱敏错误；
- [ ] 音色管理四个 Tab 均消费真实 API，不使用 mock/localStorage；
- [ ] 新建任务可选择 active VoiceProfile，并在 Task/Run 写入 revision snapshot；
- [ ] MiMo 预置音色完成受控真实合成 smoke test；
- [ ] 动态信息图完成第 5 节所有条件后才开放可提交入口；
- [ ] 原白板、现有 VoiceAsset 和旧任务仍可读取与运行，相关回归门禁通过。

## 7. 依据

MiMo 官方 TTS 2.5 文档确认：预置音色、文本音色设计和音频样本复刻分别对应不同模型；预置音色可使用冰糖、茉莉、苏打、白桦等 Voice ID；发音风格可采用自然语言指令或标签控制。实现以 Provider capability 和实际 API 响应为准，不将文档示例视为永远稳定的硬编码配置。
