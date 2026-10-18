from dataclasses import dataclass
from typing import Dict
from PySide6.QtGui import QColor, QFont


@dataclass
class LyricTheme:
    name: str
    active_color: str
    context_color: str
    meta_color: str
    font_family: str
    active_weight: int = int(QFont.Bold)
    context_weight: int = int(QFont.Normal)
    active_opacity: float = 1.0
    context_opacity: float = 0.50
    next_opacity: float = 0.50
    prev_opacity: float = 0.25
    meta_opacity: float = 0.65

    def get_active_qcolor(self) -> QColor:
        c = QColor(self.active_color)
        c.setAlphaF(self.active_opacity)
        return c

    def get_context_qcolor(self) -> QColor:
        c = QColor(self.context_color)
        c.setAlphaF(self.context_opacity)
        return c

    def get_meta_qcolor(self) -> QColor:
        c = QColor(self.meta_color)
        c.setAlphaF(self.meta_opacity)
        return c


THEMES: Dict[str, LyricTheme] = {
    "Minimalist": LyricTheme(
        name="Minimalist",
        active_color="#FFFFFF",
        context_color="#94A3B8",
        meta_color="#CBD5E1",
        font_family="Segoe UI",
        active_opacity=1.0,
        context_opacity=0.45,
        meta_opacity=0.70,
    ),
    "Cyberpunk": LyricTheme(
        name="Cyberpunk",
        active_color="#00F0FF",
        context_color="#008899",
        meta_color="#00D2E0",
        font_family="Consolas",
        active_opacity=1.0,
        context_opacity=0.45,
        meta_opacity=0.75,
    ),
    "Sunset": LyricTheme(
        name="Sunset",
        active_color="#FFAA44",
        context_color="#885544",
        meta_color="#FFCC88",
        font_family="Segoe UI",
        active_opacity=1.0,
        context_opacity=0.45,
        meta_opacity=0.70,
    ),
    "Emerald": LyricTheme(
        name="Emerald",
        active_color="#00FF88",
        context_color="#006633",
        meta_color="#66FFAA",
        font_family="Segoe UI",
        active_opacity=1.0,
        context_opacity=0.45,
        meta_opacity=0.70,
    ),
    "Neon Contrast": LyricTheme(
        name="Neon Contrast",
        active_color="#39FF14",
        context_color="#00E5FF",
        meta_color="#FFFF00",
        font_family="Segoe UI",
        active_opacity=1.0,
        context_opacity=0.60,
        meta_opacity=0.85,
    ),
}


def get_theme(name: str) -> LyricTheme:
    return THEMES.get(name, THEMES["Minimalist"])
