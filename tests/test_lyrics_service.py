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
        state, prev, active, nxt, idx = self.service.match_lyrics(lines, pos=3.0, duration=100.0)
        self.assertEqual(state, "INTRO")
        self.assertEqual(active, "(Intro)")
        self.assertEqual(nxt, "First line")

    def test_match_active_lyrics(self):
        lines = [LyricLine(5.0, "Line 1"), LyricLine(10.0, "Line 2"), LyricLine(15.0, "Line 3")]
        state, prev, active, nxt, idx = self.service.match_lyrics(lines, pos=11.5, duration=100.0)
        self.assertEqual(state, "LYRICS")
        self.assertEqual(prev, "Line 1")
        self.assertEqual(active, "Line 2")
        self.assertEqual(nxt, "Line 3")
        self.assertEqual(idx, 1)

    def test_match_instrumental_gap(self):
        lines = [LyricLine(5.0, "Before Break"), LyricLine(30.0, "After Break")]
        # At 15 seconds: gap is 25s, elapsed since active is 10s (> 7s)
        state, prev, active, nxt, idx = self.service.match_lyrics(lines, pos=15.0, duration=100.0)
        self.assertEqual(state, "INSTRUMENTAL")
        self.assertEqual(active, "(Instrumental)")
        self.assertEqual(nxt, "After Break")

    def test_match_no_lyrics(self):
        state, prev, active, nxt, idx = self.service.match_lyrics([], pos=10.0, duration=100.0)
        self.assertEqual(state, "NO_LYRICS")
        self.assertEqual(active, "(No synchronized lyrics found)")


if __name__ == "__main__":
    unittest.main()
