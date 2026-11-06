"""Accessibility lint: things a deck can get wrong that no validator catches.

A block that fails validation is already an ErrorBlock. These checks look at
decks that are *valid* but hard to use: an image with no alt text, a video
called "Video", a slide with no heading to navigate by, a wall of text.

Errors break the deck; warnings are advice. `python -m slidedeck check`
prints both, and the presenter view shows the ones for the current slide.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator, Literal

from markdown_it.token import Token

from .models import Block, Deck, Slide
from .render import markdown

MAX_WORDS = 120
VAGUE_LINK_TEXT = {"here", "click here", "this", "link", "this link", "more", "read more"}
URL_LIKE = re.compile(r"^(https?://|www\.)", re.IGNORECASE)


@dataclass(frozen=True)
class Issue:
    slide: int  # 1-based, as people count
    level: Literal["error", "warning"]
    code: str
    message: str

    def __str__(self) -> str:
        return f"slide {self.slide}: {self.level} [{self.code}] {self.message}"


# --- Walking blocks and Markdown ---------------------------------------------


def walk(blocks: list[Block]) -> Iterator[Block]:
    """Every block, including the ones nested inside columns."""
    for block in blocks:
        yield block
        if block.type == "columns":
            for column in block.columns:
                yield from walk(column)
        elif block.type == "steps":
            for item in block.items:
                yield from walk(item)


def tokens(text: str) -> list[Token]:
    return markdown.parse(text or "")


def inline_text(token: Token) -> str:
    """Plain text of an inline token: emphasis and code markers removed."""
    parts = []
    for child in token.children or []:
        if child.type in ("text", "code_inline"):
            parts.append(child.content)
        elif child.type in ("softbreak", "hardbreak"):
            parts.append(" ")
        elif child.type == "image":
            parts.append(child.content)
    return "".join(parts).strip()


def headings(text: str) -> list[tuple[int, str]]:
    """[(level, plain text)] for every heading in a Markdown string."""
    found = []
    stream = tokens(text)
    for i, token in enumerate(stream):
        if token.type == "heading_open" and i + 1 < len(stream):
            found.append((int(token.tag[1]), inline_text(stream[i + 1])))
    return found


def plain_text(text: str) -> str:
    stream = tokens(text)
    words = [inline_text(t) for t in stream if t.type == "inline"]
    words += [t.content for t in stream if t.type in ("fence", "code_block")]
    return " ".join(w for w in words if w)


def links(text: str) -> list[tuple[str, str]]:
    """[(link text, href)] for every link in a Markdown string."""
    found = []
    for token in tokens(text):
        if token.type != "inline":
            continue
        children = token.children or []
        for i, child in enumerate(children):
            if child.type != "link_open":
                continue
            label = []
            for inner in children[i + 1:]:
                if inner.type == "link_close":
                    break
                if inner.type in ("text", "code_inline"):
                    label.append(inner.content)
            found.append(("".join(label).strip(), str(child.attrs.get("href", ""))))
    return found


def block_texts(block: Block) -> list[str]:
    """The Markdown strings a block shows on screen."""
    if block.type == "markdown":
        return [block.source]
    if block.type in ("callout", "dialog"):
        return [block.body, getattr(block, "title", None) or ""]
    if block.type == "meter":
        return [block.label, block.body]
    if block.type in ("gallery", "video", "sprite", "qr"):
        return [block.caption or ""]
    if block.type == "chart":
        return [block.title, block.caption or "", *(bar.label for bar in block.bars)]
    if block.type == "quiz":
        return [block.question, *(option.text for option in block.options), block.explain]
    return []


# --- Slide titles --------------------------------------------------------------


def slide_title(blocks: list[Block]) -> str:
    """The text of the slide's most important heading.

    h1 beats h2 beats h3 (the small kicker), and the first one wins a tie.
    A slide with no heading at all falls back to its first words.
    """
    best: tuple[int, str] | None = None
    for block in walk(blocks):
        for text in block_texts(block):
            for level, heading in headings(text):
                if heading and (best is None or level < best[0]):
                    best = (level, heading)
    if best:
        return best[1]
    for block in walk(blocks):
        for text in block_texts(block):
            words = plain_text(text).split()
            if words:
                return " ".join(words[:8]) + ("…" if len(words) > 8 else "")
    return ""


# --- The rules -------------------------------------------------------------------


def lint_slide(slide: Slide) -> list[Issue]:
    number = slide.index + 1
    issues: list[Issue] = []

    def add(level: Literal["error", "warning"], code: str, message: str) -> None:
        issues.append(Issue(number, level, code, message))

    has_heading = False
    word_count = 0
    for block in walk(slide.blocks):
        if block.type == "error":
            add("error", "block-error", f":::{block.block_name} - {block.message}")
            continue
        if block.type == "gallery":
            for position, image in enumerate(block.images, start=1):
                if not image.alt.strip():
                    add("warning", "image-alt",
                        f"gallery image {position} ({image.src}) has no alt text; describe it in ![...]")
        if block.type == "video":
            if not block.title:
                add("warning", "video-title", 'video has no title=; screen readers will only say "Video"')
            if block.provider == "local" and not block.captions:
                add("warning", "video-captions", "local video has no captions= (a media/*.vtt file)")
        for text in block_texts(block):
            if any(level <= 3 for level, _ in headings(text)):
                has_heading = True
            word_count += len(plain_text(text).split())
            for label, href in links(text):
                if label.lower() in VAGUE_LINK_TEXT or URL_LIKE.match(label):
                    add("warning", "link-text",
                        f"link text {label!r} does not say where {href} goes")

    if not has_heading:
        add("warning", "slide-heading", "no heading; screen reader users navigate decks by headings")
    if word_count > MAX_WORDS:
        add("warning", "word-count", f"{word_count} words; over {MAX_WORDS} is hard to read from the back row")
    return issues


def lint_deck(deck: Deck) -> list[Issue]:
    issues = [issue for slide in deck.slides for issue in lint_slide(slide)]
    # Two slides with one title sound the same in the outline and to a screen
    # reader. A deliberate "(continued)" slide should say so in its title.
    first_with: dict[str, int] = {}
    for slide in deck.slides:
        key = " ".join(slide.title.lower().split())
        if not key:
            continue
        if key in first_with:
            issues.append(Issue(slide.index + 1, "warning", "slide-title-duplicate",
                                f"same title as slide {first_with[key]} ({slide.title!r}); "
                                "give each slide its own, so the outline can tell them apart"))
        else:
            first_with[key] = slide.index + 1
    return sorted(issues, key=lambda issue: issue.slide)
