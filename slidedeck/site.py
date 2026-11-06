"""A deck as a set of finished pages, with no server.

The mobile app runs this module inside the browser (Pyodide): it renders
every page of a deck once, stores them, and a service worker serves them
offline. The pages are the same templates the server uses, so a deck looks
and behaves the same on a phone as on the desktop.
"""
from __future__ import annotations

import json

from .lint import lint_deck
from .models import Deck
from .parser import DeckError, parse_deck
from .render import env
from .themes import THEMES, theme_css


def _render(template: str, base: str, **context) -> str:
    env.globals["base"] = base
    try:
        return env.get_template(template).render(dev=False, **context)
    finally:
        env.globals["base"] = ""


def render_pages(name: str, deck: Deck, base: str = "") -> dict[str, str]:
    """Every page of one deck, keyed by its path below the base."""
    common = dict(deck=deck, name=name, theme=deck.theme, theme_query="", lang=deck.lang)
    issues: dict[int, list] = {}
    for issue in lint_deck(deck):
        issues.setdefault(issue.slide - 1, []).append(issue)

    pages = {}
    for index in range(len(deck.slides)):
        number = index + 1
        pages[f"/deck/{name}/{number}"] = _render(
            "deck.html", base, index=index, mode="screen", issues={}, **common)
        pages[f"/deck/{name}/{number}/presenter"] = _render(
            "presenter.html", base, index=index, mode="screen", issues=issues, **common)
    pages[f"/deck/{name}/text"] = _render("text.html", base, mode="text", show_notes=False, **common)
    pages[f"/deck/{name}/text?notes=1"] = _render("text.html", base, mode="text", show_notes=True, **common)
    pages[f"/deck/{name}/print"] = _render("print.html", base, mode="print", show_notes=False, **common)
    pages[f"/deck/{name}/print?notes=1"] = _render("print.html", base, mode="print", show_notes=True, **common)
    return pages


def build(name: str, source: str, base: str = "") -> str:
    """Parse and render a deck. Returns JSON, which crosses into JavaScript
    cheaply: {"ok": true, "summary": {...}, "pages": {...}} or
    {"ok": false, "error": "..."}."""
    try:
        deck = parse_deck(source)
    except DeckError as exc:
        return json.dumps({"ok": False, "error": str(exc)})
    if not deck.slides:
        return json.dumps({"ok": False, "error": "This deck has no slides yet."})
    issues = [{"slide": i.slide, "level": i.level, "code": i.code, "message": i.message}
              for i in lint_deck(deck)]
    summary = {"name": name, "title": deck.title, "author": deck.author,
               "count": len(deck.slides), "theme": deck.theme,
               "theme_label": THEMES[deck.theme].label, "issues": issues}
    return json.dumps({"ok": True, "summary": summary, "pages": render_pages(name, deck, base)})


def stylesheet() -> str:
    return theme_css()


def starters() -> str:
    """The New deck choices, as JSON."""
    from .starters import catalogue

    return catalogue()


def new_deck(title: str, starter: str) -> str:
    """The text of a new deck from a starter."""
    from .starters import render

    return render(title, starter)


def duplicate(source: str) -> str:
    """A copy of a deck, titled "... (copy)"."""
    from .starters import retitle

    return retitle(source)
