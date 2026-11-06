"""Starter decks for "New deck": a blank page is the hardest slide to write.

Shared by the desktop app, the mobile app (through site.py) and
`python -m slidedeck new`. Each starter uses the blocks it suits, so it
doubles as an example of them.
"""
from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Starter:
    name: str
    label: str
    description: str
    body: str  # everything after the front matter; {title} is replaced


STARTERS: dict[str, Starter] = {s.name: s for s in [
    Starter("basic", "Basic", "Two slides to start from.", """\
class: title

### New deck
# {title}

Edit this file and save it: the open slides reload on their own.

???
Speaker notes go after three question marks.

---

## A second slide

:::dialog GUIDE
Blocks start with three colons. The README lists all of them.
:::

:::meter label="Progress" value=1 max=3
:::
"""),
    Starter("talk", "Talk", "Title, agenda that builds, a chart, and a QR code to finish.", """\
class: title

### A talk
# {title}

Your name · the event · the date

???
Say who you are and why this matters, in two sentences.

---

### Today

## Three things

:::steps
1. The problem
2. What we tried
3. What worked
:::

???
Each press of Next shows one more line.

---

### The problem

## Say it in one line

:::callout warning title="Why now"
One sentence on what goes wrong today.
:::

---

### The numbers

:::chart title="Before and after" unit=minutes
Before: 42
After: 12
:::

???
The bars are a picture; screen readers get the numbers as a table.

---

class: center

### Thanks

## Questions?

:::qr https://example.com
Slides and links
:::
"""),
    Starter("lesson", "Lesson", "Goals, a guide, a quiz and a recap.", """\
class: title

### Lesson
# {title}

---

### Goals

## By the end you can

:::steps
- Say what the topic is
- Use it once on your own
- Explain it to someone else
:::

---

### Guide

:::dialog GUIDE
Here is the one idea to hold on to. Keep it short: it types itself out.
:::

---

### Check

:::quiz
Which of these is true?
- [ ] A wrong answer
- [x] The right answer
- [ ] Another wrong answer
Explain why the right answer is right. This shows once someone picks.
:::

???
Let the room answer, then press A to show the answer.

---

class: inverse

### Recap

## What we learned

:::meter label="Lesson" value=3 max=3 xp
Complete!
:::
"""),
]}

DEFAULT_STARTER = "basic"


def render(title: str, starter: str = DEFAULT_STARTER, minutes: float | None = None) -> str:
    """A ready-to-edit deck file. The title is written as a JSON string,
    which is also valid YAML, so colons and quotes in it are safe."""
    chosen = STARTERS.get(starter) or STARTERS[DEFAULT_STARTER]
    title = " ".join(title.split())[:120] or "My talk"
    front = ["---", f"title: {json.dumps(title, ensure_ascii=False)}", "theme: dmg", "lang: en"]
    if minutes is None and chosen.name == "talk":
        minutes = 20
    if minutes:
        front.append(f"duration: {minutes:g}            # minutes: the presenter view counts down")
    front.append("---")
    return "\n".join(front) + "\n" + chosen.body.replace("{title}", title)


def retitle(text: str, suffix: str = " (copy)") -> str:
    """The same deck with `suffix` added to its front matter title, so a
    duplicate is told apart in the deck list. Unchanged if it has none."""
    import yaml

    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return text
        if line.startswith("title:"):
            try:
                title = yaml.safe_load(line).get("title")
            except yaml.YAMLError:
                return text
            newline = "\n" if line.endswith("\n") else ""
            lines[i] = f"title: {json.dumps(str(title) + suffix, ensure_ascii=False)}{newline}"
            return "".join(lines)
    return text


def catalogue() -> str:
    """The starters as JSON, for the mobile app's New deck menu."""
    return json.dumps([{"name": s.name, "label": s.label, "description": s.description}
                       for s in STARTERS.values()])
