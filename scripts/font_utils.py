"""Portable system-font discovery for Chinese text rendered with Pillow."""
from __future__ import annotations

from pathlib import Path

from PIL import ImageFont


# Ordered by the quality and availability of CJK glyphs on Windows, Linux/WSL,
# and macOS.  Linux distributions differ, hence several Noto locations.
FONT_CANDIDATES = (
    Path("C:/Windows/Fonts/msyhbd.ttc"),
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("C:/Windows/Fonts/simhei.ttf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    Path("/System/Library/Fonts/PingFang.ttc"),
    Path("/System/Library/Fonts/STHeiti Light.ttc"),
)


def system_font_path(*, bold: bool = False, serif: bool = False) -> Path | None:
    """Return a usable CJK font path, or ``None`` when none is installed."""
    candidates = list(FONT_CANDIDATES)
    if serif:
        candidates = [
            Path("C:/Windows/Fonts/simkai.ttf"),
            Path("C:/Windows/Fonts/simsun.ttc"),
            Path("/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/noto/NotoSerifCJK-Regular.ttc"),
            Path("/System/Library/Fonts/Supplemental/Songti.ttc"),
            *candidates,
        ]
    if bold:
        candidates.sort(key=lambda path: 0 if "Bold" in path.name or "bd" in path.name.lower() else 1)
    return next((path for path in candidates if path.exists()), None)


def load_system_font(size: int, *, bold: bool = False, serif: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = system_font_path(bold=bold, serif=serif)
    return ImageFont.truetype(str(path), size=size) if path else ImageFont.load_default()
