# WebUI 原型变更记录

本文件记录经过产品确认的原型变化。第三方工具修改原型时，应在“未冻结”下说明页面、交互和状态变化；确认后再更新 `docs/Mountain/webui-prototype-baseline/` 的截图和验收矩阵。

## 未冻结

- 无。

## 2026-09-01：建立独立原型源

- 从 `docs/Mountain/webui-prototype-baseline/source/` 迁移到 `prototypes/webui/`。
- 明确原型允许 fixture/mock 用于交互展示，但生产 `web-v2/` 禁止复制这些数据路径。
- `docs/Mountain/webui-prototype-baseline/` 改为冻结基准，不再作为第三方工具的工作目录。
