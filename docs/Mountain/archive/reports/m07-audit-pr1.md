# M07 PR-1 审计报告

## 范围

Project API 增强 — 完整 6 阶段 Pipeline API 端点

## 变更清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `webapp/mountain_api.py` | 修改 | 添加缺失的 API 端点 |
| `tests/test_mountain_api.py` | 新增 | API 端点测试 |

## 新增 API 端点

### 阶段操作端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/mountain/projects/{id}/runs/{id}/stages/plan-storyboard` | POST | 生成分镜 |
| `/api/mountain/projects/{id}/runs/{id}/stages/generate-illustrations` | POST | 生成插画 |
| `/api/mountain/projects/{id}/runs/{id}/stages/render-visuals` | POST | 渲染视觉 |
| `/api/mountain/projects/{id}/runs/{id}/stages/compose-video` | POST | 合成视频 |

### Pipeline 操作端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/mountain/projects/{id}/runs/{id}/pipeline/run` | POST | 运行 Pipeline |
| `/api/mountain/projects/{id}/runs/{id}/pipeline/resume` | POST | 恢复 Pipeline |

### Stage 重试端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/mountain/projects/{id}/runs/{id}/stages/{stage}/retry` | POST | 重试指定阶段 |

### 产物端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/mountain/projects/{id}/runs/{id}/artifacts` | GET | 列出所有产物 |
| `/api/mountain/projects/{id}/runs/{id}/artifacts/{key}/content` | GET | 获取产物内容 |

## 架构符合性

### 六边形架构

- API 端点仅做 request/response 转换
- 业务逻辑通过 MountainCommands 调用
- 无直接操作文件系统或 Provider

### Pipeline 集成

- 所有 6 个阶段都有对应的 API 端点
- 支持 auto/gated/targeted 三种策略
- 支持 pipeline run/resume 操作

## 测试覆盖

### API 端点测试 (13 tests)

- ✅ capabilities 返回能力列表
- ✅ 创建项目
- ✅ 列出项目
- ✅ 获取项目详情
- ✅ 项目不存在返回 404
- ✅ 分割文案
- ✅ 生成分镜
- ✅ 运行 Pipeline
- ✅ Stage 重试不存在返回 404
- ✅ 列出产物
- ✅ 获取产物内容
- ✅ 获取 Trace
- ✅ 获取事件

## 验证命令

```bash
# 运行 API 测试
python -m unittest tests.test_mountain_api -v

# 运行所有测试
python -m unittest discover tests -v
```

## 结论

M07 PR-1 完成了 Project API 的增强，包括：

1. ✅ 所有 6 个阶段的 API 端点
2. ✅ Pipeline run/resume 端点
3. ✅ Stage retry 端点
4. ✅ 产物列表和内容端点
5. ✅ 140 个测试全部通过

API 现在支持完整的 6 阶段 pipeline 操作，可以继续 M07 PR-2 (Vite WebUI) 的实施。
