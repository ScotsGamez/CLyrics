import sys
import ctypes
from ctypes import wintypes
from typing import Optional

from PySide6.QtCore import Qt, QPoint, Signal, QRect
from PySide6.QtGui import QAction, QActionGroup, QGuiApplication, QCursor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QMenu

from .renderer import LyricsRenderer
from .config import ConfigManager
from .themes import THEMES, get_theme

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000


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
    """100% Transparent, Always-on-Top Floating Lyrics Window with Click-Through Support."""

    lock_changed = Signal(bool)
    theme_changed = Signal(str)

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.is_locked = False
        self._drag_pos = QPoint()

        # Frameless, Always on Top, Tool window, Transparent
        self.setWindowFlags(
            Qt.Window
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

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

    def center_on_screen(self):
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            x = (screen_geo.width() - self.width()) // 2
            y = screen_geo.height() - self.height() - 100  # Default lower-third
            self.move(x, y)
            self._save_position()

    def _save_position(self):
        pos = self.pos()
        self.config.set("pos_x", pos.x())
        self.config.set("pos_y", pos.y())

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

    def mousePressEvent(self, event):
        if not self.is_locked and event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self.is_locked and event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if not self.is_locked and event.button() == Qt.LeftButton:
            self._save_position()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        if self.is_locked:
            return  # Clicks pass through when locked

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

        # Themes Submenu
        theme_menu = menu.addMenu("🎨 Themes")
        current_theme = self.config.get("theme", "Minimalist")
        theme_group = QActionGroup(theme_menu)

        for name in THEMES.keys():
            act = QAction(name, theme_menu, checkable=True)
            act.setChecked(name == current_theme)
            act.triggered.connect(lambda checked, n=name: self.apply_theme(n))
            theme_group.addAction(act)
            theme_menu.addAction(act)

        menu.addSeparator()
        exit_act = menu.addAction("✕ Exit")
        exit_act.triggered.connect(QGuiApplication.quit)

        menu.exec(event.globalPos())
