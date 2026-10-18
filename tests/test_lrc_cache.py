import os
import shutil
import tempfile
import unittest
from pathlib import Path
from transparent_lyrics.lrc_cache import LrcFileCache


class TestLrcFileCache(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cache = LrcFileCache(cache_dir=Path(self.temp_dir), max_size=5)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_retrieve_lrc(self):
        sample_lrc = "[00:10.00] First line\n[00:20.00] Second line"
        path = self.cache.save_lrc("track_1", sample_lrc)
        self.assertIsNotNone(path)
        self.assertTrue(path.exists())

        retrieved = self.cache.get_lrc("track_1")
        self.assertEqual(retrieved, sample_lrc)
        self.assertTrue(self.cache.has_lrc("track_1"))
        self.assertFalse(self.cache.has_lrc("non_existent"))

    def test_rolling_limit_enforced_to_5(self):
        # Save 5 distinct tracks
        for i in range(1, 6):
            self.cache.save_lrc(f"track_{i}", f"[00:0{i}.00] Lyric {i}")

        self.assertEqual(self.cache.count(), 5)
        for i in range(1, 6):
            self.assertTrue(self.cache.has_lrc(f"track_{i}"))

        # Add 6th track: track_1 (the oldest) should be deleted from disk
        track_1_file = self.cache.cache_dir / self.cache._entries[0]["filename"]
        self.assertTrue(track_1_file.exists())

        self.cache.save_lrc("track_6", "[00:06.00] Lyric 6")

        self.assertEqual(self.cache.count(), 5)
        self.assertFalse(self.cache.has_lrc("track_1"))
        self.assertFalse(track_1_file.exists())
        self.assertTrue(self.cache.has_lrc("track_6"))

    def test_reload_manifest(self):
        self.cache.save_lrc("song_a", "[00:01.00] Song A")
        self.cache.save_lrc("song_b", "[00:02.00] Song B")

        # Create new cache instance pointing to same directory
        reloaded = LrcFileCache(cache_dir=Path(self.temp_dir), max_size=5)
        self.assertEqual(reloaded.count(), 2)
        self.assertEqual(reloaded.get_lrc("song_a"), "[00:01.00] Song A")
        self.assertEqual(reloaded.get_lrc("song_b"), "[00:02.00] Song B")

    def test_clear_cache(self):
        self.cache.save_lrc("song_x", "lyrics x")
        self.cache.save_lrc("song_y", "lyrics y")
        self.assertEqual(self.cache.count(), 2)

        self.cache.clear()
        self.assertEqual(self.cache.count(), 0)
        self.assertIsNone(self.cache.get_lrc("song_x"))


if __name__ == "__main__":
    unittest.main()
