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

    def __init__(self, prefer_uncensored: bool = True):
        self._cache: Dict[str, Optional[List[LyricLine]]] = {}
        self._lock = threading.Lock()
        self._fetch_threads: Dict[str, threading.Thread] = {}
        self._last_matched_index: int = -1
        self._last_matched_track: str = ""
        self.prefer_uncensored: bool = prefer_uncensored

    def set_prefer_uncensored(self, prefer: bool):
        """Updates uncensored lyrics preference and invalidates cache if changed."""
        if self.prefer_uncensored != prefer:
            self.prefer_uncensored = prefer
            self.clear_cache()

    def clear_cache(self, track_key: Optional[str] = None):
        """Clears cached lyrics for a specific track or all tracks."""
        with self._lock:
            if track_key:
                self._cache.pop(track_key, None)
            else:
                self._cache.clear()

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

            text = tag_pattern.sub("", raw_line).strip()

            # Ignore non-musical headers
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
                    query = f"{title} {artist}".strip()
                    # LRCLIB provides community uncensored lyrics, while NetEase censors explicit words
                    if self.prefer_uncensored:
                        providers = ['Lrclib', 'Musixmatch', 'Lyricsify', 'Genius', 'Megalobiz', 'Deezer', 'NetEase']
                    else:
                        providers = ['NetEase', 'Musixmatch', 'Lrclib', 'Lyricsify', 'Genius']

                    raw = syncedlyrics.search(query, providers=providers)
                    
                    if not raw and artist and artist.lower() not in title.lower():
                        raw = syncedlyrics.search(title.strip(), providers=providers)

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
        duration: float,
        track_key: str = ""
    ) -> Tuple[str, List[LyricLine], int, str]:
        """
        Calculates (state, lyrics_list, active_index, special_label).
        States: 'IDLE', 'LOADING', 'INTRO', 'LYRICS', 'INSTRUMENTAL', 'NO_LYRICS'
        """
        if track_key != self._last_matched_track:
            self._last_matched_track = track_key
            self._last_matched_index = -1

        if lyrics is None:
            return ("LOADING", [], -1, "Fetching synchronized lyrics...")

        if len(lyrics) == 0:
            return ("NO_LYRICS", [], -1, "(No synchronized lyrics found)")

        times = [l.time for l in lyrics]
        raw_idx = bisect.bisect_right(times, pos) - 1

        # Hysteresis: Prevent micro-jitter from fluctuating back to previous index
        if self._last_matched_index >= 0 and raw_idx == self._last_matched_index - 1:
            # Check if we are within 0.3s of the current index start time
            curr_time = times[self._last_matched_index]
            if (curr_time - pos) < 0.30:
                raw_idx = self._last_matched_index

        self._last_matched_index = raw_idx

        # Case 1: Before first lyric
        if raw_idx < 0:
            first_time = lyrics[0].time
            if first_time > 2.5:
                return ("INTRO", lyrics, -1, "(Intro)")
            else:
                return ("LYRICS", lyrics, 0, "")

        # Case 2: Interlude / Instrumental break
        if raw_idx + 1 < len(lyrics):
            gap = lyrics[raw_idx + 1].time - lyrics[raw_idx].time
            elapsed_since_active = pos - lyrics[raw_idx].time
            if gap > 13.0 and elapsed_since_active > 6.5:
                return ("INSTRUMENTAL", lyrics, raw_idx, "(Instrumental)")

        return ("LYRICS", lyrics, raw_idx, "")
