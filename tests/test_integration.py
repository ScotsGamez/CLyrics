import os
import unittest
from PySide6.QtWidgets import QApplication

# Run Qt offscreen for automated CI/testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"


class TestIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tempfile
        cls.test_dir = tempfile.mkdtemp(prefix="clyrics_test_")
        os.environ["TRANSPARENT_LYRICS_TEST_DIR"] = cls.test_dir
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.test_dir, ignore_errors=True)
        os.environ.pop("TRANSPARENT_LYRICS_TEST_DIR", None)

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

        # 5. Test Album Cover Modes & Auto-Widening
        controller.window.set_album_cover_mode("left", adjust_ratio=True)
        self.assertEqual(controller.window.renderer.album_cover_mode, "left")
        self.assertGreaterEqual(controller.window.width(), 1200)

        controller.window.set_album_cover_mode("right", adjust_ratio=True)
        self.assertEqual(controller.window.renderer.album_cover_mode, "right")

        controller.window.set_album_cover_mode("off", adjust_ratio=True)
        self.assertEqual(controller.window.renderer.album_cover_mode, "off")

        # 6. Test Window Sizing
        controller.window.set_window_dimensions(1000, 240)
        self.assertEqual(controller.window.width(), 1000)
        self.assertEqual(controller.window.height(), 240)

        # 7. Test Sync Offset
        controller.window.set_sync_offset(1.5)
        self.assertEqual(controller.config.get("sync_offset"), 1.5)
        controller.window.set_sync_offset(0.0)
        self.assertEqual(controller.config.get("sync_offset"), 0.0)

        # 8. Test 3-Tier Opacities
        controller.window.set_opacities(1.0, 0.70, 0.40)
        self.assertAlmostEqual(controller.window.renderer.active_opacity, 1.0)
        self.assertAlmostEqual(controller.window.renderer.next_opacity, 0.70)
        self.assertAlmostEqual(controller.window.renderer.prev_opacity, 0.40)
        self.assertAlmostEqual(controller.config.get("active_opacity"), 1.0)
        self.assertAlmostEqual(controller.config.get("next_opacity"), 0.70)
        self.assertAlmostEqual(controller.config.get("prev_opacity"), 0.40)

        # 9. Test Uncensored Lyrics Preference
        controller.window.set_prefer_uncensored(False)
        self.assertFalse(controller.config.get("prefer_uncensored"))
        self.assertFalse(controller.lyrics_service.prefer_uncensored)
        controller.window.set_prefer_uncensored(True)
        self.assertTrue(controller.config.get("prefer_uncensored"))
        self.assertTrue(controller.lyrics_service.prefer_uncensored)

        # 10. Test Settings Dialog, safe live theme apply, and restart flow
        from unittest.mock import patch
        controller.window.open_settings_dialog()
        self.assertIsNotNone(controller.window._settings_dialog)
        controller.window._on_settings_applied({
            "theme": "Sunset",
        })
        self.assertEqual(controller.window.renderer.theme.name, "Sunset")
        controller.window._settings_dialog.close()

        # 11. Test restart_application execution without killing test runner
        with patch("transparent_lyrics.app.subprocess.Popen") as mock_popen, patch("PySide6.QtWidgets.QApplication.quit") as mock_quit:
            controller.restart_application()
            mock_popen.assert_called_once()
            mock_quit.assert_called_once()

        # 12. Clean Shutdown
        controller.shutdown()


if __name__ == "__main__":
    unittest.main()
