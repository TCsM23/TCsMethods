"""Pixel Slides install wizard for Windows, written in Python.

Double-click "Install Pixel Slides.pyw" (or run: python "Install Pixel Slides.pyw").

Why a Python wizard as well as Setup.exe? Smart App Control and other
application control policies block programs that are not signed by a
publisher Windows knows, and a home-built Setup.exe is not. This wizard only
ever runs Python's own signed programs (python.exe, pythonw.exe), and it
uses "python -m pip" instead of pip.exe, so it gets through.

It installs per user (no admin prompt):
  %LOCALAPPDATA%\\Programs\\Pixel Slides     the app and its own Python environment
  Start menu and desktop shortcuts         run pythonw.exe -m slidedeck app
  Settings > Apps                          lists it, with an uninstaller
Decks stay in Documents\\Pixel Slides and are never removed.
"""
from __future__ import annotations

import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP = "Pixel Slides"
VERSION = "0.4.0"
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "packaging"))
from winlink import write_shortcut  # noqa: E402

UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\PixelSlides"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
COPY = ["slidedeck", "decks", "packaging", "requirements-desktop.txt", "README.md", "INSTALL.md"]
DARK, PAPER, MID = "#0f380f", "#c4d88a", "#306230"


def base_python(windowed: bool = False) -> Path:
    """The installed Python (not a venv), console or windowed."""
    exe = Path(sys._base_executable if hasattr(sys, "_base_executable") else sys.executable)
    name = "pythonw.exe" if windowed else "python.exe"
    return exe.with_name(name) if exe.with_name(name).exists() else exe


def shell_folder(csidl: int) -> Path:
    import ctypes
    from ctypes import wintypes

    buffer = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
    ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buffer)
    return Path(buffer.value)


def start_menu() -> Path:
    return shell_folder(2)  # CSIDL_PROGRAMS


def desktop() -> Path:
    return shell_folder(0)  # CSIDL_DESKTOP


