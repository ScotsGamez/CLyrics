import os
import atexit
import shutil
import tempfile

# Automatically isolate all unit test execution in a throwaway temporary directory
# This guarantees that tests NEVER touch or modify the user's live settings.json
_TEST_TEMP_DIR = tempfile.mkdtemp(prefix="clyrics_test_")
os.environ["TRANSPARENT_LYRICS_TEST_DIR"] = _TEST_TEMP_DIR
os.environ["QT_QPA_PLATFORM"] = "offscreen"


def _cleanup_test_dir():
    try:
        shutil.rmtree(_TEST_TEMP_DIR, ignore_errors=True)
    except Exception:
        pass


atexit.register(_cleanup_test_dir)
