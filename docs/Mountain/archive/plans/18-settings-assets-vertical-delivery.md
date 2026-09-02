# 设置与资产垂直交付契约

状态：设置与资产阶段契约；核心能力已交付，保留作回归基线，不是当前工作指令。

基线分支：`integration/mountain-v2`。

## 1. 协作方式

设置和资产按用户能力形成两个最终 PR，不再形成互相独立验收的“纯前端 PR”和“纯后端 PR”。CCF、CCB 可在各自 worktree/开发分支提交，但必须合入同一功能集成分支并共同通过浏览器验收后，才允许创建最终 PR。

任何一方不得用 fixture、fallback、localStorage 或静态业务常量补齐另一方尚未提供的契约。发现 gap 时记录为阻塞，并在同一垂直交付中修复。

## 2. PR-P1：模型服务配置闭环

### CCB 范围

- 动态 Service Registry 是唯一服务配置来源；不得恢复固定 Provider Profile。
- 修正 `config_status`、`secret_status`、`availability` 的一致性。
- OpenAI-compatible 服务至少支持 endpoint、model、api_mode、加密 api_key 和真实 Probe。
- Secret 跨进程重启仍可读取，不进入服务 JSON、日志、诊断或响应。
- 只允许创建 ProviderFactory 实际支持的自动 Adapter；手动 Skill 服务必须显式标记 execution mode，不能伪装自动可用。

### CCF 范围

- 保留动态多供应商、多能力服务模型。
- 普通用户使用 endpoint、model、API Key 表单；Secret 名称和 config JSON 放入高级设置。
- 创建、编辑、保存 Secret、删除 Secret、Probe、启停、设默认均调用真实 API。
- 页面刷新后必须回读持久化状态；Secret 只能显示 masked value。

### 联合验收

在全新数据目录完成：打开模型服务 → 编辑 OpenAI-compatible 文本服务 → 保存 endpoint/model/API Key → Probe → 重启后端 → 页面仍显示已配置且 Secret 不回显。

## 3. PR-P2：资产管理闭环

### CCB 范围

- 首次启动幂等安装 13 个 preset StyleTemplate；12 个预览图由 Asset Repository 提供真实 blob。
- Prompt、negative prompt、tags、engine、preview asset 必须持久化。
- preset 只读并可复制为 custom；custom 支持 CRUD/启停。
- 音色上传、元数据、播放、启停和删除使用真实文件。
- 新建 Task 输入可引用 style_id/voice_id，保存时验证资产存在且可用。

### CCF 范围

- 严格对照冻结原型的信息层级实现预置风格、自定义风格和音色库。
- 图片、音频和详情全部来自真实资产 URL/API。
- 引擎筛选只使用产品输出引擎，不把 DALL·E、SDXL 等供应商名称硬编码为风格引擎。
- 新建任务能够选择风格和音色，并在回读时恢复选择。

### 联合验收

全新数据目录启动后立即看到 13 个预置风格；复制一个 preset、修改并刷新仍存在；上传音色后可播放；新建 Task 选择风格/音色并保存，刷新后选择保持。

## 4. 共同门禁

- Python 全量测试 0 failed；前端 build 和全量 Vitest 0 failed。
- 真实后端 contract checker 通过。
- 浏览器控制台 warning/error 为 0。
- 使用独立验收数据目录，不复用开发者历史 `.csboard`。
- 最终 PR 描述附真实请求、磁盘持久化位置和浏览器验收证据。
