import re
import json
import urllib.request
import urllib.parse
import threading
from typing import Optional, Dict
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPixmap, QImage


class ArtworkService(QObject):
    """Asynchronously fetches and caches high-resolution album artwork."""

    artwork_ready = Signal(str, QPixmap)  # track_key, pixmap

    def __init__(self):
        super().__init__()
        self._cache: Dict[str, Optional[QPixmap]] = {}
        self._lock = threading.Lock()
        self._pending_threads: Dict[str, threading.Thread] = {}

    @staticmethod
    def _clean_track_id(title: str, artist: str) -> str:
        t = re.sub(r"[^\w\s]", "", title.lower()).strip()
        a = re.sub(r"[^\w\s]", "", artist.lower()).strip()
        return f"{t} - {a}"

    def get_cached_artwork(self, title: str, artist: str) -> Optional[QPixmap]:
        track_key = self._clean_track_id(title, artist)
        with self._lock:
            return self._cache.get(track_key)

    def fetch_artwork_async(self, title: str, artist: str):
        track_key = self._clean_track_id(title, artist)

        with self._lock:
            if track_key in self._cache:
                pix = self._cache[track_key]
                if pix:
                    self.artwork_ready.emit(track_key, pix)
                return

            if track_key in self._pending_threads and self._pending_threads[track_key].is_alive():
                return

            def worker():
                pixmap = None
                try:
                    query = f"{title} {artist}".strip()
                    encoded = urllib.parse.quote(query)
                    url = f"https://itunes.apple.com/search?term={encoded}&entity=song&limit=1"

                    req = urllib.request.Request(
                        url,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                    )
                    with urllib.request.urlopen(req, timeout=4) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        results = data.get("results", [])
                        if results:
                            raw_art_url = results[0].get("artworkUrl100", "")
                            if raw_art_url:
                                high_res_url = raw_art_url.replace("100x100bb", "600x600bb")
                                img_req = urllib.request.Request(
                                    high_res_url,
                                    headers={"User-Agent": "Mozilla/5.0"}
                                )
                                img_bytes = urllib.request.urlopen(img_req, timeout=5).read()
                                qimg = QImage.fromData(img_bytes)
                                if not qimg.isNull():
                                    pixmap = QPixmap.fromImage(qimg)
                except Exception as e:
                    print(f"[ArtworkService] Fetch error for {title}: {e}")

                with self._lock:
                    self._cache[track_key] = pixmap

                if pixmap:
                    self.artwork_ready.emit(track_key, pixmap)

            th = threading.Thread(target=worker, daemon=True)
            self._pending_threads[track_key] = th
            th.start()
