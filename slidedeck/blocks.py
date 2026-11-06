"""The block ("interpreter") system.

Inside a slide, a block looks like:

    :::callout warning title="Heads up"
    Body text in **Markdown**.
    :::

The pipeline for each block:
  1. lex     - find the opening line, read name + options, collect the body
  2. build   - turn name/options/body into a plain dict for that block type
  3. validate- hand the dict to Pydantic (the discriminated union)
  4. render  - done later by render.py, one Jinja template per type

Anything that goes wrong becomes an ErrorBlock, so one typo shows a visible
error card on that slide instead of crashing the whole deck.
"""
from __future__ import annotations

import re
import shlex
from typing import Callable

from pydantic import TypeAdapter, ValidationError

from .models import Block, ErrorBlock, MarkdownBlock

OPEN = re.compile(r"^:::\s*([a-z][a-z0-9-]*)\s*(.*)$")
CLOSE = re.compile(r"^:::\s*$")
COLUMN_BREAK = "+++"
OPTION_KEY = re.compile(r"^[a-z_][a-z0-9_-]*$")
IMAGE_LINE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<src>[^)\s]+)\)$")
BULLET_ITEM = re.compile(r"^[-*+]\s+(?P<text>.*)$")
NUMBER_ITEM = re.compile(r"^\d{1,3}[.)]\s+(?P<text>.*)$")
QUIZ_OPTION = re.compile(r"^\s*[-*]\s+\[(?P<mark>[ xX])\]\s+(?P<text>.+)$")
CHART_LINE = re.compile(r"^(?P<label>.+?)\s*:\s*(?P<value>-?[0-9][0-9_,]*(?:\.[0-9]+)?)\s*$")

# The first bare word after the block name fills this field,
# so `:::callout warning` means variant=warning.
POSITIONAL = {"callout": "variant", "columns": "layout", "gallery": "variant", "video": "src",
              "meter": "variant", "dialog": "speaker", "qr": "data", "chart": "title"}

block_adapter: TypeAdapter[Block] = TypeAdapter(Block)


