# CS Board WebUI v2

`web-v2/` 是 Mountain 新 WebUI 的独立工作目录。它将在 M07 实现为纯 React + Vite SPA，并由 FastAPI 在生产环境同源托管其 `dist`。

当前 M01 只建立目录边界，不创建应用或更改启动器：

- 现有 `web/` 仍是 legacy Vinext 前端，也是当前唯一运行入口；
- `web-v2/` 不导入 legacy `web/` 的页面、状态或构建产物；
- 未来共享的 API 类型只能来自稳定 API Schema/生成客户端，不能通过相对路径跨目录导入；
- 新前端开发端口、构建、部署和 FastAPI 静态托管会在 M07 接入；
- 删除 legacy `web/` 只能在新工作台稳定并完成历史任务回归后单独决定。

目录隔离用于保证新 UI 可以渐进开发、独立构建和独立回滚，而不会影响现有用户入口。
