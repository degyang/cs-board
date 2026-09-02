# M06 Audit — PR-1: Storyboard + Illustrations

**Date:** 2026-08-29
**Scope:** StoryboardService、IllustrationService、Artifact 文档生成、Commands 集成
**Status:** ✅ Complete

---

## Deliverables

### 1. StoryboardService (`csboard/application/storyboard.py`)

| Aspect | Details |
|--------|---------|
| 依赖 | TextModelPort、av-plan、timeline |
| 输出 | `planning.storyboard` artifact |

**关键行为：**
- 读取 av-plan 获取 Voice Units 和 Visual Items
- 读取 timeline 获取每个 Visual 的时长
- 调用 TextModelPort 生成全局视觉 bible（风格、色彩、构图规则、情感基调）
- 为每个 Visual Item 生成 prompt、negative_prompt、composition
- 构建 storyboard document 并提交 artifact

**容错：**
- TextModel 返回无效 JSON 时使用默认 bible
- 缺少 av-plan 或 timeline 时抛出 ValueError

### 2. IllustrationService (`csboard/application/illustrations.py`)

| Aspect | Details |
|--------|---------|
| 依赖 | ImageModelPort、storyboard |
| 输出 | `illustrations.manifest` artifact + 图片文件 |

**关键行为：**
- 读取 storyboard 获取每个 Visual 的 prompt
- 调用 ImageModelPort 生成图片
- 保存图片到 `media/images/` 目录
- 计算 SHA256 hash
- 构建 illustration manifest 并提交 artifact

**单图重试：**
- 支持 `visual_id` 参数只生成指定 Visual 的插画
- 用于 `stage retry --visual` 场景

### 3. Artifact 文档生成 (`csboard/application/av_artifacts.py`)

**新增函数：**

| 函数 | Artifact Key |
|------|-------------|
| `storyboard_document()` | `planning.storyboard` |
| `illustration_manifest_document()` | `illustrations.manifest` |
| `render_manifest_document()` | `render.manifest` |
| `final_manifest_document()` | `output.final-manifest` |

### 4. Commands 集成 (`csboard/application/commands.py`)

**新增方法：**

| 方法 | 功能 |
|------|------|
| `plan_storyboard()` | 生成 storyboard |
| `generate_illustrations()` | 生成插画 |
| `_exec_plan_storyboard()` | 阶段执行器（使用 FakeTextModel） |
| `_exec_generate_illustrations()` | 阶段执行器（使用 FakeImageModel） |

**阶段执行器注册：**
- `plan-storyboard` → `_exec_plan_storyboard`
- `generate-illustrations` → `_exec_generate_illustrations`

---

## Tests

### `tests/test_storyboard.py` (6 tests)

| Test | Coverage |
|------|----------|
| `test_returns_storyboard` | 返回 storyboard 文档 |
| `test_visual_count_matches` | Visual 数量正确 |
| `test_bible_generated` | 生成视觉 bible |
| `test_artifact_committed` | artifact 正确提交 |
| `test_visuals_have_prompts` | 每个 Visual 有 prompt |
| `test_missing_av_plan_raises` | 缺少 av-plan 抛异常 |

### `tests/test_illustrations.py` (7 tests)

| Test | Coverage |
|------|----------|
| `test_returns_illustrations` | 返回 illustrations 文档 |
| `test_image_count_matches` | 图片数量正确 |
| `test_artifact_committed` | artifact 正确提交 |
| `test_images_saved_to_disk` | 图片保存到磁盘 |
| `test_single_visual_retry` | 单图重试 |
| `test_missing_visual_id_raises` | 不存在的 visual_id 抛异常 |
| `test_missing_storyboard_raises` | 缺少 storyboard 抛异常 |

---

## Pipeline 集成

`plan-storyboard` 和 `generate-illustrations` 已注册到 PipelineOrchestrator：

```python
pipeline.register_stage("plan-storyboard", self._exec_plan_storyboard)
pipeline.register_stage("generate-illustrations", self._exec_generate_illustrations)
```

现在 pipeline 可以执行 4 个阶段：
- segment-script ✅
- clone-voice ✅
- plan-storyboard ✅ (新)
- generate-illustrations ✅ (新)
- render-visuals ❌ (PR-2)
- compose-video ❌ (PR-2)

---

## Files added/modified

| File | Action |
|------|--------|
| `csboard/application/storyboard.py` | Created (180 lines) |
| `csboard/application/illustrations.py` | Created (140 lines) |
| `csboard/application/av_artifacts.py` | Modified (+30 lines: 4 new document generators) |
| `csboard/application/commands.py` | Modified (+100 lines: plan_storyboard, generate_illustrations, stage executors) |
| `tests/test_storyboard.py` | Created (6 tests) |
| `tests/test_illustrations.py` | Created (7 tests) |
| `tests/test_cli_csboard.py` | Modified (updated unregistered stage test) |

---

## Test results

```
Ran 88 tests in 0.849s — OK
```

所有测试通过。
