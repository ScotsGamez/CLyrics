import unittest
import tempfile
import os
from pathlib import Path
from transparent_lyrics.config import ConfigManager


class TestConfig(unittest.TestCase):
    def test_default_values(self):
        cfg = ConfigManager()
        self.assertIn("pos_x", cfg.config)
        self.assertIn("is_locked", cfg.config)
        self.assertIn("theme", cfg.config)

    def test_set_and_get(self):
        cfg = ConfigManager()
        cfg.set("test_key", "test_val")
        self.assertEqual(cfg.get("test_key"), "test_val")


if __name__ == "__main__":
    unittest.main()
