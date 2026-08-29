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
| `/` | ProjectsPage | 项目列表 |
| `/projects/new` | CreateProjectPage | 创建项目 |
| `/projects/:id` | ProjectDetailPage | 项目详情 |
| `/settings/providers` | ProvidersPage | Provider 配置列表 |
| `/settings/providers/:name` | ProviderDetailPage | Provider 详情与配置 |

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

## 开发代理

开发模式下，Vite 会将 `/api` 请求代理到后端服务器。默认后端地址为 `http://127.0.0.1:8000`。

如需修改代理目标，编辑 `vite.config.ts`：

```ts
server: {
  proxy: {
    '/api': {
      target: 'http://your-server:port',
      changeOrigin: true,
    },
  },
},
```

## 项目结构

```
web-v2/
├── src/
│   ├── main.tsx              # 入口
│   ├── app/
│   │   ├── router.tsx        # 路由定义
│   │   └── providers.tsx     # 全局 Provider
│   ├── components/
│   │   └── layout/
│   │       └── AppShell.tsx  # 布局骨架
│   ├── pages/
│   │   ├── ProjectsPage.tsx
│   │   ├── CreateProjectPage.tsx
│   │   ├── ProjectDetailPage.tsx
│   │   ├── ProvidersPage.tsx
│   │   └── ProviderDetailPage.tsx
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts     # API 客户端
│   │   │   └── types.ts      # TypeScript 类型
│   │   └── formatting.ts     # 格式化工具
│   └── styles/
│       ├── tokens.css        # 设计 Token
│       └── app.css           # 组件样式
└── tests/
    ├── setup.ts
    ├── api-client.test.ts
    ├── providers-page.test.tsx
    └── create-project.test.tsx
```
