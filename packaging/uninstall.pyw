"""Removes Pixel Slides (installed by the Python wizard). Decks are kept."""
from __future__ import annotations

import shutil
import tkinter as tk
import winreg
from pathlib import Path
from tkinter import messagebox

APP = "Pixel Slides"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\PixelSlides"
HERE = Path(__file__).resolve().parent


def shell_folder(csidl: int) -> Path:
    import ctypes
    from ctypes import wintypes

    buffer = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
    ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buffer)
    return Path(buffer.value)


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    if not messagebox.askyesno(f"Uninstall {APP}", f"Remove {APP} from this PC?\n\n"
                                                    "Your decks in Documents\\Pixel Slides are kept."):
        return
    for place in (shell_folder(2), shell_folder(0)):  # Start menu programs, desktop
        (place / f"{APP}.lnk").unlink(missing_ok=True)
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    except OSError:
        pass
    # This script runs from the base Python, not the app's venv, so the
    # whole folder (venv included) can go.
    shutil.rmtree(HERE, ignore_errors=True)
    messagebox.showinfo(f"Uninstall {APP}", f"{APP} was removed.")


if __name__ == "__main__":
    main()
