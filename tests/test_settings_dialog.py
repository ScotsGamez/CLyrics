import os
import unittest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"


class TestSettingsDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])

    def test_settings_dialog_theme_only_applies_live_without_restart(self):
        from transparent_lyrics.config import ConfigManager
        from transparent_lyrics.settings_dialog import SettingsDialog

        cfg = ConfigManager()
        cfg.set("theme", "Minimalist")

        dialog = SettingsDialog(cfg)

        applied_data = {}
        restart_called = [False]
        dialog.settings_applied.connect(lambda data: applied_data.update(data))
        dialog.restart_requested.connect(lambda: restart_called.__setitem__(0, True))

        # Change only the theme in the GUI
        idx = dialog.theme_combo.findData("Sunset")
        self.assertGreaterEqual(idx, 0)
        dialog.theme_combo.setCurrentIndex(idx)

        dialog._save_and_apply()

        # Theme should be applied live
        self.assertEqual(applied_data.get("theme"), "Sunset")
        # Restart must NOT be requested
        self.assertFalse(restart_called[0])
        # Config should have new theme
        self.assertEqual(cfg.get("theme"), "Sunset")

        dialog.close()

    def test_settings_dialog_non_theme_requests_restart(self):
        from transparent_lyrics.config import ConfigManager
        from transparent_lyrics.settings_dialog import SettingsDialog

        cfg = ConfigManager()
        cfg.set("theme", "Minimalist")
        cfg.set("active_opacity", 1.0)
        cfg.set("next_opacity", 0.50)
        cfg.set("prev_opacity", 0.25)
        cfg.set("sync_offset", 0.0)
        cfg.set("prefer_uncensored", True)

        dialog = SettingsDialog(cfg)

        applied_data = {}
        restart_called = [False]
        dialog.settings_applied.connect(lambda data: applied_data.update(data))
        dialog.restart_requested.connect(lambda: restart_called.__setitem__(0, True))

        # Change non-theme settings
        dialog.active_slider.setValue(90)
        dialog.next_slider.setValue(60)
        dialog.prev_slider.setValue(30)
        dialog.sync_spin.setValue(1.5)
        dialog.uncensored_check.setChecked(False)

        dialog._save_and_apply()

        # Restart MUST be requested for non-theme settings
        self.assertTrue(restart_called[0])
        # Live settings_applied must NOT be emitted to prevent stalls
        self.assertEqual(applied_data, {})

        # Values should be saved to config for next process boot
        self.assertAlmostEqual(cfg.get("active_opacity"), 0.90)
        self.assertAlmostEqual(cfg.get("next_opacity"), 0.60)
        self.assertAlmostEqual(cfg.get("prev_opacity"), 0.30)
        self.assertAlmostEqual(cfg.get("sync_offset"), 1.5)
        self.assertEqual(cfg.get("prefer_uncensored"), False)

        dialog.close()

    def test_settings_dialog_theme_and_non_theme_requests_restart(self):
        from transparent_lyrics.config import ConfigManager
        from transparent_lyrics.settings_dialog import SettingsDialog

        cfg = ConfigManager()
        cfg.set("theme", "Minimalist")
        cfg.set("width", 960)

        dialog = SettingsDialog(cfg)

        applied_data = {}
        restart_called = [False]
        dialog.settings_applied.connect(lambda data: applied_data.update(data))
        dialog.restart_requested.connect(lambda: restart_called.__setitem__(0, True))

        # Change both theme AND width
        idx = dialog.theme_combo.findData("Cyberpunk")
        dialog.theme_combo.setCurrentIndex(idx)
        dialog.width_spin.setValue(1200)

        dialog._save_and_apply()

        # Restart should be requested because a non-theme setting changed
        self.assertTrue(restart_called[0])
        self.assertEqual(applied_data, {})
        self.assertEqual(cfg.get("theme"), "Cyberpunk")
        self.assertEqual(cfg.get("width"), 1200)

        dialog.close()

    def test_settings_dialog_no_changes_does_not_restart_or_apply(self):
        from transparent_lyrics.config import ConfigManager
        from transparent_lyrics.settings_dialog import SettingsDialog

        cfg = ConfigManager()
        dialog = SettingsDialog(cfg)

        applied_data = {}
        restart_called = [False]
        dialog.settings_applied.connect(lambda data: applied_data.update(data))
        dialog.restart_requested.connect(lambda: restart_called.__setitem__(0, True))

        # Save without any changes
        dialog._save_and_apply()

        self.assertFalse(restart_called[0])
        self.assertEqual(applied_data, {})

    def test_settings_dialog_contrast_and_update_toggles(self):
        from transparent_lyrics.config import ConfigManager
        from transparent_lyrics.settings_dialog import SettingsDialog

        cfg = ConfigManager()
        cfg.set("high_contrast_outline", False)
        cfg.set("check_for_updates", False)

        dialog = SettingsDialog(cfg)
        self.assertFalse(dialog.contrast_check.isChecked())
        self.assertFalse(dialog.update_check.isChecked())

        dialog.contrast_check.setChecked(True)
        dialog.update_check.setChecked(True)

        restart_called = [False]
        dialog.restart_requested.connect(lambda: restart_called.__setitem__(0, True))

        dialog._save_and_apply()

        self.assertTrue(restart_called[0])
        self.assertTrue(cfg.get("high_contrast_outline"))
        self.assertTrue(cfg.get("check_for_updates"))

        dialog.close()


if __name__ == "__main__":
    unittest.main()
