import sys
import ctypes
from ctypes import wintypes
from typing import Optional

from PySide6.QtCore import Qt, QPoint, Signal, QRect
from PySide6.QtGui import QAction, QActionGroup, QGuiApplication, QCursor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QMenu, QInputDialog

from .renderer import LyricsRenderer
from .config import ConfigManager
from .themes import THEMES, get_theme

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000

SIZE_PRESETS = [
    ("Compact (800 × 200)", 800, 200),
    ("Standard (960 × 220)", 960, 220),
    ("Large (1160 × 260)", 1160, 260),
    ("Wide (1360 × 280)", 1360, 280),
    ("Ultra-Wide (1560 × 300)", 1560, 300),
]

OPACITY_PRESETS = [
    ("Default (100% / 50% / 25%)", 1.0, 0.50, 0.25),
    ("High Visibility (100% / 70% / 40%)", 1.0, 0.70, 0.40),
    ("Ultra Contrast (100% / 40% / 15%)", 1.0, 0.40, 0.15),
    ("Active Focus (100% / 25% / 10%)", 1.0, 0.25, 0.10),
    ("Active Only (100% / 0% / 0%)", 1.0, 0.0, 0.0),
]


def _setup_win32_functions():
    if sys.platform != "win32":
        return None, None
    user32 = ctypes.windll.user32
    get_fn = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
    set_fn = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)

    get_fn.argtypes = [wintypes.HWND, ctypes.c_int]
    get_fn.restype = ctypes.c_longlong

    set_fn.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_longlong]
    set_fn.restype = ctypes.c_longlong
    return get_fn, set_fn


GET_WINDOW_LONG, SET_WINDOW_LONG = _setup_win32_functions()


