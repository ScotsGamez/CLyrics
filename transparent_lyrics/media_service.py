import os
import sys
import json
import time
import atexit
import subprocess
from pathlib import Path
from PySide6.QtCore import QThread, Signal

# Windows OS-level Job Object helper guaranteeing child process termination
_WINDOWS_JOB_HANDLE = None


def _get_or_create_kill_on_close_job():
    """Initializes a Windows Job Object configured to kill all child processes when the parent closes."""
    global _WINDOWS_JOB_HANDLE
    if sys.platform != "win32":
        return None
    if _WINDOWS_JOB_HANDLE is not None:
        return _WINDOWS_JOB_HANDLE

    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return None

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
                ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_uint64),
                ("WriteOperationCount", ctypes.c_uint64),
                ("OtherOperationCount", ctypes.c_uint64),
                ("ReadTransferCount", ctypes.c_uint64),
                ("WriteTransferCount", ctypes.c_uint64),
                ("OtherTransferCount", ctypes.c_uint64),
            ]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryLimit", ctypes.c_size_t),
                ("PeakJobMemoryLimit", ctypes.c_size_t),
            ]

        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        res = kernel32.SetInformationJobObject(
            job,
            9,  # JobObjectExtendedLimitInformation
            ctypes.byref(info),
            ctypes.sizeof(info),
        )
        if res:
            _WINDOWS_JOB_HANDLE = job
            return _WINDOWS_JOB_HANDLE
    except Exception:
        pass
    return None


def kill_orphaned_media_readers():
    """Finds and forcefully terminates any orphaned media_reader.ps1 background processes."""
    if sys.platform != "win32" or os.environ.get("TRANSPARENT_LYRICS_TEST_DIR"):
        return
    try:
        cmd = [
            "powershell.exe",
            "-ExecutionPolicy", "Bypass",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*media_reader.ps1*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)
    except Exception:
        pass


# Register sweeper on interpreter exit
atexit.register(kill_orphaned_media_readers)


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

        # Clean any stale/orphaned reader processes on initialization
        kill_orphaned_media_readers()

    def run(self):
        while self.running:
            if not os.path.exists(self.script_path):
                self.error_occurred.emit(f"media_reader.ps1 not found at {self.script_path}")
                time.sleep(2.0)
                continue

            try:
                # Windows startup flags to prevent popup terminal window
                startupinfo = None
                creationflags = 0
                if sys.platform == "win32":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = 0  # SW_HIDE
                    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

                cmd = [
                    "powershell.exe",
                    "-ExecutionPolicy", "Bypass",
                    "-NoProfile",
                    "-NonInteractive",
                    "-File", self.script_path,
                    "-ParentPid", str(os.getpid()),
                ]

                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    startupinfo=startupinfo,
                    creationflags=creationflags,
                )

                # Assign process to Windows Job Object for automatic kernel cleanup
                if sys.platform == "win32":
                    job = _get_or_create_kill_on_close_job()
                    if job and hasattr(self.process, "_handle"):
                        try:
                            import ctypes
                            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                            kernel32.AssignProcessToJobObject(job, int(self.process._handle))
                        except Exception:
                            pass

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
        proc = self.process
        self.process = None
        if proc:
            pid = proc.pid
            try:
                if proc.stdout:
                    proc.stdout.close()
            except Exception:
                pass
            try:
                proc.terminate()
                proc.wait(timeout=0.3)
            except Exception:
                pass
            if proc.poll() is None:
                if sys.platform == "win32":
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(pid)],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            timeout=2,
                        )
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                else:
                    try:
                        proc.kill()
                    except Exception:
                        pass

    def stop(self):
        self.running = False
        self._terminate_process()
        self.wait(1500)
        kill_orphaned_media_readers()
