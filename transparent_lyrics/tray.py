from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction, QGuiApplication
from PySide6.QtWidgets import QSystemTrayIcon, QMenu


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
    """Clean and uncrowded System Tray Icon providing window controls and settings access."""

    def __init__(self, overlay_window, parent=None):
        super().__init__(create_tray_icon(), parent)
        self.window = overlay_window

        self.setToolTip("Transparent Live Lyrics Overlay")
        self._init_menu()

        # Connect overlay state signals
        self.window.lock_changed.connect(self._on_lock_changed)

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

        # Dedicated Settings GUI Window
        self.settings_action = self.menu.addAction("⚙ Settings...")
        self.settings_action.triggered.connect(self.window.open_settings_dialog)

        self.menu.addSeparator()

        # Desktop Shortcut
        shortcut_act = self.menu.addAction("🔗 Create Desktop Shortcut")
        shortcut_act.triggered.connect(self._create_desktop_shortcut)

        self.menu.addSeparator()

        # Exit Application
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
