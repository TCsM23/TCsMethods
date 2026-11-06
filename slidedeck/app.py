"""FastAPI app: serves decks, the presenter, print and text views, and live reload."""
from __future__ import annotations

import asyncio
import os
import re
from contextlib import asynccontextmanager
from html import escape
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .lint import lint_deck
from .models import Deck
from .navigation import index_to_number, number_to_index, parse_slide_number
from .parser import DeckError, parse_deck
from .render import env
from .themes import DEFAULT_THEME, THEMES, theme_css

PACKAGE_DIR = Path(__file__).parent
DECKS_DIR = Path(os.environ.get("SLIDES_DECKS_DIR", "decks")).resolve()
DEV = os.environ.get("SLIDES_DEV") == "1"
DECK_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

# Content-Security-Policy: the browser-side half of the embed allow-list.
# Even if a bad URL slipped past the validator, frames can only load from here.
CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "font-src 'self'",
    "img-src 'self' https: data:",
    "media-src 'self'",
    "frame-src https://www.youtube-nocookie.com https://player.vimeo.com",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
])

_cache: dict[str, tuple[float, Deck]] = {}
_listeners: set[asyncio.Queue[str]] = set()


def load_deck(name: str) -> Deck:
    if not DECK_NAME.match(name):
        raise HTTPException(404, "No such deck")
    path = DECKS_DIR / f"{name}.md"
    if not path.is_file():
        raise HTTPException(404, "No such deck")
    mtime = path.stat().st_mtime
    cached = _cache.get(name)
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        deck = parse_deck(path.read_text(encoding="utf-8"))
    except DeckError as exc:
        raise HTTPException(422, f"{name}.md: {exc}") from None
    if not deck.slides:
        raise HTTPException(422, f"{name}.md has no slides yet")
    _cache[name] = (mtime, deck)
    return deck


def pick_theme(deck: Deck, request: Request) -> tuple[str, str]:
    """?theme=night overrides the deck's theme, but only with a known name."""
    override = request.query_params.get("theme")
    if override in THEMES:
        return override, f"?theme={override}"
    return deck.theme, ""


def page(template: str, **context) -> HTMLResponse:
    return HTMLResponse(env.get_template(template).render(dev=DEV, **context))


async def watch_files() -> None:
    from watchfiles import awatch

    async for _changes in awatch(DECKS_DIR, PACKAGE_DIR / "templates", PACKAGE_DIR / "static"):
        _cache.clear()  # Jinja re-checks template mtimes on its own
        for queue in list(_listeners):
            queue.put_nowait("reload")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = asyncio.create_task(watch_files()) if DEV else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="Pixel Slides", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")
(DECKS_DIR / "media").mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=DECKS_DIR / "media"), name="media")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = CSP
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.exception_handler(HTTPException)
async def friendly_errors(_request: Request, exc: HTTPException):
    body = (
        f'<!doctype html><html lang="en" class="theme-{DEFAULT_THEME}"><meta charset="utf-8"><title>Error</title>'
        '<link rel="stylesheet" href="/themes.css"><link rel="stylesheet" href="/static/theme.css">'
        '<link rel="stylesheet" href="/static/slides.css"><body class="library-view">'
        '<main class="library-list-container"><p class="library-list-kicker">'
        f"Error {exc.status_code}</p><h1 class=\"library-list-header\">{escape(str(exc.detail))}</h1>"
        '<p><a class="library-list-item-link" href="/">Back to decks</a></p></main>'
    )
    return HTMLResponse(body, status_code=exc.status_code)


@app.get("/", response_class=HTMLResponse)
def library(request: Request):
    decks = []
    for path in sorted(DECKS_DIR.glob("*.md")):
        if not DECK_NAME.match(path.stem):
            continue
        try:
            deck = load_deck(path.stem)
        except HTTPException:
            continue
        decks.append({"name": path.stem, "title": deck.title, "author": deck.author,
                      "count": len(deck.slides), "theme": THEMES[deck.theme]})
    from .starters import STARTERS

    return page("index.html", decks=decks, theme=DEFAULT_THEME, lang="en", starters=STARTERS.values())


@app.get("/deck/{name}")
def deck_start(name: str, request: Request):
    load_deck(name)
    return RedirectResponse(f"/deck/{name}/1{_query(request)}", status_code=302)


@app.get("/deck/{name}/print", response_class=HTMLResponse)
def deck_print(name: str, request: Request):
    deck = load_deck(name)
    theme, _ = pick_theme(deck, request)
    show_notes = request.query_params.get("notes") == "1"
    return page("print.html", deck=deck, name=name, theme=theme, lang=deck.lang, mode="print",
                show_notes=show_notes)


@app.get("/deck/{name}/text", response_class=HTMLResponse)
def deck_text(name: str, request: Request):
    """The whole deck as one plain, semantic page: for screen readers,
    zooming, handouts, and anyone who wants to read rather than watch."""
    deck = load_deck(name)
    theme, theme_query = pick_theme(deck, request)
    show_notes = request.query_params.get("notes") == "1"
    return page("text.html", deck=deck, name=name, theme=theme, theme_query=theme_query,
                lang=deck.lang, mode="text", show_notes=show_notes)


@app.get("/themes.css")
def themes_stylesheet():
    return Response(theme_css(), media_type="text/css",
                    headers={"Cache-Control": "no-cache" if DEV else "max-age=3600"})


@app.get("/deck/{name}/{number}", response_class=HTMLResponse)
def deck_slide(name: str, number: str, request: Request):
    return _slide_page(name, number, request, "deck.html")


@app.get("/deck/{name}/{number}/presenter", response_class=HTMLResponse)
def deck_presenter(name: str, number: str, request: Request):
    return _slide_page(name, number, request, "presenter.html", suffix="/presenter")


def _query(request: Request) -> str:
    theme = request.query_params.get("theme")
    return f"?theme={theme}" if theme in THEMES else ""


def _slide_page(name: str, raw_number: str, request: Request, template: str, suffix: str = ""):
    deck = load_deck(name)
    number = parse_slide_number(raw_number)
    if number is None:
        raise HTTPException(404, f"'{raw_number}' is not a slide number")

    index = number_to_index(number, len(deck.slides))
    canonical = index_to_number(index)
    if str(canonical) != raw_number:  # catches 99 and -4, but also 007
        # /deck/intro/99 -> /deck/intro/12 : one URL per slide, always valid.
        return RedirectResponse(f"/deck/{name}/{canonical}{suffix}{_query(request)}", status_code=302)

    theme, theme_query = pick_theme(deck, request)
    issues: dict[int, list] = {}
    if template == "presenter.html":
        for issue in lint_deck(deck):
            issues.setdefault(issue.slide - 1, []).append(issue)
    return page(template, deck=deck, name=name, index=index, theme=theme,
                theme_query=theme_query, lang=deck.lang, mode="screen", issues=issues)


@app.get("/events")
async def events(request: Request):
    """Server-sent events: tells open pages to reload when a file changes."""
    if not DEV:
        raise HTTPException(404, "Live reload is off (start with --dev)")
    queue: asyncio.Queue[str] = asyncio.Queue()
    _listeners.add(queue)

    async def stream():
        try:
            yield "retry: 1000\n\n"
            while not await request.is_disconnected():
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {message}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            _listeners.discard(queue)

    return StreamingResponse(stream(), media_type="text/event-stream")
