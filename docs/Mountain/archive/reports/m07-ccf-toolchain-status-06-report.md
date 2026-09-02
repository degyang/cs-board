# CCF-TOOLCHAIN-STATUS-06 执行报告

**指令来源**: 统一工程台账 §3J
**执行日期**: 2026-09-01
**分支**: `feat/mountain-assets-settings-web`
**实现提交**: `7b0f35c2e97b7fd35ea3e5a8c7ae3fa154721b55`
**报告提交**: 本报告所在的本地提交；最终 hash 随交付回执提供。

## 实现范围

仅修改 `/settings/toolchain`：

- 页面改为“系统工具链”只读状态卡，说明其数据是运行环境探测结果，不是可保存配置。
- 使用既有真实 API adapter `GET /api/v1/settings/toolchain`；路由进入时请求一次，失败时“重新加载”会再次调用该 adapter。
- 为 Codex Skills、IndexTTS、Whisper、FFmpeg、FFprobe 和白板渲染器提供纯展示的名称/用途映射；未知 component 直接显示后端 component，并保留 DTO 状态。
- 仅渲染 `component` 映射、`available`、`version`、`error_code` 和 `suggestion`。不渲染 path、命令、参数、环境变量、token 或 Secret。
- loading 使用与状态卡同构的骨架；空列表显示“未探测到工具链组件”；请求错误和单组件不可用使用不同视觉/语义状态。
- 通过挂载状态和请求序号避免旧的延迟响应在卸载或后发请求后写回页面。

## 视觉基准映射

| 原型/截图元素 | 生产实现 |
| --- | --- |
| “系统工具链”卡片标题和只读说明 | `.tc-panel`、`系统工具链`与运行环境探测说明 |
| 双列状态卡 | `.tc-grid` 自适应卡片网格 |
| 名称、用途、可用徽标、版本 | `ToolCard` 的名称映射、用途、状态和 version |
| 不可用错误块 | `error_code` 和 `suggestion` 的独立错误详情块 |
| 页面加载 | 同构 `.tc-card--skeleton` 骨架 |

视觉基准已直接读取：

- `/mnt/d/workstation/projects/cs-board-main-docs/docs/Mountain/webui-prototype-baseline/screenshots/settings/03-toolchain-normal.png`
- `/mnt/d/workstation/projects/cs-board-main-docs/docs/Mountain/webui-prototype-baseline/screenshots/settings/04-toolchain-unavailable.png`

## 行为测试

`services-contract.test.tsx` 覆盖生产路由组件及其 API adapter 调用边界：

- available 工具的映射名称、用途与版本；
- unavailable 工具的真实 `error_code` 和 `suggestion`；
- 未知 component 的回退名称与 DTO 状态；
- 响应中额外携带 path、command、token 时，DOM 不出现其值；
- loading 骨架、空列表、请求错误以及 retry 成功后的状态清除；
- 卸载后的延迟响应不会写回；
- 无保存、编辑、探测或刷新控件。

## 门禁结果

| 命令 | 结果 |
| --- | --- |
| `npm --prefix web-v2 run build` | 通过 |
| `npm --prefix web-v2 run test:contract-checker` | 48/48 通过 |
| `npm --prefix web-v2 test -- --run` | 244/244 通过，0 act warning |
| `node web-v2/scripts/check-api-contract.mjs` | fixture 对齐通过；未设置 `MOUNTAIN_API_BASE`，未进行真实后端验证 |
| `! rg -n "localStorage|sessionStorage|mock|fixture" web-v2/src/pages/ToolchainPage.tsx` | 通过 |
| `git diff --check` | 通过 |

## API gap

- 本地执行环境未设置 `MOUNTAIN_API_BASE`，因此契约脚本按既有机制仅验证 fixture 对齐，未能向实际后端发起 `GET /api/v1/settings/toolchain`。页面本身仍使用生产 `fetchToolchainSettings` adapter，未引入运行时 fallback。
- 当前 DTO 的安全展示字段已满足本切片：`tools[].component`、`available`、`version`、`error_code`、`suggestion`；未要求也未增加任何运行环境细节字段。

执行者未自行宣布审核通过。
