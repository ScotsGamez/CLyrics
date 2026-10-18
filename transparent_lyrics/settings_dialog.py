from typing import Dict, Any, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QSlider,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QCheckBox,
    QPushButton,
    QGroupBox,
    QFormLayout,
)
from .config import ConfigManager, DEFAULT_CONFIG
from .themes import THEMES
from .overlay_window import SIZE_PRESETS, OPACITY_PRESETS


class SettingsDialog(QDialog):
    """Dedicated dark-themed graphical configuration manager for Transparent Live Lyrics."""

    settings_applied = Signal(dict)
    restart_requested = Signal()

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.setWindowTitle("Transparent Live Lyrics — Settings")
        self.setMinimumSize(540, 520)
        self.resize(560, 560)

        # Style the dialog with modern dark mode aesthetic
        self.setStyleSheet(
            """
            QDialog {
                background-color: #0f172a;
                color: #f8fafc;
                font-family: 'Segoe UI', sans-serif;
            }
            QTabWidget::pane {
                border: 1px solid #334155;
                background-color: #1e293b;
                border-radius: 8px;
                padding: 12px;
            }
            QTabBar::tab {
                background-color: #0f172a;
                color: #94a3b8;
                padding: 8px 18px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background-color: #1e293b;
                color: #38bdf8;
                border: 1px solid #334155;
                border-bottom: none;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #334155;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 14px;
                color: #38bdf8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QLabel {
                color: #e2e8f0;
                font-size: 13px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #334155;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #3b82f6;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #60a5fa;
                border: 1px solid #93c5fd;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
            QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #475569;
                border-radius: 4px;
                padding: 4px 8px;
                min-height: 24px;
            }
            QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
                border-color: #38bdf8;
            }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                color: #f8fafc;
                selection-background-color: #3b82f6;
            }
            QCheckBox {
                color: #e2e8f0;
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #475569;
                background-color: #0f172a;
            }
            QCheckBox::indicator:checked {
                background-color: #3b82f6;
                border-color: #60a5fa;
            }
            QPushButton {
                background-color: #334155;
                color: #f8fafc;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
                min-height: 26px;
            }
            QPushButton:hover {
                background-color: #475569;
                border-color: #64748b;
            }
            QPushButton#primaryBtn {
                background-color: #2563eb;
                border-color: #3b82f6;
            }
            QPushButton#primaryBtn:hover {
                background-color: #1d4ed8;
            }
            QPushButton#dangerBtn {
                background-color: #7f1d1d;
                border-color: #991b1b;
            }
            QPushButton#dangerBtn:hover {
                background-color: #991b1b;
            }
            """
        )

        self._init_ui()
        self.load_from_config()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Tab Widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # 1. Opacity Tab
        self._setup_opacity_tab()

        # 2. Window & Layout Tab
        self._setup_window_tab()

        # 3. Theme & Typography Tab
        self._setup_theme_tab()

        # 4. Sync & Lyrics Tab
        self._setup_sync_tab()

        # Bottom Buttons
        btn_layout = QHBoxLayout()

        self.raw_json_btn = QPushButton("📄 Open settings.json")
        self.raw_json_btn.clicked.connect(self.config.open_in_editor)
        btn_layout.addWidget(self.raw_json_btn)

        self.reset_btn = QPushButton("↺ Reset Defaults")
        self.reset_btn.setObjectName("dangerBtn")
        self.reset_btn.clicked.connect(self._reset_defaults)
        btn_layout.addWidget(self.reset_btn)

        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save & Apply")
        self.save_btn.setObjectName("primaryBtn")
        self.save_btn.clicked.connect(self._save_and_apply)
        btn_layout.addWidget(self.save_btn)

        main_layout.addLayout(btn_layout)

    # -------------------------------------------------------------
    # Tab 1: Opacity
    # -------------------------------------------------------------
    def _setup_opacity_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)

        info_lbl = QLabel("Fine-tune the independent visibility of each line in the 3-line karaoke view:")
        info_lbl.setWordWrap(True)
        layout.addWidget(info_lbl)

        form_group = QGroupBox("3-Tier Opacity Levels")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(12)

        # Active Line
        self.active_slider = QSlider(Qt.Horizontal)
        self.active_slider.setRange(0, 100)
        self.active_spin = QSpinBox()
        self.active_spin.setRange(0, 100)
        self.active_spin.setSuffix("%")
        self.active_slider.valueChanged.connect(self.active_spin.setValue)
        self.active_spin.valueChanged.connect(self.active_slider.setValue)

        h_act = QHBoxLayout()
        h_act.addWidget(self.active_slider)
        h_act.addWidget(self.active_spin)
        form_layout.addRow("Active Lyric (Current):", h_act)

        # Next Line
        self.next_slider = QSlider(Qt.Horizontal)
        self.next_slider.setRange(0, 100)
        self.next_spin = QSpinBox()
        self.next_spin.setRange(0, 100)
        self.next_spin.setSuffix("%")
        self.next_slider.valueChanged.connect(self.next_spin.setValue)
        self.next_spin.valueChanged.connect(self.next_slider.setValue)

        h_next = QHBoxLayout()
        h_next.addWidget(self.next_slider)
        h_next.addWidget(self.next_spin)
        form_layout.addRow("Next Lyric (Upcoming):", h_next)

        # Previous Line
        self.prev_slider = QSlider(Qt.Horizontal)
        self.prev_slider.setRange(0, 100)
        self.prev_spin = QSpinBox()
        self.prev_spin.setRange(0, 100)
        self.prev_spin.setSuffix("%")
        self.prev_slider.valueChanged.connect(self.prev_spin.setValue)
        self.prev_spin.valueChanged.connect(self.prev_slider.setValue)

        h_prev = QHBoxLayout()
        h_prev.addWidget(self.prev_slider)
        h_prev.addWidget(self.prev_spin)
        form_layout.addRow("Previous Lyric (Past):", h_prev)

        layout.addWidget(form_group)

        # Quick Preset Buttons
        preset_group = QGroupBox("Quick Presets")
        p_layout = QHBoxLayout(preset_group)

        presets = [
            ("Default (100/50/25)", 100, 50, 25),
            ("High Visibility (100/70/40)", 100, 70, 40),
            ("Ultra Contrast (100/40/15)", 100, 40, 15),
            ("Active Only (100/0/0)", 100, 0, 0),
        ]
        for name, a, n, p in presets:
            btn = QPushButton(name)
            btn.clicked.connect(lambda ch, av=a, nv=n, pv=p: self._apply_opacity_preset(av, nv, pv))
            p_layout.addWidget(btn)

        layout.addWidget(preset_group)
        layout.addStretch()
        self.tabs.addTab(tab, "👁 Opacity")

    def _apply_opacity_preset(self, a: int, n: int, p: int):
        self.active_slider.setValue(a)
        self.next_slider.setValue(n)
        self.prev_slider.setValue(p)

    # -------------------------------------------------------------
    # Tab 2: Window & Layout
    # -------------------------------------------------------------
    def _setup_window_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)

        geo_group = QGroupBox("Window Dimensions")
        geo_layout = QFormLayout(geo_group)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(500, 2560)
        self.width_spin.setSuffix(" px")
        geo_layout.addRow("Width:", self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(140, 1440)
        self.height_spin.setSuffix(" px")
        geo_layout.addRow("Height:", self.height_spin)

        # Preset sizes
        self.size_preset_combo = QComboBox()
        self.size_preset_combo.addItem("Select a preset...", None)
        for label, w, h in SIZE_PRESETS:
            self.size_preset_combo.addItem(label, (w, h))
        self.size_preset_combo.currentIndexChanged.connect(self._on_size_preset_selected)
        geo_layout.addRow("Preset:", self.size_preset_combo)

        layout.addWidget(geo_group)

        # Album Art & Interaction Group
        layout_group = QGroupBox("Appearance & Interaction")
        layout_form = QFormLayout(layout_group)

        self.album_combo = QComboBox()
        self.album_combo.addItem("Off / Hidden", "off")
        self.album_combo.addItem("Left Side", "left")
        self.album_combo.addItem("Right Side", "right")
        layout_form.addRow("Album Cover Art:", self.album_combo)

        self.lock_check = QCheckBox("Lock Click-Through (clicks pass to apps underneath)")
        layout_form.addRow("", self.lock_check)

        layout.addWidget(layout_group)
        layout.addStretch()
        self.tabs.addTab(tab, "📏 Window")

    def _on_size_preset_selected(self, index: int):
        data = self.size_preset_combo.currentData()
        if data:
            w, h = data
            self.width_spin.setValue(w)
            self.height_spin.setValue(h)

    # -------------------------------------------------------------
    # Tab 3: Theme & Typography
    # -------------------------------------------------------------
    def _setup_theme_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)

        theme_group = QGroupBox("Color Palette & Aesthetic")
        t_form = QFormLayout(theme_group)

        self.theme_combo = QComboBox()
        for theme_name in THEMES.keys():
            self.theme_combo.addItem(theme_name, theme_name)
        t_form.addRow("Color Theme:", self.theme_combo)

        layout.addWidget(theme_group)

        typo_group = QGroupBox("Typography")
        typo_form = QFormLayout(typo_group)

        self.font_combo = QComboBox()
        fonts = ["Segoe UI", "Consolas", "Arial", "Calibri", "Verdana", "Tahoma"]
        for f in fonts:
            self.font_combo.addItem(f, f)
        typo_form.addRow("Font Family:", self.font_combo)

        self.active_size_spin = QSpinBox()
        self.active_size_spin.setRange(14, 48)
        self.active_size_spin.setSuffix(" pt")
        typo_form.addRow("Active Font Size:", self.active_size_spin)

        self.context_size_spin = QSpinBox()
        self.context_size_spin.setRange(10, 32)
        self.context_size_spin.setSuffix(" pt")
        typo_form.addRow("Context Font Size:", self.context_size_spin)

        layout.addWidget(typo_group)
        layout.addStretch()
        self.tabs.addTab(tab, "🎨 Theme")

    # -------------------------------------------------------------
    # Tab 4: Sync & Lyrics
    # -------------------------------------------------------------
    def _setup_sync_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)

        sync_group = QGroupBox("Playback Synchronization")
        sync_layout = QVBoxLayout(sync_group)

        sync_desc = QLabel("Adjust offset to synchronize lyrics with slight audio delays or personal preference:")
        sync_desc.setWordWrap(True)
        sync_layout.addWidget(sync_desc)

        h_sync = QHBoxLayout()
        self.sync_spin = QDoubleSpinBox()
        self.sync_spin.setRange(-5.0, 5.0)
        self.sync_spin.setSingleStep(0.1)
        self.sync_spin.setSuffix(" s")
        h_sync.addWidget(QLabel("Offset:"))
        h_sync.addWidget(self.sync_spin)
        h_sync.addStretch()

        # Quick offset buttons
        offsets = [("-1.0s", -1.0), ("-0.5s", -0.5), ("0.0s", 0.0), ("+0.5s", 0.5), ("+1.0s", 1.0)]
        for lbl, val in offsets:
            b = QPushButton(lbl)
            b.clicked.connect(lambda ch, v=val: self.sync_spin.setValue(v))
            h_sync.addWidget(b)

        sync_layout.addLayout(h_sync)
        layout.addWidget(sync_group)

        provider_group = QGroupBox("Lyrics Providers & Filtering")
        provider_layout = QVBoxLayout(provider_group)

        self.uncensored_check = QCheckBox("🔞 Prefer Uncensored Lyrics (LRCLIB Priority)")
        provider_layout.addWidget(self.uncensored_check)

        uncensored_desc = QLabel(
            "When enabled, open community-sourced lyrics (LRCLIB) are prioritized over heavily censored "
            "providers (NetEase), preserving explicit lyrics, original swearing, and unedited verses."
        )
        uncensored_desc.setWordWrap(True)
        uncensored_desc.setStyleSheet("color: #94a3b8; font-size: 11px; margin-left: 26px;")
        provider_layout.addWidget(uncensored_desc)

        layout.addWidget(provider_group)
        layout.addStretch()
        self.tabs.addTab(tab, "⏱ Sync & Lyrics")

    # -------------------------------------------------------------
    # Data Loading & Saving
    # -------------------------------------------------------------
    def load_from_config(self):
        """Populates all dialog controls with current settings from ConfigManager."""
        # Opacities
        self.active_slider.setValue(int(float(self.config.get("active_opacity", 1.0)) * 100))
        self.next_slider.setValue(int(float(self.config.get("next_opacity", 0.50)) * 100))
        self.prev_slider.setValue(int(float(self.config.get("prev_opacity", 0.25)) * 100))

        # Window
        self.width_spin.setValue(int(self.config.get("width", 960)))
        self.height_spin.setValue(int(self.config.get("height", 220)))

        album_mode = str(self.config.get("album_cover_mode", "off"))
        idx = self.album_combo.findData(album_mode)
        if idx >= 0:
            self.album_combo.setCurrentIndex(idx)

        self.lock_check.setChecked(bool(self.config.get("is_locked", False)))

        # Theme & Typo
        theme = str(self.config.get("theme", "Minimalist"))
        t_idx = self.theme_combo.findData(theme)
        if t_idx >= 0:
            self.theme_combo.setCurrentIndex(t_idx)

        font_family = str(self.config.get("font_family", "Segoe UI"))
        f_idx = self.font_combo.findData(font_family)
        if f_idx >= 0:
            self.font_combo.setCurrentIndex(f_idx)

        self.active_size_spin.setValue(int(self.config.get("active_font_size", 22)))
        self.context_size_spin.setValue(int(self.config.get("context_font_size", 15)))

        # Sync & Lyrics
        self.sync_spin.setValue(float(self.config.get("sync_offset", 0.0)))
        self.uncensored_check.setChecked(bool(self.config.get("prefer_uncensored", True)))

    def _reset_defaults(self):
        """Loads default values into GUI controls without saving yet."""
        self.active_slider.setValue(100)
        self.next_slider.setValue(50)
        self.prev_slider.setValue(25)
        self.width_spin.setValue(960)
        self.height_spin.setValue(220)
        self.album_combo.setCurrentIndex(0)
        self.lock_check.setChecked(False)
        self.theme_combo.setCurrentIndex(0)
        self.font_combo.setCurrentIndex(0)
        self.active_size_spin.setValue(22)
        self.context_size_spin.setValue(15)
        self.sync_spin.setValue(0.0)
        self.uncensored_check.setChecked(True)

    def _save_and_apply(self):
        """Collects GUI values, saves to ConfigManager, and either applies theme live or restarts app."""
        new_settings = {
            "active_opacity": round(self.active_slider.value() / 100.0, 2),
            "next_opacity": round(self.next_slider.value() / 100.0, 2),
            "prev_opacity": round(self.prev_slider.value() / 100.0, 2),
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "album_cover_mode": self.album_combo.currentData(),
            "is_locked": self.lock_check.isChecked(),
            "theme": self.theme_combo.currentData(),
            "font_family": self.font_combo.currentData(),
            "active_font_size": self.active_size_spin.value(),
            "context_font_size": self.context_size_spin.value(),
            "sync_offset": round(self.sync_spin.value(), 2),
            "prefer_uncensored": self.uncensored_check.isChecked(),
        }

        changed_keys = []
        for key, new_val in new_settings.items():
            old_val = self.config.get(key)
            if key in ("active_opacity", "next_opacity", "prev_opacity", "sync_offset"):
                if old_val is None or abs(float(old_val) - float(new_val)) > 1e-4:
                    changed_keys.append(key)
            elif key in ("width", "height", "active_font_size", "context_font_size"):
                if old_val is None or int(old_val) != int(new_val):
                    changed_keys.append(key)
            elif key in ("is_locked", "prefer_uncensored"):
                if old_val is None or bool(old_val) != bool(new_val):
                    changed_keys.append(key)
            else:
                if str(old_val) != str(new_val):
                    changed_keys.append(key)

        self.config.bulk_set(new_settings)
        self.accept()

        if not changed_keys:
            return

        if set(changed_keys) == {"theme"}:
            # Only theme changed: safe live update without restarting
            self.settings_applied.emit({"theme": new_settings["theme"]})
        else:
            # Non-theme settings changed: restart the application to avoid stalls
            self.restart_requested.emit()
