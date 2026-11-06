"""Command line.

    python -m slidedeck serve            # http://127.0.0.1:8000
    python -m slidedeck serve --dev      # + live reload while you edit decks
    python -m slidedeck export intro     # -> exports/intro.pdf
    python -m slidedeck export intro --theme night --readable
    python -m slidedeck check intro      # block errors + accessibility warnings
    python -m slidedeck new "My talk" --starter talk   # -> decks/my-talk.md
    python -m slidedeck app              # the desktop app (native window)
    python -m slidedeck mobile           # build the installable mobile app (PWA)
"""
from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import time
from pathlib import Path

from .themes import THEMES


def serve(args: argparse.Namespace) -> None:
    import uvicorn

    if args.dev:
        os.environ["SLIDES_DEV"] = "1"
    uvicorn.run("slidedeck.app:app", host=args.host, port=args.port, reload=False)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def export(args: argparse.Namespace) -> None:
    """Start a throwaway server, open the print view headless, print to PDF."""
    import uvicorn

    from .pdf import PdfUnavailable, print_pdf

    port = free_port()
    server = uvicorn.Server(uvicorn.Config("slidedeck.app:app", host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)

    output = Path(args.output or f"exports/{args.deck}.pdf")
    query = f"?theme={args.theme}" if args.theme else ""
    try:
        print_pdf(f"http://127.0.0.1:{port}/deck/{args.deck}/print{query}", output, args.readable)
    except (PdfUnavailable, RuntimeError) as exc:
        sys.exit(str(exc))
    finally:
        server.should_exit = True
        thread.join(timeout=5)
    print(f"Wrote {output}")


def check(args: argparse.Namespace) -> None:
    """Parse a deck and run the accessibility lint. Errors fail the check;
    warnings only fail it with --strict."""
    from .lint import lint_deck
    from .parser import parse_deck

    path = Path(os.environ.get("SLIDES_DECKS_DIR", "decks")) / f"{args.deck}.md"
    deck = parse_deck(path.read_text(encoding="utf-8"))
    issues = lint_deck(deck)
    for issue in issues:
        print(issue)
    errors = sum(issue.level == "error" for issue in issues)
    warnings = len(issues) - errors
    print(f"{deck.title}: {len(deck.slides)} slides, {errors} error(s), {warnings} warning(s)")
    sys.exit(1 if errors or (args.strict and warnings) else 0)


def new(args: argparse.Namespace) -> None:
    """Write a new deck from a starter, without overwriting anything."""
    from .desktop import slugify
    from .starters import render

    decks = Path(os.environ.get("SLIDES_DECKS_DIR", "decks"))
    decks.mkdir(parents=True, exist_ok=True)
    slug = slugify(args.title)
    name, n = slug, 2
    while (decks / f"{name}.md").exists():
        name, n = f"{slug}-{n}", n + 1
    path = decks / f"{name}.md"
    path.write_text(render(args.title, args.starter, args.minutes), encoding="utf-8")
    print(f"Wrote {path}. Open it at /deck/{name}/1")


def main() -> None:
    if sys.argv[1:2] == ["app"]:
        from .desktop import main as app_main

        app_main(sys.argv[2:])
        return

    parser = argparse.ArgumentParser(prog="slidedeck")
    sub = parser.add_subparsers(dest="command", required=True)

    p_serve = sub.add_parser("serve", help="run the slide server")
    p_serve.add_argument("--dev", action="store_true", help="live reload on file changes")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.set_defaults(func=serve)

    p_export = sub.add_parser("export", help="print a deck to PDF")
    p_export.add_argument("deck")
    p_export.add_argument("-o", "--output")
    p_export.add_argument("--theme", choices=list(THEMES))
    p_export.add_argument("--readable", action="store_true",
                          help="use Atkinson Hyperlegible instead of pixel lettering")
    p_export.set_defaults(func=export)

    # "app" has its own options (slidedeck/desktop.py): it is dispatched above.
    sub.add_parser("app", help="run the desktop app (see: app --help)")

    p_mobile = sub.add_parser("mobile", help="build the mobile app (an installable, offline web app)")
    p_mobile.add_argument("-o", "--output", default="dist/mobile")
    p_mobile.add_argument("--pyodide", help="folder with the Pyodide runtime (default: download it)")
    p_mobile.set_defaults(func=lambda a: __import__("slidedeck.mobile").mobile.build(a))

    p_check = sub.add_parser("check", help="report block errors and accessibility warnings")
    p_check.add_argument("deck")
    p_check.add_argument("--strict", action="store_true", help="fail on warnings too")
    p_check.set_defaults(func=check)

    from .starters import STARTERS

    p_new = sub.add_parser("new", help="start a deck from a starter (basic, talk, lesson)")
    p_new.add_argument("title")
    p_new.add_argument("--starter", choices=list(STARTERS), default="basic")
    p_new.add_argument("--minutes", type=float, help="planned length, for the presenter countdown")
    p_new.set_defaults(func=new)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
