# Mountain WebUI v2

Mountain 山野小读 — 新版 WebUI（Vite + React + TypeScript）

## 快速开始

```bash
# 安装依赖
npm install

# 启动开发服务器（默认 http://localhost:5175）
npm run dev

# 构建生产版本
npm run build

# 运行测试
npm test

# 预览构建产物
npm run preview
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000/api/v1` | 后端 API 地址 |

创建 `.env.local` 文件覆盖默认值：

```env
VITE_API_BASE_URL=http://your-server:8000/api/v1
```

**安全要求**：禁止将 API Key、Secret 或任何敏感信息写入前端环境变量、localStorage、sessionStorage、URL 或构建产物。

## 路由表

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | ProjectsPage | 任务队列（状态筛选 + 搜索 + 15s 轮询） |
| `/projects/new` | CreateProjectPage | 新建任务 |
| `/projects/:projectId` | ProjectWorkbenchPage | 工作台（三栏布局：配音单元 / 阶段工作区 / 产物） |
| `/projects/:projectId/runs/:runId/diagnostics` | RunDiagnosticsPage | 运行诊断（事件流 + 日志） |
| `/settings/providers` | ProvidersPage | Provider 配置列表 |
| `/settings/providers/:name` | ProviderDetailPage | Provider 详情与配置 |
| `/help` | HelpPage | 帮助中心 |

## API 映射表

| 前端功能 | HTTP 方法 | API 端点 |
|----------|-----------|----------|
| 健康检查 | GET | `/health` |
| 能力查询 | GET | `/capabilities` |
| Provider 列表 | GET | `/providers` |
| Provider 详情 | GET | `/providers/{name}` |
| 更新配置 | PUT | `/providers/{name}/config` |
| 查看密钥状态 | GET | `/providers/{name}/secrets` |
| 设置密钥 | POST | `/providers/{name}/secrets` |
| 删除密钥 | DELETE | `/providers/{name}/secrets/{key}` |
| 项目列表 | GET | `/projects` |
| 创建项目 | POST | `/projects` |
| 项目详情 | GET | `/projects/{id}` |
| 运行详情 | GET | `/projects/{id}/runs/{runId}` |
| 取消运行 | POST | `/projects/{id}/runs/{runId}/cancel` |
| 重试运行 | POST | `/projects/{id}/runs/{runId}/retry` |
| 阶段列表 | GET | `/projects/{id}/runs/{runId}/stages` |
| 配音单元 | GET | `/projects/{id}/runs/{runId}/units` |
| 产物列表 | GET | `/projects/{id}/runs/{runId}/artifacts` |
| 事件流 | GET | `/projects/{id}/runs/{runId}/events` |
| 日志 | GET | `/projects/{id}/runs/{runId}/logs` |
| 下载成片 | GET | `/projects/{id}/runs/{runId}/final` |

## 项目结构

```
web-v2/
├── src/
│   ├── main.tsx              # 入口
│   ├── app/
│   │   ├── router.tsx        # 路由定义（createBrowserRouter）
│   │   └── providers.tsx     # 全局 Provider（AppContext + Health 轮询）
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppShell.tsx  # 布局骨架（pin/rail 模式）
│   │   │   └── Sidebar.tsx   # 侧边导航（原型结构 + 运行状态 footer）
│   │   └── ui/
│   │       ├── Tabs.tsx       # 状态筛选标签
│   │       ├── StatusBadge.tsx# 状态徽章
│   │       ├── CopyButton.tsx # 复制按钮
│   │       └── BackButton.tsx # 返回按钮
│   ├── pages/
│   │   ├── ProjectsPage.tsx        # 任务队列
│   │   ├── CreateProjectPage.tsx   # 新建任务
│   │   ├── ProjectWorkbenchPage.tsx# 工作台（三栏布局）
│   │   ├── RunDiagnosticsPage.tsx  # 运行诊断
│   │   ├── HelpPage.tsx           # 帮助中心
│   │   ├── ProvidersPage.tsx      # Provider 列表
│   │   └── ProviderDetailPage.tsx # Provider 详情
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts     # API 客户端
│   │   │   ├── types.ts      # TypeScript 类型
│   │   │   └── queries.ts    # useAsync Hook（轮询支持）
│   │   └── formatting.ts     # 格式化工具
│   └── styles/
│       ├── tokens.css        # 设计 Token（NovaTech）
│       └── app.css           # 组件样式
└── tests/
    ├── setup.ts
    ├── api-client.test.ts
    ├── providers-page.test.tsx
    └── create-project.test.tsx
```
