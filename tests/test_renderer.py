import os
import unittest
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"


class TestLyricsRenderer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])

    def test_renderer_initial_and_opacities(self):
        from transparent_lyrics.renderer import LyricsRenderer
        renderer = LyricsRenderer()
        self.assertAlmostEqual(renderer.active_opacity, 1.0)
        self.assertAlmostEqual(renderer.next_opacity, 0.50)
        self.assertAlmostEqual(renderer.prev_opacity, 0.25)

        renderer.set_opacities(0.9, 0.6, 0.3)
        self.assertAlmostEqual(renderer.active_opacity, 0.9)
        self.assertAlmostEqual(renderer.next_opacity, 0.6)
        self.assertAlmostEqual(renderer.prev_opacity, 0.3)

    def test_draw_text_line_dynamic_scaling(self):
        from transparent_lyrics.renderer import LyricsRenderer
        renderer = LyricsRenderer()
        renderer.resize(600, 200)

        # Create a test offscreen pixmap/image and painter
        img = QImage(600, 200, QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.transparent)
        painter = QPainter(img)

        # Draw a very long line that would previously have been chopped/elided into sit...ading
        long_line = "Another evening I'll be sitting reading in between your lines"
        font = QFont("Segoe UI", 22)
        color = QColor("#FFFFFF")

        # Must execute without errors and scale smoothly
        renderer._draw_text_line(
            painter,
            long_line,
            x_center=300.0,
            y_center=100.0,
            font=font,
            color=color,
            alpha_multiplier=1.0,
            max_width=400.0
        )
        painter.end()


if __name__ == "__main__":
    unittest.main()
