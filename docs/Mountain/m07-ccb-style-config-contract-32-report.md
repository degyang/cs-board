# CCB Style config contract-32 回执

## §1 执行基线与变更文件

基线 `cb22f68`；实现提交 `4db1869`。变更为 StyleTemplate 领域模型、资产 API 和领域专项测试。

## §2 Style config 领域与持久化兼容

`config` 是稳定对象字段，序列化持久化；旧 style 数据缺失或空值重建为 `{}`。copy 到 custom 深拷贝 config；preset 的 repository 与 HTTP 修改/删除限制未变。

## §3 API DTO 矩阵

list、preset list、detail、create、patch、copy 都通过 `StyleTemplate.to_dict()` 返回 `config`。Router 不拼接缺失字段；create/patch 非对象 config 返回验证错误。

本轮以真实 HTTP 覆盖 create→detail→patch→list 的 config 等值回读、create/patch 非对象拒绝，以及 preset copy 的 config 深拷贝。preset 的 patch/delete/activate/deactivate 既有拒绝边界保持不变。

## §4 专项和全量测试

专项：`tests/test_style_template.py tests/test_asset_repository.py tests/test_mountain_asset_api.py`，52 passed，6.79s。

全量：558 passed、5 skipped、4 warnings、3 subtests passed，96.33s，exit 0（低于 180 秒门禁）。

## §5 真实 CCF checker

使用临时 data dir 启动真实 `webapp.mountain_server`，以 `MOUNTAIN_API_BASE=http://127.0.0.1:18765/api/v1 node web-v2/scripts/check-api-contract.mjs` 运行 production checker，正常退出且 0 violation。该事实不构成 CCF 检查点 B 声明。

## §6 进程清理、clean status 和提交 hash

实现提交 `4db1869 fix(mountain): persist style template config dto`；测试提交 `519e1ff test(mountain): cover style config dto contract`；本报告为独立本地提交。测试和 checker 服务均正常退出；只本地提交，不推送。

## §7 未完成项

无。
