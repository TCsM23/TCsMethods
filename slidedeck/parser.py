"""Deck file -> Deck model.

A deck file is Markdown with optional YAML front matter:

    ---
    title: My Talk
    theme: dmg
    ---
    class: title

    # First slide

    ???
    Speaker notes for the first slide.

    ---

    # Second slide

A line that is exactly `---` splits slides, but only when the line before it
is blank (otherwise Markdown reads `Title` + `---` as an <h2>), and never
inside a code fence or a ::: block.
"""
from __future__ import annotations

import yaml
from pydantic import ValidationError

from .blocks import CLOSE, OPEN, is_fence, parse_blocks
from .lint import slide_title
from .models import Deck, Slide

SEPARATOR = "---"
NOTES_MARKER = "???"
CLASS_PREFIX = "class:"


class DeckError(ValueError):
    """The deck file itself is broken (bad front matter, bad settings)."""


def parse_front_matter(lines: list[str]) -> tuple[dict, list[str]]:
    if not lines or lines[0].strip() != SEPARATOR:
        return {}, lines
    for end in range(1, len(lines)):
        if lines[end].strip() == SEPARATOR:
            raw = "\n".join(lines[1:end])
            try:
                data = yaml.safe_load(raw) or {}
            except yaml.YAMLError as exc:
                raise DeckError(f"front matter is not valid YAML: {exc}") from None
            if not isinstance(data, dict):
                raise DeckError("front matter must be key: value pairs")
            return data, lines[end + 1:]
    raise DeckError("front matter starts with --- but never closes")


def split_slides(lines: list[str]) -> list[list[str]]:
    chunks: list[list[str]] = [[]]
    in_fence = False
    depth = 0  # how many ::: blocks we are inside
    previous = ""
    for line in lines:
        if is_fence(line):
            in_fence = not in_fence
        elif not in_fence:
            if OPEN.match(line):
                depth += 1
            elif CLOSE.match(line) and depth:
                depth -= 1

        is_separator = (
            line.strip() == SEPARATOR
            and previous.strip() == ""
            and not in_fence
            and depth == 0
        )
        if is_separator:
            chunks.append([])
        else:
            chunks[-1].append(line)
        previous = line
    return chunks


def build_slide(index: int, lines: list[str]) -> Slide:
    # Speaker notes: everything after a ??? line (outside code fences).
    body, notes = lines, []
    in_fence = False
    for i, line in enumerate(lines):
        if is_fence(line):
            in_fence = not in_fence
        if not in_fence and line.strip() == NOTES_MARKER:
            body, notes = lines[:i], lines[i + 1:]
            break

    # Optional first line `class: title` picks a slide layout.
    css_class = None
    first = next((i for i, line in enumerate(body) if line.strip()), None)
    if first is not None and body[first].strip().startswith(CLASS_PREFIX):
        css_class = body[first].strip()[len(CLASS_PREFIX):].strip() or None
        body = body[:first] + body[first + 1:]

    source = "\n".join(body).strip()
    blocks = parse_blocks(source)
    slide_data = {
        "index": index,
        "source": source,
        "blocks": blocks,
        "title": slide_title(blocks),
        "notes": "\n".join(notes).strip(),
        "css_class": css_class,
    }
    try:
        return Slide.model_validate(slide_data)
    except ValidationError:
        # Unknown class name: keep the slide, drop the class.
        return Slide.model_validate({**slide_data, "css_class": None})


def parse_deck(text: str) -> Deck:
    meta, lines = parse_front_matter(text.splitlines())
    chunks = [c for c in split_slides(lines) if "\n".join(c).strip()]
    slides = [build_slide(i, chunk) for i, chunk in enumerate(chunks)]
    try:
        return Deck(**meta, slides=slides)
    except ValidationError as exc:
        problems = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
        raise DeckError(f"front matter: {problems}") from None
