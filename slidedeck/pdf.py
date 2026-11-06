"""Print a deck's print view to PDF with a headless browser (Playwright)."""
from __future__ import annotations

import sys
from pathlib import Path


class PdfUnavailable(RuntimeError):
    """Playwright or a browser for it is missing."""


def _launch(p):
    # On Windows, Edge is always installed, so no 150 MB browser download is
    # needed. Elsewhere (or if Edge is missing), use Playwright's own Chromium.
    channels = ["msedge", "chrome", None] if sys.platform == "win32" else [None, "chrome", "msedge"]
    errors = []
    for channel in channels:
        try:
            return p.chromium.launch(channel=channel) if channel else p.chromium.launch()
        except Exception as exc:  # noqa: BLE001 - try the next browser
            errors.append(f"{channel or 'chromium'}: {str(exc).splitlines()[0]}")
    raise PdfUnavailable("No browser for PDF export. " + "; ".join(errors))


def print_pdf(url: str, output: Path, readable: bool = False) -> Path:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise PdfUnavailable("Playwright is not installed") from None

    output.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = _launch(p)
        try:
            page = browser.new_page(viewport={"width": 1600, "height": 900})
            if readable:
                # The same switch a viewer flips in Options, set before the page loads.
                page.add_init_script(
                    "localStorage.setItem('pixel-slides:prefs', JSON.stringify({font: 'readable'}))")
            response = page.goto(url, wait_until="networkidle")
            if response is None or not response.ok:
                raise RuntimeError(f"Could not load {url} (HTTP {response.status if response else '?'})")
            page.evaluate("document.fonts.ready")
            page.emulate_media(media="print")
            page.pdf(path=str(output), width="1600px", height="900px",
                     print_background=True, prefer_css_page_size=True)
        finally:
            browser.close()
    return output
