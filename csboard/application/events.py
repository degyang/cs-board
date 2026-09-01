"""事件总线接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class EventEmitter(ABC):
    """事件发射器接口。"""

    @abstractmethod
    def emit(self, event_type: str, **kwargs: Any) -> None:
        """发射事件。"""


class NoopEmitter(EventEmitter):
    """空操作事件发射器。"""

    def emit(self, event_type: str, **kwargs: Any) -> None:
        """什么都不做。"""


class RunEvent:
    """运行事件。"""

    def __init__(self, event_type: str, **kwargs: Any) -> None:
        self.event_type = event_type
        self.data = kwargs
