import os
import json
import tempfile
import unittest
from pathlib import Path
from transparent_lyrics.config import (
    ConfigManager,
    DEFAULT_CONFIG,
    _parse_legacy_yaml,
)


class TestConfig(unittest.TestCase):
    def test_default_values(self):
        self.assertIn("pos_x", DEFAULT_CONFIG)
        self.assertIn("is_locked", DEFAULT_CONFIG)
        self.assertIn("theme", DEFAULT_CONFIG)
        self.assertIn("sync_offset", DEFAULT_CONFIG)
        self.assertEqual(DEFAULT_CONFIG.get("active_opacity"), 1.0)
        self.assertEqual(DEFAULT_CONFIG.get("next_opacity"), 0.50)
        self.assertEqual(DEFAULT_CONFIG.get("prev_opacity"), 0.25)
        self.assertEqual(DEFAULT_CONFIG.get("prefer_uncensored"), True)

    def test_set_and_get(self):
        cfg = ConfigManager()
        cfg.set("test_key", "test_val")
        self.assertEqual(cfg.get("test_key"), "test_val")

    def test_bulk_set(self):
        cfg = ConfigManager()
        cfg.bulk_set({
            "theme": "Sunset",
            "active_opacity": 0.85,
            "sync_offset": 1.2,
        })
        self.assertEqual(cfg.get("theme"), "Sunset")
        self.assertAlmostEqual(cfg.get("active_opacity"), 0.85)
        self.assertAlmostEqual(cfg.get("sync_offset"), 1.2)

    def test_legacy_yaml_parser(self):
        yaml_content = """
        # Comments should be ignored
        pos_x: 200
        theme: "Cyberpunk"
        is_locked: true
        active_opacity: 0.95
        next_opacity: 0.65
        sync_offset: -0.75
        prefer_uncensored: false
        """
        parsed = _parse_legacy_yaml(yaml_content)
        self.assertEqual(parsed.get("pos_x"), 200)
        self.assertEqual(parsed.get("theme"), "Cyberpunk")
        self.assertEqual(parsed.get("is_locked"), True)
        self.assertAlmostEqual(parsed.get("active_opacity"), 0.95)
        self.assertAlmostEqual(parsed.get("next_opacity"), 0.65)
        self.assertAlmostEqual(parsed.get("sync_offset"), -0.75)
        self.assertEqual(parsed.get("prefer_uncensored"), False)

    def test_legacy_yaml_migration(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            legacy_yaml = tmp_path / "settings.yaml"

            # Write legacy yaml file before creating ConfigManager
            legacy_yaml.write_text(
                "theme: \"Emerald\"\nwidth: 1200\nactive_opacity: 0.8\nis_locked: true\n",
                encoding="utf-8"
            )

            # Initialize ConfigManager in isolated directory
            cfg = ConfigManager(root_dir=tmp_path, appdata_dir=tmp_path / "appdata")

            self.assertEqual(cfg.get("theme"), "Emerald")
            self.assertEqual(cfg.get("width"), 1200)
            self.assertAlmostEqual(cfg.get("active_opacity"), 0.8)
            self.assertEqual(cfg.get("is_locked"), True)

            # settings.json must now exist in root_dir
            self.assertTrue(cfg.local_json.exists())
            saved_json = json.loads(cfg.local_json.read_text(encoding="utf-8"))
            self.assertEqual(saved_json.get("theme"), "Emerald")
            self.assertEqual(saved_json.get("width"), 1200)


if __name__ == "__main__":
    unittest.main()
