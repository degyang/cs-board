"""AssetRef — 资产引用领域模型。

hash 去重：相同内容 → 相同 asset_id。
路径安全：禁止 ..、绝对路径。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class AssetRef:
    """资产引用。"""

    asset_id: str  # 内容 hash (sha256)
    original_name: str
    mime_type: str
    size_bytes: int
    storage_path: str  # 相对路径，不含 DATA_DIR 前缀
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> AssetRef:
        return cls(
            asset_id=str(value["asset_id"]),
            original_name=str(value["original_name"]),
            mime_type=str(value["mime_type"]),
            size_bytes=int(value["size_bytes"]),
            storage_path=str(value["storage_path"]),
            created_at=str(value["created_at"]),
        )
