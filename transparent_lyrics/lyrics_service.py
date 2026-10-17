import re
import bisect
import threading
from typing import List, Tuple, Optional, Dict
import syncedlyrics


class LyricLine:
    __slots__ = ("time", "text")

    def __init__(self, time: float, text: str):
        self.time = time
        self.text = text

    def __repr__(self):
        return f"[{self.time:.2f}] {self.text}"


class LyricsService:
    """Handles fetching, caching, parsing, and real-time synchronization of LRC lyrics."""

    def __init__(self):
        self._cache: Dict[str, Optional[List[LyricLine]]] = {}
        self._lock = threading.Lock()
        self._fetch_threads: Dict[str, threading.Thread] = {}

    @staticmethod
    def _clean_track_id(title: str, artist: str) -> str:
        t = re.sub(r"[^\w\s]", "", title.lower()).strip()
        a = re.sub(r"[^\w\s]", "", artist.lower()).strip()
        return f"{t} - {a}"

    def parse_lrc(self, lrc_text: str) -> List[LyricLine]:
        """Parses LRC format string into a sorted list of LyricLine objects."""
        lines: List[LyricLine] = []
        if not lrc_text:
            return lines

        tag_pattern = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")

        for raw_line in lrc_text.splitlines():
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            matches = list(tag_pattern.finditer(raw_line))
            if not matches:
                continue

            # Strip all timestamp tags from the line to get the lyric text
            text = tag_pattern.sub("", raw_line).strip()

            # Ignore common LRC metadata / credits headers if they're not musical
            if text.startswith(("作词", "作曲", "编曲", "ti:", "ar:", "al:", "by:", "offset:")):
                continue

            for match in matches:
                minutes = float(match.group(1))
                seconds = float(match.group(2))
                total_seconds = minutes * 60.0 + seconds
                lines.append(LyricLine(total_seconds, text))

        lines.sort(key=lambda x: x.time)
        return lines

    def fetch_lyrics_async(self, title: str, artist: str, callback=None):
        """Fetches lyrics in a background worker thread."""
        track_key = self._clean_track_id(title, artist)

        with self._lock:
            if track_key in self._cache:
                if callback:
                    callback(track_key, self._cache[track_key])
                return

            if track_key in self._fetch_threads and self._fetch_threads[track_key].is_alive():
                return

            def worker():
                parsed = None
                try:
                    # 1. Search with title + artist
                    query = f"{title} {artist}".strip()
                    raw = syncedlyrics.search(query)
                    
                    # 2. Fallback: Search with title only if artist combo returned nothing
                    if not raw and artist and artist.lower() not in title.lower():
                        raw = syncedlyrics.search(title.strip())

                    if raw:
                        parsed = self.parse_lrc(raw)
                except Exception as e:
                    print(f"[LyricsService] Fetch error for {title}: {e}")

                with self._lock:
                    self._cache[track_key] = parsed

                if callback:
                    callback(track_key, parsed)

            th = threading.Thread(target=worker, daemon=True)
            self._fetch_threads[track_key] = th
            th.start()

    def get_lyrics(self, title: str, artist: str) -> Optional[List[LyricLine]]:
        track_key = self._clean_track_id(title, artist)
        with self._lock:
            return self._cache.get(track_key)

    def is_cached(self, title: str, artist: str) -> bool:
        track_key = self._clean_track_id(title, artist)
        with self._lock:
            return track_key in self._cache

    def match_lyrics(
        self,
        lyrics: Optional[List[LyricLine]],
        pos: float,
        duration: float
    ) -> Tuple[str, str, str, str, int]:
        """
        Calculates (state, prev_line, active_line, next_line, active_index).
        States: 'IDLE', 'INTRO', 'LYRICS', 'INSTRUMENTAL', 'NO_LYRICS'
        """
        if lyrics is None:
            return ("LOADING", "", "Fetching synchronized lyrics...", "", -1)

        if len(lyrics) == 0:
            return ("NO_LYRICS", "", "(No synchronized lyrics found)", "", -1)

        times = [l.time for l in lyrics]
        idx = bisect.bisect_right(times, pos) - 1

        # Case 1: Before first lyric starts
        if idx < 0:
            first_lyric = lyrics[0].text
            first_time = lyrics[0].time
            if first_time > 2.5:
                return ("INTRO", "", "(Intro)", first_lyric, -1)
            else:
                return ("LYRICS", "", first_lyric, lyrics[1].text if len(lyrics) > 1 else "", 0)

        active = lyrics[idx].text
        prev = lyrics[idx - 1].text if idx > 0 else ""
        nxt = lyrics[idx + 1].text if idx + 1 < len(lyrics) else ""

        # Case 2: Check for long instrumental interlude between lyrics
        if idx + 1 < len(lyrics):
            gap = lyrics[idx + 1].time - lyrics[idx].time
            elapsed_since_active = pos - lyrics[idx].time
            if gap > 14.0 and elapsed_since_active > 7.0:
                return ("INSTRUMENTAL", active, "(Instrumental)", nxt, idx)

        return ("LYRICS", prev, active, nxt, idx)
