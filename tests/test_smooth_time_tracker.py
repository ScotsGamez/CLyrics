import time
import unittest
from transparent_lyrics.app import SmoothTimeTracker


class TestSmoothTimeTracker(unittest.TestCase):
    def test_smooth_advancement(self):
        tracker = SmoothTimeTracker()
        tracker.update_from_telemetry(reported_pos=10.0, is_playing=True, duration=200.0)
        time.sleep(0.05)
        pos = tracker.get_current_pos()
        self.assertGreater(pos, 10.0)

    def test_large_seek_detection(self):
        tracker = SmoothTimeTracker()
        tracker.update_from_telemetry(reported_pos=10.0, is_playing=True, duration=200.0)
        # Seek to 80.0
        tracker.update_from_telemetry(reported_pos=80.0, is_playing=True, duration=200.0)
        pos = tracker.get_current_pos()
        self.assertGreaterEqual(pos, 79.9)

    def test_paused_state(self):
        tracker = SmoothTimeTracker()
        tracker.update_from_telemetry(reported_pos=25.0, is_playing=False, duration=200.0)
        time.sleep(0.05)
        pos = tracker.get_current_pos()
        self.assertAlmostEqual(pos, 25.0, places=2)


if __name__ == "__main__":
    unittest.main()
