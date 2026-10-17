import sys
import os
import signal
from pathlib import Path

from PySide6.QtCore import Qt, QObject, Slot
from PySide6.QtWidgets import QApplication

from .config import ConfigManager
from .lyrics_service import LyricsService
from .media_service import MediaService
from .overlay_window import OverlayWindow
from .tray import LyricsTrayIcon


class TransparentLyricsApp(QObject):
    """Main application controller coordinating media telemetry, lyrics, and overlay UI."""

    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.lyrics_service = LyricsService()

        # Create overlay window
        self.window = OverlayWindow(self.config)

        # Create system tray icon
        self.tray = LyricsTrayIcon(self.window)
        self.tray.show()

        # Current track tracking
        self.current_track_key = ""
        self.last_pos = 0.0
        self.last_dur = 0.0
        self.last_playing = False
        self.last_title = ""
        self.last_artist = ""

        # Start Media Service
        self.media_service = MediaService()
        self.media_service.media_changed.connect(self.on_media_changed)
        self.media_service.start()

        # Display window
        self.window.show()

    @Slot(str, str, bool, float, float)
    def on_media_changed(self, title: str, artist: str, is_playing: bool, pos: float, duration: float):
        self.last_title = title
        self.last_artist = artist
        self.last_playing = is_playing
        self.last_pos = pos
        self.last_dur = duration

        if not title:
            # Idle State
            self.current_track_key = ""
            self.tray.update_track_info("", "", False)
            self.window.renderer.update_lyrics(
                state="IDLE",
                title="",
                artist="",
                is_playing=False,
                prev_line="",
                active_line="Ready for Music",
                next_line="Play any song on Spotify, YouTube, or Windows Media",
                active_index=-1
            )
            return

        track_key = self.lyrics_service._clean_track_id(title, artist)
        self.tray.update_track_info(title, artist, is_playing)

        # Track changed: Initiate background lyrics fetch
        if track_key != self.current_track_key:
            self.current_track_key = track_key
            if not self.lyrics_service.is_cached(title, artist):
                # Temporary loading state
                self.window.renderer.update_lyrics(
                    state="LOADING",
                    title=title,
                    artist=artist,
                    is_playing=is_playing,
                    prev_line="",
                    active_line="Fetching synchronized lyrics...",
                    next_line="",
                    active_index=-1
                )
                self.lyrics_service.fetch_lyrics_async(
                    title,
                    artist,
                    callback=self.on_lyrics_fetched
                )
                return

        # Synchronize active lyrics
        self._refresh_lyrics_display()

    def on_lyrics_fetched(self, track_key: str, parsed_lines):
        # Only refresh if the fetched lyrics correspond to the current song
        if track_key == self.current_track_key:
            self._refresh_lyrics_display()

    def _refresh_lyrics_display(self):
        if not self.last_title:
            return

        lyrics = self.lyrics_service.get_lyrics(self.last_title, self.last_artist)
        state, prev, active, nxt, idx = self.lyrics_service.match_lyrics(
            lyrics,
            self.last_pos,
            self.last_dur
        )

        self.window.renderer.update_lyrics(
            state=state,
            title=self.last_title,
            artist=self.last_artist,
            is_playing=self.last_playing,
            prev_line=prev,
            active_line=active,
            next_line=nxt,
            active_index=idx
        )

    def shutdown(self):
        if self.media_service:
            self.media_service.stop()
        if self.tray:
            self.tray.hide()


def main():
    # Enable high-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("TransparentLyrics")
    app.setOrganizationName("ScotsGamez")
    app.setQuitOnLastWindowClosed(False)

    controller = TransparentLyricsApp()

    # Graceful Ctrl+C handling
    signal.signal(signal.SIGINT, lambda *args: QApplication.quit())

    ret = app.exec()
    controller.shutdown()
    sys.exit(ret)


if __name__ == "__main__":
    main()
