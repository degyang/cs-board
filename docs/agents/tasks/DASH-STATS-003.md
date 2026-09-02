# DASH-STATS-003：原团队看板统计横栏与动态成员证明

- Owner: DASH
- Status: READY
- Priority: P1
- Depends on: `PM-AUTO-001=APPROVED`
- Worktree: `/mnt/d/Workstation/Projects/POS-agent-coordination/00-System/Skills/skills-pos-magents/pos-magents/scripts/team-dashboard`
- Branch: `feat/pos-codex-agent-coordination`
- Base commit: `7254c2f`

## Goal

只在原 `http://127.0.0.1:4317` 团队看板做微调：在右侧任务看板上方增加一条紧凑统计横栏，展示
总工作时长、总任务数、初次完成任务数和返工完成任务数；同时用测试锁定左侧成员完全来自项目
registry，新增或删除真实 Agent 时无需改 HTML/JavaScript 角色常量。

## Allowed surfaces

- `state.mjs`、`heartbeat.mjs`、`teamctl.mjs`；
- `public/index.html`、`public/app.js`、`public/styles.css`；
- `tests/*.test.mjs`。

## Forbidden surfaces

- 新建独立 Dashboard、改端口、重做整体布局/导航/配色；
- 修改 cs-board 产品代码、`web-v2`、任务业务状态或 Agent registry；
- 用 Git 提交间隔伪造工作时长、回填无法观测的历史时长；
- 把 PM/WEB/CORE/MEDIA 写成固定角色列表。

## Metrics semantics

- `总工作时长`：所有 registry Agent 从本功能启用后，由 runtime `working` session 实际累计的时长；
  active session 计至当前刷新时刻，切换 idle/blocked/review 或租约到期时结算，重复 working 不得倒退或双计；
- `总任务数`：`docs/agents/status.md` 当前任务行总数；
- `初次完成`：完成态（`APPROVED`/`REJECTED`）且 cycle 不含“返工”的任务数；
- `返工完成`：完成态且 cycle 含“返工”的任务数。

## Acceptance

1. 原页面右侧标题与三列 lanes 之间只增加一条横向四项统计条，窄屏可换行；
2. `/api/team` 返回结构化 `stats`，数字计算在服务端 state 层，前端只格式化时长并 escape；
3. heartbeat/runtime 保存 session start 与累计毫秒，working→working/终态/lease expiry 均不重复计算；
4. registry 任意增加 `REVIEWER` 等角色时 API 和左栏自动出现，删除后自动消失；源码无固定成员数组；
5. 现有状态、任务 lane、三秒刷新和 4317 服务行为不回退；
6. 测试覆盖统计分类、active/closed duration、重复 transition、动态角色和 HTML 渲染数据入口。

## Gates

```bash
npm test
git diff --check 7254c2f...HEAD
! rg -n "\['PM'.*'WEB'|\['WEB'.*'CORE'|PM.*WEB.*CORE.*MEDIA" public state.mjs
curl -fsS http://127.0.0.1:4317/api/team
```

## Stop condition

提交原 Dashboard 分支并返回 commit；重启原 4317 server，验证 API stats、动态成员列表和页面资源。不得
创建第二套页面或服务，不得改 cs-board 产品 UI。
