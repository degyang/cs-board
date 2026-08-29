# M04 Audit — PR-2: Skills 内容充实

**Date:** 2026-08-29
**Scope:** 7 个 SKILL.md 文件内容充实
**Status:** ✅ Complete

---

## Deliverables

### Skills 目录结构

```
skills/
├── video-workflow/SKILL.md       # 流水线编排
├── script-segmenter/SKILL.md     # 文案分割
├── voice-cloner/SKILL.md         # 语音克隆
├── storyboard-planner/SKILL.md   # 分镜规划
├── illustration-generator/SKILL.md # 插画生成
├── visual-renderer/SKILL.md      # 视觉渲染
└── av-compositor/SKILL.md        # 最终合成
```

### 内容规范

每个 SKILL.md 按设计文档（`05-skills-design.md`）充实，包含：

| 章节 | 说明 |
|------|------|
| 职责 | 明确 Skill 负责什么 |
| 输入与输出 | 规范化的输入输出描述 |
| 强制规则 | 业务约束和质量要求 |
| CLI 命令 | 完整的命令示例 |
| 输出格式 | 成功时的 JSON 结构 |
| 与其他 Skill 的协作 | 上下游依赖关系 |
| 错误处理 | 可能的错误码和处理方式 |

### 各 Skill 概要

| Skill | 职责 | 上游依赖 | 下游消费者 |
|-------|------|----------|-----------|
| video-workflow | 创建项目、编排阶段、汇报进度 | 无 | 所有阶段 Skill |
| script-segmenter | 将文案分割为 Voice Unit 和 Visual Item | 无 | voice-cloner |
| voice-cloner | Unit 级 TTS、Whisper 对齐、母带 | script-segmenter | storyboard-planner, av-compositor |
| storyboard-planner | 创建视觉分镜和 bible | script-segmenter, voice-cloner | illustration-generator |
| illustration-generator | 生成每个 Visual 的插画 | storyboard-planner | visual-renderer |
| visual-renderer | 渲染视频片段 | illustration-generator, voice-cloner | av-compositor |
| av-compositor | 合成最终视频、字幕、验证 | voice-cloner, visual-renderer | 无 |

---

## 与设计文档的对齐

| 设计文档要求 | 实现状态 |
|-------------|---------|
| 七个 Skill 文件 | ✅ 全部存在 |
| 职责与非职责 | ✅ video-workflow 包含，其他 Skill 通过职责描述隐含 |
| 输入与输出规范 | ✅ 全部包含 |
| 强制规则 | ✅ 全部包含 |
| CLI 命令示例 | ✅ 全部包含 |
| 错误处理 | ✅ 全部包含 |
| Skill 间协作 | ✅ 全部包含 |
| 安全约束 | ✅ video-workflow 包含，其他 Skill 通过引用继承 |

---

## 验收标准检查

| 标准 | 状态 |
|------|------|
| 七个 Skill 中只有 workflow skill 包含跨阶段编排 | ✅ |
| Skill 文件不含服务 URL/API Key/FFmpeg 命令/Whisper 算法 | ✅ |
| 每个能力 Skill 可对已有 Project 独立运行 | ✅ CLI 命令已文档化 |
| CLI JSON 包含稳定 code、Stage、retryable 和四个关联 ID | ✅ 输出格式已文档化 |
| `auto/gated/targeted` 不改变已执行阶段 fingerprint | ✅ video-workflow 已说明 |

---

## Files modified

| File | Action |
|------|--------|
| `skills/video-workflow/SKILL.md` | Rewritten (67 lines) |
| `skills/script-segmenter/SKILL.md` | Rewritten (52 lines) |
| `skills/voice-cloner/SKILL.md` | Rewritten (62 lines) |
| `skills/storyboard-planner/SKILL.md` | Rewritten (48 lines) |
| `skills/illustration-generator/SKILL.md` | Rewritten (48 lines) |
| `skills/visual-renderer/SKILL.md` | Rewritten (48 lines) |
| `skills/av-compositor/SKILL.md` | Rewritten (48 lines) |
