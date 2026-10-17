import time
from typing import List, Optional
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QFont, QFontMetrics, QColor, QPixmap, QPainterPath, QPen
from PySide6.QtWidgets import QWidget
from .themes import LyricTheme, get_theme
from .lyrics_service import LyricLine


class LyricsRenderer(QWidget):
    """Custom paint widget rendering continuous 60 FPS smooth-scrolling floating lyrics and album art."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.theme: LyricTheme = get_theme("Minimalist")

        # Telemetry & State
        self.state: str = "IDLE"  # IDLE, LOADING, INTRO, LYRICS, INSTRUMENTAL, NO_LYRICS
        self.title: str = ""
        self.artist: str = ""
        self.is_playing: bool = False

        # Lyrics data
        self.lyrics: List[LyricLine] = []
        self.active_index: int = -1
        self.special_label: str = ""

        # Continuous smooth scroll float tracking
        self._current_index: float = -1.0
        self._target_index: float = -1.0

        # Album Art Configuration & State
        self.album_cover_mode: str = "off"  # "off", "left", "right"
        self.current_artwork: Optional[QPixmap] = None
        self.target_artwork: Optional[QPixmap] = None
        self._art_alpha: float = 1.0

        # Timers & animations
        self._track_change_time: float = 0.0
        self._no_lyrics_time: float = 0.0
        self._global_fade_alpha: float = 1.0

        # Master 60 FPS tick timer for ultra-smooth continuous animation
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)  # ~60 FPS
        self._anim_timer.timeout.connect(self._on_tick)
        self._anim_timer.start()

    def set_theme(self, theme: LyricTheme):
        self.theme = theme
        self.update()

    def set_album_cover_mode(self, mode: str):
        self.album_cover_mode = mode
        self.update()

    def set_artwork(self, pixmap: Optional[QPixmap]):
        self.target_artwork = pixmap
        if self.current_artwork is None and pixmap is not None:
            self.current_artwork = pixmap
            self._art_alpha = 1.0
        self.update()

    def update_lyrics_state(
        self,
        state: str,
        title: str,
        artist: str,
        is_playing: bool,
        lyrics: List[LyricLine],
        active_index: int,
        special_label: str = ""
    ):
        now = time.time()

        # Detect track change
        if title != self.title or artist != self.artist:
            self._track_change_time = now
            self._current_index = float(active_index)
            self._target_index = float(active_index)
            self._global_fade_alpha = 1.0
            self.target_artwork = None
            self.current_artwork = None
            if state == "NO_LYRICS":
                self._no_lyrics_time = now

        # Detect NO_LYRICS state transition
        if state == "NO_LYRICS" and self.state != "NO_LYRICS":
            self._no_lyrics_time = now

        self.state = state
        self.title = title
        self.artist = artist
        self.is_playing = is_playing
        self.lyrics = lyrics
        self.active_index = active_index
        self.special_label = special_label

        # Set target index for continuous scrolling
        if active_index >= 0:
            self._target_index = float(active_index)
            if self._current_index < 0:
                self._current_index = float(active_index)
            # If seeking happened (jump > 2 lines), snap close to avoid flying across many lines
            elif abs(self._target_index - self._current_index) > 2.5:
                if self._target_index > self._current_index:
                    self._current_index = self._target_index - 0.7
                else:
                    self._current_index = self._target_index + 0.7
        else:
            self._target_index = -1.0
            self._current_index = -1.0

        self.update()

    def _on_tick(self):
        needs_redraw = False

        # 1. Smoothly interpolate current scroll float index towards target index
        if self._target_index >= 0 and self._current_index >= 0:
            diff = self._target_index - self._current_index
            if abs(diff) > 0.003:
                # Smooth spring/ease-out step (~200ms arrival)
                self._current_index += diff * 0.16
                needs_redraw = True
            elif self._current_index != self._target_index:
                self._current_index = self._target_index
                needs_redraw = True

        # 2. Smoothly cross-fade album artwork if target changed
        if self.target_artwork != self.current_artwork:
            self.current_artwork = self.target_artwork
            self._art_alpha = 0.0
            needs_redraw = True

        if self._art_alpha < 1.0 and self.current_artwork is not None:
            self._art_alpha = min(1.0, self._art_alpha + 0.08)
            needs_redraw = True

        # 3. Handle NO_LYRICS graceful fade-out
        if self.state == "NO_LYRICS" and self._no_lyrics_time > 0:
            elapsed = time.time() - self._no_lyrics_time
            if elapsed > 4.0:
                fade = max(0.0, 1.0 - (elapsed - 4.0) / 1.5)
                if abs(self._global_fade_alpha - fade) > 0.01:
                    self._global_fade_alpha = fade
                    needs_redraw = True
            elif self._global_fade_alpha != 1.0:
                self._global_fade_alpha = 1.0
                needs_redraw = True
        elif self._global_fade_alpha < 1.0:
            self._global_fade_alpha = min(1.0, self._global_fade_alpha + 0.05)
            needs_redraw = True

        # 4. Redraw if banner is in transition
        if (time.time() - self._track_change_time) < 8.0:
            needs_redraw = True

        if needs_redraw:
            self.update()

    def _draw_text_line(
        self,
        painter: QPainter,
        text: str,
        x_center: float,
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

        draw_text = text
        if fm.horizontalAdvance(text) > max_width:
            draw_text = fm.elidedText(text, Qt.ElideMiddle, int(max_width))

        draw_color = QColor(color)
        final_alpha = max(0.0, min(1.0, color.alphaF() * alpha_multiplier * self._global_fade_alpha))
        draw_color.setAlphaF(final_alpha)
        painter.setPen(draw_color)

        rect = QRectF(x_center - max_width / 2.0, y_center - 24, max_width, 48)
        painter.drawText(rect, Qt.AlignCenter | Qt.AlignVCenter, draw_text)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        w = float(self.width())
        h = float(self.height())
        cy = h / 2.0
        line_spacing = 54.0

        # Determine Layout: Album cover left/right vs full width
        has_album_art = (self.album_cover_mode in ("left", "right"))
        art_size = min(h - 28.0, 175.0)

        if self.album_cover_mode == "left":
            art_x = 24.0
            art_y = (h - art_size) / 2.0
            text_x_start = art_x + art_size + 24.0
            text_w = w - text_x_start - 24.0
            text_center_x = text_x_start + text_w / 2.0
        elif self.album_cover_mode == "right":
            text_x_start = 24.0
            text_w = w - art_size - 72.0
            text_center_x = text_x_start + text_w / 2.0
            art_x = w - art_size - 24.0
            art_y = (h - art_size) / 2.0
        else:
            text_w = w - 48.0
            text_center_x = w / 2.0

        # 1. Render Album Artwork (if enabled)
        if has_album_art:
            art_rect = QRectF(art_x, art_y, art_size, art_size)
            path = QPainterPath()
            path.addRoundedRect(art_rect, 14.0, 14.0)

            painter.save()
            painter.setClipPath(path)

            if self.current_artwork and not self.current_artwork.isNull():
                scaled = self.current_artwork.scaled(
                    int(art_size),
                    int(art_size),
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation
                )
                painter.setOpacity(self._art_alpha * self._global_fade_alpha)
                painter.drawPixmap(int(art_x), int(art_y), scaled)
            else:
                # Subtle placeholder for album cover
                painter.setBrush(QColor(255, 255, 255, 12))
                painter.setPen(Qt.NoPen)
                painter.drawRect(art_rect)
                painter.setPen(QColor(255, 255, 255, 40))
                painter.setFont(QFont("Segoe UI", 12))
                painter.drawText(art_rect, Qt.AlignCenter, "♪")

            painter.restore()

            # Elegant border outline
            border_color = QColor(255, 255, 255, int(45 * self._global_fade_alpha))
            painter.setPen(QPen(border_color, 1.5))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(art_rect, 14.0, 14.0)

        # 2. Render Track Header Banner
        font_family = self.theme.font_family
        font_active = QFont(font_family, 22, QFont.Weight(self.theme.active_weight))
        font_context = QFont(font_family, 15, QFont.Weight(self.theme.context_weight))
        font_meta = QFont(font_family, 11, QFont.Weight.Medium)

        active_color = self.theme.get_active_qcolor()
        context_color = self.theme.get_context_qcolor()
        meta_color = self.theme.get_meta_qcolor()

        now = time.time()
        if self.title:
            banner_text = f"♪ {self.title}"
            if self.artist:
                banner_text += f"  •  {self.artist}"

            banner_elapsed = now - self._track_change_time
            banner_alpha = 1.0
            if banner_elapsed > 5.0:
                banner_alpha = max(0.35, 1.0 - (banner_elapsed - 5.0) / 2.5)

            banner_rect = QRectF(text_center_x - text_w / 2.0, 8, text_w, 24)
            b_color = QColor(meta_color)
            b_color.setAlphaF(max(0.0, min(1.0, meta_color.alphaF() * banner_alpha * self._global_fade_alpha)))
            painter.setFont(font_meta)
            painter.setPen(b_color)
            fm_meta = QFontMetrics(font_meta)
            elided_banner = fm_meta.elidedText(banner_text, Qt.ElideRight, int(text_w))
            painter.drawText(banner_rect, Qt.AlignCenter, elided_banner)

        # 3. Render Continuous 3-Line Scrolling Lyrics
        if self.state in ("LYRICS", "INSTRUMENTAL") and self.lyrics and self._current_index >= 0:
            c_idx = self._current_index
            min_i = max(0, int(c_idx) - 2)
            max_i = min(len(self.lyrics), int(c_idx) + 3)

            for i in range(min_i, max_i):
                rel = float(i) - c_idx
                y_pos = cy + rel * line_spacing

                # Prominence and opacity as smooth continuous functions of relative offset
                dist = abs(rel)
                if dist <= 0.5:
                    # Prominent active zone
                    p = 1.0 - (dist / 0.5) * (1.0 - self.theme.context_opacity)
                    font_to_use = font_active
                    color_to_use = active_color
                    alpha = p
                elif dist <= 1.5:
                    # Secondary / context zone
                    p = max(0.0, self.theme.context_opacity * (1.0 - (dist - 0.5)))
                    font_to_use = font_context
                    color_to_use = context_color
                    alpha = p
                else:
                    alpha = 0.0
                    font_to_use = font_context
                    color_to_use = context_color

                text_to_draw = self.lyrics[i].text
                # If during an instrumental break and this is the active line
                if self.state == "INSTRUMENTAL" and i == int(round(c_idx)):
                    text_to_draw = "(Instrumental)"

                self._draw_text_line(
                    painter,
                    text_to_draw,
                    text_center_x,
                    y_pos,
                    font_to_use,
                    color_to_use,
                    alpha,
                    text_w
                )

        elif self.state == "INTRO":
            # Show (Intro) in center, and preview upcoming first line
            self._draw_text_line(
                painter,
                "(Intro)",
                text_center_x,
                cy,
                font_active,
                active_color,
                1.0,
                text_w
            )
            if self.lyrics:
                self._draw_text_line(
                    painter,
                    self.lyrics[0].text,
                    text_center_x,
                    cy + line_spacing,
                    font_context,
                    context_color,
                    self.theme.context_opacity,
                    text_w
                )

        elif self.state == "LOADING":
            self._draw_text_line(
                painter,
                "Fetching synchronized lyrics...",
                text_center_x,
                cy,
                font_active,
                active_color,
                0.85,
                text_w
            )

        elif self.state == "NO_LYRICS":
            self._draw_text_line(
                painter,
                "(No synchronized lyrics found)",
                text_center_x,
                cy,
                font_active,
                active_color,
                1.0,
                text_w
            )

        else:
            # IDLE State
            self._draw_text_line(
                painter,
                "Ready for Music",
                text_center_x,
                cy - 16,
                font_active,
                active_color,
                1.0,
                text_w
            )
            self._draw_text_line(
                painter,
                "Play any song on Spotify, YouTube, or Windows Media",
                text_center_x,
                cy + 28,
                font_context,
                context_color,
                self.theme.context_opacity,
                text_w
            )
