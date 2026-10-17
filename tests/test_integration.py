import os
import unittest
from PySide6.QtWidgets import QApplication

# Run Qt offscreen for automated CI/testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"


class TestIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])

    def test_app_lifecycle_and_events(self):
        from transparent_lyrics.app import TransparentLyricsApp
        from transparent_lyrics.themes import THEMES

        controller = TransparentLyricsApp()

        # 1. Verify initial idle state
        self.assertEqual(controller.window.renderer.state, "IDLE")

        # 2. Simulate Media Event: Song starts
        controller.on_media_changed("Test Song", "Test Artist", True, 12.5, 180.0)
        self.assertEqual(controller.last_title, "Test Song")
        self.assertEqual(controller.last_artist, "Test Artist")

        # 3. Test Theme Change
        for theme_name in THEMES.keys():
            controller.window.apply_theme(theme_name)
            self.assertEqual(controller.window.renderer.theme.name, theme_name)

        # 4. Test Lock and Unlock
        controller.window.set_locked(True)
        self.assertTrue(controller.window.is_locked)
        controller.window.set_locked(False)
        self.assertFalse(controller.window.is_locked)

        # 5. Clean Shutdown
        controller.shutdown()


if __name__ == "__main__":
    unittest.main()