def is_fence(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("```") or stripped.startswith("~~~")


def parse_options(name: str, text: str) -> dict[str, str]:
    """`warning title="Heads up"` -> {"variant": "warning", "title": "Heads up"}"""
    options: dict[str, str] = {}
    try:
        tokens = shlex.split(text)
    except ValueError as exc:  # e.g. an unclosed quote
        raise ValueError(f"could not read options: {exc}") from None
    for token in tokens:
        key, sep, value = token.partition("=")
        # A URL like ...watch?v=abc contains "=", but "https://...?v" is no key.
        if sep and OPTION_KEY.match(key):
            options[key] = value
        elif name in POSITIONAL and POSITIONAL[name] not in options:
            options[POSITIONAL[name]] = token
        else:
            raise ValueError(f"unexpected option {token!r} (use key=value)")
    return options


def split_top_level(lines: list[str], marker: str) -> list[list[str]]:
    """Split on `marker` lines that are not inside a code fence or a nested block."""
    groups: list[list[str]] = [[]]
    in_fence = False
    depth = 0
    for line in lines:
        if is_fence(line):
            in_fence = not in_fence
        elif not in_fence:
            if OPEN.match(line):
                depth += 1
            elif CLOSE.match(line) and depth:
                depth -= 1
        if not in_fence and depth == 0 and line.strip() == marker:
            groups.append([])
        else:
            groups[-1].append(line)
    return groups


def read_body(lines: list[str], start: int) -> tuple[list[str], int, bool]:
    """Collect a block body from lines[start:], matching nested ::: pairs.

    Returns (body, index after the closing line, whether it was closed).
    """
    body: list[str] = []
    depth = 0
    in_fence = False
    i = start
    while i < len(lines):
        line = lines[i]
        if is_fence(line):
            in_fence = not in_fence
        elif not in_fence:
            if OPEN.match(line):
                depth += 1
            elif CLOSE.match(line):
                if depth == 0:
                    return body, i + 1, True
                depth -= 1
        body.append(line)
        i += 1
    return body, i, False


# --- builders: name/options/body -> dict ready for validation -------------

def build_callout(options: dict, body: list[str]) -> dict:
    return {**options, "body": "\n".join(body).strip()}


def build_columns(options: dict, body: list[str]) -> dict:
    # Each column is parsed recursively, so blocks can live inside columns.
    columns = [parse_blocks("\n".join(group)) for group in split_top_level(body, COLUMN_BREAK)]
    return {**options, "columns": columns}


def build_gallery(options: dict, body: list[str]) -> dict:
    images = []
    for line in body:
        line = line.strip()
        if not line:
            continue
        match = IMAGE_LINE.match(line)
        if not match:
            raise ValueError(f"gallery lines must be images like ![alt](media/a.jpg), got {line!r}")
        images.append({"alt": match["alt"], "src": match["src"]})
    return {**options, "images": images}


def build_video(options: dict, body: list[str]) -> dict:
    caption = "\n".join(body).strip()
    return {**options, **({"caption": caption} if caption else {})}


def build_sprite(options: dict, body: list[str]) -> dict:
    # Indentation and blank lines are for the author's eyes only.
    return {**options, "rows": [line.strip() for line in body if line.strip()]}


def list_items(body: list[str]) -> tuple[str, list[str]] | None:
    """If the body is exactly one Markdown list, its items' sources.

    Continuation lines (indented) stay with their item, so an item can hold
    a nested list or a second paragraph. Returns None for anything else."""
    lines = [line for line in body]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return None
    style = "bullet" if BULLET_ITEM.match(lines[0]) else "number" if NUMBER_ITEM.match(lines[0]) else None
    if style is None:
        return None
    pattern = BULLET_ITEM if style == "bullet" else NUMBER_ITEM
    items: list[list[str]] = []
    for line in lines:
        match = pattern.match(line)
        if match:
            items.append([match["text"]])
        elif not line.strip() or line[:1] in (" ", "\t"):
            items[-1].append(line[2:] if line.startswith("  ") else line.strip())
        else:
            return None  # some other paragraph: treat the body as free parts
    return style, ["\n".join(item).strip() for item in items]


def build_steps(options: dict, body: list[str]) -> dict:
    parts = split_top_level(body, COLUMN_BREAK)
    if len(parts) == 1:
        found = list_items(body)
        if found:
            style, sources = found
            return {**options, "style": style, "items": [parse_blocks(source) for source in sources]}
    items = [parse_blocks("\n".join(part)) for part in parts]
    items = [item for item in items if item]
    if not items:
        raise ValueError("steps needs a list, or parts separated by +++")
    return {**options, "style": "blocks", "items": items}


def build_chart(options: dict, body: list[str]) -> dict:
    bars = []
    for line in body:
        if not line.strip():
            continue
        match = CHART_LINE.match(line.strip())
        if not match:
            raise ValueError(f"chart lines look like `Label: 42`, got {line.strip()!r}")
        bars.append({"label": match["label"].strip(), "value": float(match["value"].replace(",", "").replace("_", ""))})
    return {**options, "bars": bars}


def build_quiz(options: dict, body: list[str]) -> dict:
    question: list[str] = []
    choices: list[dict] = []
    explain: list[str] = []
    for line in body:
        match = QUIZ_OPTION.match(line)
        if match:
            if any(text.strip() for text in explain):
                raise ValueError("put all the options together, after the question")
            explain.clear()
            choices.append({"text": match["text"].strip(), "correct": match["mark"] != " "})
        elif choices:
            explain.append(line)
        else:
            question.append(line)
    if not choices:
        raise ValueError("a quiz needs options like `- [ ] wrong` and `- [x] right`")
    return {**options, "question": "\n".join(question).strip(), "options": choices,
            "explain": "\n".join(explain).strip()}


def build_qr(options: dict, body: list[str]) -> dict:
    caption = "\n".join(body).strip()
    return {**options, **({"caption": caption} if caption else {})}


BUILDERS: dict[str, Callable[[dict, list[str]], dict]] = {
    "callout": build_callout,
    "columns": build_columns,
    "gallery": build_gallery,
    "video": build_video,
    "sprite": build_sprite,
    "dialog": build_callout,  # options + a Markdown body, same shape
    "meter": build_callout,
    "steps": build_steps,
    "chart": build_chart,
    "quiz": build_quiz,
    "qr": build_qr,
}


def build_block(name: str, option_text: str, body: list[str]) -> Block:
    source = "\n".join([f":::{name} {option_text}".rstrip(), *body, ":::"])
    if name not in BUILDERS:
        known = ", ".join(sorted(BUILDERS))
        return ErrorBlock(block_name=name, message=f"unknown block type (known: {known})", source=source)
    try:
        data = BUILDERS[name](parse_options(name, option_text), body)
        return block_adapter.validate_python({**data, "type": name})
    except ValidationError as exc:
        message = "; ".join(
            (f"{'.'.join(map(str, err['loc'][1:]))}: " if err["loc"][1:] else "")
            + err["msg"].removeprefix("Value error, ")
            for err in exc.errors()
        )
        return ErrorBlock(block_name=name, message=message, source=source)
    except ValueError as exc:
        return ErrorBlock(block_name=name, message=str(exc), source=source)


def parse_blocks(source: str) -> list[Block]:
    """Turn one slide's Markdown into a list of blocks."""
    blocks: list[Block] = []
    prose: list[str] = []
    lines = source.splitlines()
    i = 0
    in_fence = False

    def flush_prose() -> None:
        text = "\n".join(prose).strip()
        if text:
            blocks.append(MarkdownBlock(source=text))
        prose.clear()

    while i < len(lines):
        line = lines[i]
        if is_fence(line):
            in_fence = not in_fence

        match = None if in_fence else OPEN.match(line)
        if not match:
            prose.append(line)
            i += 1
            continue

        flush_prose()
        name, option_text = match.group(1), match.group(2)
        body, i, closed = read_body(lines, i + 1)
        if closed:
            blocks.append(build_block(name, option_text, body))
        else:
            blocks.append(ErrorBlock(
                block_name=name,
                message="block was never closed (add a line with just :::)",
                source="\n".join([line, *body]),
            ))

    flush_prose()
    return blocks
