# WEB-PARITY-004 独立评审（attempt 2）

Verdict: `CHANGES_REQUESTED`

## 评审范围

- 契约基线：`51656c91bb378d3a62ce5668d9d1c8b861de4847`；交付：`cdda8725e7c23ad8dfa9b3d6548d8d7e4323bd1c`；报告交接：`eadf15a1f8d706999660d2a42c9ccb4aae579101`。
- `51656c9...cdda872` 的 16 个变更文件仅涉及允许的 WebUI shell/CSS、parity verifier、报告与该任务 evidence。未修改 backend、prototype、DTO、Pipeline、Work Order 或媒体链路。

## 已核验

- 五组 golden 和五组 actual PNG 均为 `1366x900`；重新计算的 SHA-256 与 `golden-manifest.json` / `manifest.json` 一致。golden 来源固定为已批准的 `PROTOTYPE-GOLDEN-005` commit `0f56e82`。
- 逐对目视检查证实图片可打开，且分别是品牌壳、队列、六 Tab 创建、设置、资产页；actual 的队列为空态和资产/设置的真实数据差异没有伪装成 prototype mock。
- `node /home/ubuntu/.nvm/versions/node/v24.15.0/lib/node_modules/npm/bin/npm-cli.js --prefix web-v2 run build`：exit 0。
- 同一 Node 工具链的 `npm --prefix web-v2 test -- --run`：16 files、349 tests passed，exit 0。
- `git diff --check 51656c9...cdda872`：exit 0。

## 必须纠正

契约的 forbidden-pattern gate 失败，因新增 `web-v2/scripts/verify-prototype-parity-e2e.mjs:50` 包含：

```text
{ name: 'task-queue', route: '/', golden: '02-task-queue.png', prototypeRoute: '/projects' },
```

以下契约命令因此匹配该新增行并返回成功（也就是前置 `!` 使门禁失败）：

```text
git diff --unified=0 51656c9...cdda872 -- web-v2/src web-v2/scripts | \
  rg '^\+.*(localStorage|mockResolvedValue|mockImplementation|/projects|project_id|api[_-]?key\s*[:=]\s*[^[:space:]]{12}|Authorization\s*[:=])'
```

这同时违反了“正式源码和测试不存在新增 `/projects` 旧契约”的 acceptance。旧路由只能留在 evidence/manifest 的视觉来源说明，不能进入生产 verifier 源码。

## 有界返工范围与复现

仅移除 verifier 源码中的 legacy `/projects` 字面量/契约引用，并保留 manifest 中已批准的 prototype-to-Task 视觉映射；不得改动 prototype、backend、Work Order 或领取 `WEB-WO-003`。随后重新执行全部契约 gates，尤其是上面的 forbidden-pattern audit、真实 API checker 和浏览器 parity verifier。

本 verdict 只记录独立审核，不合并、不批准任务或选择后续任务。
