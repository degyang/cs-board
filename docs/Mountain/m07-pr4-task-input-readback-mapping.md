# M07 PR-4：任务制作输入读取与 Workbench 刷新恢复

## 概述

实现任务制作输入的持久化读取：用户保存文案、参考音频和视觉参数后，刷新页面或重新进入工作台时自动回填所有已保存内容，允许继续标准视频制作流程。

## 术语规范

| 内部字段/API路径 | 用户界面文本 | 说明 |
|---|---|---|
| `project_id` | 不显示 | 内部标识符 |
| `/projects/{project_id}` | 任务工作台 | API路径不变 |
| `project.title` | 任务标题 | 用户可见 |
| `active_run` | 运行 | 后端字段 |

**严禁**：用户界面中不得出现"项目"字样，统一使用"任务"。

## API 契约

### GET /api/v1/projects/{project_id}/inputs

读取已保存的任务制作输入。

**响应（已保存）**:
```json
{
  "project_id": "proj-abc123",
  "saved": true,
  "inputs": {
    "script": "完整文案内容...",
    "style": "极简粗线简笔白板风",
    "include_subtitles": true,
    "pen_text": "",
    "stroke_detail": "detailed"
  },
  "reference_audio": {
    "uploaded": true,
    "filename": "reference.wav",
    "content_type": "audio/wav",
    "size_bytes": 204800
  }
}
```

**响应（未保存）**:
```json
{
  "project_id": "proj-abc123",
  "saved": false,
  "inputs": null,
  "reference_audio": {
    "uploaded": false,
    "filename": null,
    "content_type": null,
    "size_bytes": null
  }
}
```

**错误**: 404 — 任务不存在。

### POST /api/v1/projects/{project_id}/inputs

保存任务制作输入。`reference` 文件为可选（重新保存时可省略，前提是已有参考音频）。

## 前端行为

### Workbench 加载流程

```
fetchProject(projectId)  →  渲染标题、状态
fetchInputs(projectId)   →  回填表单、设置 inputsSaved
fetchCapabilities()      →  检查 Provider 可用性
```

### inputsSaved 状态生命周期

| 事件 | inputsSaved |
|---|---|
| 从 fetchInputs 回填 | `true` |
| 用户编辑任何字段 | `false` |
| 保存成功 | `true` |

### 开始制作按钮逻辑

```
enabled = inputsSaved && hasCapability && !actionLoading
```

- 刷新后 inputsSaved=true（从 API 回填）+ hasCapability=true → 按钮可用
- 编辑任何字段 → inputsSaved=false → 按钮禁用
- 重新保存 → inputsSaved=true → 按钮恢复

### 参考音频显示

- 已保存音频：显示 `已保存参考音频：reference.wav（200.0 KB）`
- 用户选择新文件：显示文件名，隐藏已保存信息
- 保存时：无文件且无已保存音频 → 错误 "请上传参考音频"

## 存储结构

```
{STATE_DIR}/{project_id}/
├── request.json          # 制作输入参数
├── inputs/
│   ├── reference.wav     # 参考音频
│   ├── reference.mp3
│   └── ...
└── runs/
    └── ...
```

## 前端类型

```typescript
interface InputsReadback {
  project_id: string
  saved: boolean
  inputs: {
    script: string
    style: string
    include_subtitles: boolean
    pen_text: string
    stroke_detail: string
  } | null
  reference_audio: {
    uploaded: boolean
    filename: string | null
    content_type: string | null
    size_bytes: number | null
  }
}
```

## 测试覆盖

### 后端（tests/test_mountain_v1_api.py）

| 测试 | 验证点 |
|---|---|
| `test_v1_get_inputs_saved` | 已保存输入返回 saved=true + 完整数据 |
| `test_v1_get_inputs_unsaved` | 无 request.json 返回 saved=false + null |
| `test_v1_get_inputs_not_found` | 不存在的 project_id 返回 404 |
| `test_v1_get_inputs_no_secrets_or_paths` | 响应不含文件路径或密钥 |

### 前端（web-v2/tests/contract.test.tsx）

| 测试 | 验证点 |
|---|---|
| `restores saved inputs from fetchInputs` | 回填文案内容 |
| `shows saved audio filename and size` | 显示音频元数据 |
| `Start button enabled when inputs saved` | 条件满足时按钮可用 |
| `Start button disabled after editing` | 编辑后按钮禁用 |
| `Start button disabled when unsaved` | 未保存时按钮禁用 |

## 验证路径

1. 创建任务 → 进入工作台
2. 填写文案、上传参考音频、设置参数 → 保存
3. 刷新页面（F5）
4. 验证：文案回填、音频信息显示、"开始制作"按钮可用
5. 编辑文案 → 按钮禁用
6. 重新保存 → 按钮恢复
7. 点击"开始制作"→ 启动运行

## Gate 清单

```bash
.venv/bin/python -m pytest -q              # 后端测试
npm --prefix web-v2 run build              # TypeScript 编译
npm --prefix web-v2 test                   # 前端测试
git diff --check                           # 无 trailing whitespace
```
