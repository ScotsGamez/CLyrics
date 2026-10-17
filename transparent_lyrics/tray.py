from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction, QActionGroup, QGuiApplication
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from .themes import THEMES
from .overlay_window import SIZE_PRESETS


def create_tray_icon() -> QIcon:
    """Generates a high-DPI musical note tray icon procedurally."""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)

    # Gradient-like circular badge
    painter.setBrush(QColor("#2563EB"))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(4, 4, 56, 56)

    # Stylized musical note
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#FFFFFF"))

    # Left note head
    painter.drawEllipse(18, 36, 12, 10)
    # Right note head
    painter.drawEllipse(36, 30, 12, 10)

    # Vertical stems
    painter.setPen(QColor("#FFFFFF"))
    pen = painter.pen()
    pen.setWidth(4)
    painter.setPen(pen)
    painter.drawLine(28, 40, 28, 18)
    painter.drawLine(46, 34, 46, 12)

    # Horizontal connector bar
    pen.setWidth(5)
    painter.setPen(pen)
    painter.drawLine(26, 18, 48, 12)

    painter.end()
    return QIcon(pixmap)


class LyricsTrayIcon(QSystemTrayIcon):
    """System Tray Icon providing background window control, resizing, and album art management."""

    def __init__(self, overlay_window, parent=None):
        super().__init__(create_tray_icon(), parent)
        self.window = overlay_window

        self.setToolTip("Transparent Live Lyrics Overlay")
        self._init_menu()

        # Connect overlay state signals
        self.window.lock_changed.connect(self._on_lock_changed)
        self.window.theme_changed.connect(self._on_theme_changed)
        self.window.album_mode_changed.connect(self._on_album_mode_changed)
        self.window.size_changed.connect(self._on_size_changed)
        self.window.sync_offset_changed.connect(self._on_sync_offset_changed)

    def _init_menu(self):
        self.menu = QMenu()
        self.menu.setStyleSheet(
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
            QMenu::item:disabled {
                color: #94a3b8;
                font-weight: bold;
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

        # Track Header Info
        self.header_action = self.menu.addAction("Ready for Music")
        self.header_action.setEnabled(False)

        self.menu.addSeparator()

        # Lock (Click-Through) toggle
        self.lock_action = QAction("🔒 Lock (Click-Through)", self.menu, checkable=True)
        self.lock_action.setChecked(self.window.is_locked)
        self.lock_action.triggered.connect(self._toggle_lock)
        self.menu.addAction(self.lock_action)

        # Center on screen
        self.center_action = self.menu.addAction("↺ Center on Screen")
        self.center_action.triggered.connect(self.window.center_on_screen)

        # Visibility toggle
        self.visibility_action = QAction("👁 Visible", self.menu, checkable=True)
        self.visibility_action.setChecked(True)
        self.visibility_action.triggered.connect(self._toggle_visibility)
        self.menu.addAction(self.visibility_action)

        self.menu.addSeparator()

        # 1. Album Cover Submenu
        self.album_menu = self.menu.addMenu("🖼 Album Cover")
        self.album_group = QActionGroup(self.album_menu)
        curr_album_mode = self.window.config.get("album_cover_mode", "off")

        for mode_id, mode_label in [("off", "Off / Hidden"), ("left", "Left Side"), ("right", "Right Side")]:
            act = QAction(mode_label, self.album_menu, checkable=True)
            act.setChecked(curr_album_mode == mode_id)
            act.triggered.connect(lambda checked, m=mode_id: self.window.set_album_cover_mode(m))
            self.album_group.addAction(act)
            self.album_menu.addAction(act)

        # 2. Window Size Submenu
        self.size_menu = self.menu.addMenu("📏 Window Size")
        self.size_group = QActionGroup(self.size_menu)

        for label, w, h in SIZE_PRESETS:
            act = QAction(label, self.size_menu, checkable=True)
            act.setChecked(self.window.width() == w and self.window.height() == h)
            act.triggered.connect(lambda checked, w=w, h=h: self.window.set_window_dimensions(w, h))
            self.size_group.addAction(act)
            self.size_menu.addAction(act)

        self.size_menu.addSeparator()
        custom_act = self.size_menu.addAction("Custom Dimensions...")
        custom_act.triggered.connect(self.window.prompt_custom_size)

        # 3. Themes Submenu
        self.theme_menu = self.menu.addMenu("🎨 Themes")
        self.theme_group = QActionGroup(self.theme_menu)
        current_theme = self.window.config.get("theme", "Minimalist")

        for name in THEMES.keys():
            act = QAction(name, self.theme_menu, checkable=True)
            act.setChecked(name == current_theme)
            act.triggered.connect(lambda checked, n=name: self.window.apply_theme(n))
        # 4. Sync Offset Submenu
        self.offset_menu = self.menu.addMenu("⏱ Sync Offset")
        self.offset_group = QActionGroup(self.offset_menu)
        curr_offset = float(self.window.config.get("sync_offset", 0.0))

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
            act = QAction(label, self.offset_menu, checkable=True)
            act.setChecked(abs(curr_offset - val) < 0.01)
            act.triggered.connect(lambda checked, v=val: self.window.set_sync_offset(v))
            self.offset_group.addAction(act)
            self.offset_menu.addAction(act)

        self.offset_menu.addSeparator()
        custom_off_act = self.offset_menu.addAction("Custom Offset...")
        custom_off_act.triggered.connect(self.window.prompt_custom_offset)

        self.menu.addSeparator()
        shortcut_act = self.menu.addAction("🔗 Create Desktop Shortcut")
        shortcut_act.triggered.connect(self._create_desktop_shortcut)

        self.menu.addSeparator()
        exit_action = self.menu.addAction("✕ Exit")
        exit_action.triggered.connect(QGuiApplication.quit)

        self.setContextMenu(self.menu)

    def _create_desktop_shortcut(self):
        import subprocess
        from pathlib import Path
        script = Path(__file__).resolve().parent.parent / "scripts" / "create_shortcut.ps1"
        try:
            subprocess.run(["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile", "-File", str(script)], check=True)
            self.showMessage("Transparent Live Lyrics", "Desktop shortcut created successfully!", QSystemTrayIcon.Information, 3000)
        except Exception as e:
            print(f"[Tray] Error creating shortcut: {e}")

    def _toggle_lock(self, checked: bool):
        self.window.set_locked(checked)

    def _on_lock_changed(self, is_locked: bool):
        if self.lock_action.isChecked() != is_locked:
            self.lock_action.setChecked(is_locked)

    def _on_theme_changed(self, theme_name: str):
        for act in self.theme_group.actions():
            act.setChecked(act.text() == theme_name)

    def _on_album_mode_changed(self, mode: str):
        mode_labels = {"off": "Off / Hidden", "left": "Left Side", "right": "Right Side"}
        target_label = mode_labels.get(mode, "Off / Hidden")
        for act in self.album_group.actions():
            act.setChecked(act.text() == target_label)

    def _on_size_changed(self, width: int, height: int):
        for act in self.size_group.actions():
            # Check if text matches preset dimensions
            dim_str = f"{width} × {height}"
            act.setChecked(dim_str in act.text())

    def _on_sync_offset_changed(self, offset: float):
        for act in self.offset_group.actions():
            dim = f"({offset:+.1f}s)" if offset != 0.0 else "(0.0s)"
            act.setChecked(dim in act.text())

    def _toggle_visibility(self, visible: bool):
        if visible:
            self.window.show()
        else:
            self.window.hide()

    def update_track_info(self, title: str, artist: str, playing: bool):
        if title:
            status = "▶ " if playing else "⏸ "
            text = f"{status}{title}"
            if artist:
                text += f" - {artist}"
            self.header_action.setText(text[:36])
            self.setToolTip(f"Lyrics Overlay: {text}")
        else:
            self.header_action.setText("Ready for Music")
            self.setToolTip("Transparent Live Lyrics Overlay (Idle)")
