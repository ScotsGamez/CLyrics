import unittest
from transparent_lyrics.lyrics_service import LyricsService, LyricLine


class TestLyricsService(unittest.TestCase):
    def setUp(self):
        self.service = LyricsService()

    def test_parse_lrc(self):
        lrc = """
        [ti:Test Title]
        [ar:Test Artist]
        [00:05.50]First line of lyrics
        [00:10.00]Second line of lyrics
        [00:25.00]Third line after a gap
        """
        lines = self.service.parse_lrc(lrc)
        self.assertEqual(len(lines), 3)
        self.assertAlmostEqual(lines[0].time, 5.50)
        self.assertEqual(lines[0].text, "First line of lyrics")
        self.assertAlmostEqual(lines[1].time, 10.00)
        self.assertEqual(lines[1].text, "Second line of lyrics")
        self.assertAlmostEqual(lines[2].time, 25.00)
        self.assertEqual(lines[2].text, "Third line after a gap")

    def test_match_intro(self):
        lines = [LyricLine(10.0, "First line"), LyricLine(20.0, "Second line")]
        state, lyrics_list, idx, special_label = self.service.match_lyrics(lines, pos=3.0, duration=100.0)
        self.assertEqual(state, "INTRO")
        self.assertEqual(special_label, "(Intro)")
        self.assertEqual(idx, -1)

    def test_match_active_lyrics(self):
        lines = [LyricLine(5.0, "Line 1"), LyricLine(10.0, "Line 2"), LyricLine(15.0, "Line 3")]
        state, lyrics_list, idx, special_label = self.service.match_lyrics(lines, pos=11.5, duration=100.0)
        self.assertEqual(state, "LYRICS")
        self.assertEqual(idx, 1)
        self.assertEqual(lyrics_list[idx].text, "Line 2")

    def test_hysteresis_prevents_bouncing(self):
        lines = [LyricLine(5.0, "Line 1"), LyricLine(10.0, "Line 2")]
        # Song reaches line 2
        state, _, idx1, _ = self.service.match_lyrics(lines, pos=10.05, duration=100.0, track_key="test")
        self.assertEqual(idx1, 1)

        # Micro jitter reports 9.92 (within 0.3s of line 2 start): hysteresis keeps index at 1!
        state, _, idx2, _ = self.service.match_lyrics(lines, pos=9.92, duration=100.0, track_key="test")
        self.assertEqual(idx2, 1)

    def test_match_instrumental_gap(self):
        lines = [LyricLine(5.0, "Before Break"), LyricLine(30.0, "After Break")]
        # At 15 seconds: gap is 25s, elapsed since active is 10s (> 6.5s)
        state, lyrics_list, idx, special_label = self.service.match_lyrics(lines, pos=15.0, duration=100.0)
        self.assertEqual(state, "INSTRUMENTAL")
        self.assertEqual(special_label, "(Instrumental)")
        self.assertEqual(idx, 0)

    def test_match_no_lyrics(self):
        state, lyrics_list, idx, special_label = self.service.match_lyrics([], pos=10.0, duration=100.0)
        self.assertEqual(state, "NO_LYRICS")
        self.assertEqual(special_label, "(No synchronized lyrics found)")

    def test_prefer_uncensored_toggle_and_cache(self):
        service = LyricsService(prefer_uncensored=True)
        self.assertTrue(service.prefer_uncensored)

        # Populate fake cache
        service._cache["song - artist"] = [LyricLine(1.0, "Lyric")]
        self.assertTrue(service.is_cached("Song", "Artist"))

        # Changing uncensored preference clears cache
        service.set_prefer_uncensored(False)
        self.assertFalse(service.prefer_uncensored)
        self.assertFalse(service.is_cached("Song", "Artist"))

        # Selective cache clearing
        service._cache["song - artist"] = [LyricLine(1.0, "Lyric")]
        service._cache["other - artist"] = [LyricLine(2.0, "Other")]
        service.clear_cache("song - artist")
        self.assertFalse(service.is_cached("Song", "Artist"))
        self.assertTrue(service.is_cached("Other", "Artist"))

    def test_file_cache_lookup_avoids_network(self):
        import tempfile
        import shutil
        from pathlib import Path
        from transparent_lyrics.lrc_cache import LrcFileCache

        temp_dir = tempfile.mkdtemp()
        try:
            fc = LrcFileCache(cache_dir=Path(temp_dir), max_size=5)
            fc.save_lrc("cached song - cached artist", "[00:05.00] Line from cached LRC file")

            service = LyricsService(file_cache=fc)

            # fetch_lyrics_async should find it in fc and return parsed without any network call
            result = []
            service.fetch_lyrics_async("Cached Song", "Cached Artist", callback=lambda k, lines: result.append((k, lines)))

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0][0], "cached song - cached artist")
            self.assertEqual(len(result[0][1]), 1)
            self.assertEqual(result[0][1][0].text, "Line from cached LRC file")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
