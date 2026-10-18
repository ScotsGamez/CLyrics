import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from transparent_lyrics.media_service import (
    MediaService,
    kill_orphaned_media_readers,
    _get_or_create_kill_on_close_job,
)


class TestMediaServiceLifecycle(unittest.TestCase):
    def test_job_object_creation_on_windows(self):
        if sys.platform == "win32":
            job = _get_or_create_kill_on_close_job()
            self.assertIsNotNone(job)

    def test_kill_orphaned_media_readers_skips_in_test_mode(self):
        with patch.dict(os.environ, {"TRANSPARENT_LYRICS_TEST_DIR": "test_dir"}):
            with patch("subprocess.run") as mock_run:
                kill_orphaned_media_readers()
                mock_run.assert_not_called()

    def test_terminate_process_cleans_up_and_resets(self):
        service = MediaService()
        mock_proc = MagicMock()
        mock_proc.pid = 99999
        mock_proc.poll.return_value = None
        service.process = mock_proc

        with patch("subprocess.run") as mock_run:
            service._terminate_process()
            mock_proc.terminate.assert_called_once()
            self.assertIsNone(service.process)


if __name__ == "__main__":
    unittest.main()
