import os
import json
from pathlib import Path

DEFAULT_CONFIG = {
    "pos_x": 100,
    "pos_y": 100,
    "width": 960,
    "height": 220,
    "is_locked": False,
    "theme": "Minimalist",
    "font_family": "Segoe UI",
    "active_font_size": 22,
    "context_font_size": 15,
    "album_cover_mode": "off",  # "off", "left", "right"
    "sync_offset": 0.0,         # In seconds (e.g. +0.5 or -0.5)
}

CONFIG_DIR = Path(os.environ.get("APPDATA", ".")) / "TransparentLyrics"
CONFIG_FILE = CONFIG_DIR / "config.json"


class ConfigManager:
    """Manages persistent user configuration."""

    def __init__(self):
        self.config = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.config.update(data)
        except Exception as e:
            print(f"[ConfigManager] Error loading config: {e}")

    def save(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"[ConfigManager] Error saving config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()
