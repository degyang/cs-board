# 预置风格资产基准

## 范围

本快照从 `/mnt/d/Workstation/SynologyDrive/workbuddy/Workshop/mountain` 同步，覆盖原型资产管理中的 13 个预置风格及其图片、提示词和路由参数。

- 参数权威快照：`source/src/features/asset-management/assetStore.ts`
- 图片根目录：`source/public/styles/`
- 图片校验：`source/public/styles/SHA256SUMS`
- 原始参数来源：旧 `webapp/server.py` 的 `STYLE_PRESETS` 与 `INFOGRAPHIC_STYLE`
- 深度参考图来源：项目 `assets/style-references/paper-metaphor` 和 `assets/style-references/oil-visual`
- `oil-visual` 的来源与 MIT 许可随图片保存在同目录的 `SOURCE.md` 和 `LICENSE`

## 风格清单

| ID | 名称 | 主预览 | 参考图 |
| --- | --- | --- | ---: |
| ps-cs-1 | 极简粗线简笔白板风 | `previews/minimal-whiteboard.webp` | 1 |
| ps-cs-2 | 极简商务涂鸦风 | `previews/business-doodle.webp` | 1 |
| ps-cs-3 | 暖米黄素描白板风 | `previews/warm-pencil.webp` | 1 |
| ps-cs-4 | 粗线扁平国风卡通 | `previews/guofeng-flat.webp` | 1 |
| ps-cs-5 | 爆款高热吸睛风 | `previews/viral-pop.webp` | 1 |
| ps-cs-6 | 黑金科技发布会风 | `previews/black-gold-tech.webp` | 1 |
| ps-cs-7 | 清新治愈手账风 | `previews/healing-journal.webp` | 1 |
| ps-cs-8 | 复古报纸拼贴风 | `previews/retro-collage.webp` | 1 |
| ps-cs-9 | 纸感隐喻拼贴风 | `paper-metaphor/01-cause-heart-vs-wound.png` | 11 |
| ps-cs-10 | 漫画墨线解释风 | `oil-visual/from-complex-to-clear.png` | 6 |
| ps-cs-11 | 3D黏土趣味风 | `previews/clay-3d.webp` | 1 |
| ps-cs-12 | 赛博霓虹漫画风 | `previews/cyber-neon.webp` | 1 |
| ps-cs-13 | 国风动态信息图 | 暂无图片 | 0 |

这里的“参考图”按 `assetStore.ts` 中主图和 `refImages` 的产品关系计数；磁盘实际为 27 个图片文件，其中两个 previews 是对应深度参考图的副本。

## 参数边界

每个预置风格至少保留 `id/name/image/intro/source`，并可包含：

- `shortDesc`：卡片摘要；
- `tags`：检索及风格路由关键词；
- `badge`：热门或新增标识；
- `refImages`：多参考图列表；
- `prompt`：可选英文提示词，空值时以 `intro` 为最终视觉配方。

`纸感隐喻拼贴风` 和 `漫画墨线解释风` 的 `intro` 还包含按文案语义选择参考图的路由规则，正式资产模板不得只保留主预览图而丢失这些规则。

## 实现注意

本目录是设计与迁移基准，不是运行时资产仓储。正式后端应把这些种子迁移为只读 preset StyleTemplate，并通过资产 API 返回逻辑 asset ID/URL；不得把原型的 localStorage 存储、data URL 或绝对路径迁入生产实现。自定义风格由用户复制 preset 后产生，不能直接修改 preset。
