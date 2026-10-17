import os
import unittest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap

os.environ["QT_QPA_PLATFORM"] = "offscreen"


class TestArtworkService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])

    def test_clean_track_id(self):
        from transparent_lyrics.artwork_service import ArtworkService
        svc = ArtworkService()
        cleaned = svc._clean_track_id("Song (Remix)!", "Artist, The?")
        self.assertEqual(cleaned, "song remix - artist the")

    def test_cache_miss_initially(self):
        from transparent_lyrics.artwork_service import ArtworkService
        svc = ArtworkService()
        art = svc.get_cached_artwork("Nonexistent Song", "Nonexistent Artist")
        self.assertIsNone(art)


if __name__ == "__main__":
    unittest.main()
