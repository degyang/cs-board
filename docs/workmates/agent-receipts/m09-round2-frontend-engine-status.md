# M09 第二轮调度 — Frontend 回执

状态：无需新增代码，既有实现已覆盖；未提交。
日期：2026-09-05

## 发现

前端 `CreateTaskPage.tsx` 已实现完整的引擎只读状态/错误呈现：

1. **引擎选择网格**（line 115）：`engineDisplayOptions` 遍历后端返回的引擎列表，`!item.available` 时显示 `status-pill limited` 标签"暂未开放"
2. **原因展示**：禁用引擎卡片底部显示 `服务端：{item.reason || '能力未就绪'}`
3. **只读预览按钮**：infographic-remotion 不可用时显示"预览成片设置"按钮，点击后进入只读预览模式
4. **只读模式提示**（line 129）：`previewEngine` 非空时显示 "只读预览：动态信息图未被当前服务端开放，本页不会把它写入任务"
5. **提交拦截**：`validate()` 中 `if (!engine || !engine.available) errors.engine = ...` 阻止提交不可用引擎的任务
6. **测试覆盖**（create-task.test.tsx line 9）：OPTIONS fixture 已包含 `infographic-remotion available: false`；line 199 测试了引擎开放后的切换行为

## 后端联动

本轮 Backend 已修改 `commands.py create_options()` 动态返回 infographic-remotion 引擎条目。前端无需修改，只需后端部署后前端自动消费新的引擎状态。

## 验证

```text
cd web-v2 && npx vitest run tests/create-task.test.tsx
41 passed
```

## 不需要前端变更的原因

- 引擎列表来自 `/api/v1/tasks/create-options`，后端已动态返回
- 前端已有完整的 `available`/`!available` 分支渲染逻辑
- 前端已有 infographic-remotion 的 reason 显示和只读预览
- 测试 fixture 已覆盖 infographic 引擎状态
