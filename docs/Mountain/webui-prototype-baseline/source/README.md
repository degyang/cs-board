# Mountain WebUI v2（山野小读）

基于 `docs/Mountain/` 设计文档（04-webui-redesign、13-webui-functional-spec）落地的 React + Vite 工程。
视觉遵循山野小读 NovaTech 品牌规范（苔绿主色 / 落日橙 / 远山蓝 / 宣纸中性色，见 `src/styles/tokens.css`）。

## 运行

```bash
npm install
npm run dev      # http://localhost:5175
npm run build    # tsc 类型检查 + vite 产物
```

后端就绪前默认使用 mock View（`src/lib/api/mock.ts`）：

| 环境变量 | 说明 |
| --- | --- |
| `VITE_USE_MOCK=off` | 切换到真实 `/api`（不可达时自动回退 mock） |
| `VITE_API_BASE` | API 前缀，默认 `/api`（dev 经 vite proxy → 127.0.0.1:8787） |

## 目录（对应 04 号文档 §8）

```text
src/
├── app/                 # router / providers（全局 Run 状态条上下文）
├── pages/               # 六路由页面
│   ├── CreateProjectPage.tsx        /create 单页四区
│   ├── ProjectsPage.tsx             /projects 状态过滤 Tabs
│   ├── ProjectWorkbenchPage.tsx     /projects/:id 三栏工作台
│   ├── RunDiagnosticsPage.tsx       /projects/:id/runs/:rid/diagnostics
│   ├── SettingsPage.tsx             /settings 五页签
│   └── HelpPage.tsx                 /help
├── features/
│   ├── stage-timeline/  # 六阶段时间线（可点击）
│   ├── voice-units/     # Voice Unit / Visual Item 列表
│   ├── artifact-gallery/# Artifact 产物栏（逻辑 key，无物理路径）
│   ├── run-activity/    # 活动/日志/指标/诊断 四页签面板
│   └── project-workbench/ # 阶段主工作区
├── components/          # layout(Sidebar/AppShell) + ui(Tabs/StatusBadge/CopyButton)
└── lib/
    ├── api/             # types(View 契约) / client / queries / mock
    └── formatting.ts
```

## 关键设计约束（实现时勿破坏）

- engine 与 visual_source 是两个独立字段；不支持的组合由 Capability API 返回，前端只标记不隐藏。
- 所有返工操作（重跑/重试/重生成/重合成）统一走共享 Application Command（`submitCommand`），禁止旁路删文件。
- Artifact 只展示逻辑 key / schema version / revision / hash；物理路径不对用户展示。
- fallback 单元（平均切图）可见但不计为失败。
- Tabs 只用于页面内局部上下文切换（项目过滤、活动诊断四页签、设置分页），路由级切换走侧边导航。
- WebUI v2 只消费 API View，不导入 Python Domain，不复制状态机或 fallback 公式。

## 侧边栏钉住（Pin）

侧边栏品牌区右侧有图钉按钮，状态持久化到 `localStorage`（`mountain.ui.sidebarPinned`）：

| 状态 | 图钉 | 侧边栏行为 |
| --- | --- | --- |
| 已钉住（默认） | 竖直、苔绿高亮 | 常驻展开 264px，占据网格列，永不折叠/隐藏 |
| 未钉住 | 倾斜 45° | 收窄为 64px 图标栏（文字隐藏、图标居中），悬停临时展开为浮层（阴影盖在内容上方，不挤压内容），移开自动收起 |

窄屏（≤1100px）为顶部横条布局，图钉按钮隐藏。实现位于 `components/layout/AppShell.tsx`（状态）+ `Sidebar.tsx`（按钮）+ `styles/app.css`（`.is-rail` 模式）。

