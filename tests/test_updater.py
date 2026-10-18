import unittest
from unittest.mock import patch, MagicMock
from transparent_lyrics.updater import (
    parse_version,
    UpdateCheckerThread,
    launch_update_bat_and_exit,
    prompt_first_run_update_check,
)
from transparent_lyrics.config import ConfigManager


class TestUpdater(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(parse_version("v1.5.0"), (1, 5, 0))
        self.assertEqual(parse_version("1.4.1"), (1, 4, 1))
        self.assertGreater(parse_version("v1.5.0"), parse_version("v1.4.1"))
        self.assertEqual(parse_version("invalid"), (0,))

    def test_update_checker_thread_update_available(self):
        mock_response_data = b'{"tag_name": "v1.6.0", "body": "Release notes", "html_url": "https://example.com"}'
        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response_data
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            thread = UpdateCheckerThread(current_version="1.5.0")
            result = []
            thread.update_available.connect(lambda v, n, u: result.append((v, n, u)))
            thread.run()

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0][0], "v1.6.0")

    def test_update_checker_thread_up_to_date(self):
        mock_response_data = b'{"tag_name": "v1.5.0", "body": "Same", "html_url": "https://example.com"}'
        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response_data
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            thread = UpdateCheckerThread(current_version="1.5.0")
            none_result = []
            thread.no_update.connect(lambda v: none_result.append(v))
            thread.run()

            self.assertEqual(len(none_result), 1)
            self.assertEqual(none_result[0], "1.5.0")

    def test_launch_update_bat_and_exit(self):
        shutdown_called = [False]
        with patch("subprocess.Popen") as mock_popen, patch("PySide6.QtWidgets.QApplication.quit") as mock_quit:
            launch_update_bat_and_exit(app_shutdown_callback=lambda: shutdown_called.__setitem__(0, True))
            self.assertTrue(shutdown_called[0])
            mock_popen.assert_called_once()
            mock_quit.assert_called_once()

    def test_get_current_repo_name(self):
        from transparent_lyrics.updater import get_current_repo_name
        name = get_current_repo_name()
        self.assertEqual(name, "CLyrics")

    def test_check_and_update_desktop_shortcut(self):
        import tempfile
        from pathlib import Path
        from transparent_lyrics.updater import check_and_update_desktop_shortcut

        with tempfile.TemporaryDirectory() as tmp_desktop:
            with patch.dict("os.environ", {"USERPROFILE": tmp_desktop}):
                with patch("transparent_lyrics.updater.get_current_repo_name", return_value="CLyrics"):
                    with patch("subprocess.run") as mock_run:
                        # Should detect missing CLyrics.lnk and trigger create_shortcut.ps1
                        updated = check_and_update_desktop_shortcut()
                        self.assertTrue(updated)
                        mock_run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
