import os
import sys
import json
import time
import subprocess
from pathlib import Path
from PySide6.QtCore import QThread, Signal


class MediaService(QThread):
    """Background worker supervising the PowerShell Windows Media Transport Controls daemon."""

    # Signal payload: title, artist, is_playing, position_sec, duration_sec
    media_changed = Signal(str, str, bool, float, float)
    error_occurred = Signal(str)

    def __init__(self, script_path: str = None):
        super().__init__()
        self.running = True
        self.process = None

        if script_path:
            self.script_path = script_path
        else:
            base_dir = Path(__file__).resolve().parent.parent
            self.script_path = str(base_dir / "scripts" / "media_reader.ps1")

    def run(self):
        while self.running:
            if not os.path.exists(self.script_path):
                self.error_occurred.emit(f"media_reader.ps1 not found at {self.script_path}")
                time.sleep(2.0)
                continue

            try:
                # Windows startup flags to prevent popup terminal window
                startupinfo = None
                if sys.platform == "win32":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = 0  # SW_HIDE

                self.process = subprocess.Popen(
                    [
                        "powershell.exe",
                        "-ExecutionPolicy", "Bypass",
                        "-NoProfile",
                        "-NonInteractive",
                        "-File", self.script_path
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    startupinfo=startupinfo
                )

                while self.running and self.process.poll() is None:
                    line = self.process.stdout.readline()
                    if not line:
                        time.sleep(0.05)
                        continue

                    line = line.strip()
                    if not line or not line.startswith("{"):
                        continue

                    try:
                        data = json.loads(line)
                        title = str(data.get("title", ""))
                        artist = str(data.get("artist", ""))
                        is_playing = bool(data.get("playing", False))
                        pos = float(data.get("pos", 0.0))
                        dur = float(data.get("duration", 0.0))

                        self.media_changed.emit(title, artist, is_playing, pos, dur)
                    except json.JSONDecodeError:
                        pass

            except Exception as e:
                self.error_occurred.emit(f"MediaService error: {e}")
                time.sleep(1.0)
            finally:
                self._terminate_process()

            if self.running:
                time.sleep(1.0)

    def _terminate_process(self):
        if self.process:
            try:
                if self.process.stdout:
                    self.process.stdout.close()
            except Exception:
                pass
            try:
                self.process.terminate()
                self.process.wait(timeout=0.5)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

    def stop(self):
        self.running = False
        self._terminate_process()
        self.wait(1000)
