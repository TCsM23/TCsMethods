"""Slide paging.

Two number systems, kept apart on purpose:
  index  - 0-based, what the code uses: 0 .. count-1
  number - 1-based, what people see and what goes in the URL: 1 .. count

Every conversion goes through these functions, so an off-by-one bug can
only live in one place, and the tests pin that place down.
"""
from __future__ import annotations

import re


def clamp(index: int, count: int) -> int:
    """Force index into 0..count-1."""
    if count <= 0:
        raise ValueError("cannot page through a deck with no slides")
    return max(0, min(index, count - 1))


def number_to_index(number: int, count: int) -> int:
    return clamp(number - 1, count)


def index_to_number(index: int) -> int:
    return index + 1


def parse_slide_number(raw: str) -> int | None:
    """URL segment -> int, or None if it is not a whole number at all."""
    # re.ASCII matters: str.isdigit() accepts "²", which int() then rejects.
    if re.fullmatch(r"-?[0-9]{1,18}", raw.strip(), re.ASCII):
        return int(raw)
    return None