class OverlayWindow(QWidget):
    """100% Transparent, Always-on-Top Floating Lyrics Window with Resizing and Album Cover Support."""

    lock_changed = Signal(bool)
    theme_changed = Signal(str)
    size_changed = Signal(int, int)
    album_mode_changed = Signal(str)
    sync_offset_changed = Signal(float)
    opacity_changed = Signal(float, float, float)
    uncensored_changed = Signal(bool)
    restart_requested = Signal()

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.is_locked = False
        self._drag_pos = QPoint()
        self._is_resizing = False
        self._resize_start_geometry = QRect()
        self._resize_start_mouse = QPoint()

        # Frameless, Always on Top, Tool window, Transparent
        self.setWindowFlags(
            Qt.Window
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        # Setup child renderer
        self.renderer = LyricsRenderer(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.renderer)

        # Load geometry
        self.restore_geometry()

        # Load Theme
        theme_name = self.config.get("theme", "Minimalist")
        self.apply_theme(theme_name)

        # Load Album Cover Mode
        album_mode = self.config.get("album_cover_mode", "off")
        self.set_album_cover_mode(album_mode, adjust_ratio=False)

        # Load Opacities
        active_op = float(self.config.get("active_opacity", 1.0))
        next_op = float(self.config.get("next_opacity", 0.50))
        prev_op = float(self.config.get("prev_opacity", 0.25))
        self.renderer.set_opacities(active_op, next_op, prev_op)

        # Load High-Contrast Outline
        contrast = bool(self.config.get("high_contrast_outline", False))
        self.renderer.set_high_contrast_outline(contrast)

        # Apply initial lock state
        init_locked = self.config.get("is_locked", False)
        self.set_locked(init_locked)

    def restore_geometry(self):
        w = self.config.get("width", 960)
        h = self.config.get("height", 220)
        self.resize(w, h)

        x = self.config.get("pos_x")
        y = self.config.get("pos_y")

        if x is not None and y is not None:
            self.move(x, y)
        else:
            self.center_on_screen()

    def set_window_dimensions(self, width: int, height: int):
        width = max(500, min(2560, width))
        height = max(140, min(1440, height))
        self.resize(width, height)
        self._save_geometry()
        self.size_changed.emit(width, height)

    def set_album_cover_mode(self, mode: str, adjust_ratio: bool = True):
        prev_mode = self.renderer.album_cover_mode
        self.renderer.set_album_cover_mode(mode)
        self.config.set("album_cover_mode", mode)

        # Keep ratio wider when album art is enabled to prevent text crunching
        if adjust_ratio:
            if mode in ("left", "right") and self.width() < 1200:
                self.set_window_dimensions(max(1200, self.width() + 240), self.height())
            elif mode == "off" and prev_mode in ("left", "right") and self.width() >= 1200:
                self.set_window_dimensions(max(960, self.width() - 240), self.height())

        self.album_mode_changed.emit(mode)

    def center_on_screen(self):
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            x = (screen_geo.width() - self.width()) // 2
            y = screen_geo.height() - self.height() - 100
            self.move(x, y)
            self._save_geometry()

    def _save_geometry(self):
        pos = self.pos()
        self.config.set("pos_x", pos.x())
        self.config.set("pos_y", pos.y())
        self.config.set("width", self.width())
        self.config.set("height", self.height())

    def apply_theme(self, theme_name: str):
        theme = get_theme(theme_name)
        self.renderer.set_theme(theme)
        self.config.set("theme", theme_name)
        self.theme_changed.emit(theme_name)

    def set_locked(self, locked: bool):
        self.is_locked = locked
        self.config.set("is_locked", locked)

        hwnd = int(self.winId())
        if GET_WINDOW_LONG and SET_WINDOW_LONG and hwnd:
            try:
                style = GET_WINDOW_LONG(hwnd, GWL_EXSTYLE)
                if locked:
                    SET_WINDOW_LONG(hwnd, GWL_EXSTYLE, style | WS_EX_TRANSPARENT | WS_EX_LAYERED)
                else:
                    SET_WINDOW_LONG(hwnd, GWL_EXSTYLE, style & ~WS_EX_TRANSPARENT)
            except Exception as e:
                print(f"[OverlayWindow] Failed to update win32 window styles: {e}")

        self.setAttribute(Qt.WA_TransparentForMouseEvents, locked)
        self.lock_changed.emit(locked)

    def _is_near_corner(self, pos: QPoint) -> bool:
        # Check if cursor is within 24px of bottom-right corner
        return (self.width() - pos.x() <= 24) and (self.height() - pos.y() <= 24)

    def mousePressEvent(self, event):
        if not self.is_locked and event.button() == Qt.LeftButton:
            if self._is_near_corner(event.pos()):
                self._is_resizing = True
                self._resize_start_geometry = self.geometry()
                self._resize_start_mouse = event.globalPosition().toPoint()
            else:
                self._is_resizing = False
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self.is_locked:
            if self._is_resizing:
                delta = event.globalPosition().toPoint() - self._resize_start_mouse
                new_w = max(500, self._resize_start_geometry.width() + delta.x())
                new_h = max(140, self._resize_start_geometry.height() + delta.y())
                self.resize(new_w, new_h)
                event.accept()
                return

            if event.buttons() == Qt.LeftButton:
                self.move(event.globalPosition().toPoint() - self._drag_pos)
                event.accept()
                return

            # Update cursor icon for corner resizing
            if self._is_near_corner(event.pos()):
                self.setCursor(Qt.SizeFDiagCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if not self.is_locked and event.button() == Qt.LeftButton:
            self._is_resizing = False
            self._save_geometry()
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def prompt_custom_size(self):
        text, ok = QInputDialog.getText(
            self,
            "Custom Window Size",
            "Enter dimensions (Width × Height, e.g. 1100x240):",
            text=f"{self.width()}x{self.height()}"
        )
        if ok and text:
            try:
                parts = text.lower().replace(" ", "").replace("×", "x").split("x")
                if len(parts) == 2:
                    w = int(parts[0])
                    h = int(parts[1])
                    self.set_window_dimensions(w, h)
            except Exception:
                pass

    def set_sync_offset(self, offset: float):
        self.config.set("sync_offset", round(offset, 2))
        self.sync_offset_changed.emit(offset)

    def prompt_custom_offset(self):
        val, ok = QInputDialog.getDouble(
            self,
            "Custom Sync Offset",
            "Enter offset in seconds (e.g. +1.5 to show lyrics earlier, -1.5 for later):",
            value=float(self.config.get("sync_offset", 0.0)),
            decimals=2
        )
        if ok:
            self.set_sync_offset(val)

    def set_opacities(self, active: float, next_op: float, prev_op: float):
        self.config.set("active_opacity", round(active, 2))
        self.config.set("next_opacity", round(next_op, 2))
        self.config.set("prev_opacity", round(prev_op, 2))
        self.renderer.set_opacities(active, next_op, prev_op)
        self.opacity_changed.emit(active, next_op, prev_op)

    def prompt_custom_opacities(self):
        curr_act = self.config.get("active_opacity", 1.0)
        curr_next = self.config.get("next_opacity", 0.50)
        curr_prev = self.config.get("prev_opacity", 0.25)
        text, ok = QInputDialog.getText(
            self,
            "Custom Opacity Levels",
            "Enter Active, Next, Previous opacities (0.0 to 1.0, e.g. 1.0, 0.6, 0.3):",
            text=f"{curr_act}, {curr_next}, {curr_prev}"
        )
        if ok and text:
            try:
                parts = [float(p.strip()) for p in text.split(",")]
                if len(parts) == 3:
                    self.set_opacities(parts[0], parts[1], parts[2])
            except Exception:
                pass

    def set_prefer_uncensored(self, prefer: bool):
        self.config.set("prefer_uncensored", prefer)
        self.uncensored_changed.emit(prefer)

    def reload_settings(self):
        self.config.load()
        self.restore_geometry()
        self.apply_theme(self.config.get("theme", "Minimalist"))
        self.set_album_cover_mode(self.config.get("album_cover_mode", "off"), adjust_ratio=False)
        self.set_locked(self.config.get("is_locked", False))
        self.sync_offset_changed.emit(float(self.config.get("sync_offset", 0.0)))

        active_op = float(self.config.get("active_opacity", 1.0))
        next_op = float(self.config.get("next_opacity", 0.50))
        prev_op = float(self.config.get("prev_opacity", 0.25))
        self.renderer.set_opacities(active_op, next_op, prev_op)
        self.opacity_changed.emit(active_op, next_op, prev_op)
        self.uncensored_changed.emit(bool(self.config.get("prefer_uncensored", True)))
        self.renderer.set_high_contrast_outline(bool(self.config.get("high_contrast_outline", False)))

    def open_settings_dialog(self):
        """Opens the dedicated graphical Settings Dialog window."""
        from .settings_dialog import SettingsDialog
        if not hasattr(self, "_settings_dialog") or self._settings_dialog is None:
            self._settings_dialog = SettingsDialog(self.config, self)
            self._settings_dialog.settings_applied.connect(self._on_settings_applied)
            self._settings_dialog.restart_requested.connect(self.restart_requested.emit)

        self._settings_dialog.load_from_config()
        self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()

    def _on_settings_applied(self, settings: dict):
        """Applies safe live settings (such as theme color change) without full restart."""
        if "theme" in settings:
            self.apply_theme(settings["theme"])

    def contextMenuEvent(self, event):
        if self.is_locked:
            return

        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background-color: #1e2430;
                color: #ffffff;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3b82f6;
            }
            QMenu::separator {
                height: 1px;
                background-color: #334155;
                margin: 4px 8px;
            }
            """
        )

        lock_act = menu.addAction("🔒 Lock (Click-Through)")
        lock_act.triggered.connect(lambda: self.set_locked(True))

        center_act = menu.addAction("↺ Center on Screen")
        center_act.triggered.connect(self.center_on_screen)

        menu.addSeparator()

        settings_act = menu.addAction("⚙ Settings...")
        settings_act.triggered.connect(self.open_settings_dialog)

        menu.addSeparator()

        shortcut_act = menu.addAction("🔗 Create Desktop Shortcut")
        shortcut_act.triggered.connect(self._create_desktop_shortcut)

        menu.addSeparator()

        exit_act = menu.addAction("✕ Exit")
        exit_act.triggered.connect(QGuiApplication.quit)

        menu.exec(event.globalPos())

    def _create_desktop_shortcut(self):
        from .updater import check_and_update_desktop_shortcut
        try:
            check_and_update_desktop_shortcut(force=True)
        except Exception as e:
            print(f"[OverlayWindow] Error creating shortcut: {e}")
