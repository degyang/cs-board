"""StyleTemplate — 风格模板领域模型。

preset 只读，只允许查看和复制为 custom。
删除只允许停用（is_active=False），不做不可恢复的物理删除。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class StyleTemplate:
    """风格模板。"""

    template_id: str
    revision: int
    name: str
    kind: str  # "preset" | "custom"
    prompt_text: str
    negative_prompt: str = ""
    reference_images: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> StyleTemplate:
        return cls(
            template_id=str(value["template_id"]),
            revision=int(value.get("revision", 1)),
            name=str(value["name"]),
            kind=str(value["kind"]),
            prompt_text=str(value["prompt_text"]),
            negative_prompt=str(value.get("negative_prompt", "")),
            reference_images=[str(v) for v in value.get("reference_images", [])],
            tags=[str(v) for v in value.get("tags", [])],
            is_active=bool(value.get("is_active", True)),
            created_at=str(value.get("created_at", "")),
            updated_at=str(value.get("updated_at", "")),
        )

    def copy_to_custom(self, new_id: str, now: str) -> StyleTemplate:
        """深拷贝为新 custom 模板。"""
        return StyleTemplate(
            template_id=new_id,
            revision=1,
            name=self.name,
            kind="custom",
            prompt_text=self.prompt_text,
            negative_prompt=self.negative_prompt,
            reference_images=list(self.reference_images),
            tags=list(self.tags),
            is_active=True,
            created_at=now,
            updated_at=now,
        )
