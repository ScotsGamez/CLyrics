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
    "active_opacity": 1.0,      # Active lyric line opacity (0.0 - 1.0)
    "next_opacity": 0.50,       # Next upcoming lyric opacity (0.0 - 1.0)
    "prev_opacity": 0.25,       # Previous lyric opacity (0.0 - 1.0)
    "prefer_uncensored": True,  # Prioritize uncensored lyrics providers (LRCLIB)
    "high_contrast_outline": False,  # Thick solid dark outline for maximum readability
    "check_for_updates": False,      # Automatically check for updates on startup (off by default)
    "first_run_update_notified": False,  # Whether user has been prompted on first run
}

# Primary local location (project root) and AppData fallback
PROJECT_ROOT = Path(__file__).resolve().parent.parent
APPDATA_DIR = Path(os.environ.get("APPDATA", ".")) / "TransparentLyrics"
LRC_CACHE_DIR = APPDATA_DIR / "lrc_cache"


def _parse_legacy_yaml(text: str) -> Dict[str, Any]:
    """Lightweight backward-compatibility parser for legacy YAML settings files."""
    data: Dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip()
            val = parts[1].split("#")[0].strip()
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


class ConfigManager:
    """Manages persistent user configuration via a single settings.json file with automatic legacy migration."""

    def __init__(self, root_dir: Optional[Path] = None, appdata_dir: Optional[Path] = None):
        self.config = DEFAULT_CONFIG.copy()

        self.root_dir = Path(root_dir) if root_dir else PROJECT_ROOT
        self.appdata_dir = Path(appdata_dir) if appdata_dir else APPDATA_DIR

        self.local_json = self.root_dir / "settings.json"
        self.appdata_json = self.appdata_dir / "settings.json"

        # Legacy file paths for migration
        self.legacy_local_yaml = self.root_dir / "settings.yaml"
        self.legacy_appdata_yaml = self.appdata_dir / "settings.yaml"
        self.legacy_appdata_json = self.appdata_dir / "config.json"

        self.load()

    def get_preferred_json_path(self) -> Path:
        return self.local_json if self.local_json.exists() else self.appdata_json

    def load(self):
        """Loads configuration from settings.json and automatically migrates legacy settings if present."""
        loaded_from_json = False

        # 1. Primary: load existing settings.json
        for file_path in [self.local_json, self.appdata_json]:
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding="utf-8")
                    loaded = json.loads(content)
                    if isinstance(loaded, dict):
                        self.config.update(loaded)
                        loaded_from_json = True
                        break
                except Exception as e:
                    print(f"[ConfigManager] Could not load from {file_path}: {e}")

        # 2. Backwards-compatibility: Check and migrate legacy YAML or config.json
        migrated = False
        legacy_sources = [
            (self.legacy_local_yaml, True),
            (self.legacy_appdata_yaml, True),
            (self.legacy_appdata_json, False),
        ]

        for legacy_file, is_yaml in legacy_sources:
            if legacy_file.exists():
                try:
                    content = legacy_file.read_text(encoding="utf-8")
                    if is_yaml:
                        legacy_data = _parse_legacy_yaml(content)
                    else:
                        legacy_data = json.loads(content)

                    if isinstance(legacy_data, dict) and legacy_data:
                        self.config.update(legacy_data)
                        migrated = True

                    # Remove or archive the legacy file once migrated
                    try:
                        legacy_file.unlink(missing_ok=True)
                    except Exception:
                        pass
                except Exception as e:
                    print(f"[ConfigManager] Error migrating legacy file {legacy_file}: {e}")

        # If settings were migrated or settings.json does not yet exist, persist to disk
        if migrated or not loaded_from_json:
            self.save()

    def save(self):
        """Saves current settings to settings.json (both local project root and %APPDATA%)."""
        json_content = json.dumps(self.config, indent=4, sort_keys=True)

        # 1. Local project root (portable)
        try:
            self.local_json.write_text(json_content, encoding="utf-8")
        except Exception:
            pass

        # 2. %APPDATA%\TransparentLyrics (persistent backup)
        try:
            self.appdata_dir.mkdir(parents=True, exist_ok=True)
            self.appdata_json.write_text(json_content, encoding="utf-8")
        except Exception as e:
            print(f"[ConfigManager] Error saving to AppData: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any, auto_save: bool = True):
        self.config[key] = value
        if auto_save:
            self.save()

    def bulk_set(self, mapping: Dict[str, Any]):
        """Updates multiple configuration keys at once with a single atomic save."""
        self.config.update(mapping)
        self.save()

    def reset_defaults(self):
        """Resets all settings back to DEFAULT_CONFIG."""
        self.config = DEFAULT_CONFIG.copy()
        self.save()

    def open_in_editor(self):
        """Opens settings.json in the user's default text editor."""
        self.save()
        target = self.get_preferred_json_path()
        try:
            os.startfile(str(target))
        except Exception as e:
            print(f"[ConfigManager] Failed to open editor for {target}: {e}")

    def open_folder(self):
        """Opens the folder containing settings.json in Windows Explorer."""
        self.save()
        target_dir = PROJECT_ROOT if self.local_json.exists() else APPDATA_DIR
        try:
            os.startfile(str(target_dir))
        except Exception as e:
            print(f"[ConfigManager] Failed to open folder {target_dir}: {e}")
