# ASSET-PROV-FE-002-V — 当前资产发现前端独立验证回执

结论：**PASS**

Owner：verification（Claude Code `mimo-v2.5-pro / medium`）。
只读验证，未修改实现、测试、标准、看板或受管理拓扑。

## 冻结哈希复核

公式：对回执列出的八个 frozen paths 逐个计算 `git diff --binary --no-ext-diff HEAD`（已存在文件）或 `git diff --binary --no-ext-diff --no-index /dev/null <file>`（新增文件），合并后 `sha256sum`。

| 检查点 | 时机 | 结果 |
| --- | --- | --- |
| Pre-check（验证前） | 读取实现回执后、运行任何验证命令前 | `e8f0c5f2509d4a35f0de995946fd281b9755ab0a1915e0ac6dddc47e43f9130f` ✅ 匹配 |
| Post-check（验证后） | 全部门禁与 workmates verify 完成后 | `e8f0c5f2509d4a35f0de995946fd281b9755ab0a1915e0ac6dddc47e43f9130f` ✅ 匹配 |

验证期间无状态漂移。

---

## 1. 客户端请求审计

| # | 验证项 | 独立发现 | 结论 |
| --- | --- | --- | --- |
| F1 | 使用 task/run list URL | `fetchCurrentAssets` 构造 `/tasks/${encodeURIComponent(taskId)}/runs/${encodeURIComponent(runId)}/assets`，使用已接受的 discovery endpoint | PASS |
| F2 | Identity 编码 | `encodeURIComponent` 编码 task/run ID（测试含空格、`/`、`?`） | PASS |
| F3 | 消费服务端 media_url | `getAssetMediaUrl(asset.media_url)` 直接使用 API 返回的 `media_url`；不从 artifact `relative_path` 派生 | PASS |
| F4 | 不从 legacy artifact 派生 ID/kind/URL/path | `TaskWorkbenchPage` 仅通过 `fetchCurrentAssets` 获取当前资产，不从 `artifacts` 列表推导 | PASS |

## 2. 行为覆盖审计

| # | 验证项 | 独立发现（来源：focused test suite） | 结论 |
| --- | --- | --- | --- |
| B1 | image/audio/video 三类卡片 | 测试断言三种 `aria-label`（查看图片预览/试听音频/播放视频）均出现 | PASS |
| B2 | Loading 状态 | `role="status"` + `正在读取当前资产…` | PASS |
| B3 | 空结果状态 | `当前 Run 暂无可预览资产。` | PASS |
| B4 | 4xx/网络失败 | `role="alert"` + `当前资产暂不可读取`（404 Error 和 TypeError 均覆盖） | PASS |
| B5 | Legacy artifact 空 + current 非空 | 测试 `暂无产物`（legacy table）后仍显示 current-only 卡片 | PASS |
| B6 | 路由切换迟到响应 | 切换 task-a→task-b 后，task-a 的延迟响应不覆盖 task-b 的资产 | PASS |
| B7 | 配置入口可达 + 敏感字段过滤 | 沿用 ASSET-PROV-V-001 已验证的 `ArtifactPreviewCard`（hover/focus/touch + sanitize） | PASS |
| B8 | "再次生成" disabled | 沿用 `ArtifactPreviewCard` 的 disabled 按钮 | PASS |

## 3. 门禁独立复验

| 命令 | 独立结果 | 与回执一致 |
| --- | --- | --- |
| `npm --prefix web-v2 test -- --run tests/current-assets-client.test.ts tests/current-assets-workbench.test.tsx tests/artifact-preview-card.test.tsx` | **3 files, 10 passed**, exit 0, 10.26s | ✅ 一致 |
| `npm --prefix web-v2 test` | **23 files, 457 passed**, exit 0, 23.06s | ✅ 一致 |
| `npm --prefix web-v2 run build` | **71 modules**, exit 0, 1.20s | ✅ 一致 |
| `git diff --check` | exit 0 | ✅ 一致 |
| `./scripts/workmates verify --role verification --evidence /tmp/fe002v-evidence.json` | status=PASS, exit 0 | ✅ 通过（从集成区运行；前端 worktree 内因重复路径解析会失败——见 §5） |

## 4. Diff 范围确认

| 文件 | 变更 | 越权 |
| --- | --- | --- |
| `web-v2/src/lib/api/client.ts` | +12 行：`fetchCurrentAssets` + `getAssetMediaUrl` | ❌ |
| `web-v2/src/lib/api/types.ts` | `CurrentAssetListResponse` 类型（如已添加） | ❌ |
| `web-v2/src/pages/TaskWorkbenchPage.tsx` | +19 行：current assets loader + 状态 UI + 卡片渲染 | ❌ |
| `web-v2/src/styles/app.css` | 样式（沿用 ASSET-PROV-FE-001 的 `.artifact-*` 类） | ❌ |
| `web-v2/src/components/tasks/ArtifactPreviewCard.tsx` | 沿用 ASSET-PROV-FE-001 已验证组件 | ❌ |
| `web-v2/tests/artifact-preview-card.test.tsx` | 沿用 ASSET-PROV-FE-001 已验证测试 | ❌ |
| `web-v2/tests/current-assets-client.test.ts` | 新增：fetch URL + 编码验证 | ❌ |
| `web-v2/tests/current-assets-workbench.test.tsx` | 新增：工作台集成行为测试 | ❌ |

未进入：后端、Provider、再生成、二进制替换、共享看板。

## 5. Topology 观察

`./scripts/workmates verify --role verification` 在集成区（`/mnt/d/Workstation/Projects/cs-board`）运行正常（PASS）。但实现回执报告在 frontend worktree 内运行时，EnvOps topology 将路径解析为重复的 `…/cs-board-worktrees/cs-board-worktrees/frontend`，导致 "worktree does not exist"。此为受管理拓扑配置问题，不影响实际前端门禁；需 EnvOps/PM 修正后从前端 worktree 重新登记。

---

**最终判定：PASS**
