"""StyleTemplate — 风格模板领域模型。

preset 只读，只允许查看和复制为 custom。
删除只允许停用（status=inactive），不做不可恢复的物理删除。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class StyleTemplate:
    """风格模板。"""

    style_id: str
    revision: int
    name: str
    kind: str  # "preset" | "custom"
    prompt_text: str
    engine: str = "whiteboard"
    description: str = ""
    negative_prompt: str = ""
    tags: list[str] = field(default_factory=list)
    preview_asset_id: str = ""
    status: str = "active"  # "active" | "inactive"
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> StyleTemplate:
        return cls(
            style_id=str(value.get("style_id", value.get("template_id", ""))),
            revision=int(value.get("revision", 1)),
            name=str(value["name"]),
            kind=str(value["kind"]),
            prompt_text=str(value["prompt_text"]),
            engine=str(value.get("engine", "whiteboard")),
            description=str(value.get("description", "")),
            negative_prompt=str(value.get("negative_prompt", "")),
            tags=[str(v) for v in value.get("tags", [])],
            preview_asset_id=str(value.get("preview_asset_id", "")),
            status=str(value.get("status", "active")),
            created_at=str(value.get("created_at", "")),
            updated_at=str(value.get("updated_at", "")),
        )

    def copy_to_custom(self, new_id: str, now: str) -> StyleTemplate:
        """深拷贝为新 custom 模板。"""
        return StyleTemplate(
            style_id=new_id,
            revision=1,
            name=self.name,
            kind="custom",
            prompt_text=self.prompt_text,
            engine=self.engine,
            description=self.description,
            negative_prompt=self.negative_prompt,
            tags=list(self.tags),
            preview_asset_id=self.preview_asset_id,
            status="active",
            created_at=now,
            updated_at=now,
        )
