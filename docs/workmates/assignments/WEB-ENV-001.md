# WEB-ENV-001 — 5182 单实例部署

`worker_env`，请接手 5182 联调环境收敛。

工作目录：`/mnt/d/Workstation/Projects/cs-board`

遵照：`docs/workmates/team-contract.md` 的 WebUI Definition of done。

回执写入：`docs/workmates/receipts/WEB-ENV-001.md`

本轮动作：

- 确认 8000 只存在一个监听进程，并使用项目 `.venv`。
- 确认 5182 只存在一个 Vite 监听进程，cwd/入口为当前 `web-v2`。
- 如需重启，精确终止旧 PID 后再启动；禁止叠加多个版本。
- 验证 `/api/v1/health`、5182 根页面及 `/settings/voice-alignment` 均可访问。

完成门槛：回执包含监听 PID、命令行、HTTP 状态和启动日志位置。

注意事项：不得修改产品代码，不得创建第二套服务，不得提交。
