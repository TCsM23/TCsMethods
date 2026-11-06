"""The desktop app: the slide server in its own window.

    python -m slidedeck app                 # what the Start menu shortcut runs
    python -m slidedeck app --window edge   # force a window type (see WINDOWS)

Decks live in Documents/Pixel Slides/decks, so they survive updates and
uninstalls. The first start copies the sample deck there. The server runs on
127.0.0.1 only, with live reload on, so saving a deck in any editor updates
the open slides.

The window is the first of these that works:
  webview  a native window (pywebview: Edge WebView2 on Windows)
  edge     Edge or Chrome in app mode: its own window, no tabs or address bar
  browser  a tab in the default browser
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

from .starters import STARTERS
from .starters import render as render_starter
from .starters import retitle

APP_NAME = "Pixel Slides"
# A fixed port keeps the page origin stable, so viewer preferences (palette,
# lettering, motion) saved in the window's storage survive a restart.
PREFERRED_PORT = 47823
WINDOWS = ("auto", "webview", "edge", "browser", "none")

# The basic starter, kept under its old name. {title} is filled in.
NEW_DECK = render_starter("{title}")


# --- Folders ---------------------------------------------------------------------


def documents_dir() -> Path:
    """The user's Documents folder, wherever Windows has moved it (OneDrive)."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        buffer = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        CSIDL_PERSONAL = 5
        if ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, 0, buffer) == 0:
            return Path(buffer.value)
    return Path.home() / "Documents"


