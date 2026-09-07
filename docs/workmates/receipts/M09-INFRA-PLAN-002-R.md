# M09-INFRA-PLAN-002-R — P3a 职责单一真源修订回执

结论：**READY_FOR_INDEPENDENT_PLAN_VERIFICATION**。仅修订计划与本回执；未改产品代码、测试、配置或看板，未运行 render、未创建任务、未开放 submission，未提交或推送。

## 对 FAIL 的逐项修订映射

- FAIL 指出 P3a 同时被要求和禁止检查 Node、脚本、锁定依赖、browser、FFmpeg/ffprobe。计划现于“Capability”定义中把 P3a 定义为唯一 bootstrap/toolchain 诊断真源；P3a 工作包的目的、输入/输出、测试、entry/exit 和禁止项统一为只读、fail-closed 的 Node、render script、lockfile、Remotion/browser、FFmpeg/ffprobe、服务/secret/probe 与 external gate 检查。它不执行 render、不读 P2/P6 evidence、也不 activation 或宣告 supported。
- P3a 的稳定 fail-closed reason-code 所有权集中在 real-render gate 的 P3a matrix：`NODE_NOT_FOUND` 至 `EXTERNAL_STAGE_BLOCKED`；P3b/create-options 的 activation codes 保持独立，不由 P3a 诊断替换。
- P4 entry 明确合流 P2 adapter contract 与 P3a bootstrap/toolchain diagnosis；两者缺一不可，合流后仍仅允许 internal/test 真实任务通道，不能使 create-options available 或开放用户/API/WebUI 提交。
- P6 entry 保持 P1、P2、P3a、P4、P5 全部 exit 且 P3a `bootstrap_ready=true`；P6 不依赖 P3b。依赖图及其说明维持 `P1 → (P2 || P3a) → P4 → P5 → P6 → P3b/P7`，没有反向边或循环。
- 修正 next queue 中错误的 `PLAN-003` 前置，改为本次 **PLAN-002-R 独立 PASS** 后才能派 P1；P1 独立 PASS 后才并行 P2/P3a，之后严格 P4→P5→P6→P3b，最后联调仍需独立产品授权。

## 检查

```text
git diff --check
exit 0
```

未运行测试或真实渲染：本任务为计划文本修订，运行它们会越过任务边界。停止于此，等待独立计划验证；本回执不自行接受计划，也不授权派发 P1。
