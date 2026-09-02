# Mountain 文档归档

本目录保存已经完成、被替代或仅用于审计的材料。归档内容保留原始事实，但不再作为当前产品需求或工程指令。

## plans

- `01-current-architecture.md`：旧Vinext、`webapp/server.py`和内存Job架构快照；
- `06-pr-roadmap.md`：最初九里程碑路线，实际状态已变化；
- `17-project-consolidation-preview-and-archive-plan.md`：目录与Legacy收口阶段计划；
- `18-settings-assets-vertical-delivery.md`：已完成的设置/资产垂直切片契约；
- `19-webui-surface-parity-execution.md`：已完成或被后续分支指令替代的表面对齐计划。

## reports

包含M02–M07审计、映射、CCF/CCB交付报告和纠偏历史。报告只证明某个commit当时的执行结果；后续代码和契约可能已经变化。

## 使用规则

1. 当前工作从上级 [README.md](../README.md) 开始；
2. 不得从归档报告提取字段或命令覆盖现行契约；
3. 排障、追责或核对历史commit时可以引用归档文件；
4. 如归档内容仍约束当前实现，应由PM提炼回现行专题文档，而不是把文件移回顶层；
5. 新的过程报告在对应PR开发期可以存在于分支，合并收口时统一移入`archive/reports/`。
