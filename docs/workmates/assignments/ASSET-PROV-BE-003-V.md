# ASSET-PROV-BE-003-V — 独立验证任务内资产发现 API

状态：working
Owner：verification
目标工作区：`/mnt/d/Workstation/Projects/cs-board-worktrees/backend`

## Frozen target

- HEAD：`e34ba6e83ef1a6c3ec3ad5274485505379ce0a21`
- 状态哈希：`978ce5a23ed396cb1f51c11ca8e93e86ee9fb9acf2b04edd021744873e3fe52c`
- 实现回执：`docs/workmates/receipts/ASSET-PROV-BE-003.md`（backend worktree）

## Required verification

1. 只读检查 `FilesystemGenerationRecordStore.list_current` 与 `GET /api/v1/tasks/{task_id}/runs/{run_id}/assets`，确认只枚举 current `generation.json`，排序稳定，返回稳定 identity、完整实际 generation record 与服务端相对 `media_url`。
2. 独立创建全新临时 `CSBOARD_DATA_DIR`，通过 TestClient 或 ASGI HTTP transport 实际请求列表 URL；覆盖 image/audio/video、空列表、损坏 JSON、identity mismatch、task/run 缺失与 traversal，并确认错误不泄露绝对路径。
3. 独立复跑 generation-record schema/store、Mountain contracts 与 stage work-order 受影响门禁；必须干净退出，记录命令、退出码、数量、耗时、warnings/skips。任何 timeout/中止输出不得计为通过。
4. 核对 BE-002 的两个单资产 URL 合约未回归，且实现未写真实 `outputs/`、未触碰 Provider/再生成/替换/失效和前端边界。
5. 在验证前后重算状态哈希；若与 frozen target 不同则停止并报告 `TARGET_MOVED`，不得对漂移状态给 PASS。
6. 运行项目验证入口：`./scripts/workmates verify --role verification --evidence <本轮新的本地证据路径>`；证据路径不得包含秘密、真实素材或完整凭据。

## Deliverable

写入 `docs/workmates/receipts/ASSET-PROV-BE-003-V.md`，给出明确 `PASS` 或 `FAIL`、逐项标准结论、实际命令/退出码/计数/耗时、冻结哈希复核和剩余风险。不得修改产品实现或共享看板；完成后停止。
