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

    def test_settings_dialog_load_and_apply(self):
        from transparent_lyrics.config import ConfigManager
        from transparent_lyrics.settings_dialog import SettingsDialog

        cfg = ConfigManager()
        cfg.set("theme", "Minimalist")
        cfg.set("active_opacity", 1.0)
        cfg.set("next_opacity", 0.50)
        cfg.set("prev_opacity", 0.25)
        cfg.set("sync_offset", 0.0)

        dialog = SettingsDialog(cfg)

        # Verify initial values loaded into GUI controls
        self.assertEqual(dialog.active_slider.value(), 100)
        self.assertEqual(dialog.next_slider.value(), 50)
        self.assertEqual(dialog.prev_slider.value(), 25)
        self.assertAlmostEqual(dialog.sync_spin.value(), 0.0)

        # Simulate changing values in GUI
        dialog.active_slider.setValue(90)
        dialog.next_slider.setValue(60)
        dialog.prev_slider.setValue(30)
        dialog.sync_spin.setValue(1.5)
        dialog.uncensored_check.setChecked(False)

        # Connect signal capture
        applied_data = {}
        dialog.settings_applied.connect(lambda data: applied_data.update(data))

        dialog._save_and_apply()

        # Check emitted values
        self.assertAlmostEqual(applied_data.get("active_opacity"), 0.90)
        self.assertAlmostEqual(applied_data.get("next_opacity"), 0.60)
        self.assertAlmostEqual(applied_data.get("prev_opacity"), 0.30)
        self.assertAlmostEqual(applied_data.get("sync_offset"), 1.5)
        self.assertEqual(applied_data.get("prefer_uncensored"), False)

        # Check config updated
        self.assertAlmostEqual(cfg.get("active_opacity"), 0.90)
        self.assertAlmostEqual(cfg.get("next_opacity"), 0.60)
        self.assertAlmostEqual(cfg.get("prev_opacity"), 0.30)
        self.assertAlmostEqual(cfg.get("sync_offset"), 1.5)
        self.assertEqual(cfg.get("prefer_uncensored"), False)

        dialog.close()


if __name__ == "__main__":
    unittest.main()