class Wizard(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP} Setup")
        self.geometry("620x440")
        self.resizable(False, False)
        self.configure(bg=PAPER)
        icon = HERE / "packaging" / "icons" / "icon-48.png"
        if icon.exists():
            self.iconphoto(True, tk.PhotoImage(file=str(icon)))

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=PAPER, foreground=DARK, font=("Segoe UI", 10))
        style.configure("TButton", background=DARK, foreground=PAPER, padding=(14, 6), borderwidth=0)
        style.map("TButton", background=[("active", MID), ("disabled", "#8bac0f")])
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 16))
        style.configure("TCheckbutton", background=PAPER)
        style.configure("Horizontal.TProgressbar", background=DARK, troughcolor="#b3cb6f")

        self.folder = tk.StringVar(value=str(Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Programs" / APP))
        self.want_desktop = tk.BooleanVar(value=True)
        self.want_pdf = tk.BooleanVar(value=True)
        self.want_launch = tk.BooleanVar(value=True)
        self.events: queue.Queue = queue.Queue()

        banner = tk.Frame(self, bg=DARK, height=56)
        banner.pack(fill="x")
        tk.Label(banner, text=f"  {APP}", bg=DARK, fg=PAPER, font=("Consolas", 18, "bold")).pack(side="left", pady=10)
        tk.Label(banner, text=f"v{VERSION}  ", bg=DARK, fg="#8bac0f", font=("Consolas", 10)).pack(side="right")

        self.body = ttk.Frame(self, padding=24)
        self.body.pack(fill="both", expand=True)
        nav = ttk.Frame(self, padding=(24, 0, 24, 18))
        nav.pack(fill="x")
        self.cancel_button = ttk.Button(nav, text="Cancel", command=self.destroy)
        self.cancel_button.pack(side="right")
        self.next_button = ttk.Button(nav, text="Next >", command=self.next)
        self.next_button.pack(side="right", padx=8)
        self.back_button = ttk.Button(nav, text="< Back", command=self.back)
        self.back_button.pack(side="right")

        self.pages = [self.page_welcome, self.page_folder, self.page_options, self.page_install, self.page_done]
        self.step = 0
        self.show()

    # --- Pages -----------------------------------------------------------------------

    def heading(self, title: str, text: str) -> None:
        ttk.Label(self.body, text=title, style="Title.TLabel").pack(anchor="w")
        ttk.Label(self.body, text=text, wraplength=560, justify="left").pack(anchor="w", pady=(8, 16))

    def page_welcome(self) -> None:
        self.heading(f"Welcome to {APP}",
                     "This wizard installs Pixel Slides for you only, with no admin rights needed.\n\n"
                     "It sets up a private Python environment for the app, downloads what it needs "
                     "(about 60 MB, so stay online), and adds Start menu and desktop shortcuts.\n\n"
                     f"Using Python {sys.version.split()[0]} from {base_python()}.")
        if sys.version_info < (3, 11):
            ttk.Label(self.body, text="Pixel Slides needs Python 3.11 or newer. Install it from python.org first.",
                      foreground="#5a1414").pack(anchor="w")
            self.next_button.state(["disabled"])

    def page_folder(self) -> None:
        self.heading("Install folder", "Pixel Slides will be installed here. Your decks are kept separately, "
                                       "in Documents\\Pixel Slides.")
        row = ttk.Frame(self.body)
        row.pack(fill="x")
        ttk.Entry(row, textvariable=self.folder).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Browse…", command=self.browse).pack(side="left", padx=(8, 0))

    def browse(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self.folder.get())
        if chosen:
            self.folder.set(str(Path(chosen) / APP) if Path(chosen).name != APP else chosen)

    def page_options(self) -> None:
        self.heading("Options", "Choose what to add.")
        ttk.Checkbutton(self.body, text="Desktop shortcut", variable=self.want_desktop).pack(anchor="w", pady=4)
        ttk.Checkbutton(self.body, text="PDF export (uses Microsoft Edge in the background, about 50 MB)",
                        variable=self.want_pdf).pack(anchor="w", pady=4)
        ttk.Label(self.body, text="\nA Start menu shortcut is always added. Press Install to begin.",
                  wraplength=560).pack(anchor="w")

    def page_install(self) -> None:
        self.heading("Installing", "This takes a minute or two.")
        self.progress = ttk.Progressbar(self.body, mode="determinate", maximum=100)
        self.progress.pack(fill="x")
        self.log = tk.Text(self.body, height=10, bg="#b3cb6f", fg=DARK, relief="flat", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, pady=(12, 0))
        for button in (self.back_button, self.next_button, self.cancel_button):
            button.state(["disabled"])
        # Tk variables belong to the window's thread: read them here, not in the worker.
        options = {"target": Path(self.folder.get()), "desktop": self.want_desktop.get(), "pdf": self.want_pdf.get()}
        threading.Thread(target=self.install, args=(options,), daemon=True).start()
        self.after(100, self.poll)

    def page_done(self) -> None:
        self.heading("Done", f"{APP} is installed. Find it in the Start menu"
                             f"{' and on your desktop' if self.want_desktop.get() else ''}.\n\n"
                             "Your decks are in Documents\\Pixel Slides\\decks. Press Edit next to a deck "
                             "to open it in your text editor; the slides reload when you save.\n\n"
                             "To remove it later: Settings > Apps > Installed apps > Pixel Slides.")
        ttk.Checkbutton(self.body, text=f"Start {APP} now", variable=self.want_launch).pack(anchor="w")
        self.next_button.configure(text="Finish")
        self.back_button.state(["disabled"])
        self.cancel_button.state(["disabled"])

    # --- Navigation ------------------------------------------------------------------

    def show(self) -> None:
        for child in self.body.winfo_children():
            child.destroy()
        self.back_button.state(["!disabled"] if 0 < self.step < 3 else ["disabled"])
        self.next_button.state(["!disabled"])
        self.next_button.configure(text="Install" if self.step == 2 else "Next >")
        self.pages[self.step]()

    def next(self) -> None:
        if self.step == len(self.pages) - 1:
            if self.want_launch.get():
                self.launch()
            self.destroy()
            return
        self.step += 1
        self.show()

    def back(self) -> None:
        self.step = max(0, self.step - 1)
        self.show()

    # --- Work (in a thread; talks to the window through a queue) ---------------------

    def say(self, text: str, percent: int | None = None) -> None:
        self.events.put(("log", text, percent))

    def poll(self) -> None:
        try:
            while True:
                kind, text, percent = self.events.get_nowait()
                if kind == "log":
                    self.log.insert("end", text + "\n")
                    self.log.see("end")
                    if percent is not None:
                        self.progress["value"] = percent
                elif kind == "done":
                    self.step += 1
                    self.show()
                    return
                elif kind == "failed":
                    messagebox.showerror(f"{APP} Setup", text)
                    self.cancel_button.state(["!disabled"])
                    return
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def run(self, *args: str) -> None:
        self.say("> " + " ".join(Path(a).name if os.sep in a else a for a in args))
        result = subprocess.run(args, capture_output=True, text=True, creationflags=NO_WINDOW)
        tail = (result.stdout + result.stderr).strip().splitlines()[-3:]
        for line in tail:
            self.say("  " + line)
        if result.returncode:
            raise RuntimeError(f"This step failed:\n{' '.join(args[1:])}\n\n" + "\n".join(tail))

    def install(self, options: dict) -> None:
        try:
            target = options["target"]
            target.mkdir(parents=True, exist_ok=True)
            self.say(f"Copying the app to {target}", 5)
            for name in COPY:
                source = HERE / name
                if source.is_dir():
                    shutil.copytree(source, target / name, dirs_exist_ok=True,
                                    ignore=shutil.ignore_patterns("__pycache__"))
                elif source.exists():
                    shutil.copy2(source, target / name)
            shutil.copy2(HERE / "packaging" / "uninstall.pyw", target / "uninstall.pyw")

            venv = target / "venv"
            self.say("Creating the app's Python environment", 15)
            if not (venv / "Scripts" / "python.exe").exists():
                self.run(str(base_python()), "-m", "venv", str(venv))
            py = str(venv / "Scripts" / "python.exe")
            self.say("Updating pip", 25)
            self.run(py, "-m", "pip", "install", "--upgrade", "--disable-pip-version-check", "pip")
            self.say("Installing the slide engine (FastAPI, Pydantic, Jinja2, markdown-it)", 35)
            core = [line for line in (target / "requirements-desktop.txt").read_text().splitlines()
                    if line and not line.startswith("#") and not line.startswith(("playwright", "pywebview"))]
            self.run(py, "-m", "pip", "install", "--disable-pip-version-check", *core)

            self.say("Installing the native window (pywebview)", 60)
            try:
                self.run(py, "-m", "pip", "install", "--disable-pip-version-check", "pywebview>=5.0")
            except RuntimeError:
                self.say("  No native window for this Python; the app will open in an Edge app window instead.")
            if options["pdf"]:
                self.say("Installing PDF export (Playwright, drives Edge)", 75)
                self.run(py, "-m", "pip", "install", "--disable-pip-version-check", "playwright>=1.42")

            self.say("Adding shortcuts", 90)
            pythonw = str(venv / "Scripts" / "pythonw.exe")
            icon = str(target / "packaging" / "icons" / "pixel-slides.ico")
            places = [start_menu()] + ([desktop()] if options["desktop"] else [])
            for place in places:
                write_shortcut(place / f"{APP}.lnk", pythonw, "-m slidedeck app", str(target), icon,
                               "Markdown in, handheld-console slides out")
            self.register(target, icon)
            self.say("Finished.", 100)
            self.events.put(("done", "", None))
        except Exception as exc:  # noqa: BLE001 - show every failure to the user
            self.events.put(("failed", f"Setup could not finish.\n\n{exc}", None))

    def register(self, target: Path, icon: str) -> None:
        """List the app in Settings > Apps, with an uninstaller."""
        import winreg

        uninstall = f'"{base_python(windowed=True)}" "{target / "uninstall.pyw"}"'
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
            for name, value in {"DisplayName": APP, "DisplayVersion": VERSION, "Publisher": "TCsM",
                                "DisplayIcon": icon, "InstallLocation": str(target),
                                "UninstallString": uninstall}.items():
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)

    def launch(self) -> None:
        target = Path(self.folder.get())
        subprocess.Popen([str(target / "venv" / "Scripts" / "pythonw.exe"), "-m", "slidedeck", "app"],
                         cwd=target, creationflags=NO_WINDOW)


if __name__ == "__main__":
    if sys.platform != "win32":
        sys.exit("This wizard is for Windows. Elsewhere: python -m slidedeck app")
    Wizard().mainloop()
