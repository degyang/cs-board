# MEDIA-SKILLS-003 Review

- Reviewer: PM (`/root/pm`)
- Delivery: `eb2a985`
- Base: `7bc8af9`
- Verdict: **CHANGES_REQUESTED**
- Next attempt: 2

## 已通过部分

- 变更严格限制在七个 Skill、确定性 linter、测试/失败 fixture 和报告；
- Project/聊天输入、`--script`、`--reference`、`--tts-url`、`--tts-mode` 已从项目 Skills 清除；
- 六 Stage 示例使用 `task_id/run_id`，持久化参数、相对路径、结构化结果和 Artifact 边界已经写明；
- 独立复现 linter exit 0、失败 fixture exit non-zero、`2 passed`、forbidden rg 与 diff-check 通过。

## 必须纠正

1. `visual-anchor-generator` 写成“输入 Artifact：`planning.av-plan`，输出 Artifact：
   `planning.av-plan`”。第一阶段真实输入是 WebUI 已持久化的 script preparation/设置；当前自循环会让
   Codex 在第一个 Stage 前寻找一个尚不存在的输出。
2. `illustration-generator` 明确说 external candidate Gate 的 retry 尚未实现，却紧接着展示
   `stage retry ... generate-illustrations --visual`。这仍会诱导 Codex 执行本 Skill 自己声明不存在的
   Gate。linter 反而强制要求该矛盾命令。
3. linter 用“token 在文件中出现”代替 inputs/outputs 语义验证，因而没有捕获上述自循环。失败
   fixture 目前只证明旧 `--reference` 会失败。
4. 任务要求全量测试终态；报告诚实说明两次未结束。PM 独立运行到 176.99 秒、223 passed/4 skipped
   后仍未结束并手动中断。这不是通过证据，返工应按组定位，而不是继续无界等待。

## 有界范围

只纠正两份 Skill、linter 结构/fixture 和报告证据；不推翻已正确的五份 Stage Skill 和 workflow，
不进入生产实现。
