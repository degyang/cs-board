"""Idempotently install the initial read-only Precondition catalog."""

from __future__ import annotations

import json
from pathlib import Path

from csboard.adapters.filesystem.asset_repository import FilesystemAssetRepository


ROOT = Path(__file__).resolve().parents[2]


def _preview_asset_id(repository: FilesystemAssetRepository, relative_path: str) -> str:
    """Store a project-owned preview as an opaque blob reference, never a path."""
    source = ROOT / relative_path
    if not source.is_file():
        return ""
    return repository.save_asset(
        source.read_bytes(), source.name, "image/png"
    ).asset_id


def seed(data_dir: Path) -> dict[str, int]:
    """Persist the safe legacy-inventory catalog without reading legacy runtime state."""
    repository = FilesystemAssetRepository(data_dir)
    catalog_path = data_dir / "assets" / "preconditions" / "preconditions.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing = json.loads(catalog_path.read_text(encoding="utf-8")) if catalog_path.exists() else []
    except (json.JSONDecodeError, OSError):
        existing = []
    if not isinstance(existing, list):
        existing = []
    existing_ids = {item.get("precondition_id") for item in existing if isinstance(item, dict)}

    catalog = [
        {
            "precondition_id": "precondition-visual-explainer-default",
            "revision": 1,
            "name": "通用讲解者",
            "kind": "visual-explainer",
            "applies_to": ["storyboard", "illustration"],
            "status": "active",
            "enabled": True,
            "engine_compatibility": ["whiteboard"],
            "preview_asset_id": _preview_asset_id(repository, "assets/style-references/oil-visual/explainer-cost-comparison.png"),
            "description": "原文未指定人物且画面确实需要讲解角色时可用的通用视觉约束。",
            "condition_text": "仅在原文未指定人物或动物身份时使用；不覆盖 Style revision 内的人物约束。",
        },
        {
            "precondition_id": "precondition-renderer-hand-default",
            "revision": 1,
            "name": "白板绘制手",
            "kind": "renderer-hand",
            "applies_to": ["whiteboard"],
            "status": "active",
            "enabled": True,
            "engine_compatibility": ["whiteboard"],
            "preview_asset_id": _preview_asset_id(repository, "assets/drawing-hand-clean.png"),
            "description": "白板渲染阶段使用的基础绘制手和笔尖兼容性约束。",
            "condition_text": "品牌文字属于 Task 渲染设置；派生手部文件和 handPath 不属于此资产。",
        },
    ]
    additions = [item for item in catalog if item["precondition_id"] not in existing_ids]
    if additions:
        tmp = catalog_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(existing + additions, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(catalog_path)
    return {"count": len(additions)}
