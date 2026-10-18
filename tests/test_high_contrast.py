import os
import unittest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPainter, QPixmap

os.environ["QT_QPA_PLATFORM"] = "offscreen"


class TestHighContrast(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])

    def test_neon_contrast_theme_exists(self):
        from transparent_lyrics.themes import THEMES, get_theme
        self.assertIn("Neon Contrast", THEMES)
        theme = get_theme("Neon Contrast")
        self.assertEqual(theme.name, "Neon Contrast")
        self.assertEqual(theme.active_color, "#39FF14")

    def test_renderer_high_contrast_outline(self):
        from transparent_lyrics.renderer import LyricsRenderer
        from transparent_lyrics.lyrics_service import LyricLine

        renderer = LyricsRenderer()
        renderer.resize(800, 200)

        # Enable high-contrast outline
        renderer.set_high_contrast_outline(True)
        self.assertTrue(renderer.high_contrast_outline)

        # Update lyrics
        lyrics = [
            LyricLine(0.0, "Line 1"),
            LyricLine(5.0, "High Contrast Lyric Line"),
            LyricLine(10.0, "Line 3"),
        ]
        renderer.update_lyrics_state("LYRICS", "Test Track", "Test Artist", True, lyrics, 1)

        # Paint onto offscreen pixmap to ensure QPainterPath outline logic executes with 0 errors
        pix = QPixmap(800, 200)
        renderer.render(pix)

        # Disable outline
        renderer.set_high_contrast_outline(False)
        self.assertFalse(renderer.high_contrast_outline)

        renderer.close()


if __name__ == "__main__":
    unittest.main()
