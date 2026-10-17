import unittest
from transparent_lyrics.themes import THEMES, get_theme, LyricTheme
from PySide6.QtGui import QColor


class TestThemes(unittest.TestCase):
    def test_theme_retrieval(self):
        theme = get_theme("Minimalist")
        self.assertEqual(theme.name, "Minimalist")

        # Unknown theme should fallback to Minimalist
        fallback = get_theme("NonExistentTheme")
        self.assertEqual(fallback.name, "Minimalist")

    def test_theme_colors(self):
        for name, theme in THEMES.items():
            active_qcolor = theme.get_active_qcolor()
            self.assertIsInstance(active_qcolor, QColor)
            self.assertGreater(active_qcolor.alphaF(), 0.0)

            context_qcolor = theme.get_context_qcolor()
            self.assertIsInstance(context_qcolor, QColor)
            self.assertGreater(context_qcolor.alphaF(), 0.0)

            meta_qcolor = theme.get_meta_qcolor()
            self.assertIsInstance(meta_qcolor, QColor)
            self.assertGreater(meta_qcolor.alphaF(), 0.0)


if __name__ == "__main__":
    unittest.main()
