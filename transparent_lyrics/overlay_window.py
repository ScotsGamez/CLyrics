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

    def reload_settings(self):
        self.config.load()
        self.restore_geometry()
        self.apply_theme(self.config.get("theme", "Minimalist"))
        self.set_album_cover_mode(self.config.get("album_cover_mode", "off"), adjust_ratio=False)
        self.set_locked(self.config.get("is_locked", False))
        self.sync_offset_changed.emit(float(self.config.get("sync_offset", 0.0)))

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

        # 1. Album Cover Submenu
        album_menu = menu.addMenu("🖼 Album Cover")
        album_group = QActionGroup(album_menu)
        curr_album_mode = self.config.get("album_cover_mode", "off")

        for mode_id, mode_label in [("off", "Off / Hidden"), ("left", "Left Side"), ("right", "Right Side")]:
            act = QAction(mode_label, album_menu, checkable=True)
            act.setChecked(curr_album_mode == mode_id)
            act.triggered.connect(lambda checked, m=mode_id: self.set_album_cover_mode(m))
            album_group.addAction(act)
            album_menu.addAction(act)

        # 2. Window Size Submenu
        size_menu = menu.addMenu("📏 Window Size")
        size_group = QActionGroup(size_menu)
        for label, w, h in SIZE_PRESETS:
            act = QAction(label, size_menu, checkable=True)
            act.setChecked(self.width() == w and self.height() == h)
            act.triggered.connect(lambda checked, w=w, h=h: self.set_window_dimensions(w, h))
            size_group.addAction(act)
            size_menu.addAction(act)

        size_menu.addSeparator()
        custom_act = size_menu.addAction("Custom Dimensions...")
        custom_act.triggered.connect(self.prompt_custom_size)

        # 3. Themes Submenu
        theme_menu = menu.addMenu("🎨 Themes")
        current_theme = self.config.get("theme", "Minimalist")
        theme_group = QActionGroup(theme_menu)

        for name in THEMES.keys():
            act = QAction(name, theme_menu, checkable=True)
            act.setChecked(name == current_theme)
            act.triggered.connect(lambda checked, n=name: self.apply_theme(n))
        # 4. Sync Offset Submenu
        offset_menu = menu.addMenu("⏱ Sync Offset")
        offset_group = QActionGroup(offset_menu)
        curr_offset = float(self.config.get("sync_offset", 0.0))

        OFFSET_PRESETS = [
            ("No Offset (0.0s)", 0.0),
            ("+0.5s Earlier", 0.5),
            ("+1.0s Earlier", 1.0),
            ("+2.0s Earlier", 2.0),
            ("-0.5s Later", -0.5),
            ("-1.0s Later", -1.0),
            ("-2.0s Later", -2.0),
        ]
        for label, val in OFFSET_PRESETS:
            act = QAction(label, offset_menu, checkable=True)
            act.setChecked(abs(curr_offset - val) < 0.01)
            act.triggered.connect(lambda checked, v=val: self.set_sync_offset(v))
            offset_group.addAction(act)
            offset_menu.addAction(act)

        offset_menu.addSeparator()
        custom_off_act = offset_menu.addAction("Custom Offset...")
        custom_off_act.triggered.connect(self.prompt_custom_offset)

        # 5. Settings Submenu
        settings_menu = menu.addMenu("⚙ Settings")
        settings_menu.addAction("📄 Edit settings.yaml...", lambda: self.config.open_in_editor("yaml"))
        settings_menu.addAction("📄 Edit settings.json...", lambda: self.config.open_in_editor("json"))
        settings_menu.addAction("📁 Open Settings Folder...", self.config.open_folder)
        settings_menu.addSeparator()
        settings_menu.addAction("🔄 Reload Settings from File", self.reload_settings)

        menu.addSeparator()
        shortcut_act = menu.addAction("🔗 Create Desktop Shortcut")
        shortcut_act.triggered.connect(self._create_desktop_shortcut)

        menu.addSeparator()
        exit_act = menu.addAction("✕ Exit")
        exit_act.triggered.connect(QGuiApplication.quit)

        menu.exec(event.globalPos())

    def _create_desktop_shortcut(self):
        import subprocess
        from pathlib import Path
        script = Path(__file__).resolve().parent.parent / "scripts" / "create_shortcut.ps1"
        try:
            subprocess.run(["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile", "-File", str(script)], check=True)
        except Exception as e:
            print(f"[OverlayWindow] Error creating shortcut: {e}")
