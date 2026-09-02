# PROTOTYPE-GOLDEN-005 独立评审

Verdict: `CHANGES_REQUESTED`

## 评审范围

- 契约基线：`0f56e824c0d49ab5c090e7ea07086dc9d47f47a9`；
- 交付提交：`069ace12ae35243ff01d6af986c05b76009d6755`；
- 分支：`feat/mountain-prototype-golden`，与 `origin/feat/mountain-prototype-golden` 一致；
- 差异：`git diff 0f56e82...069ace12`。

差异限于允许的 `prototypes/webui` 构建/捕获外壳、五张 golden、manifest 和交付报告。`git diff --check`
通过；差异中没有 `web-v2/`，也没有 backend、DTO、Pipeline、媒体链路或 Dashboard 改动。原型既有的
视觉/交互 `src/` 未被本交付改写。

## 独立复现的通过项

```text
npm --prefix prototypes/webui install
exit 0

npm --prefix prototypes/webui run build
exit 0; tsc --noEmit + vite build completed

node prototypes/webui/scripts/capture-golden.mjs
exit 0; Playwright Chromium loopback preview captured five routes
```

- `/help`、`/projects`、`/create`、`/settings`、`/assets` 都由本工作树 `127.0.0.1:5182`
  production preview 真实访问；五张截图目视检查包含品牌壳、队列、六 Tab 创建、设置和资产内容。
- `file golden/*.png` 对五项均报告 `1366 x 900`、RGB PNG；脚本设置 DPR 1 和 100% zoom，并对 console
  error、pageerror、failed request、HTTP >=400 fail closed。此次独立运行正常完成。
- manifest 逐项包含 prototype route、golden 路径、尺寸、DPR、SHA-256 和 bytes；`/projects` 与 `/create`
  明确仅视觉映射到正式 `/tasks`、`/tasks/new`。
- capture finally 后 `ss -ltn '( sport = :5182 )'` 无监听器；本次 Vite/Chromium 已退出。为不污染交付，
  Reviewer 已仅还原本次 capture 生成的 tracked golden/manifest，工作树恢复干净。

## 必须纠正：golden hash 不能复现

“冻结”基准的核心完整性未满足。相同 checkout、相同依赖、同一 Chromium 和相同机器上连续运行 capture
两次，第二次会覆写部分 golden，并改变 SHA-256；脚本随后无条件把新 hash 写进 manifest，完全没有将结果与
已冻结 manifest 比较后 fail closed。

精确复现：

```text
sha256sum docs/Mountain/webui-prototype-baseline/screenshots/WEB-PARITY-004/golden/*.png > /tmp/first.sha256
node prototypes/webui/scripts/capture-golden.mjs
sha256sum docs/Mountain/webui-prototype-baseline/screenshots/WEB-PARITY-004/golden/*.png > /tmp/second.sha256
diff -u /tmp/first.sha256 /tmp/second.sha256
```

在交付 `069ace12` 上，`02-task-queue.png` 从
`752072be1ef9791b64c944c2b8672d899649d16afa4452a6643afd32859c7994` 变为
`aa48193e91075a0df6f127a6b36aac2088378f32ac745a2e22c857c66a5ce47a`；`05-assets.png` 也变化为
`c5adc17f6ac7fb8ea003be4b47c9a9cf3f343c438a86e8bd83f2d15405db3261`。此前独立首轮亦观察到品牌壳、创建和
资产图 hash 变化。像素差虽很小（动画脉冲的相位），但仍违反逐文件 SHA-256 冻结承诺，且会静默改写已提交
的 evidence，不能作为 `WEB-PARITY-004` 的不可变输入。

报告还把 delivery 写成早期 `3c53772`，而当前 handoff/捕获稳定化提交为 `069ace12`；纠正时应报告最终
implementation/evidence commit，避免来源歧义。

## 有界返工范围与复验

只修改 `prototypes/webui/scripts/capture-golden.mjs` 及所需的 regenerated golden、manifest、报告：在 capture
环境中可靠冻结/禁用会影响截图的动画（不改原型视觉源码），并使默认复验路径对现有 manifest/hash fail
closed；如需要更新基准，使用明确的生成模式。重新生成五项后，连续两次 capture 必须保持全部五项 hash 和
manifest 字节一致，同时保留原 build、尺寸、浏览器问题计数和 5182 清理门禁。

复验命令：

```text
npm --prefix prototypes/webui install
npm --prefix prototypes/webui run build
node prototypes/webui/scripts/capture-golden.mjs
sha256sum docs/Mountain/webui-prototype-baseline/screenshots/WEB-PARITY-004/golden/*.png > /tmp/prototype-golden-first.sha256
node prototypes/webui/scripts/capture-golden.mjs
sha256sum docs/Mountain/webui-prototype-baseline/screenshots/WEB-PARITY-004/golden/*.png > /tmp/prototype-golden-second.sha256
diff -u /tmp/prototype-golden-first.sha256 /tmp/prototype-golden-second.sha256
ss -ltn '( sport = :5182 )'
git diff --check 0f56e82...HEAD
! git diff --name-only 0f56e82...HEAD | rg '^web-v2/'
```

本结论不批准、合并、解除 `WEB-PARITY-004` blocker 或领取其他任务。
