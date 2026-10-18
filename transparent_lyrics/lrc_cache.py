import os
import re
import json
import hashlib
import threading
from pathlib import Path
from typing import Optional, List, Dict
from .config import APPDATA_DIR


class LrcFileCache:
    """
    Rolling on-disk temporary file cache storing up to 5 previous track .lrc files.
    When a new previous track comes in and the cache exceeds 5 files, the oldest .lrc file
    is automatically deleted from disk.
    """

    def __init__(self, cache_dir: Optional[Path] = None, max_size: int = 5):
        self.max_size = max_size
        if cache_dir is None:
            self.cache_dir = Path(APPDATA_DIR) / "lrc_cache"
        else:
            self.cache_dir = Path(cache_dir)

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_file = self.cache_dir / "cache_manifest.json"
        self._lock = threading.Lock()
        self._entries: List[Dict[str, str]] = []  # List of {"track_key": key, "filename": filename}
        self._load_manifest()

    def _load_manifest(self):
        with self._lock:
            if self.manifest_file.exists():
                try:
                    with open(self.manifest_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            valid = []
                            for item in data:
                                fname = item.get("filename")
                                if fname and (self.cache_dir / fname).exists():
                                    valid.append(item)
                            self._entries = valid
                except Exception as e:
                    print(f"[LrcFileCache] Error loading manifest: {e}")
                    self._entries = []
            else:
                self._entries = []
            self._enforce_limit()

    def _save_manifest(self):
        try:
            with open(self.manifest_file, "w", encoding="utf-8") as f:
                json.dump(self._entries, f, indent=2)
        except Exception as e:
            print(f"[LrcFileCache] Error saving manifest: {e}")

    def _enforce_limit(self):
        """Deletes the oldest .lrc files if the cache exceeds max_size (default: 5)."""
        while len(self._entries) > self.max_size:
            oldest = self._entries.pop(0)
            old_file = self.cache_dir / oldest["filename"]
            try:
                if old_file.exists():
                    old_file.unlink()
            except Exception as e:
                print(f"[LrcFileCache] Error deleting old cache file {old_file}: {e}")

    def save_lrc(self, track_key: str, lrc_content: str) -> Optional[Path]:
        """Saves a track's .lrc file to disk, updating rolling order and deleting excess files."""
        if not track_key or not lrc_content or not lrc_content.strip():
            return None

        with self._lock:
            # Check if this track is already in the cache
            existing = [item for item in self._entries if item["track_key"] == track_key]
            if existing:
                filename = existing[0]["filename"]
                filepath = self.cache_dir / filename
                # Move to most recent position
                self._entries = [item for item in self._entries if item["track_key"] != track_key]
                self._entries.append({"track_key": track_key, "filename": filename})
            else:
                slug = re.sub(r"[^\w\-]", "_", track_key).strip("_")[:40]
                h = hashlib.sha256(track_key.encode("utf-8")).hexdigest()[:8]
                filename = f"{slug}_{h}.lrc"
                filepath = self.cache_dir / filename
                self._entries.append({"track_key": track_key, "filename": filename})

            # Write .lrc content to disk
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(lrc_content)
            except Exception as e:
                print(f"[LrcFileCache] Error writing {filepath}: {e}")
                return None

            self._enforce_limit()
            self._save_manifest()
            return filepath

    def get_lrc(self, track_key: str) -> Optional[str]:
        """Retrieves raw .lrc content from disk if present in cache."""
        if not track_key:
            return None

        with self._lock:
            item = next((x for x in self._entries if x["track_key"] == track_key), None)
            if not item:
                return None

            filepath = self.cache_dir / item["filename"]
            if not filepath.exists():
                self._entries.remove(item)
                self._save_manifest()
                return None

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                print(f"[LrcFileCache] Error reading {filepath}: {e}")
                return None

    def has_lrc(self, track_key: str) -> bool:
        """Checks whether an .lrc file exists in cache for the given track_key."""
        with self._lock:
            item = next((x for x in self._entries if x["track_key"] == track_key), None)
            if item:
                filepath = self.cache_dir / item["filename"]
                return filepath.exists()
            return False

    def get_cached_track_keys(self) -> List[str]:
        with self._lock:
            return [x["track_key"] for x in self._entries]

    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def clear(self):
        """Cleans up all cached .lrc files on disk."""
        with self._lock:
            for item in self._entries:
                try:
                    f = self.cache_dir / item["filename"]
                    if f.exists():
                        f.unlink()
                except Exception:
                    pass
            self._entries.clear()
            self._save_manifest()
