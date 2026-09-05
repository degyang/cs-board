# PRESET-VOICE-UX-002-BE — 预置音色创建契约修复

`worker_backend`，请只修复 `PRESET-VOICE-UX-001-V` 定位的创建契约问题。

工作目录：`/mnt/d/Workstation/Projects/cs-board`

输入：`docs/workmates/receipts/PRESET-VOICE-UX-001-V.md`。

回执写入：`docs/workmates/receipts/PRESET-VOICE-UX-002-BE.md`

必须完成：

- 保持既定 Provider/service + model + remote voice 稳定身份规则。当 UI 的预置音色 create 请求未提供 `profile_id` 时，后端从该稳定身份确定性生成合法的 `profile_id` 并返回创建结果；不要要求前端硬编码厂商或猜测 ID。
- 明确冲突/重复行为：同一规范化身份的重复 create 必须有安全、确定的结果；不同 provider/model/remote voice identity 不得碰撞。
- 在 `tests/test_voice_profiles_api.py` 增加非 mock 的 in-process API 回归：提交与现有 UI 相同、无 `profile_id` 的 body，应成功并返回稳定 ID；验证重建/重复和同名异身份规则。该测试不得只调用内部 catalog 方法。

边界：仅修改 `csboard/application/voice_profiles.py`、直接相关 native voice-profile API 文件与 `tests/test_voice_profiles_api.py`，以及本回执；不改 `web-v2`、动态信息图规划、服务进程或无关路径。不重启 5182/8000，不提交、不推送、不加 skip。

门槛：focused voice-profile API tests 和适当受影响后端 suite 均通过；回执记录命令、退出码、通过/失败/skip 数和耗时。完成后交回独立验证，不得自行验收。
