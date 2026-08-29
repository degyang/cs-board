from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True, slots=True)
class RuntimePaths:
    root: Path
    @classmethod
    def resolve(cls, app_name: str = "cs-board") -> "RuntimePaths":
        explicit = os.environ.get("CSBOARD_DATA_DIR")
        if explicit: return cls(Path(explicit))
        if os.name == "nt": return cls(Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / app_name)
        return cls(Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / app_name)
    @property
    def projects(self) -> Path: return self.root / "projects"
    @property
    def logs(self) -> Path: return self.root / "logs"
    @property
    def diagnostics(self) -> Path: return self.root / "diagnostics"
    @property
    def toolchain(self) -> Path: return self.root / "toolchain"
    def ensure(self) -> "RuntimePaths":
        for path in (self.projects,self.logs,self.diagnostics,self.toolchain): path.mkdir(parents=True,exist_ok=True)
        return self
