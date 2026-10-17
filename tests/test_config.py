import unittest
from transparent_lyrics.config import ConfigManager, parse_simple_yaml, dump_annotated_yaml, DEFAULT_CONFIG


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

    def test_yaml_roundtrip(self):
        data = {
            "pos_x": 150,
            "width": 1100,
            "is_locked": True,
            "theme": "Cyberpunk",
            "sync_offset": -1.25,
            "album_cover_mode": "left",
            "active_opacity": 1.0,
            "next_opacity": 0.60,
            "prev_opacity": 0.30,
            "prefer_uncensored": True,
        }
        yaml_str = dump_annotated_yaml(data)
        self.assertIn("pos_x: 150", yaml_str)
        self.assertIn("theme: \"Cyberpunk\"", yaml_str)
        self.assertIn("active_opacity: 1.0", yaml_str)
        self.assertIn("next_opacity: 0.6", yaml_str)
        self.assertIn("prefer_uncensored: true", yaml_str)

        parsed = parse_simple_yaml(yaml_str)
        self.assertEqual(parsed.get("pos_x"), 150)
        self.assertEqual(parsed.get("width"), 1100)
        self.assertEqual(parsed.get("is_locked"), True)
        self.assertEqual(parsed.get("theme"), "Cyberpunk")
        self.assertAlmostEqual(parsed.get("sync_offset"), -1.25)
        self.assertEqual(parsed.get("album_cover_mode"), "left")
        self.assertAlmostEqual(parsed.get("active_opacity"), 1.0)
        self.assertAlmostEqual(parsed.get("next_opacity"), 0.60)
        self.assertAlmostEqual(parsed.get("prev_opacity"), 0.30)
        self.assertEqual(parsed.get("prefer_uncensored"), True)


if __name__ == "__main__":
    unittest.main()
