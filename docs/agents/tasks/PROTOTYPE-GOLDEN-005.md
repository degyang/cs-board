# PROTOTYPE-GOLDEN-005：恢复并冻结 5182 WebUI 原型基准

- Owner: PROTOTYPE
- Status: REVIEW_READY
- Priority: P0
- Depends on: none
- Worktree: `/mnt/d/workstation/projects/cs-board-prototype-golden`
- Branch: `feat/mountain-prototype-golden`
- Base commit: `0f56e824c0d49ab5c090e7ea07086dc9d47f47a9`

## Goal

恢复 Git 已跟踪 `prototypes/webui` 的最小可构建/只读运行外壳，在不改变现有视觉与交互源码的前提下，
固定用户先前确认的 5182 原型来源，并生成 WEB-PARITY-004 所需五组 `1366x900`、DPR 1 golden、逐文件
SHA-256/尺寸/route/source manifest。该任务只解决验收基准依赖，不修改正式 WebUI。

## Allowed surfaces

- `prototypes/webui` 缺失的构建入口与配置文件，以及仅为修复构建错误所需的最小类型纠正；
- `docs/Mountain/webui-prototype-baseline/screenshots/WEB-PARITY-004/golden/`；
- `docs/Mountain/webui-prototype-baseline/WEB-PARITY-004-manifest.json`；
- `docs/agents/reports/PROTOTYPE-GOLDEN-005.md`。

## Forbidden surfaces

- `web-v2`、Python/backend、API DTO、Pipeline、Stage Work Order、媒体链路和 Dashboard；
- 改写原型视觉 token、布局、文案或交互来迁就正式实现；
- 将 mock/localStorage/Project 契约复制到生产代码；
- 伪造截图、拉伸/裁切截图、用正式 WebUI actual 充当 golden；
- skip、删除断言或仅声明“看起来一致”。

## Acceptance

1. `npm --prefix prototypes/webui run build` 正常 exit 0，原型可在 loopback 只读启动并访问；
2. manifest 固定 source commit，并逐组记录 prototype route、golden 文件、width、height、DPR、SHA-256；
3. 至少覆盖品牌壳、任务队列、六 Tab 新建任务映射、设置、资产五组 golden；历史 Project 路由只作视觉
   映射，报告明确其对应正式 Task 路由，不改产品契约；
4. 五张截图均为浏览器真实访问 prototype 得到的 `1366x900`、DPR 1、100% zoom，控制台 error、pageerror、
   failed request 和 HTTP >=400 均为 0；
5. 报告列出恢复的构建外壳、所有命令终态、截图 hash、临时服务/浏览器/端口清理证据；
6. Reviewer 必须独立复现 build、抽查截图来源与 manifest；通过前不得解除 WEB blocker。

## Gates

```bash
npm --prefix prototypes/webui install
npm --prefix prototypes/webui run build
node prototypes/webui/scripts/capture-golden.mjs
git diff --check 0f56e82...HEAD
! git diff --name-only 0f56e82...HEAD | rg '^web-v2/'
```

截图脚本必须自行有界启动/停止 prototype，任一页面、截图、尺寸、hash 或浏览器问题缺失时非零退出。

## Stop condition

提交并推送当前分支，写入报告并通知 CEO。全部 acceptance 满足才置为 `REVIEW_READY`；否则提交具体
`BLOCKED` 证据。不得自行解除 `WEB-PARITY-004`、批准或领取其他任务。

## Dispatch

- Attempt: 1（初次）
- Coordination decision: `8fbed11`
- Worker: `/root/prototype_golden_worker_medium`
- State: `DISPATCHED`

先前误启动的 `sol + ultra` 与随后仍偏高的 `terra + high` 会话均已在产生文件变更前终止；正式执行使用
`gpt-5.6-terra + medium`。未经用户审批不得升级；连续三次返工仍未解决时，CEO 才可提出升级申请。

## Review handoff

- Delivery: `069ace12ae35243ff01d6af986c05b76009d6755`
- Implementation: `3c53772`
- Report: `docs/agents/reports/PROTOTYPE-GOLDEN-005.md`
- State: `REVIEW_READY`

本节只记录 Worker 交接，不代表 CEO、Reviewer 或用户批准。

## Attempt 1 independent review

- Review: `docs/agents/reviews/PROTOTYPE-GOLDEN-005.md`
- Review commit: `7f4aaab`
- Verdict: `CHANGES_REQUESTED`

同一 checkout/Chromium/机器连续 capture 会因动画相位改变部分 PNG SHA-256，且默认脚本会静默重写
manifest，未满足不可变 golden 的核心约束。attempt 2 仅可修改 capture 脚本、重新生成的五张 golden、
manifest 与报告：在捕获环境中冻结动画而不改原型视觉源码；默认复验必须对已冻结 hash fail closed，更新
基准必须使用显式生成模式；连续两次 capture 的五项 hash 和 manifest 字节必须一致，并保留原 build、
尺寸、浏览器问题计数与 5182 清理门禁。

- Attempt 2 dispatch state: `DISPATCHED`
- Attempt 2 worker: `/root/prototype_golden_attempt2_worker`

## Attempt 2 review handoff

- Implementation: `7db041b`
- Delivery: `b4287d9`
- Report: `docs/agents/reports/PROTOTYPE-GOLDEN-005.md`
- State: `REVIEW_READY`

Worker 已提交并推送 deterministic immutable capture 纠正，分支干净且与远端一致；本节仅记录交接，
不代表 CEO、Reviewer 或用户批准，也不解除 `WEB-PARITY-004` blocker。
