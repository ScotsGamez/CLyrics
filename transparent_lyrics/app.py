import sys
import os
import time
import signal
from pathlib import Path

from PySide6.QtCore import Qt, QObject, Slot, QTimer
from PySide6.QtWidgets import QApplication

from .config import ConfigManager
from .lyrics_service import LyricsService
from .media_service import MediaService
from .artwork_service import ArtworkService
from .overlay_window import OverlayWindow
from .tray import LyricsTrayIcon


class SmoothTimeTracker:
    """Monotonic high-precision playback position tracker that eliminates Windows GSMTC jitter."""

    def __init__(self):
        self.anchor_pos: float = 0.0
        self.anchor_perf: float = 0.0
        self.is_playing: bool = False
        self.duration: float = 0.0

    def update_from_telemetry(self, reported_pos: float, is_playing: bool, duration: float):
        now = time.perf_counter()
        self.duration = duration

        if not self.is_playing and is_playing:
            # Resumed playback
            self.anchor_pos = reported_pos
            self.anchor_perf = now
            self.is_playing = True
            return

        if not is_playing:
            self.anchor_pos = reported_pos
            self.anchor_perf = now
            self.is_playing = False
            return

        # Track is playing: compare estimated position with reported position
        estimated = self.anchor_pos + (now - self.anchor_perf)
        diff = reported_pos - estimated

        # If difference is large (> 1.5s), a seek or skip occurred
        if abs(diff) > 1.5:
            self.anchor_pos = reported_pos
            self.anchor_perf = now
        else:
            # Absorb micro-jitter smoothly without ever stepping backwards
            if diff > 0.04:
                self.anchor_pos += diff * 0.25
            elif diff < -0.04:
                # Reported is slightly behind estimated: slow down slightly but do not jump back
                self.anchor_pos += diff * 0.05

    def get_current_pos(self) -> float:
        if not self.is_playing:
            return self.anchor_pos
        now = time.perf_counter()
        pos = self.anchor_pos + (now - self.anchor_perf)
        if self.duration > 0:
            return min(self.duration, max(0.0, pos))
        return max(0.0, pos)


class TransparentLyricsApp(QObject):
    """Main application controller coordinating media telemetry, lyrics, artwork, and overlay UI."""

    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        prefer_uncensored = bool(self.config.get("prefer_uncensored", True))
        self.lyrics_service = LyricsService(prefer_uncensored=prefer_uncensored)
        self.artwork_service = ArtworkService()
        self.time_tracker = SmoothTimeTracker()

        # Create overlay window
        self.window = OverlayWindow(self.config)
        self.window.uncensored_changed.connect(self.on_uncensored_changed)

        # Create system tray icon
        self.tray = LyricsTrayIcon(self.window)
        self.tray.show()

        # Connect artwork service
        self.artwork_service.artwork_ready.connect(self.on_artwork_ready)

        # Current track tracking
        self.current_track_key = ""
        self.last_title = ""
        self.last_artist = ""
        self.last_playing = False

        # Start Media Service
        self.media_service = MediaService()
        self.media_service.media_changed.connect(self.on_media_changed)
        self.media_service.start()

        # High-frequency 50ms display sync timer
        self.sync_timer = QTimer(self)
        self.sync_timer.setInterval(50)
        self.sync_timer.timeout.connect(self._sync_lyrics_tick)
        self.sync_timer.start()

        # Display window
        self.window.show()

    @Slot(str, str, bool, float, float)
    def on_media_changed(self, title: str, artist: str, is_playing: bool, pos: float, duration: float):
        self.last_title = title
        self.last_artist = artist
        self.last_playing = is_playing
        self.time_tracker.update_from_telemetry(pos, is_playing, duration)

        if not title:
            # Idle State
            self.current_track_key = ""
            self.tray.update_track_info("", "", False)
            self.window.renderer.set_artwork(None)
            self.window.renderer.update_lyrics_state(
                state="IDLE",
                title="",
                artist="",
                is_playing=False,
                lyrics=[],
                active_index=-1
            )
            return

        track_key = self.lyrics_service._clean_track_id(title, artist)
        self.tray.update_track_info(title, artist, is_playing)

        # Track changed: Fetch lyrics and artwork asynchronously
        if track_key != self.current_track_key:
            self.current_track_key = track_key

            # Fetch Album Art
            cached_art = self.artwork_service.get_cached_artwork(title, artist)
            if cached_art:
                self.window.renderer.set_artwork(cached_art)
            else:
                self.window.renderer.set_artwork(None)
                self.artwork_service.fetch_artwork_async(title, artist)

            # Fetch Lyrics
            if not self.lyrics_service.is_cached(title, artist):
                self.window.renderer.update_lyrics_state(
                    state="LOADING",
                    title=title,
                    artist=artist,
                    is_playing=is_playing,
                    lyrics=[],
                    active_index=-1,
                    special_label="Fetching synchronized lyrics..."
                )
                self.lyrics_service.fetch_lyrics_async(
                    title,
                    artist,
                    callback=self.on_lyrics_fetched
                )
                return

        self._sync_lyrics_tick()

    def on_lyrics_fetched(self, track_key: str, parsed_lines):
        if track_key == self.current_track_key:
            self._sync_lyrics_tick()

    def on_uncensored_changed(self, prefer: bool):
        self.lyrics_service.set_prefer_uncensored(prefer)
        if self.last_title:
            self.window.renderer.update_lyrics_state(
                state="LOADING",
                title=self.last_title,
                artist=self.last_artist,
                is_playing=self.last_playing,
                lyrics=[],
                active_index=-1,
                special_label="Fetching synchronized lyrics..."
            )
            self.lyrics_service.fetch_lyrics_async(
                self.last_title,
                self.last_artist,
                callback=self.on_lyrics_fetched
            )

    @Slot(str, object)
    def on_artwork_ready(self, track_key: str, pixmap):
        if track_key == self.current_track_key and pixmap:
            self.window.renderer.set_artwork(pixmap)

    def _sync_lyrics_tick(self):
        if not self.last_title:
            return

        offset = float(self.config.get("sync_offset", 0.0))
        current_pos = max(0.0, self.time_tracker.get_current_pos() + offset)
        lyrics = self.lyrics_service.get_lyrics(self.last_title, self.last_artist)

        state, lyrics_list, active_index, special_label = self.lyrics_service.match_lyrics(
            lyrics,
            current_pos,
            self.time_tracker.duration,
            track_key=self.current_track_key
        )

        self.window.renderer.update_lyrics_state(
            state=state,
            title=self.last_title,
            artist=self.last_artist,
            is_playing=self.last_playing,
            lyrics=lyrics_list,
            active_index=active_index,
            special_label=special_label
        )

    def shutdown(self):
        if self.sync_timer:
            self.sync_timer.stop()
        if self.media_service:
            self.media_service.stop()
        if self.tray:
            self.tray.hide()


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("TransparentLyrics")
    app.setOrganizationName("ScotsGamez")
    app.setQuitOnLastWindowClosed(False)

    controller = TransparentLyricsApp()

    signal.signal(signal.SIGINT, lambda *args: QApplication.quit())

    ret = app.exec()
    controller.shutdown()
    sys.exit(ret)


if __name__ == "__main__":
    main()
