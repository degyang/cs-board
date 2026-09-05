# M09-INFRA-ADAPTER-002 — P2 实现回执

状态：`READY_FOR_INDEPENDENT_P2_VERIFICATION`

本回执只报告 P2 实现和执行证据，**不是**独立验证或 PM 验收；未授权 P3/P4/P5/P6、real render、Task 创建、capability activation 或 submission。

## 交付

- `InfographicStoryboardAdapter` 只消费 P1 `InfographicStoryboard v1`，输出 `schemaVersion: 1` props，并使用 P1 的 floor cue-frame / ceil duration-frame 语义和 run-relative asset validation。
- `RemotionRendererAdapter` 只消费 P1 已提交 `infographic_storyboard` artifact；不从旧 planning fragments 重新构造 storyboard。
- renderer 在当前 run 的 `.remotion-private/` 写临时 props，执行锁定的 render script argv，finally 清理 props；输出目录被限制为当前 run 内。
- 非空候选 MP4 必须通过 ffprobe 容器格式、视频流、正时长、正尺寸以及 props 尺寸匹配验证；probe 失败、无输出或空输出均不会返回成功，probe failure 会删除候选输出。
- 子进程 nonzero、timeout、缺 Node、坏 JSON/P1 props、ffprobe 失败/尺寸不匹配均映射为稳定、无绝对路径/secret 的错误；adapter AST test 确认无 `webapp` import。
- P2 仅声明 renderer prerequisite contract 给 P3a/P4 消费；没有自行探测、宣布 readiness 或改变 capability。

## 测试证据

| 命令 | 结果 |
| --- | --- |
| `.venv/bin/python -m pytest -q tests/test_remotion_renderer_adapter.py tests/test_infographic_storyboard_adapter.py tests/test_infographic_contract_fixture.py` | PASS — `72 passed in 0.87s` |
| `npm --prefix video_renderer run build` | PASS — `tsc --noEmit` |
| `git diff --check` | PASS — 无输出 |

直接 adapter 测试覆盖 mock success/nonzero/timeout、坏 props、缺 Node、run-private temp cleanup、ffprobe invalid/dimension mismatch、候选输出删除、路径/secret 脱敏和无 legacy import。

## 边界确认

未修改 domain schema、capabilities、commands/API/CLI、legacy/webapp 或前端；未执行真实 render、未生成 MP4、未创建任务、未开放 capability/submission、未 commit/push。