def data_dir() -> Path:
    """App state that is not the user's work: window storage, logs."""
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = root / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def bundled(*parts: str) -> Path:
    """A file shipped with the app: next to the package, or inside the
    PyInstaller bundle when frozen."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return root.joinpath(*parts)


SAMPLES_RECORD = ".pixel-slides-samples"  # sample decks already offered


def seed_decks(decks_dir: Path, samples: Path | None = None) -> list[str]:
    """Give the user each sample deck once: all of them on the first start,
    and after an update, only the new ones. A sample the user deleted stays
    deleted, and nothing the user has is ever overwritten."""
    decks_dir.mkdir(parents=True, exist_ok=True)
    samples = samples or bundled("decks")
    if not samples.is_dir():
        return []
    record = decks_dir / SAMPLES_RECORD
    if record.is_file():
        offered = set(record.read_text(encoding="utf-8").split())
    else:
        # Before 0.4 there was no record: a folder with decks in it was
        # seeded with the one sample of that time.
        offered = {"intro.md"} if any(decks_dir.glob("*.md")) else set()
    added = []
    for deck in sorted(samples.glob("*.md")):
        if deck.name not in offered and not (decks_dir / deck.name).exists():
            shutil.copy2(deck, decks_dir / deck.name)
            added.append(deck.name)
        offered.add(deck.name)
    media = samples / "media"
    if media.is_dir():
        (decks_dir / "media").mkdir(exist_ok=True)
        for file in media.iterdir():
            if file.is_file() and not (decks_dir / "media" / file.name).exists():
                shutil.copy2(file, decks_dir / "media" / file.name)
    record.write_text("\n".join(sorted(offered)) + "\n", encoding="utf-8")
    return added


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48].strip("-")
    return slug or "deck"


def open_path(path: Path, reveal: bool = False) -> bool:
    """Open a file or folder with the system's default app. False if there is none."""
    try:
        if sys.platform == "win32":
            if reveal:
                subprocess.Popen(["explorer", "/select,", str(path)])
            else:
                os.startfile(path)  # noqa: S606 - the user's own file
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(path)] if reveal else ["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path.parent if reveal else path)])
    except OSError:
        return False
    return True


# --- Server ----------------------------------------------------------------------


def port_is_free(port: int) -> bool:
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def running_instance(port: int) -> bool:
    """Is Pixel Slides already serving on this port? Then reuse it."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/desktop/ping", timeout=1) as response:
            return json.load(response).get("app") == "pixel-slides"
    except (OSError, ValueError):
        return False


def make_router(decks_dir: Path, exports_dir: Path, token: str, host: "WindowHost"):
    from fastapi import APIRouter, Body, Depends, Header, HTTPException

    from .app import DECK_NAME

    def check_token(x_desktop_token: str = Header("")):
        # A custom header forces a CORS preflight, which other sites fail,
        # and the token is only in pages served by this app.
        if not secrets.compare_digest(x_desktop_token, token):
            raise HTTPException(403, "Bad token")

    def deck_path(name: str) -> Path:
        path = decks_dir / f"{name}.md"
        if not DECK_NAME.match(name) or not path.is_file():
            raise HTTPException(404, "No such deck")
        return path

    public = APIRouter(prefix="/desktop")
    router = APIRouter(prefix="/desktop", dependencies=[Depends(check_token)])

    @public.get("/ping")
    def ping():
        return {"app": "pixel-slides"}

    def free_name(wanted: str) -> str:
        slug, n = slugify(wanted), 2
        name = slug
        while (decks_dir / f"{name}.md").exists():
            name, n = f"{slug}-{n}", n + 1
        return name

    @router.get("/starters")
    def starters():
        return [{"name": s.name, "label": s.label, "description": s.description} for s in STARTERS.values()]

    @router.post("/new-deck")
    def new_deck(title: str = Body("My talk", embed=True), starter: str = Body("basic", embed=True)):
        title = " ".join(title.split())[:120] or "My talk"
        if starter not in STARTERS:
            raise HTTPException(400, "Unknown starter")
        name = free_name(title)
        path = decks_dir / f"{name}.md"
        path.write_text(render_starter(title, starter), encoding="utf-8")
        open_path(path)
        return {"name": name}

    @router.post("/duplicate/{name}")
    def duplicate(name: str):
        source = deck_path(name)
        copy = free_name(f"{name}-copy")
        (decks_dir / f"{copy}.md").write_text(retitle(source.read_text(encoding="utf-8")), encoding="utf-8")
        return {"name": copy}

    @router.post("/edit/{name}")
    def edit(name: str):
        open_path(deck_path(name))
        return {"ok": True}

    @router.post("/open-folder")
    def open_folder():
        open_path(decks_dir)
        return {"ok": True}

    @router.post("/export/{name}")
    def export(name: str, handout: bool = Body(False, embed=True)):
        """The slides as a PDF, or with handout=true, slides plus speaker notes."""
        from .pdf import PdfUnavailable, print_pdf

        deck_path(name)
        output = exports_dir / f"{name}{'-handout' if handout else ''}.pdf"
        try:
            print_pdf(f"{host.origin}/deck/{name}/print{'?notes=1' if handout else ''}", output)
        except PdfUnavailable:
            return {"path": None}
        open_path(output, reveal=True)
        return {"path": str(output)}

    @router.post("/window")
    def window(url: str = Body(..., embed=True)):
        if not url.startswith("/") or url.startswith("//"):
            raise HTTPException(400, "Only this app's pages")
        return {"opened": host.open_window(url)}

    return public, router


# --- Windows ---------------------------------------------------------------------


class WindowHost:
    """Shows the app's pages. Subclasses pick how."""

    kind = "none"

    def __init__(self, origin: str):
        self.origin = origin

    def open_window(self, path: str) -> bool:
        return False  # let the page open it itself

    def run(self, stop: threading.Event) -> None:
        stop.wait()


class WebviewHost(WindowHost):
    kind = "webview"

    def __init__(self, origin: str):
        super().__init__(origin)
        import webview  # noqa: F401 - fail here, so "auto" can fall back

        self.webview = webview

    def open_window(self, path: str) -> bool:
        title = "Presenter" if path.endswith("/presenter") or "/presenter?" in path else APP_NAME
        self.webview.create_window(f"{title} · {APP_NAME}", self.origin + path, width=1280, height=800)
        return True

    def run(self, stop: threading.Event) -> None:
        self.webview.create_window(APP_NAME, self.origin + "/", width=1280, height=820, min_size=(480, 360))
        # Not private: keep localStorage (the viewer's preferences) between runs.
        self.webview.start(private_mode=False, storage_path=str(data_dir() / "webview"))


def find_app_browser() -> str | None:
    names = ["msedge", "chrome", "google-chrome", "chromium", "chromium-browser"]
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    if sys.platform == "win32":
        for root in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"),
                     os.environ.get("LOCALAPPDATA")):
            for rel in (r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe"):
                if root and (Path(root) / rel).is_file():
                    return str(Path(root) / rel)
    return None


class AppBrowserHost(WindowHost):
    """Edge or Chrome with --app: a plain window with no browser chrome.
    A separate profile means this process lives exactly as long as the window."""

    kind = "edge"

    def __init__(self, origin: str):
        super().__init__(origin)
        self.exe = find_app_browser()
        if not self.exe:
            raise RuntimeError("No Edge or Chrome found")

    def run(self, stop: threading.Event) -> None:
        profile = data_dir() / "browser-profile"
        subprocess.run([self.exe, f"--app={self.origin}/", f"--user-data-dir={profile}",
                        "--no-first-run", "--no-default-browser-check", "--window-size=1280,820"],
                       check=False)


class BrowserHost(WindowHost):
    kind = "browser"

    def run(self, stop: threading.Event) -> None:
        webbrowser.open(self.origin + "/")
        stop.wait()  # no way to see the tab close: run until the process ends


HOSTS = {"webview": WebviewHost, "edge": AppBrowserHost, "browser": BrowserHost, "none": WindowHost}


def candidate_hosts(choice: str, origin: str):
    """The window types to try, best first. "auto" falls back step by step."""
    order = ["webview", "edge", "browser"] if choice == "auto" else [choice]
    for kind in order:
        try:
            yield HOSTS[kind](origin)
        except Exception as exc:  # noqa: BLE001 - try the next kind of window
            print(f"{kind} window unavailable: {exc}", file=sys.stderr)
    if order[-1] != "browser" and choice != "none":
        yield BrowserHost(origin)


class FallbackHost(WindowHost):
    """Runs the first window type that works. pywebview can import fine and
    still fail on start (no WebView2 runtime, blocked .NET), so failures in
    run() move on to the next type too."""

    def __init__(self, choice: str, origin: str):
        super().__init__(origin)
        self.choice = choice
        self.current: WindowHost = WindowHost(origin)

    @property
    def kind(self) -> str:  # type: ignore[override]
        return self.current.kind

    def open_window(self, path: str) -> bool:
        return self.current.open_window(path)

    def run(self, stop: threading.Event) -> None:
        for host in candidate_hosts(self.choice, self.origin):
            self.current = host
            try:
                host.run(stop)
                return
            except Exception as exc:  # noqa: BLE001
                print(f"{host.kind} window failed: {exc}", file=sys.stderr)
        self.current = WindowHost(self.origin)


# --- Main ------------------------------------------------------------------------


def quiet_streams() -> None:
    """A windowed app (pythonw, or the frozen .exe) has no console:
    sys.stdout is None and uvicorn's logging would crash on it."""
    if sys.stdout is None or sys.stderr is None:
        log = open(data_dir() / "pixel-slides.log", "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        sys.stdout = sys.stdout or log
        sys.stderr = sys.stderr or log


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="slidedeck app", description=f"Run {APP_NAME} as a desktop app.")
    parser.add_argument("--decks", type=Path, help="deck folder (default: Documents/Pixel Slides/decks)")
    parser.add_argument("--window", choices=WINDOWS, default=os.environ.get("PIXEL_SLIDES_WINDOW", "auto"))
    parser.add_argument("--port", type=int, default=PREFERRED_PORT)
    args = parser.parse_args(argv)
    quiet_streams()

    if running_instance(args.port):
        # Already running: open another window onto it, then leave.
        if args.window != "none":
            FallbackHost("edge" if args.window in ("auto", "webview") else args.window,
                         f"http://127.0.0.1:{args.port}").run(threading.Event())
        return

    home = documents_dir() / APP_NAME
    decks_dir = (args.decks or home / "decks").resolve()
    exports_dir = home / "exports"
    seed_decks(decks_dir)

    # The app module reads these when it is imported.
    os.environ["SLIDES_DECKS_DIR"] = str(decks_dir)
    os.environ["SLIDES_DEV"] = "1"  # live reload: save a deck, the slides update

    import uvicorn

    from .app import app
    from .render import env

    port = args.port if port_is_free(args.port) else free_port()
    origin = f"http://127.0.0.1:{port}"
    token = secrets.token_urlsafe(24)
    host = FallbackHost(args.window, origin)
    public, router = make_router(decks_dir, exports_dir, token, host)
    app.include_router(public)
    app.include_router(router)
    env.globals["desktop"] = {"token": token, "decks_dir": str(decks_dir)}

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        if not thread.is_alive():
            sys.exit("The slide server could not start")
        time.sleep(0.05)
    print(f"{APP_NAME} at {origin}, decks in {decks_dir}", flush=True)

    stop = threading.Event()
    try:
        host.run(stop)
    except KeyboardInterrupt:
        pass
    finally:
        server.should_exit = True
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
