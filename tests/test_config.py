import unittest
from transparent_lyrics.config import ConfigManager, parse_simple_yaml, dump_annotated_yaml


class TestConfig(unittest.TestCase):
    def test_default_values(self):
        cfg = ConfigManager()
        self.assertIn("pos_x", cfg.config)
        self.assertIn("is_locked", cfg.config)
        self.assertIn("theme", cfg.config)
        self.assertIn("sync_offset", cfg.config)

    def test_set_and_get(self):
        cfg = ConfigManager()
        cfg.set("test_key", "test_val")
        self.assertEqual(cfg.get("test_key"), "test_val")

    def test_yaml_roundtrip(self):
        data = {
            "pos_x": 150,
            "width": 1100,
            "is_locked": True,
            "theme": "Cyberpunk",
            "sync_offset": -1.25,
            "album_cover_mode": "left"
        }
        yaml_str = dump_annotated_yaml(data)
        self.assertIn("pos_x: 150", yaml_str)
        self.assertIn("theme: \"Cyberpunk\"", yaml_str)

        parsed = parse_simple_yaml(yaml_str)
        self.assertEqual(parsed.get("pos_x"), 150)
        self.assertEqual(parsed.get("width"), 1100)
        self.assertEqual(parsed.get("is_locked"), True)
        self.assertEqual(parsed.get("theme"), "Cyberpunk")
        self.assertAlmostEqual(parsed.get("sync_offset"), -1.25)
        self.assertEqual(parsed.get("album_cover_mode"), "left")


if __name__ == "__main__":
    unittest.main()
