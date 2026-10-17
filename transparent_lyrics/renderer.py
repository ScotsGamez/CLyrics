import time
from typing import Optional
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QFont, QFontMetrics, QColor, QPen
from PySide6.QtWidgets import QWidget
from .themes import LyricTheme, get_theme


def ease_out_cubic(x: float) -> float:
    return 1.0 - pow(1.0 - x, 3)


class LyricsRenderer(QWidget):
    """Custom paint widget rendering 3-line animated smooth-scrolling floating lyrics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.theme: LyricTheme = get_theme("Minimalist")

        # Display Data
        self.state: str = "IDLE"  # IDLE, LOADING, INTRO, LYRICS, INSTRUMENTAL, NO_LYRICS
        self.title: str = ""
        self.artist: str = ""
        self.is_playing: bool = False
        self.active_index: int = -1

        self.prev_line: str = ""
        self.active_line: str = "Ready for Music"
        self.next_line: str = "Play any song on Spotify, YouTube, or Windows Media"

        # Smooth Scroll Animation state
        self._last_index: int = -1
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)  # ~60 FPS
        self._anim_timer.timeout.connect(self._on_anim_tick)
        self._anim_start_time: float = 0.0
        self._anim_duration: float = 0.32  # 320ms transition
        self._is_animating: bool = False
        self._anim_progress: float = 1.0  # 0.0 -> 1.0

        # Snapshot of previous lines during transition
        self._trans_old_prev: str = ""
        self._trans_old_active: str = ""
        self._trans_old_next: str = ""

        # Banner & Graceful Fade-Out state
        self._track_change_time: float = 0.0
        self._no_lyrics_time: float = 0.0
        self._global_fade_alpha: float = 1.0

        # Master redraw timer for subtle fade animations
        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(50)
        self._clock_timer.timeout.connect(self._on_clock_tick)
        self._clock_timer.start()

    def set_theme(self, theme: LyricTheme):
        self.theme = theme
        self.update()

    def update_lyrics(
        self,
        state: str,
        title: str,
        artist: str,
        is_playing: bool,
        prev_line: str,
        active_line: str,
        next_line: str,
        active_index: int,
    ):
        now = time.time()

        # Detect track change
        if title != self.title or artist != self.artist:
            self._track_change_time = now
            self._last_index = -1
            self._global_fade_alpha = 1.0
            if state == "NO_LYRICS":
                self._no_lyrics_time = now

        # Detect NO_LYRICS state transition
        if state == "NO_LYRICS" and self.state != "NO_LYRICS":
            self._no_lyrics_time = now

        # Detect lyric line change -> Trigger smooth vertical slide animation
        if active_index != self.active_index and state in ("LYRICS", "INSTRUMENTAL", "INTRO"):
            if self.active_line and active_line != self.active_line:
                # Capture snapshot for interpolation
                self._trans_old_prev = self.prev_line
                self._trans_old_active = self.active_line
                self._trans_old_next = self.next_line

                self._anim_start_time = now
                self._anim_progress = 0.0
                self._is_animating = True
                if not self._anim_timer.isActive():
                    self._anim_timer.start()

            self._last_index = active_index

        self.state = state
        self.title = title
        self.artist = artist
        self.is_playing = is_playing
        self.prev_line = prev_line
        self.active_line = active_line
        self.next_line = next_line
        self.active_index = active_index

        self.update()

    def _on_anim_tick(self):
        if not self._is_animating:
            self._anim_timer.stop()
            return

        elapsed = time.time() - self._anim_start_time
        prog = elapsed / self._anim_duration
        if prog >= 1.0:
            self._anim_progress = 1.0
            self._is_animating = False
            self._anim_timer.stop()
        else:
            self._anim_progress = prog

        self.update()

    def _on_clock_tick(self):
        # Handle graceful fade-out for NO_LYRICS
        if self.state == "NO_LYRICS" and self._no_lyrics_time > 0:
            elapsed = time.time() - self._no_lyrics_time
            if elapsed > 4.0:
                fade = max(0.0, 1.0 - (elapsed - 4.0) / 1.5)
                if abs(self._global_fade_alpha - fade) > 0.02:
                    self._global_fade_alpha = fade
                    self.update()
            else:
                if self._global_fade_alpha != 1.0:
                    self._global_fade_alpha = 1.0
                    self.update()
        elif self._global_fade_alpha < 1.0:
            self._global_fade_alpha = min(1.0, self._global_fade_alpha + 0.1)
            self.update()

        # Redraw if track banner is in the process of fading
        if (time.time() - self._track_change_time) < 8.0:
            self.update()

    def _draw_centered_line(
        self,
        painter: QPainter,
        text: str,
        y_center: float,
        font: QFont,
        color: QColor,
        alpha_multiplier: float,
        max_width: float,
    ):
        if not text or alpha_multiplier <= 0.01:
            return

        painter.setFont(font)
        fm = QFontMetrics(font)

        # Truncate or scale if line is exceedingly wide
        text_w = fm.horizontalAdvance(text)
        draw_text = text
        if text_w > max_width:
            draw_text = fm.elidedText(text, Qt.ElideMiddle, int(max_width))

        draw_color = QColor(color)
        final_alpha = max(0.0, min(1.0, color.alphaF() * alpha_multiplier * self._global_fade_alpha))
        draw_color.setAlphaF(final_alpha)
        painter.setPen(draw_color)

        rect = QRectF(20, y_center - 24, self.width() - 40, 48)
        painter.drawText(rect, Qt.AlignCenter | Qt.AlignVCenter, draw_text)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        # 100% Transparent background: We paint ZERO background fills.
        w = float(self.width())
        h = float(self.height())
        cy = h / 2.0
        line_spacing = 54.0
        max_text_width = w - 60.0

        # Fonts configuration
        font_family = self.theme.font_family
        font_active = QFont(font_family, 22, QFont.Weight(self.theme.active_weight))
        font_context = QFont(font_family, 15, QFont.Weight(self.theme.context_weight))
        font_meta = QFont(font_family, 11, QFont.Weight.Medium)

        active_color = self.theme.get_active_qcolor()
        context_color = self.theme.get_context_qcolor()
        meta_color = self.theme.get_meta_qcolor()

        now = time.time()

        # 1. Subtle Track Header Banner (Shows Title & Artist)
        if self.title:
            banner_text = f"♪ {self.title}"
            if self.artist:
                banner_text += f"  •  {self.artist}"

            banner_elapsed = now - self._track_change_time
            banner_alpha = 1.0
            if banner_elapsed > 5.0:
                banner_alpha = max(0.35, 1.0 - (banner_elapsed - 5.0) / 2.5)

            banner_rect = QRectF(20, 8, w - 40, 24)
            b_color = QColor(meta_color)
            b_color.setAlphaF(max(0.0, min(1.0, meta_color.alphaF() * banner_alpha * self._global_fade_alpha)))
            painter.setFont(font_meta)
            painter.setPen(b_color)
            fm_meta = QFontMetrics(font_meta)
            elided_banner = fm_meta.elidedText(banner_text, Qt.ElideRight, int(max_text_width))
            painter.drawText(banner_rect, Qt.AlignCenter, elided_banner)

        # 2. Render 3-Line Scrolling Lyrics
        if self._is_animating:
            # Interpolation easing
            t = ease_out_cubic(self._anim_progress)
            shift_y = (1.0 - t) * line_spacing

            # Old active line slides up and fades from 1.0 -> context_opacity
            old_active_alpha = 1.0 - t * (1.0 - self.theme.context_opacity)
            self._draw_centered_line(
                painter,
                self._trans_old_active,
                cy - shift_y,
                font_active,
                active_color,
                old_active_alpha,
                max_text_width,
            )

            # New active line slides up from bottom into center and fades in from context_opacity -> 1.0
            new_active_alpha = self.theme.context_opacity + t * (1.0 - self.theme.context_opacity)
            self._draw_centered_line(
                painter,
                self.active_line,
                (cy + line_spacing) - shift_y,
                font_active,
                active_color,
                new_active_alpha,
                max_text_width,
            )

            # Previous line fades and slides above
            old_prev_alpha = max(0.0, self.theme.context_opacity * (1.0 - t))
            self._draw_centered_line(
                painter,
                self._trans_old_prev,
                (cy - line_spacing) - shift_y,
                font_context,
                context_color,
                old_prev_alpha,
                max_text_width,
            )

            # Next line slides up from below
            nxt_alpha = self.theme.context_opacity * t
            self._draw_centered_line(
                painter,
                self.next_line,
                (cy + line_spacing * 2) - shift_y,
                font_context,
                context_color,
                nxt_alpha,
                max_text_width,
            )

        else:
            # Static 3-Line Presentation
            # Line 1: Previous
            self._draw_centered_line(
                painter,
                self.prev_line,
                cy - line_spacing,
                font_context,
                context_color,
                1.0,
                max_text_width,
            )

            # Line 2: Active Line (Prominent)
            self._draw_centered_line(
                painter,
                self.active_line,
                cy,
                font_active,
                active_color,
                1.0,
                max_text_width,
            )

            # Line 3: Next Line (Upcoming)
            self._draw_centered_line(
                painter,
                self.next_line,
                cy + line_spacing,
                font_context,
                context_color,
                1.0,
                max_text_width,
            )
