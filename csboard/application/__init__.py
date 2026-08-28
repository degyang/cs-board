"""Application services will be added without framework dependencies."""
from csboard.application.legacy_bridge import LegacyJobBridge, LegacyRunLink

__all__ = ["LegacyJobBridge", "LegacyRunLink"]
