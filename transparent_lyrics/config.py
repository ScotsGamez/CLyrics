import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

DEFAULT_CONFIG: Dict[str, Any] = {
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

# Primary local location (project root) and AppData fallback
PROJECT_ROOT = Path(__file__).resolve().parent.parent
APPDATA_DIR = Path(os.environ.get("APPDATA", ".")) / "TransparentLyrics"


def parse_simple_yaml(text: str) -> Dict[str, Any]:
    """Lightweight zero-dependency YAML parser for key-value configuration."""
    data: Dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip()
            val = parts[1].split("#")[0].strip()  # Remove inline comments
            if not val:
                continue
            if val.lower() == "true":
                data[key] = True
            elif val.lower() == "false":
                data[key] = False
            elif val.lower() in ("null", "none"):
                data[key] = None
            elif (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                data[key] = val[1:-1]
            else:
                try:
                    if "." in val:
                        data[key] = float(val)
                    else:
                        data[key] = int(val)
                except ValueError:
                    data[key] = val
    return data


def dump_annotated_yaml(data: Dict[str, Any]) -> str:
    """Formats a human-readable annotated YAML file."""
    lines = [
        "# ========================================================\n",
        "# Transparent Live Lyrics Overlay - User Settings (YAML)\n",
        "# This file is automatically updated whenever settings change.\n",
        "# You can also edit it directly in Notepad and click 'Reload Settings'.\n",
        "# ========================================================\n\n",
        "# --- Window Geometry ---\n",
        f"pos_x: {data.get('pos_x', 100)}\n",
        f"pos_y: {data.get('pos_y', 100)}\n",
        f"width: {data.get('width', 960)}\n",
        f"height: {data.get('height', 220)}\n\n",
        "# --- Behavior & Layout ---\n",
        f"is_locked: {'true' if data.get('is_locked', False) else 'false'}  # Click-through mode\n",
        f"theme: \"{data.get('theme', 'Minimalist')}\"  # Minimalist, Cyberpunk, Sunset, Emerald\n",
        f"album_cover_mode: \"{data.get('album_cover_mode', 'off')}\"  # off, left, right\n",
        f"sync_offset: {data.get('sync_offset', 0.0)}  # In seconds (e.g. +0.5 earlier, -0.5 later)\n\n",
        "# --- Typography ---\n",
        f"font_family: \"{data.get('font_family', 'Segoe UI')}\"\n",
        f"active_font_size: {data.get('active_font_size', 22)}\n",
        f"context_font_size: {data.get('context_font_size', 15)}\n",
    ]
    return "".join(lines)


class ConfigManager:
    """Manages persistent user configuration with dual YAML and JSON automatic saving."""

    def __init__(self):
        self.config = DEFAULT_CONFIG.copy()

        # Decide primary target paths
        self.local_json = PROJECT_ROOT / "settings.json"
        self.local_yaml = PROJECT_ROOT / "settings.yaml"

        self.appdata_json = APPDATA_DIR / "settings.json"
        self.appdata_yaml = APPDATA_DIR / "settings.yaml"

        self.load()

    def get_preferred_yaml_path(self) -> Path:
        return self.local_yaml if self.local_yaml.exists() else self.appdata_yaml

    def get_preferred_json_path(self) -> Path:
        return self.local_json if self.local_json.exists() else self.appdata_json

    def load(self):
        """Loads configuration from YAML or JSON (local project prioritized over AppData)."""
        candidate_files = [
            self.local_yaml,
            self.local_json,
            self.appdata_yaml,
            self.appdata_json,
            # Legacy fallback
            APPDATA_DIR / "config.json",
        ]

        for file_path in candidate_files:
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding="utf-8")
                    if file_path.suffix.lower() in (".yaml", ".yml"):
                        loaded = parse_simple_yaml(content)
                    else:
                        loaded = json.loads(content)

                    if loaded and isinstance(loaded, dict):
                        self.config.update(loaded)
                        break
                except Exception as e:
                    print(f"[ConfigManager] Could not load from {file_path}: {e}")

    def save(self):
        """Automatically saves settings to BOTH settings.yaml and settings.json."""
        yaml_content = dump_annotated_yaml(self.config)
        json_content = json.dumps(self.config, indent=4, sort_keys=True)

        # 1. Save in project root directory (portable)
        try:
            self.local_yaml.write_text(yaml_content, encoding="utf-8")
            self.local_json.write_text(json_content, encoding="utf-8")
        except Exception:
            pass

        # 2. Save in %APPDATA%\TransparentLyrics (persistent backup)
        try:
            APPDATA_DIR.mkdir(parents=True, exist_ok=True)
            self.appdata_yaml.write_text(yaml_content, encoding="utf-8")
            self.appdata_json.write_text(json_content, encoding="utf-8")
        except Exception as e:
            print(f"[ConfigManager] Error saving to AppData: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        self.config[key] = value
        self.save()

    def open_in_editor(self, fmt: str = "yaml"):
        """Opens the chosen settings file (YAML or JSON) in the user's default text editor."""
        self.save()  # Ensure latest state is flushed to disk first
        target = self.local_yaml if fmt == "yaml" else self.local_json
        if not target.exists():
            target = self.appdata_yaml if fmt == "yaml" else self.appdata_json

        try:
            os.startfile(str(target))
        except Exception as e:
            print(f"[ConfigManager] Failed to open editor for {target}: {e}")

    def open_folder(self):
        """Opens the folder containing the settings files in Windows Explorer."""
        self.save()
        target_dir = PROJECT_ROOT if self.local_yaml.exists() else APPDATA_DIR
        try:
            os.startfile(str(target_dir))
        except Exception as e:
            print(f"[ConfigManager] Failed to open folder {target_dir}: {e}")
