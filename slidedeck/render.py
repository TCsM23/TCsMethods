"""Blocks -> HTML, through one Jinja template per block type."""
from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown_it import MarkdownIt
from markupsafe import Markup

from .models import Block
from .themes import THEMES, lcd_table

TEMPLATES_DIR = Path(__file__).parent / "templates"

# html=False: raw HTML typed into a deck is escaped, not executed.
markdown = MarkdownIt("commonmark", {"html": False, "typographer": True}).enable(
    ["table", "strikethrough", "replacements", "smartquotes"]
)


def render_markdown(text: str | None) -> Markup:
    return Markup(markdown.render(text or ""))


def render_markdown_inline(text: str | None) -> Markup:
    return Markup(markdown.renderInline(text or ""))


env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
    trim_blocks=True,
    lstrip_blocks=True,
)
env.filters["md"] = render_markdown
env.filters["md_inline"] = render_markdown_inline


HEADING_TAG = re.compile(r"<(/?)h([1-6])\b")
KICKER = re.compile(r"<h3>(.*?)</h3>", re.DOTALL)

# In the text view the page has an h1 and each slide an h2, so a slide's own
# headings move down to fit under them. On slides, h3 is the small kicker
# label above the title; in a reading outline it is a label, not a heading.
TEXT_VIEW_LEVELS = {1: 3, 2: 3, 4: 4, 5: 5, 6: 6}


def text_view_headings(html: str) -> str:
    """Rewrite a slide's headings for the text view's outline.

    Safe on rendered output only: raw HTML in decks is escaped, so every
    <hN> here was produced by markdown-it."""
    html = KICKER.sub(r'<p class="text-view-kicker-label">\1</p>', html)
    return HEADING_TAG.sub(lambda m: f"<{m[1]}h{TEXT_VIEW_LEVELS[int(m[2])]}", html)


def render_block(block: Block, mode: str = "screen") -> Markup:
    template = env.get_template(f"blocks/{block.type}.html")
    return Markup(template.render(block=block, mode=mode))


def render_text_block(block: Block) -> Markup:
    """A top-level block for the text view. Rewrite once here, not in
    render_block, or blocks nested in columns would be rewritten twice."""
    return Markup(text_view_headings(render_block(block, "text")))


def site_url(path: str | None) -> str:
    """Prefix a site-absolute path ("/media/a.png") with the URL base.

    The base is empty on the server. The mobile app is served from a folder
    (say /pixel-slides), so it renders with that folder as the base."""
    if path and path.startswith("/") and not path.startswith("//"):
        return env.globals["base"] + path
    return path or ""


env.filters["url"] = site_url
env.globals["base"] = ""
env.globals["desktop"] = None
env.globals["render_block"] = render_block
env.globals["render_text_block"] = render_text_block
env.globals["themes"] = THEMES
env.globals["lcd_table"] = lcd_table
