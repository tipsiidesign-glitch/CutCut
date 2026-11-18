"""The two programs Instant runs to work on video: ffmpeg and ffprobe.

They are not part of Instant and have to be on the computer. On Windows a missing one shows up as the bare
"[WinError 2] The system cannot find the file specified", which tells nobody what to do. So Instant looks for them
itself (also in the places installers put them before Windows has told running programs), uses them from there,
and when they really are missing says so in plain words, before any video is started."""
import os
import shutil
import sys
import time
from pathlib import Path

from . import config

NEEDED = ("ffmpeg", "ffprobe")
HELP = ("CutCut requires both ffmpeg and ffprobe. Install FFmpeg (on Windows, for example: "
        "winget install Gyan.FFmpeg), then add the folder containing both executables to PATH, "
        "or set CUTCUT_FFMPEG_DIR to that folder. Restart CutCut after changing the configuration.")
_seen = {"at": 0.0, "missing": list(NEEDED)}


def _places() -> list:
    """Return the optional user-configured directory after normal PATH lookup."""
    custom = config.env("CUTCUT_FFMPEG_DIR")
    return [Path(custom)] if custom else []


def setup() -> list:
    """Make ffmpeg and ffprobe reachable for everything Instant runs. Returns the ones that could not be found."""
    exe = ".exe" if sys.platform == "win32" else ""
    missing = []
    custom_places = _places()
    for name in NEEDED:
        # Respect normal PATH resolution first. The custom directory is only a fallback.
        if shutil.which(name):
            continue
        for d in custom_places:
            try:
                if (d / (name + exe)).is_file():
                    current = os.environ.get("PATH", "")
                    if str(d) not in current.split(os.pathsep):
                        os.environ["PATH"] = str(d) + (os.pathsep + current if current else "")
                    break
            except OSError:
                pass
        if not shutil.which(name):
            missing.append(name)
    _seen.update(at=time.time(), missing=missing)
    return missing


def missing() -> list:
    """What is still missing. Looked at again every 20 seconds while something is, so installing ffmpeg is noticed
    without a restart whenever its folder is one of the usual ones."""
    if _seen["missing"] and time.time() - _seen["at"] > 20:
        setup()
    return list(_seen["missing"])


def explain(e) -> str:
    """The plain-words version of "the program could not be found", or "" if the error is something else."""
    text = str(e)
    not_found = isinstance(e, FileNotFoundError) or "WinError 2" in text or "No such file or directory: 'ff" in text
    return HELP if not_found and (missing() or "ffmpeg" in text or "ffprobe" in text or "WinError 2" in text) else ""


setup()
