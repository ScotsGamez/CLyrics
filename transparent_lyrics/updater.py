import sys
import os
import re
import json
import subprocess
import urllib.request
from pathlib import Path
from typing import Optional, Tuple
from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtWidgets import QMessageBox, QApplication
from .config import PROJECT_ROOT

GITHUB_API_LATEST_RELEASE = "https://api.github.com/repos/ScotsGamez/Clyrics/releases/latest"


def parse_version(v_str: str) -> Tuple[int, ...]:
    """Extracts numeric tuple from version string, e.g. 'v1.5.0' -> (1, 5, 0)."""
    clean = re.sub(r"^[vV]", "", v_str.strip())
    nums = re.findall(r"\d+", clean)
    return tuple(int(n) for n in nums) if nums else (0,)


def get_current_repo_name() -> str:
    """Retrieves current repository name from git remote or defaults to 'CLyrics'."""
    try:
        out = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=str(PROJECT_ROOT),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        name = out.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]
        if name:
            return "CLyrics" if name.lower() == "clyrics" else name
    except Exception:
        pass
    return "CLyrics"


def check_and_update_desktop_shortcut(force: bool = False) -> bool:
    """
    Checks if the desktop shortcut matches the repository name (e.g. CLyrics.lnk)
    and ensures it is up to date with the latest icon and executable paths.
    Removes legacy shortcuts and refreshes the shortcut.
    """
    repo_name = get_current_repo_name()
    desktop = Path(os.environ.get("USERPROFILE", "")) / "Desktop"
    if not desktop.exists():
        desktop = Path(os.path.expanduser("~/Desktop"))

    expected_shortcut = desktop / f"{repo_name}.lnk"

    # Known legacy shortcut names to clean up
    legacy_shortcuts = [
        desktop / "Transparent Live Lyrics.lnk",
        desktop / "Transparent Lyrics.lnk",
        desktop / "Clyrics.lnk",
    ]

    for leg in legacy_shortcuts:
        if leg.exists() and leg != expected_shortcut:
            try:
                leg.unlink()
            except Exception as e:
                print(f"[Updater] Error removing legacy shortcut {leg}: {e}")

    if sys.platform == "win32":
        script = PROJECT_ROOT / "scripts" / "create_shortcut.ps1"
        if script.exists():
            try:
                cmd = [
                    "powershell.exe",
                    "-ExecutionPolicy", "Bypass",
                    "-NoProfile",
                    "-File", str(script),
                    "-TargetDir", str(PROJECT_ROOT),
                    "-ShortcutName", repo_name,
                ]
                subprocess.run(cmd, check=True, timeout=10)
                return True
            except Exception as e:
                print(f"[Updater] Error updating desktop shortcut: {e}")
    return False


class UpdateCheckerThread(QThread):
    update_available = Signal(str, str, str)  # remote_version, release_notes, html_url
    no_update = Signal(str)                   # current_version
    error = Signal(str)

    def __init__(self, current_version: str, parent=None):
        super().__init__(parent)
        self.current_version = current_version

    def run(self):
        # Verify and ensure desktop shortcut name matches repo name
        try:
            check_and_update_desktop_shortcut()
        except Exception as e:
            print(f"[Updater] Error checking shortcut name: {e}")

        try:
            req = urllib.request.Request(
                GITHUB_API_LATEST_RELEASE,
                headers={"User-Agent": "Clyrics-App"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                tag_name = data.get("tag_name", "")
                release_notes = data.get("body", "")
                html_url = data.get("html_url", "")

                remote_v = parse_version(tag_name)
                local_v = parse_version(self.current_version)

                if remote_v > local_v:
                    self.update_available.emit(tag_name, release_notes, html_url)
                else:
                    self.no_update.emit(self.current_version)
        except Exception as e:
            self.error.emit(str(e))


def prompt_update_confirmation(remote_ver: str, release_notes: str = "", parent=None) -> bool:
    """Shows a confirmation dialog for applying an available update."""
    msg = QMessageBox(parent)
    msg.setWindowTitle("CLyrics — Update Available")
    msg.setText(f"A new version of CLyrics is available: <b>{remote_ver}</b>")
    preview = release_notes.strip()[:400] + ("..." if len(release_notes.strip()) > 400 else "")
    if preview:
        msg.setInformativeText(f"<b>What's New:</b>\n{preview}\n\nWould you like to update now? The app will close, run update.bat, and restart automatically.")
    else:
        msg.setInformativeText("Would you like to update now? The app will close, run update.bat, and restart automatically.")
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg.setDefaultButton(QMessageBox.Yes)
    msg.button(QMessageBox.Yes).setText("Update Now")
    msg.button(QMessageBox.No).setText("Later")
    return msg.exec() == QMessageBox.Yes


def prompt_first_run_update_check(config_manager, parent=None):
    """Notifies user on first run that auto-update checking is available and OFF by default."""
    if config_manager.get("first_run_update_notified", False):
        return

    msg = QMessageBox(parent)
    msg.setWindowTitle("CLyrics — Automatic Updates")
    msg.setText("<b>Automatic Update Checking</b>")
    msg.setInformativeText(
        "CLyrics (C (See) Lyrics) can periodically check for new updates and bugfixes on startup.<br><br>"
        "This feature is <b>turned OFF by default</b>.<br><br>"
        "Would you like to turn on automatic update checking?"
    )
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg.setDefaultButton(QMessageBox.Yes)
    msg.button(QMessageBox.Yes).setText("Turn On Auto-Updates")
    msg.button(QMessageBox.No).setText("Keep Turned Off")

    choice = msg.exec()
    if choice == QMessageBox.Yes:
        config_manager.set("check_for_updates", True)
    else:
        config_manager.set("check_for_updates", False)

    config_manager.set("first_run_update_notified", True)


def launch_update_bat_and_exit(app_shutdown_callback=None):
    """
    Closes the app, runs update.bat in a separate process, which updates git & dependencies
    and automatically relaunches the app on its own.
    """
    if app_shutdown_callback:
        try:
            app_shutdown_callback()
        except Exception as e:
            print(f"[Updater] Error in shutdown callback: {e}")

    bat_file = PROJECT_ROOT / "update.bat"

    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200) | getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010)
        subprocess.Popen(
            ["cmd.exe", "/c", str(bat_file)],
            cwd=str(PROJECT_ROOT),
            creationflags=creationflags
        )
    else:
        subprocess.Popen(["bash", str(bat_file)], cwd=str(PROJECT_ROOT))

    QApplication.quit()
