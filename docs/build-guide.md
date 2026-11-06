# Pixel Slides Build Guide

Oct 30, 2026 · @TCsM

## How to use this guide

You will build the whole of Pixel Slides in 21 steps, typing every file yourself. Each step ends with a check (a passing test run, a command's output, or a working page) and a Git commit, so you always have a working version to return to.

Steps 1 to 10 build the **engine**: plain Python with no web server, which holds every data shape and algorithm. It splits a Markdown file into slides, reads `:::blocks`, validates them with Pydantic, checks colour contrast, and lints decks for accessibility. Steps 11 to 15 wrap that engine in a FastAPI web app: the deck library, the slide view, the Game Boy look, keyboard controls, the presenter view, and the print and text views. Steps 16 to 21 turn it into something you can hand to people: PDF export, a desktop app with a Windows install wizard, an offline mobile app, and an optional `Setup.exe`. Keeping the engine apart from the web code means you can test the algorithms on their own, and explain them in a defense without talking about web code.

Three rules hold for every step:

- **Type the code, don't paste it.** Typing is how you learn where each piece lives. Binary files (fonts, icons, the sample images) are the only exception: you copy those from the zip, and the step says so.
- **Always use `python -m`.** Your PC's Application Control blocks `pip.exe`, `pytest.exe` and other small launcher programs, but it allows `python.exe`. So it is always `python -m pip`, `python -m pytest`, `python -m slidedeck`, never the short forms.
- **Don't move on with a red check.** If a check fails, compare your file with the guide line by line. Most failures are one typo, one wrong indent, or a missing file.

If you already started the folder `slidedeck-steps/step1` (a small `models.py` and `test_parser.py`), treat it as a warm-up. This guide builds the full versions: every test from that `test_parser.py` comes back in step 9.

## What you will build

Pixel Slides turns a Markdown file into a slide deck that looks like a four-shade handheld LCD screen. You write `decks/intro.md`, open `http://127.0.0.1:8000`, and present. It has five palettes (all checked against WCAG AA by a test), pixel-art sprites typed as digits, RPG dialog boxes, HP-style meters, a presenter view with notes and a timer, a text version for screen readers, live reload, PDF export, a desktop app and an offline phone app.

**This is where you will end up** (the number is the step that creates each file):

```text
pixel-slides/
  .venv/                         your virtual environment (never committed)
  .gitignore                     1
  requirements.txt               1   the engine and web server
  requirements-desktop.txt       18  + the native window
  pyproject.toml                 1   project settings, pytest settings
  Install Pixel Slides.pyw       19  copy of the install wizard, for double-clicking
  slidedeck/
    __init__.py                  1
    themes.py                    2   palettes, WCAG contrast maths, generated CSS
    navigation.py                3   slide numbers vs indexes, clamping
    embeds.py                    4   video and media allow-list
    models.py                    5   Pydantic shapes: blocks, slides, decks
    blocks.py                    6   the ::: block lexer and builders
    render.py                    7   Markdown + Jinja2 to HTML
    lint.py                      8   accessibility checks, slide titles
    parser.py                    9   a deck file to a Deck
    __main__.py                  10  python -m slidedeck serve | check | export | app | mobile
    app.py                       11  the FastAPI web app
    pdf.py                       16  PDF export with Playwright
    site.py                      17  render a whole deck without a server
    desktop.py                   18  the desktop app
    mobile.py                    20  builds the phone app
    templates/
      blocks/                    7   one template per block type (9 files)
      base.html                  11  every page's frame
      index.html                 11  the deck library
      _slide.html                11  one slide
      deck.html                  11  the audience view
      _dialogs.html              11  slide list, options, help
      presenter.html             14  notes, next slide, timer
      print.html                 15  every slide, one per page
      text.html                  15  the whole deck as one readable page
    static/
      fonts/                     11  copied from the zip (pixel and readable fonts)
      theme.css                  12  fonts and the LCD look
      slides.css                 12  every layout
      prefs.js                   13  saved viewer preferences
      deck.js                    13  keys, paging, presenter sync
      desktop.js                 18  buttons that only the desktop app has
    mobile_shell/                20  the phone app's own pages (5 files)
  decks/
    intro.md                     10  the sample deck
    media/                       10  4 PNG files, copied from the zip
  tests/
    conftest.py                  1
    test_themes.py               2
    test_navigation.py           3
    test_blocks.py               6
    test_new_blocks.py           7
    test_parser.py               9
    test_lint.py                 10
    test_app.py                  11
    test_apps.py                 20
  packaging/
    winlink.py                   19  writes Windows shortcuts in plain Python
    install_wizard.pyw           19  the setup wizard
    uninstall.pyw                19
    after-install.txt            19
    make_icons.py                19
    icons/                       19  copied from the zip
    launch.py                    21  optional Setup.exe build
    pixel-slides.spec            21
    pixel-slides.iss             21
    build-windows.ps1            21
  .github/workflows/
    build-apps.yml               21
```

The engine files depend on each other in one direction only, so each step can be tested as soon as it is typed: `themes` and `embeds` come first, `models` uses both, `blocks` builds models, `render` draws them, `lint` reads them, `parser` uses `blocks` and `lint`, and `app` uses everything. At the end, `python -m pytest` runs **238 tests**.

## Before you start

You need four things on the PC, and two zips from the project files.

| What | Why | How to check |
| --- | --- | --- |
| Python 3.11 or newer, from python.org, with "Add python.exe to PATH" ticked | Runs everything | `python --version` |
| Git for Windows | A commit after every step | `git --version` |
| A code editor (VS Code works well) | Typing the files |  |
| Microsoft Edge | PDF export and the desktop window use it (it is already on Windows) |  |
| `pixel-slides-app.zip` from the project files | The finished code to compare with, and the binary files you copy | Unzip it next to (not inside) your project, for example into `Downloads` |

Every command in this guide is for **PowerShell**, run from inside the `pixel-slides` folder unless the step says otherwise. Paths use backslashes in commands (`decks\intro.md`) and forward slashes in code (`decks/intro.md`), because Python accepts forward slashes on Windows too.

When a step shows a file, type the whole file. Indentation is four spaces in Python. When a step's check prints something different from the guide, stop and compare before you commit.

## Part 1: the engine (steps 1 to 10)

The engine is plain Python. Nothing in Part 1 starts a web server: every step is checked with `python -m pytest` or a one-line `python -c` command.

### Step 1: Set up the project

You make the folder, a virtual environment, Git, and the five files every later step relies on.

In PowerShell, in the folder where you keep projects:

```powershell
mkdir pixel-slides
cd pixel-slides
git init
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
mkdir slidedeck, tests
```

If `Activate.ps1` is blocked, open **Command Prompt** instead of PowerShell and run `.venv\Scripts\activate.bat`. Your prompt now starts with `(.venv)`. Do this every time you open a new terminal for the project.

**`requirements.txt`** lists what the engine and web app need. Playwright is for PDF export; pytest and httpx are for the tests.

```text
fastapi>=0.110
uvicorn>=0.29
jinja2>=3.1
markdown-it-py>=3.0
pydantic>=2.6
pyyaml>=6.0
watchfiles>=0.21
playwright>=1.42
pytest>=8
httpx>=0.27
```

**`pyproject.toml`** holds the project's name and, more importantly for now, pytest's settings: where the tests are, and that the project folder is on the import path, so `import slidedeck` works in tests. The `scripts` and `package-data` parts are for the desktop app in step 18.

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "pixel-slides"
version = "0.3.0"
description = "Markdown in, handheld-console slides out."
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.110",
  "uvicorn>=0.29",
  "jinja2>=3.1",
  "markdown-it-py>=3.0",
  "pydantic>=2.6",
  "pyyaml>=6.0",
  "watchfiles>=0.21",
]

[project.scripts]
pixel-slides = "slidedeck.desktop:main"

[project.optional-dependencies]
export = ["playwright>=1.42"]
desktop = ["playwright>=1.42", "pywebview>=5.0"]
mobile = ["pillow>=10"]
dev = ["pytest>=8", "httpx>=0.27"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.setuptools.packages.find]
include = ["slidedeck*"]

[tool.setuptools.package-data]
slidedeck = ["templates/**/*.html", "static/**/*", "mobile_shell/*"]
```

**`.gitignore`** keeps the virtual environment and generated files out of Git.

```text
__pycache__/
.venv*/
build/
dist/
exports/
*.pyc
```

**`slidedeck/__init__.py`** makes `slidedeck` a package. One docstring line is enough.

```python
"""Editorial Slides: Markdown in, magazine-style slides out."""
```

**`tests/conftest.py`** runs before any test. It points the app at the sample decks folder before the app is imported (you need this from step 11).

```python
import os
from pathlib import Path

# Point the app at the sample decks before it is imported.
os.environ.setdefault("SLIDES_DECKS_DIR", str(Path(__file__).resolve().parent.parent / "decks"))
```

Now install the packages:

```powershell
python -m pip install -r requirements.txt
```

**Check:**

```powershell
python -c "import fastapi, jinja2, markdown_it, pydantic, yaml; print('ok')"
python -m pytest
```

The first prints `ok`. The second prints `no tests ran`, which is right: there are no tests yet.

**Commit:**

```powershell
git add .
git commit -m "Step 1: project setup"
```

### Step 2: Palettes and the contrast rules

You write the five palettes and the WCAG contrast maths that every palette must pass. This file comes first because everything that draws colour (the models, the CSS, the photo filter) reads it.

How it works:

- A Game Boy screen has four shades. Each `Theme` keeps four `shades` (background tone to ink tone) for sprites and photos, plus named **roles** (`paper`, `ink`, `accent`...) for the stylesheet.
- `contrast_ratio` is the WCAG 2.x formula: turn each colour into its relative luminance, then divide the lighter by the darker, each plus 0.05. Black on white is 21:1, a colour on itself is 1:1.
- `CONTRAST_RULES` lists 13 pairs (foreground role, background role, minimum). A test runs every rule on every palette, so a palette edit that makes text hard to read fails the build instead of shipping.
- `theme_css()` writes one `.theme-<name>` CSS rule per palette, so the palettes live in one place only. `lcd_table()` builds the numbers for the SVG filter that snaps photos to four shades (step 7).

**`slidedeck/themes.py`**

```python
"""Palettes, and the contrast rules every palette must pass.

A Game Boy screen has four shades. Each theme here keeps to that idea: four
`shades` (from background tone to ink tone) that sprites and the LCD photo
filter use, plus named roles (paper, ink, accent...) that the stylesheet uses.

The real DMG greens are lovely but fail WCAG for small text (dark green on
light green is about 3.3:1). So the palettes are tuned: they keep the look,
and `CONTRAST_RULES` below is checked by the test suite, so a palette edit
that makes text hard to read fails a test instead of shipping.

This module is the single source of truth: /themes.css and the SVG filters
are generated from it.
"""
from __future__ import annotations

from dataclasses import dataclass, fields

# --- WCAG 2.x contrast ------------------------------------------------------


def parse_hex(color: str) -> tuple[int, int, int]:
    value = color.removeprefix("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        raise ValueError(f"not a hex color: {color!r}")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def relative_luminance(color: str) -> float:
    def channel(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in parse_hex(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: str, b: str) -> float:
    """1.0 (identical) .. 21.0 (black on white)."""
    hi, lo = sorted((relative_luminance(a), relative_luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


# WCAG AA: 4.5:1 for body text, 3:1 for large text and UI parts (borders, icons).
AA_TEXT = 4.5
AA_LARGE = 3.0

# (foreground role, background role, minimum ratio). Accent is used for small
# labels too, so it has to meet the body-text level, not just the large one.
CONTRAST_RULES: list[tuple[str, str, float]] = [
    ("ink", "paper", AA_TEXT),
    ("muted", "paper", AA_TEXT),
    ("accent", "paper", AA_TEXT),
    ("ink", "raised", AA_TEXT),
    ("muted", "raised", AA_TEXT),
    ("accent", "raised", AA_TEXT),
    ("accent_ink", "accent", AA_TEXT),
    ("error", "paper", AA_TEXT),
    ("rule", "paper", AA_LARGE),
    ("inverse_ink", "inverse_paper", AA_TEXT),
    ("inverse_muted", "inverse_paper", AA_TEXT),
    ("inverse_accent", "inverse_paper", AA_TEXT),
    ("chrome_ink", "chrome", AA_TEXT),  # labels around the slide in the presenter view
]


# --- Themes -----------------------------------------------------------------


@dataclass(frozen=True)
class Theme:
    name: str
    label: str
    description: str
    shades: tuple[str, str, str, str]  # background tone -> ink tone
    paper: str
    raised: str
    ink: str
    muted: str
    accent: str
    accent_ink: str
    rule: str
    error: str
    inverse_paper: str
    inverse_ink: str
    inverse_muted: str
    inverse_accent: str
    chrome: str       # the area around the slide
    chrome_ink: str   # labels on that area
    lcd_grid: bool = True  # the faint pixel-grid overlay on slides

    @property
    def roles(self) -> dict[str, str]:
        skip = {"name", "label", "description", "shades", "lcd_grid"}
        return {f.name: getattr(self, f.name) for f in fields(self) if f.name not in skip}

    @property
    def shades_by_luminance(self) -> list[str]:
        """Darkest first. The photo filter maps dark pixels to dark shades,
        whatever order the theme lists them in (dark themes list light ink last)."""
        return sorted(self.shades, key=relative_luminance)


THEMES: dict[str, Theme] = {
    theme.name: theme
    for theme in [
        Theme(
            name="dmg",
            label="DMG green",
            description="The original pea-green LCD, tuned for readable contrast.",
            shades=("#c4d88a", "#8bac0f", "#306230", "#0f380f"),
            paper="#c4d88a",
            raised="#b3cb6f",
            ink="#0f380f",
            muted="#25502a",
            accent="#1d4d1f",
            accent_ink="#c4d88a",
            rule="#306230",
            error="#5a1414",
            inverse_paper="#0f380f",
            inverse_ink="#c4d88a",
            inverse_muted="#9bbc0f",
            inverse_accent="#c4d88a",
            chrome="#3d4a1c",
            chrome_ink="#c4d88a",
        ),
        Theme(
            name="pocket",
            label="Pocket grey",
            description="The grey-green screen of the slimmer handheld.",
            shades=("#dcdcc8", "#a3a38e", "#55554a", "#1e1e19"),
            paper="#dcdcc8",
            raised="#cbcbb4",
            ink="#1e1e19",
            muted="#45453c",
            accent="#3a3a32",
            accent_ink="#dcdcc8",
            rule="#55554a",
            error="#6b1d1d",
            inverse_paper="#1e1e19",
            inverse_ink="#dcdcc8",
            inverse_muted="#b4b4a0",
            inverse_accent="#dcdcc8",
            chrome="#4a4a40",
            chrome_ink="#dcdcc8",
        ),
        Theme(
            name="berry",
            label="Berry color",
            description="A colour-handheld palette: cream, berry and ink purple.",
            shades=("#fff4dc", "#f08ca0", "#a8235a", "#2a1145"),
            paper="#fff4dc",
            raised="#fde3c8",
            ink="#2a1145",
            muted="#5c2a62",
            accent="#a8235a",
            accent_ink="#fff4dc",
            rule="#a8235a",
            error="#8a1010",
            inverse_paper="#2a1145",
            inverse_ink="#fff4dc",
            inverse_muted="#f5b8c4",
            inverse_accent="#ff9cb4",
            chrome="#3c1a52",
            chrome_ink="#fff4dc",
        ),
        Theme(
            name="night",
            label="Night LCD",
            description="Dark mode: a backlit screen for dim rooms.",
            shades=("#081820", "#346856", "#88c070", "#e0f8d0"),
            paper="#081820",
            raised="#12302c",
            ink="#e0f8d0",
            muted="#a8d098",
            accent="#88c070",
            accent_ink="#081820",
            rule="#5c9a6c",
            error="#ff9b8a",
            inverse_paper="#e0f8d0",
            inverse_ink="#081820",
            inverse_muted="#2a4a3c",
            inverse_accent="#1f4d3a",
            chrome="#03090c",
            chrome_ink="#e0f8d0",
        ),
        Theme(
            name="contrast",
            label="High contrast",
            description="Black, white and yellow at maximum contrast, no screen effects.",
            shades=("#000000", "#5c5c5c", "#c8c8c8", "#ffffff"),
            paper="#000000",
            raised="#141414",
            ink="#ffffff",
            muted="#e8e8e8",
            accent="#ffe14d",
            accent_ink="#000000",
            rule="#ffffff",
            error="#ff8a80",
            inverse_paper="#ffffff",
            inverse_ink="#000000",
            inverse_muted="#1a1a1a",
            inverse_accent="#3d2fa0",
            chrome="#000000",
            chrome_ink="#ffffff",
            lcd_grid=False,
        ),
    ]
}

DEFAULT_THEME = "dmg"
THEME_NAMES = tuple(THEMES)


def contrast_failures(theme: Theme) -> list[str]:
    roles = theme.roles
    problems = []
    for fg, bg, minimum in CONTRAST_RULES:
        ratio = contrast_ratio(roles[fg], roles[bg])
        if ratio < minimum:
            problems.append(f"{theme.name}: {fg} on {bg} is {ratio:.2f}:1, needs {minimum}:1")
    return problems


# --- Generated CSS and SVG ---------------------------------------------------


def css_name(role: str) -> str:
    return role.replace("_", "-")


def theme_css() -> str:
    """One `.theme-<name>` rule per theme, defining every color token."""
    blocks = []
    for theme in THEMES.values():
        lines = [f"  --{css_name(role)}: {value};" for role, value in theme.roles.items()]
        lines += [f"  --shade-{i}: {value};" for i, value in enumerate(theme.shades)]
        lines.append(f"  --lcd-filter: url(#lcd-{theme.name});")
        lines.append(f"  --lcd-grid: {1 if theme.lcd_grid else 0};")
        blocks.append(f".theme-{theme.name} {{\n" + "\n".join(lines) + "\n}")
    return "/* Generated from slidedeck/themes.py. Edit palettes there. */\n\n" + "\n\n".join(blocks) + "\n"


def lcd_table(theme: Theme) -> dict[str, str]:
    """feComponentTransfer tables that snap a greyscale image to 4 shades.

    A 'discrete' table splits 0..1 into equal steps, so after the image is
    turned grey, each brightness band becomes one palette colour, channel
    by channel. That is the whole 'Game Boy camera' effect.
    """
    shades = [parse_hex(c) for c in theme.shades_by_luminance]
    return {
        channel: " ".join(f"{shade[i] / 255:.3f}" for shade in shades)
        for i, channel in enumerate("RGB")
    }
```

**`tests/test_themes.py`** pins the maths with known answers (black on white is exactly 21), then checks every shipped palette.

```python
import pytest

from slidedeck.themes import (
    CONTRAST_RULES, THEMES, contrast_failures, contrast_ratio, lcd_table, parse_hex, theme_css,
)


# --- the contrast maths ----------------------------------------------------

def test_black_on_white_is_21():
    assert contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0)


def test_same_colour_is_1():
    assert contrast_ratio("#9bbc0f", "#9bbc0f") == pytest.approx(1.0)


def test_ratio_is_symmetric():
    assert contrast_ratio("#0f380f", "#c4d88a") == contrast_ratio("#c4d88a", "#0f380f")


def test_short_hex_expands():
    assert parse_hex("#fff") == (255, 255, 255)


@pytest.mark.parametrize("bad", ["#12345", "red", "#gggggg"])
def test_bad_hex_raises(bad):
    with pytest.raises(ValueError):
        parse_hex(bad)


def test_the_original_handheld_greens_would_fail():
    # Why the palettes are tuned: authentic DMG mid-green on light green
    # is too faint for small text.
    assert contrast_ratio("#306230", "#9bbc0f") < 4.5


# --- every shipped palette -------------------------------------------------

@pytest.mark.parametrize("name", list(THEMES))
def test_palette_meets_wcag_aa(name):
    assert contrast_failures(THEMES[name]) == []


@pytest.mark.parametrize("name", list(THEMES))
def test_palette_has_four_distinct_shades(name):
    shades = THEMES[name].shades
    assert len(shades) == 4
    assert len(set(shades)) == 4


@pytest.mark.parametrize("name", list(THEMES))
def test_ink_shade_stands_out_from_background_shade(name):
    # Sprites draw shade 3 on the slide paper, so it must be visible there.
    theme = THEMES[name]
    assert contrast_ratio(theme.shades[3], theme.paper) >= 3


def test_rules_only_name_real_roles():
    roles = next(iter(THEMES.values())).roles
    for fg, bg, _ in CONTRAST_RULES:
        assert fg in roles and bg in roles


def test_high_contrast_theme_turns_off_the_lcd_grid():
    assert THEMES["contrast"].lcd_grid is False


# --- generated CSS and filters -------------------------------------------------

def test_css_defines_every_theme_and_token():
    css = theme_css()
    for name in THEMES:
        assert f".theme-{name} {{" in css
        assert f"--lcd-filter: url(#lcd-{name});" in css
    assert "--inverse-paper:" in css and "--shade-3:" in css
    assert "_" not in css.split("*/", 1)[1]  # snake_case roles become kebab-case


def test_lcd_table_runs_dark_to_light_even_for_dark_themes():
    # Night lists its shades background-first, which is darkest-first...
    table = lcd_table(THEMES["night"])
    reds = [float(v) for v in table["R"].split()]
    assert len(reds) == 4
    # ...and the filter must map dark pixels to the darkest shade regardless.
    assert reds[0] == pytest.approx(0x08 / 255, abs=1e-3)
    assert reds[-1] == pytest.approx(0xE0 / 255, abs=1e-3)


def test_lcd_table_for_light_theme_starts_with_ink():
    reds = [float(v) for v in lcd_table(THEMES["dmg"])["R"].split()]
    assert reds[0] == pytest.approx(0x0F / 255, abs=1e-3)
```

**Check:**

```powershell
python -m pytest tests/test_themes.py
```

You should see `28 passed`.

**Commit:**

```powershell
git add .
git commit -m "Step 2: palettes and WCAG contrast rules"
```

### Step 3: Slide numbers and paging

You write the four small functions that turn "slide 7" in a URL into a position in a list, and back. Off-by-one bugs love this spot, so it gets its own module and a test for every edge.

How it works:

- Two number systems are kept apart on purpose. An **index** counts from 0 and is what the code uses. A **number** counts from 1 and is what people see and what goes in the URL.
- `clamp` forces any index into `0 .. count-1`, so `/deck/intro/99` can be redirected to the last slide instead of crashing.
- `parse_slide_number` uses a regular expression with `re.ASCII`, because `str.isdigit()` accepts characters like `²` that `int()` then rejects. It also caps the length at 18 digits.

**`slidedeck/navigation.py`**

```python
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
```

**`tests/test_navigation.py`**

```python
"""Paging edge cases. Off-by-one bugs live here, so pin every boundary."""
import pytest

from slidedeck.navigation import clamp, index_to_number, number_to_index, parse_slide_number


@pytest.mark.parametrize(
    ("index", "count", "expected"),
    [
        (0, 5, 0),        # first
        (4, 5, 4),        # last
        (5, 5, 4),        # one past the end -> last
        (-1, 5, 0),       # one before the start -> first
        (99, 5, 4),       # way past
        (-99, 5, 0),      # way before
        (0, 1, 0),        # single-slide deck
        (3, 1, 0),
        (-3, 1, 0),
        (10**18, 12, 11), # absurd URL number
    ],
)
def test_clamp_boundaries(index, count, expected):
    assert clamp(index, count) == expected


def test_clamp_never_leaves_range():
    for count in range(1, 8):
        for index in range(-10, 20):
            assert 0 <= clamp(index, count) <= count - 1


def test_clamp_is_identity_inside_range():
    assert [clamp(i, 6) for i in range(6)] == list(range(6))


@pytest.mark.parametrize("count", [0, -1])
def test_clamp_rejects_empty_deck(count):
    with pytest.raises(ValueError):
        clamp(0, count)


def test_rapid_input_settles_at_the_edge():
    """Twenty quick presses of Next on a 5-slide deck stop at the last slide."""
    index = 0
    for _ in range(20):
        index = clamp(index + 1, 5)
    assert index == 4
    for _ in range(20):
        index = clamp(index - 1, 5)
    assert index == 0


@pytest.mark.parametrize(
    ("number", "count", "expected_index"),
    [(1, 5, 0), (5, 5, 4), (6, 5, 4), (0, 5, 0), (-2, 5, 0), (99, 12, 11)],
)
def test_url_number_to_index(number, count, expected_index):
    assert number_to_index(number, count) == expected_index


def test_round_trip_number_index():
    for number in range(1, 13):
        assert index_to_number(number_to_index(number, 12)) == number


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("1", 1), ("12", 12), ("-3", -3), ("007", 7), (" 4 ", 4),
     ("abc", None), ("", None), ("-", None), ("1.5", None), ("3a", None),
     ("²", None), ("--2", None), ("9" * 40, None)],
)
def test_parse_slide_number(raw, expected):
    assert parse_slide_number(raw) == expected
```

**Check:** `python -m pytest tests/test_navigation.py` shows `35 passed`.

**Commit:** `git add .` then `git commit -m "Step 3: slide numbers and paging"`

### Step 4: The video and media allow-list

You write the security rule for anything a deck embeds. A deck is text someone else may have written, so a video URL is never copied into the page as it is.

How it works:

- `resolve_video` parses the URL, pulls out only the video ID, checks the ID against a strict pattern, and builds the embed URL itself from a fixed template. Only YouTube (through the privacy-friendly `youtube-nocookie.com`), Vimeo and local `media/` files are allowed.
- `safe_media_path` accepts only plain paths inside `media/`, so `media/../app.py` or `/etc/passwd` are refused. It can also limit file types.
- Step 11 adds the second half of this rule: a Content-Security-Policy header that tells the browser to load frames only from those two hosts.

**`slidedeck/embeds.py`**

```python
"""Video allow-list.

The rule: never put the author's URL into the page. Parse it, pull out the
one piece we need (a video ID), check that piece against a strict pattern,
and build the embed URL ourselves from a hard-coded template.
"""
from __future__ import annotations

import re
from pathlib import PurePosixPath
from urllib.parse import parse_qs, urlparse

YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
VIMEO_ID = re.compile(r"^[0-9]{1,12}$")
LOCAL_VIDEO_EXTENSIONS = {".mp4", ".webm"}

YOUTUBE_HOSTS = {"youtube.com", "m.youtube.com", "youtu.be"}
VIMEO_HOSTS = {"vimeo.com", "player.vimeo.com"}


def resolve_video(src: str) -> tuple[str, str]:
    """Return (provider, embed_url) or raise ValueError if not allowed."""
    src = src.strip()

    if src.startswith("media/"):
        return "local", "/" + safe_media_path(src, LOCAL_VIDEO_EXTENSIONS)

    url = urlparse(src)
    if url.scheme != "https":
        raise ValueError("video URL must use https (or be a media/ file)")

    host = (url.hostname or "").lower().removeprefix("www.")
    parts = [p for p in url.path.split("/") if p]

    if host in YOUTUBE_HOSTS:
        if host == "youtu.be":
            video_id = parts[0] if parts else ""
        elif parts[:1] == ["watch"]:
            video_id = parse_qs(url.query).get("v", [""])[0]
        elif parts[:1] in (["embed"], ["shorts"]) and len(parts) > 1:
            video_id = parts[1]
        else:
            video_id = ""
        if not YOUTUBE_ID.match(video_id):
            raise ValueError("could not find a valid YouTube video ID")
        return "youtube", f"https://www.youtube-nocookie.com/embed/{video_id}"

    if host in VIMEO_HOSTS:
        video_id = parts[-1] if parts else ""
        if not VIMEO_ID.match(video_id):
            raise ValueError("could not find a valid Vimeo video ID")
        return "vimeo", f"https://player.vimeo.com/video/{video_id}"

    raise ValueError(f"video provider not allowed: {host or src!r}")


def safe_media_path(src: str, allowed_extensions: set[str] | None = None) -> str:
    """Accept only plain paths inside media/, e.g. media/photo.jpg."""
    path = PurePosixPath(src)
    if path.is_absolute() or ".." in path.parts or path.parts[:1] != ("media",):
        raise ValueError("media paths must stay inside media/")
    if len(path.parts) < 2:
        raise ValueError("media path is missing a file name")
    if allowed_extensions and path.suffix.lower() not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise ValueError(f"file type not allowed here (use {allowed})")
    return str(path)
```

**Check:** the full tests for this file come in step 6, with the blocks that use it. For now, try it by hand:

```powershell
python -c "from slidedeck.embeds import resolve_video; print(resolve_video('https://youtu.be/dQw4w9WgXcQ'))"
```

It prints `('youtube', 'https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ')`. Try `'https://evil.example.com/x'` too: you get a `ValueError` that says the provider is not allowed.

**Commit:** `git add .` then `git commit -m "Step 4: video and media allow-list"`

### Step 5: The data shapes

You describe, with Pydantic, every shape a deck can take: eight block types, a slide, and a deck. From here on, nothing invalid gets past this file.

How it works:

- Each block type is its own model with a literal `type` field (`"callout"`, `"sprite"`...). `Block` is a **discriminated union**: Pydantic reads `type` first and validates against exactly one model, so an error points at the right field instead of saying "none of 9 models matched".
- `ColumnsBlock` holds lists of blocks, so it refers to `Block` before `Block` exists. `ColumnsBlock.model_rebuild()` at the end fixes that forward reference.
- Validators carry the rules: a sprite's rows must be the same width and use only `0-3` and `.`; a meter's value must sit between 0 and max; a video is resolved through step 4's allow-list; a deck's theme must be one of step 2's palettes.
- `SpriteBlock.runs` merges neighbouring pixels of the same shade into one rectangle, so a 16-pixel row of one colour becomes one SVG `<rect>`, not sixteen.
- `filled_segments` decides how many of a meter's 20 segments light up. Any value above 0 lights at least one, so "almost empty" never looks "empty".

**`slidedeck/models.py`**

```python
"""Data shapes for a deck.

Each block type is its own Pydantic model with a literal `type` field.
`Block` is a discriminated union: Pydantic reads `type` first, then
validates against exactly one model, so error messages point at the
right fields instead of "none of 6 models matched".
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from .embeds import resolve_video, safe_media_path
from .themes import DEFAULT_THEME, THEMES

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".avif"}
CAPTION_EXTENSIONS = {".vtt"}
SPRITE_PALETTE = "0123"  # 0 = background tone ... 3 = ink tone
SPRITE_EMPTY = "."
SPRITE_MAX_SIDE = 64
METER_SEGMENTS = 20


class MarkdownBlock(BaseModel):
    type: Literal["markdown"] = "markdown"
    source: str


class CalloutBlock(BaseModel):
    type: Literal["callout"]
    variant: Literal["note", "warning", "quote", "stat"] = "note"
    title: str | None = None
    cite: str | None = None
    body: str = ""


class ColumnsBlock(BaseModel):
    type: Literal["columns"]
    layout: Literal["two", "sidebar", "split", "three"] = "two"
    # A column is a list of blocks, so columns can hold callouts, galleries...
    columns: list[list["Block"]]

    @model_validator(mode="after")
    def check_column_count(self) -> "ColumnsBlock":
        expected = 3 if self.layout == "three" else 2
        if len(self.columns) != expected:
            raise ValueError(
                f"layout '{self.layout}' needs {expected} columns separated by +++, "
                f"got {len(self.columns)}"
            )
        return self


class GalleryImage(BaseModel):
    src: str
    alt: str = ""

    @field_validator("src")
    @classmethod
    def check_src(cls, src: str) -> str:
        if src.startswith("https://"):
            return src
        return "/" + safe_media_path(src, IMAGE_EXTENSIONS)


class GalleryBlock(BaseModel):
    type: Literal["gallery"]
    variant: Literal["grid", "carousel"] = "grid"
    # lcd: snap photos to the theme's four shades, like a handheld camera.
    filter: Literal["lcd", "none"] = "lcd"
    caption: str | None = None
    images: list[GalleryImage] = Field(min_length=1)


class VideoBlock(BaseModel):
    type: Literal["video"]
    src: str
    # No default on purpose: "Video" tells a screen reader user nothing,
    # so the linter asks for a real title.
    title: str | None = None
    captions: str | None = None
    caption: str | None = None
    # Filled in by the validator below, never by the deck author.
    provider: Literal["youtube", "vimeo", "local"] | None = None
    embed_url: str = ""

    @model_validator(mode="after")
    def resolve(self) -> "VideoBlock":
        self.provider, self.embed_url = resolve_video(self.src)
        if self.captions is not None:
            if self.provider != "local":
                raise ValueError("captions= only works for media/ videos (YouTube and Vimeo carry their own)")
            self.captions = "/" + safe_media_path(self.captions, CAPTION_EXTENSIONS)
        return self


class SpriteRun(BaseModel):
    """A horizontal run of same-shade pixels: one <rect> instead of many."""
    x: int
    y: int
    width: int
    shade: int


class SpriteBlock(BaseModel):
    """Pixel art typed straight into the deck, one character per pixel.

        :::sprite alt="A heart" scale=12
        .33.33.
        3223223
        .32223.
        ..323..
        ...3...
        :::

    Digits pick one of the theme's four shades, so sprites recolour with the
    theme. A dot is a transparent pixel.
    """
    type: Literal["sprite"]
    alt: str = Field(min_length=1)
    scale: int = Field(default=12, ge=2, le=32)
    caption: str | None = None
    rows: list[str]

    @field_validator("alt")
    @classmethod
    def alt_is_not_blank(cls, alt: str) -> str:
        if not alt.strip():
            raise ValueError("a sprite needs alt text that describes it")
        return alt.strip()

    @field_validator("rows")
    @classmethod
    def check_rows(cls, rows: list[str]) -> list[str]:
        if not rows:
            raise ValueError("a sprite needs at least one row of pixels")
        width = len(rows[0])
        allowed = set(SPRITE_PALETTE + SPRITE_EMPTY)
        for number, row in enumerate(rows, start=1):
            if len(row) != width:
                raise ValueError(f"row {number} is {len(row)} pixels wide, row 1 is {width}")
            bad = sorted(set(row) - allowed)
            if bad:
                raise ValueError(f"row {number} has {''.join(bad)!r}; use 0-3 for shades and . for empty")
        if width > SPRITE_MAX_SIDE or len(rows) > SPRITE_MAX_SIDE:
            raise ValueError(f"sprites can be at most {SPRITE_MAX_SIDE}x{SPRITE_MAX_SIDE} pixels")
        return rows

    @property
    def width(self) -> int:
        return len(self.rows[0])

    @property
    def height(self) -> int:
        return len(self.rows)

    @property
    def runs(self) -> list[SpriteRun]:
        runs: list[SpriteRun] = []
        for y, row in enumerate(self.rows):
            x = 0
            while x < len(row):
                char = row[x]
                end = x
                while end < len(row) and row[end] == char:
                    end += 1
                if char != SPRITE_EMPTY:
                    runs.append(SpriteRun(x=x, y=y, width=end - x, shade=int(char)))
                x = end
        return runs


class DialogBlock(BaseModel):
    """An RPG text box. The text types itself out on screen (unless the
    viewer asked for reduced motion); screen readers get it all at once."""
    type: Literal["dialog"]
    speaker: str | None = None
    body: str = Field(min_length=1)


def filled_segments(value: float, maximum: float, segments: int = METER_SEGMENTS) -> int:
    """How many bar segments to light for value out of maximum.

    Edge cases are the point: 0 lights none, a full value lights all, and any
    value above 0 lights at least one, so "almost empty" never looks "empty".
    """
    if segments <= 0 or maximum <= 0:
        raise ValueError("segments and maximum must be positive")
    if value <= 0:
        return 0
    if value >= maximum:
        return segments
    return min(segments - 1, max(1, round(value / maximum * segments)))


class MeterBlock(BaseModel):
    """An HP/XP style bar: `:::meter label="Tests passing" value=96 max=100`."""
    type: Literal["meter"]
    label: str = Field(min_length=1)
    value: float
    max: float = Field(default=100, gt=0)
    variant: Literal["hp", "xp"] = "hp"
    unit: str = ""
    body: str = ""

    @model_validator(mode="after")
    def value_in_range(self) -> "MeterBlock":
        if not 0 <= self.value <= self.max:
            raise ValueError(f"value must be between 0 and max ({self.max:g}), got {self.value:g}")
        return self

    @property
    def filled(self) -> int:
        return filled_segments(self.value, self.max)

    @property
    def segments(self) -> int:
        return METER_SEGMENTS

    @property
    def value_text(self) -> str:
        unit = f" {self.unit}" if self.unit else ""
        return f"{self.value:g}{unit} of {self.max:g}{unit}"


class ErrorBlock(BaseModel):
    """Shown in place of a block that failed to parse or validate."""
    type: Literal["error"] = "error"
    block_name: str
    message: str
    source: str = ""


Block = Annotated[
    Union[MarkdownBlock, CalloutBlock, ColumnsBlock, GalleryBlock, VideoBlock,
          SpriteBlock, DialogBlock, MeterBlock, ErrorBlock],
    Field(discriminator="type"),
]

# ColumnsBlock refers to Block before Block existed; resolve that now.
ColumnsBlock.model_rebuild()

SlideClass = Literal["title", "feature", "center", "inverse"]


class Slide(BaseModel):
    index: int
    source: str
    blocks: list[Block] = []
    notes: str = ""
    css_class: SlideClass | None = None
    # Plain text of the slide's main heading: used for announcements,
    # the outline, the text view and the browser tab title.
    title: str = ""


class Deck(BaseModel):
    title: str = "Untitled deck"
    author: str | None = None
    theme: str = DEFAULT_THEME
    # The language of the deck's text, so screen readers pronounce it right.
    lang: str = Field(default="en", pattern=r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$")
    # Show the start-up screen when the deck opens.
    boot: bool = False
    slides: list[Slide]

    @field_validator("theme")
    @classmethod
    def known_theme(cls, theme: str) -> str:
        if theme not in THEMES:
            raise ValueError(f"unknown theme {theme!r} (use {', '.join(THEMES)})")
        return theme
```

**Check:** the block tests come with the lexer in step 6. For now, check the meter maths by hand:

```powershell
python -c "from slidedeck.models import filled_segments; print(filled_segments(0, 100), filled_segments(1, 100), filled_segments(100, 100))"
```

It prints `0 1 20`: empty lights nothing, 1 out of 100 still lights one segment, and full lights all 20.

**Commit:** `git add .` then `git commit -m "Step 5: Pydantic models for blocks, slides and decks"`

### Step 6: The block lexer

You write the code that finds `:::name options` ... `:::` blocks inside a slide and turns each into one of step 5's models. This is the heart of the engine.

How it works, as a four-stage pipeline for each block:

1. **Lex:** find the opening line with the `OPEN` regular expression, read the name and options, and collect the body up to the matching `:::`. `read_body` counts nested `:::` pairs, so a callout inside columns closes in the right place.
2. **Build:** a small function per block type (`BUILDERS`) turns name, options and body into a plain dict. Columns call `parse_blocks` again on each column, which is recursion.
3. **Validate:** the dict goes to Pydantic through a `TypeAdapter` for the `Block` union.
4. **Render:** done later, in step 7.

Two details matter in a defense. First, `parse_options` uses `shlex.split`, the same rules as a shell, so `title="Heads up"` keeps its space. Second, **nothing raises out of `build_block`**: any error becomes an `ErrorBlock`, so one typo shows a visible error card on that slide instead of crashing the whole deck. Code fences are tracked everywhere, so a `:::` inside a code example stays code.

**`slidedeck/blocks.py`** (the longest file in Part 1, take it slowly)

````python
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

# The first bare word after the block name fills this field,
# so `:::callout warning` means variant=warning.
POSITIONAL = {"callout": "variant", "columns": "layout", "gallery": "variant", "video": "src",
              "meter": "variant", "dialog": "speaker"}

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


BUILDERS: dict[str, Callable[[dict, list[str]], dict]] = {
    "callout": build_callout,
    "columns": build_columns,
    "gallery": build_gallery,
    "video": build_video,
    "sprite": build_sprite,
    "dialog": build_callout,  # options + a Markdown body, same shape
    "meter": build_callout,
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
````

**`tests/test_blocks.py`** tests the lexer, each builder, and the video allow-list from step 4. Notice how many tests check that bad input becomes an `error` block rather than an exception.

````python
import pytest

from slidedeck.blocks import parse_blocks
from slidedeck.embeds import resolve_video


def only(source):
    blocks = parse_blocks(source)
    assert len(blocks) == 1, blocks
    return blocks[0]


# --- the lexer -------------------------------------------------------------

def test_prose_and_blocks_interleave():
    blocks = parse_blocks("# Hi\n\n:::callout\nBody\n:::\n\nAfter")
    assert [b.type for b in blocks] == ["markdown", "callout", "markdown"]


def test_block_inside_code_fence_is_just_code():
    block = only("```\n:::callout\nnot a block\n:::\n```")
    assert block.type == "markdown"


def test_unclosed_block_is_an_error_card():
    block = only(":::callout\nforgot to close")
    assert block.type == "error"
    assert "never closed" in block.message


def test_unknown_block_type():
    block = only(":::sparkles\nhi\n:::")
    assert block.type == "error"
    assert "unknown block type" in block.message


def test_bad_option_syntax():
    block = only(':::callout title="unclosed\nhi\n:::')
    assert block.type == "error"


# --- callout -----------------------------------------------------------------

def test_callout_positional_variant_and_quoted_title():
    block = only(':::callout warning title="Heads up"\nBe **careful**.\n:::')
    assert (block.type, block.variant, block.title) == ("callout", "warning", "Heads up")
    assert block.body == "Be **careful**."


def test_callout_defaults_to_note():
    assert only(":::callout\nx\n:::").variant == "note"


def test_callout_rejects_unknown_variant():
    block = only(":::callout shout\nx\n:::")
    assert block.type == "error"
    assert "variant" in block.message


# --- columns ---------------------------------------------------------------

def test_columns_split_and_parse_recursively():
    block = only(":::columns two\n# Left\n+++\n:::callout stat title=42\nAnswer\n:::\n:::")
    assert block.type == "columns"
    left, right = block.columns
    assert left[0].type == "markdown"
    assert right[0].type == "callout" and right[0].title == "42"


def test_column_break_inside_nested_block_does_not_split():
    block = only(":::columns two\nA\n+++\n:::callout\nx\n+++\ny\n:::\n:::")
    assert block.type == "columns"
    assert "+++" in block.columns[1][0].body


def test_columns_count_must_match_layout():
    block = only(":::columns three\nA\n+++\nB\n:::")
    assert block.type == "error"
    assert "needs 3 columns" in block.message


# --- gallery ---------------------------------------------------------------

def test_gallery_reads_image_lines():
    block = only(":::gallery carousel\n![One](media/a.jpg)\n\n![Two](https://example.com/b.png)\n:::")
    assert block.variant == "carousel"
    assert [i.src for i in block.images] == ["/media/a.jpg", "https://example.com/b.png"]
    assert block.images[0].alt == "One"


@pytest.mark.parametrize("src", ["media/../app.py", "/etc/passwd", "http://example.com/a.jpg",
                                 "javascript:alert(1)", "media/notes.txt", "uploads/a.jpg"])
def test_gallery_rejects_unsafe_sources(src):
    assert only(f":::gallery\n![x]({src})\n:::").type == "error"


def test_gallery_rejects_non_image_lines():
    assert only(":::gallery\njust some text\n:::").type == "error"


def test_empty_gallery_is_an_error():
    assert only(":::gallery\n:::").type == "error"


# --- video allow-list ------------------------------------------------------

@pytest.mark.parametrize(
    ("src", "provider", "embed"),
    [
        ("https://www.youtube.com/watch?v=aqz-KE-bpKQ", "youtube", "https://www.youtube-nocookie.com/embed/aqz-KE-bpKQ"),
        ("https://youtu.be/aqz-KE-bpKQ", "youtube", "https://www.youtube-nocookie.com/embed/aqz-KE-bpKQ"),
        ("https://youtube.com/shorts/aqz-KE-bpKQ", "youtube", "https://www.youtube-nocookie.com/embed/aqz-KE-bpKQ"),
        ("https://vimeo.com/76979871", "vimeo", "https://player.vimeo.com/video/76979871"),
        ("media/intro.mp4", "local", "/media/intro.mp4"),
    ],
)
def test_allowed_videos(src, provider, embed):
    assert resolve_video(src) == (provider, embed)


@pytest.mark.parametrize(
    "src",
    [
        "https://evil.example.com/clip.mp4",
        "http://www.youtube.com/watch?v=aqz-KE-bpKQ",           # not https
        "https://youtube.com.evil.example/watch?v=aqz-KE-bpKQ",  # lookalike host
        "https://www.youtube.com/watch?v=x\"onload=alert(1)",    # bad ID
        "https://www.youtube.com/watch?v=short",
        "https://vimeo.com/not-a-number",
        "javascript:alert(1)",
        "media/../../secret.mp4",
        "media/clip.exe",
    ],
)
def test_rejected_videos(src):
    with pytest.raises(ValueError):
        resolve_video(src)


def test_video_block_url_with_equals_sign_is_positional():
    block = only(":::video https://www.youtube.com/watch?v=aqz-KE-bpKQ title=Demo\n:::")
    assert block.type == "video"
    assert block.embed_url.endswith("/aqz-KE-bpKQ")
    assert block.title == "Demo"


def test_video_block_error_for_unknown_provider():
    block = only(":::video https://evil.example.com/a.mp4\n:::")
    assert block.type == "error"
    assert "not allowed" in block.message
````

**Check:** `python -m pytest tests/test_blocks.py` shows `36 passed`.

**Commit:** `git add .` then `git commit -m "Step 6: block lexer and builders"`

### Step 7: Rendering blocks to HTML

You turn each block into HTML with markdown-it-py and one Jinja2 template per block type. After this step the engine can draw any slide, even though there is no web page to show it in yet.

How it works:

- `markdown` is configured with `html: False`, so raw HTML typed into a deck is **escaped**, never run. A deck cannot inject a `<script>`.
- Jinja2's `autoescape` escapes every `{{ value }}` too. Only text that went through the `md` filter is marked safe, with `Markup`.
- `render_block(block, mode)` picks `templates/blocks/<type>.html`. The `mode` is `screen`, `print` or `text`, and templates change with it: a carousel becomes a grid when printed, a video becomes a link in the text view.
- No template uses `style="..."`. Step 11's security policy forbids inline styles, so sizes and colours are classes and SVG attributes.
- `site_url` and the `base` and `desktop` globals do nothing yet (base is empty, desktop is `None`). The phone app in step 20 and the desktop app in step 18 switch them on. Typing them now saves editing this file twice.

**`slidedeck/render.py`**

```python
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
```

Now the nine block templates. Make the folder first with `mkdir slidedeck\templates\blocks`. Class names follow the project's pattern `slide-<block>-<part>`.

**`slidedeck/templates/blocks/markdown.html`**

```html
<div class="slide-prose-body">{{ block.source | md }}</div>
```

**`slidedeck/templates/blocks/callout.html`** has four looks. Notes and warnings get `role="note"` so screen readers announce them.

```html
<div class="slide-callout-card slide-callout-card--{{ block.variant }}"{% if block.variant in ("note", "warning") %} role="note"{% if block.title %} aria-label="{{ block.variant }}: {{ block.title }}"{% endif %}{% endif %}>
{% if block.variant == "stat" %}
  <p class="slide-callout-card-figure">{{ block.title or "" }}</p>
  <div class="slide-callout-card-body">{{ block.body | md }}</div>
{% elif block.variant == "quote" %}
  <blockquote class="slide-callout-card-quote">{{ block.body | md }}</blockquote>
  {% if block.cite %}<p class="slide-callout-card-cite">{{ block.cite }}</p>{% endif %}
{% else %}
  <p class="slide-callout-card-header">
    <span class="slide-callout-card-label"><span class="slide-callout-card-icon" aria-hidden="true">{{ "!" if block.variant == "warning" else "i" }}</span>{{ block.variant }}</span>
    {% if block.title %}<span class="slide-callout-card-title">{{ block.title | md_inline }}</span>{% endif %}
  </p>
  <div class="slide-callout-card-body">{{ block.body | md }}</div>
{% endif %}
</div>
```

**`slidedeck/templates/blocks/columns.html`** calls `render_block` again for each child, the template side of step 6's recursion.

```html
<div class="slide-columns-grid slide-columns-grid--{{ block.layout }}">
{% for column in block.columns %}
  <div class="slide-columns-grid-cell">
  {% for child in column %}
    {{ render_block(child, mode) }}
  {% endfor %}
  </div>
{% endfor %}
</div>
```

**`slidedeck/templates/blocks/gallery.html`**

```html
{% set variant = "carousel" if block.variant == "carousel" and mode == "screen" else "grid" %}
<figure class="slide-gallery-frame slide-gallery-frame--{{ variant }}" data-filter="{{ block.filter }}"
        {% if variant == "carousel" %}data-carousel role="group" aria-roledescription="carousel" aria-label="{{ block.caption or 'Image carousel' }}"{% endif %}>
  <div class="slide-gallery-{{ variant }}-track">
  {% for image in block.images %}
    <div class="slide-gallery-{{ variant }}-item"{% if variant == "carousel" %} role="group" aria-roledescription="slide" aria-label="{{ loop.index }} of {{ block.images | length }}"{% endif %}>
      <img class="slide-gallery-{{ variant }}-image" src="{{ image.src | url }}" alt="{{ image.alt }}"
           loading="{{ 'lazy' if mode == 'screen' else 'eager' }}" decoding="async">
    </div>
  {% endfor %}
  </div>
  {% if variant == "carousel" %}
  <div class="slide-gallery-carousel-controls">
    <button type="button" class="slide-gallery-carousel-button" data-carousel-step="-1" aria-label="Previous image">&#9664;</button>
    <span class="slide-gallery-carousel-counter" data-carousel-counter aria-live="polite">1 / {{ block.images | length }}</span>
    <button type="button" class="slide-gallery-carousel-button" data-carousel-step="1" aria-label="Next image">&#9654;</button>
  </div>
  {% endif %}
  {% if block.caption %}<figcaption class="slide-gallery-frame-caption">{{ block.caption | md_inline }}</figcaption>{% endif %}
</figure>
```

**`slidedeck/templates/blocks/video.html`** has a different output for each mode: a placeholder when printed, a link in the text view, a `<video>` for local files, and an `<iframe>` for YouTube and Vimeo.

```html
{% set title = block.title or "Video" %}
<figure class="slide-video-frame">
{% if mode == "print" %}
  <div class="slide-video-frame-placeholder">
    <span class="slide-video-frame-icon" aria-hidden="true">&#9654;</span>
    <span class="slide-video-frame-title">{{ title }}</span>
    <span class="slide-video-frame-source">{{ block.embed_url }}</span>
  </div>
{% elif mode == "text" %}
  <p class="slide-video-frame-link"><a href="{{ block.embed_url | url }}">Watch the video: {{ title }}</a>{% if block.captions %} (<a href="{{ block.captions | url }}">captions</a>){% endif %}</p>
{% elif block.provider == "local" %}
  <video class="slide-video-frame-player" src="{{ block.embed_url | url }}" controls preload="metadata" aria-label="{{ title }}"{% if block.captions %} crossorigin="anonymous"{% endif %}>
    {% if block.captions %}<track kind="captions" src="{{ block.captions | url }}" label="Captions" default>{% endif %}
  </video>
{% else %}
  <iframe class="slide-video-frame-player" src="{{ block.embed_url }}" title="{{ title }}" loading="lazy"
          allow="accelerometer; encrypted-media; gyroscope; picture-in-picture; fullscreen"
          referrerpolicy="strict-origin-when-cross-origin"></iframe>
{% endif %}
{% if block.caption %}<figcaption class="slide-video-frame-caption">{{ block.caption | md_inline }}</figcaption>{% endif %}
</figure>
```

**`slidedeck/templates/blocks/sprite.html`** draws each run from step 5 as one SVG rectangle. `crispEdges` keeps the pixels sharp when scaled.

```html
<figure class="slide-sprite-frame">
  <svg class="slide-sprite-frame-art" role="img" aria-label="{{ block.alt }}"
       viewBox="0 0 {{ block.width }} {{ block.height }}"
       width="{{ block.width * block.scale }}" height="{{ block.height * block.scale }}"
       shape-rendering="crispEdges">
    {% for run in block.runs %}<rect class="slide-sprite-frame-pixel slide-sprite-frame-pixel--{{ run.shade }}" x="{{ run.x }}" y="{{ run.y }}" width="{{ run.width }}" height="1"/>{% endfor %}
  </svg>
  {% if block.caption %}<figcaption class="slide-sprite-frame-caption">{{ block.caption | md_inline }}</figcaption>
  {% elif mode == "text" %}<figcaption class="slide-sprite-frame-caption">{{ block.alt }}</figcaption>{% endif %}
</figure>
```

**`slidedeck/templates/blocks/dialog.html`**

```html
<div class="slide-dialog-box"{% if mode == "screen" %} data-typewriter{% endif %}>
  {% if block.speaker %}<p class="slide-dialog-box-speaker">{{ block.speaker }}</p>{% endif %}
  {# The real text stays in the page for screen readers and search; the
     typewriter animates an aria-hidden copy that deck.js fills in. #}
  <div class="slide-dialog-box-body" data-typewriter-source>{{ block.body | md }}</div>
  <span class="slide-dialog-box-cursor" aria-hidden="true">&#9660;</span>
</div>
```

**`slidedeck/templates/blocks/meter.html`** uses `role="meter"` with a spoken value like "3 cups of 10 cups", and hides the visual numbers from screen readers so they are not read twice.

```html
<div class="slide-meter-bar slide-meter-bar--{{ block.variant }}">
  <p class="slide-meter-bar-label" aria-hidden="true">{{ block.label }}</p>
  <div class="slide-meter-bar-track" role="meter"
       aria-label="{{ block.label }}"
       aria-valuemin="0" aria-valuemax="{{ block.max }}" aria-valuenow="{{ block.value }}" aria-valuetext="{{ block.value_text }}">
    {% for i in range(block.segments) %}<span class="slide-meter-bar-segment{% if i < block.filled %} is-filled{% endif %}"></span>{% endfor %}
  </div>
  <p class="slide-meter-bar-value" aria-hidden="true">{{ "%g" | format(block.value) }}<span class="slide-meter-bar-max">/{{ "%g" | format(block.max) }}</span>{% if block.unit %} {{ block.unit }}{% endif %}</p>
  {% if block.body %}<div class="slide-meter-bar-note">{{ block.body | md }}</div>{% endif %}
</div>
```

**`slidedeck/templates/blocks/error.html`**

```html
<div class="slide-error-card" role="note">
  <p class="slide-error-card-header"><span class="slide-error-card-icon" aria-hidden="true">!</span> Block error in <code>:::{{ block.block_name }}</code></p>
  <p class="slide-error-card-message">{{ block.message }}</p>
  {% if block.source %}<pre class="slide-error-card-source">{{ block.source }}</pre>{% endif %}
</div>
```

**`tests/test_new_blocks.py`** tests the sprite, dialog and meter blocks, and renders them to check the accessible HTML.

```python
import pytest

from slidedeck.blocks import parse_blocks
from slidedeck.models import METER_SEGMENTS, filled_segments
from slidedeck.render import render_block


def only(source):
    blocks = parse_blocks(source)
    assert len(blocks) == 1, blocks
    return blocks[0]


# --- sprite ---------------------------------------------------------------------

HEART = ':::sprite alt="Heart" scale=8\n.3.3.\n32323\n.323.\n..3..\n:::'


def test_sprite_reads_rows_and_size():
    block = only(HEART)
    assert block.type == "sprite"
    assert (block.width, block.height, block.scale) == (5, 4, 8)


def test_sprite_ignores_indentation_and_blank_lines():
    block = only(':::sprite alt="Dot"\n   33\n\n   33\n:::')
    assert block.rows == ["33", "33"]


def test_sprite_runs_merge_same_shade_and_skip_empty():
    block = only(':::sprite alt="Bar"\n3330..11\n:::')
    runs = [(r.x, r.y, r.width, r.shade) for r in block.runs]
    assert runs == [(0, 0, 3, 3), (3, 0, 1, 0), (6, 0, 2, 1)]


def test_sprite_all_empty_has_no_runs():
    assert only(':::sprite alt="Nothing"\n...\n:::').runs == []


def test_sprite_needs_alt_text():
    block = only(":::sprite\n33\n:::")
    assert block.type == "error"
    assert "alt" in block.message


def test_sprite_blank_alt_is_rejected():
    assert only(':::sprite alt="  "\n33\n:::').type == "error"


def test_sprite_ragged_rows_are_an_error():
    block = only(':::sprite alt="x"\n333\n33\n:::')
    assert block.type == "error"
    assert "row 2 is 2 pixels wide" in block.message


def test_sprite_bad_character_is_named():
    block = only(':::sprite alt="x"\n3x4\n:::')
    assert block.type == "error"
    assert "'4x'" in block.message


def test_sprite_size_limit():
    row = "3" * 65
    assert only(f':::sprite alt="x"\n{row}\n:::').type == "error"


@pytest.mark.parametrize("scale", ["1", "33", "big"])
def test_sprite_scale_bounds(scale):
    assert only(f':::sprite alt="x" scale={scale}\n3\n:::').type == "error"


def test_sprite_renders_accessible_crisp_svg():
    html = render_block(only(HEART))
    assert 'role="img"' in html and 'aria-label="Heart"' in html
    assert 'shape-rendering="crispEdges"' in html
    assert 'width="40" height="32"' in html
    assert "slide-sprite-frame-pixel--3" in html
    assert "style=" not in html  # the CSP forbids inline styles


# --- dialog ---------------------------------------------------------------------

def test_dialog_positional_speaker():
    block = only(":::dialog SAGE\nHello **there**.\n:::")
    assert (block.type, block.speaker, block.body) == ("dialog", "SAGE", "Hello **there**.")


def test_dialog_needs_text():
    assert only(":::dialog SAGE\n:::").type == "error"


def test_dialog_keeps_full_text_in_the_page():
    html = render_block(only(":::dialog SAGE\nHello there.\n:::"))
    assert "Hello there." in html
    assert "data-typewriter" in html


def test_dialog_has_no_typewriter_in_print():
    html = render_block(only(":::dialog\nHi.\n:::"), mode="print")
    assert "data-typewriter " not in html and "data-typewriter>" not in html


# --- meter ----------------------------------------------------------------------

@pytest.mark.parametrize(
    ("value", "maximum", "expected"),
    [
        (0, 100, 0),            # empty is empty
        (100, 100, 20),         # full is full
        (0.1, 100, 1),          # a sliver still shows one segment
        (99.9, 100, 19),        # almost full never looks full
        (50, 100, 10),
        (3, 10, 6),
        (-5, 100, 0),
        (150, 100, 20),
    ],
)
def test_filled_segments_edges(value, maximum, expected):
    assert filled_segments(value, maximum, 20) == expected


@pytest.mark.parametrize(("maximum", "segments"), [(0, 20), (-1, 20), (10, 0)])
def test_filled_segments_rejects_nonsense(maximum, segments):
    with pytest.raises(ValueError):
        filled_segments(5, maximum, segments)


def test_meter_block_parses_numbers():
    block = only(':::meter xp label="Tests" value=96 max=100 unit=%\n:::')
    assert (block.variant, block.value, block.max, block.filled) == ("xp", 96, 100, 19)
    assert block.value_text == "96 % of 100 %"


def test_meter_value_over_max_is_an_error_not_a_clamp():
    block = only(':::meter label="HP" value=120 max=100\n:::')
    assert block.type == "error"
    assert "between 0 and max" in block.message


def test_meter_needs_a_label():
    assert only(":::meter value=1\n:::").type == "error"


def test_meter_renders_as_aria_meter_with_segments():
    html = render_block(only(':::meter label="Coffee" value=3 max=10 unit=cups\n:::'))
    assert 'role="meter"' in html
    assert 'aria-valuenow="3.0"' in html and 'aria-valuemax="10.0"' in html
    assert 'aria-valuetext="3 cups of 10 cups"' in html
    assert html.count("slide-meter-bar-segment") == METER_SEGMENTS
    assert html.count("is-filled") == 6
    assert "style=" not in html


# --- gallery filter and video captions -------------------------------------------

def test_gallery_defaults_to_lcd_filter():
    assert only(":::gallery\n![x](media/a.png)\n:::").filter == "lcd"


def test_gallery_filter_can_be_turned_off():
    assert only(":::gallery filter=none\n![x](media/a.png)\n:::").filter == "none"


def test_gallery_carousel_prints_and_reads_as_grid():
    block = only(":::gallery carousel\n![x](media/a.png)\n:::")
    assert "data-carousel" in render_block(block, "screen")
    assert "data-carousel" not in render_block(block, "print")
    assert "data-carousel" not in render_block(block, "text")


def test_local_video_with_captions_gets_a_track():
    block = only(':::video media/talk.mp4 title="Talk" captions=media/talk.vtt\n:::')
    assert block.captions == "/media/talk.vtt"
    html = render_block(block)
    assert '<track kind="captions" src="/media/talk.vtt"' in html


@pytest.mark.parametrize("captions", ["media/../secret.vtt", "media/talk.srt", "https://x.example/a.vtt"])
def test_unsafe_caption_files_are_refused(captions):
    assert only(f":::video media/talk.mp4 captions={captions}\n:::").type == "error"


def test_captions_only_for_local_video():
    block = only(":::video https://youtu.be/aqz-KE-bpKQ captions=media/a.vtt\n:::")
    assert block.type == "error"
    assert "only works for media/" in block.message


def test_video_in_text_mode_is_a_link_not_a_frame():
    html = render_block(only(':::video https://youtu.be/aqz-KE-bpKQ title="Demo"\n:::'), "text")
    assert "<iframe" not in html
    assert 'href="https://www.youtube-nocookie.com/embed/aqz-KE-bpKQ"' in html
```

**Check:** `python -m pytest tests/test_new_blocks.py` shows `41 passed`.

**Commit:** `git add .` then `git commit -m "Step 7: render blocks with markdown-it and Jinja2"`

### Step 8: The accessibility lint

You write the checks that no validator can do: a deck can be perfectly valid and still be hard to use. This file also finds each slide's title, which the parser needs in step 9.

How it works:

- `walk` visits every block, including the ones nested in columns, with `yield from` (a recursive generator).
- `headings`, `plain_text` and `links` read markdown-it's **token stream** instead of searching the text with regular expressions. Tokens already know what is a heading, a link or code, so `**bold**` inside a title comes out as plain `bold`.
- `slide_title` picks the most important heading (h1 beats h2 beats the small h3 kicker), and falls back to the first eight words. It names slides for screen readers, the slide list and the browser tab.
- `lint_slide` returns `Issue` objects: **errors** (a broken block) and **warnings** (an image without alt text, a video without a title, a local video without captions, no heading, over 120 words, link text like "click here").

**`slidedeck/lint.py`**

```python
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
    if block.type in ("gallery", "video", "sprite"):
        return [block.caption or ""]
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
    return [issue for slide in deck.slides for issue in lint_slide(slide)]
```

**Check:** the lint tests need whole decks, so they come in step 10. For now, check that the title finder skips the kicker and drops the Markdown stars:

```powershell
python -c "from slidedeck.blocks import parse_blocks; from slidedeck.lint import slide_title; print(slide_title(parse_blocks('### Kicker\n# Real *title*')))"
```

It prints `Real title`.

**Commit:** `git add .` then `git commit -m "Step 8: accessibility lint and slide titles"`

### Step 9: From a deck file to a Deck

You write the parser that reads a whole `.md` deck: YAML front matter for settings, `---` lines between slides, `???` for speaker notes, and an optional `class:` line per slide.

How it works:

- **Front matter** is loaded with `yaml.safe_load`, never `yaml.load`, so a deck cannot run Python code through YAML tags. A test tries exactly that.
- **Splitting slides** is a small state machine. A `---` line splits only when the line before it is blank (otherwise Markdown reads `Title` + `---` as a heading), and never inside a code fence or a `:::` block.
- **Notes** are everything after a `???` line, again outside code fences.
- An unknown `class:` keeps the slide and drops the class, but a broken deck setting (an unknown theme, a bad language tag) raises `DeckError` with a clear message. A typo on one slide should not stop a talk; a broken deck file should be fixed before it starts.

**`slidedeck/parser.py`**

```python
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
```

**`tests/test_parser.py`** includes every test from your earlier `slidedeck-steps/step1` draft, plus notes, classes, safe YAML and deck settings.

````python
import pytest

from slidedeck.parser import DeckError, parse_deck


def test_splits_on_separator():
    deck = parse_deck("# One\n\n---\n\n# Two\n")
    assert [s.source for s in deck.slides] == ["# One", "# Two"]


def test_indices_are_sequential():
    deck = parse_deck("A\n\n---\n\nB\n\n---\n\nC\n")
    assert [s.index for s in deck.slides] == [0, 1, 2]


def test_front_matter_is_metadata_not_a_slide():
    deck = parse_deck("---\ntitle: Intro\ntheme: night\n---\n# One\n")
    assert deck.title == "Intro"
    assert deck.theme == "night"
    assert len(deck.slides) == 1


def test_unclosed_front_matter_raises():
    with pytest.raises(DeckError):
        parse_deck("---\ntitle: Intro\n# One\n")


def test_unknown_theme_raises():
    with pytest.raises(DeckError, match="theme"):
        parse_deck("---\ntheme: rainbow\n---\n# One\n")


def test_front_matter_must_be_a_mapping():
    with pytest.raises(DeckError):
        parse_deck("---\n- a\n- b\n---\n# One\n")


def test_yaml_is_loaded_safely():
    with pytest.raises(DeckError):
        parse_deck("---\ntitle: !!python/object/apply:os.system ['echo hi']\n---\n# One\n")


def test_separator_inside_code_fence_is_ignored():
    text = "```yaml\n---\nkey: v\n```\n\n---\n\n# Two\n"
    assert len(parse_deck(text).slides) == 2


def test_separator_inside_block_is_ignored():
    text = ":::callout\nfirst\n\n---\n\nstill the callout\n:::\n\n---\n\n# Two\n"
    assert len(parse_deck(text).slides) == 2


def test_setext_heading_is_not_a_separator():
    assert len(parse_deck("Title\n---\n\nbody\n").slides) == 1


def test_empty_slides_are_dropped():
    assert len(parse_deck("# One\n\n---\n\n---\n\n# Two\n").slides) == 2


def test_empty_file_gives_zero_slides():
    assert parse_deck("").slides == []


def test_windows_line_endings():
    assert len(parse_deck("# One\r\n\r\n---\r\n\r\n# Two\r\n").slides) == 2


def test_speaker_notes_are_split_off():
    slide = parse_deck("# One\n\n???\nSay hello.\n").slides[0]
    assert slide.source == "# One"
    assert slide.notes == "Say hello."


def test_notes_marker_inside_code_is_content():
    slide = parse_deck("```\n???\n```\n").slides[0]
    assert slide.notes == ""
    assert "???" in slide.source


def test_slide_class_directive():
    slide = parse_deck("class: title\n\n# Big\n").slides[0]
    assert slide.css_class == "title"
    assert "class:" not in slide.source


def test_unknown_slide_class_is_dropped_not_fatal():
    slide = parse_deck("class: sparkle\n\n# Big\n").slides[0]
    assert slide.css_class is None


# --- deck settings added for the pixel engine ---------------------------------

from slidedeck.parser import DeckError  # noqa: E402


def test_default_theme_is_the_green_screen():
    assert parse_deck("# One\n").theme == "dmg"


def test_unknown_theme_is_a_clear_error():
    with pytest.raises(DeckError, match="unknown theme 'neon'"):
        parse_deck("---\ntheme: neon\n---\n# One\n")


@pytest.mark.parametrize("lang", ["en", "fr-CA", "pt-BR", "yue"])
def test_language_tags_accepted(lang):
    assert parse_deck(f"---\nlang: {lang}\n---\n# One\n").lang == lang


@pytest.mark.parametrize("lang", ["english", "e", "en_US", '"><script>'])
def test_bad_language_tags_rejected(lang):
    with pytest.raises(DeckError):
        parse_deck(f"---\nlang: '{lang}'\n---\n# One\n")


def test_slide_titles_are_filled_in():
    deck = parse_deck("# One\n\n---\n\n### Kicker\n\n## Two\n")
    assert [s.title for s in deck.slides] == ["One", "Two"]
````

**Check:** `python -m pytest tests/test_parser.py` shows `28 passed`.

**Commit:** `git add .` then `git commit -m "Step 9: deck parser with front matter, notes and classes"`

### Step 10: The sample deck and the command line

You write the deck you will present all through Part 2, the four sample pictures it uses, and `python -m slidedeck`, the program's front door. The engine is finished after this step.

**The pictures** are binary files, so copy them from the zip. Tell PowerShell once where you unzipped it (change the path if yours differs), then copy:

```powershell
$ZIP = "$HOME\Downloads\pixel-slides-app\pixel-slides"
mkdir decks\media
Copy-Item "$ZIP\decks\media\*.png" decks\media\
```

`$ZIP` lasts only as long as the terminal. Later steps use it again, so set it again when you open a new one.

**`decks/intro.md`** shows every block type. Slide 13 has two **deliberate** mistakes, so you can see what an error card looks like. Type it as it is: the tests count its 15 slides.

````markdown
---
title: Text In, Pixels Out
author: TCsM
theme: dmg
lang: en
boot: true
---
class: title

### Pixel Slides · World 1-1

# Text in, *pixels* out.

A slide engine that reads Markdown and draws a handheld screen.

???
Welcome. Press **S** for this presenter view, **F** for fullscreen, **?** for every key.
Type a number and press Enter to jump to that slide.

---

### The pipeline

## Three stages, one way

:::columns three
#### 01 Parse
The deck file is split into slides, then each slide into blocks.
+++
#### 02 Check
Every block is validated. A mistake becomes an error card, not a crash.
+++
#### 03 Draw
Each block has a template. Four colours and a pixel grid do the rest.
:::

???
Text in, parsed blocks in the middle, pixels out.

---

### Dialog block

## A word from the guide

:::dialog SAGE
Welcome to **Pixel Slides**! Every slide is a screen, and every block is a sprite. Press → to continue your journey.
:::

???
The text types itself out. With reduced motion on, it appears at once, and screen readers always get the whole sentence.

---

### Callout cards

## Notes and warnings

:::columns two
:::callout note title="Blank line first"
`Title` followed by `---` is a heading, not a slide break.
:::
+++
:::callout warning title="Never trust a URL"
Video embeds are rebuilt from a checked ID. The author's URL never reaches the page.
:::
:::

---

### By the numbers

:::columns split
:::callout stat title="0..n-1"
Every slide index is clamped to this range: keys, buttons, URLs and sync.
:::
+++
:::callout quote cite="Every off-by-one bug"
I was only out by one.
:::
:::

---

### Code

## The clamp, in full

:::columns sidebar
The whole paging rule is four lines. The tests around it are longer, which is the right way round.
+++
```python
def clamp(index: int, count: int) -> int:
    if count <= 0:
        raise ValueError("no slides")
    return max(0, min(index, count - 1))
```
:::

???
Show /deck/intro/99 in the address bar: it redirects to the last slide.

---

### Sprite block

## Pixel art, typed in

:::columns two
:::sprite alt="A red heart, drawn in pixels" scale=28
.333...333.
32213332223
32122222223
32222222223
32222222223
.322222223.
..3222223..
...32223...
....323....
.....3.....
:::
+++
Each digit is one pixel: **0** to **3** pick a shade, a dot is empty.

The art recolours with the palette, and its `alt` text is required.
:::

???
Press C to flip to high contrast and watch the heart follow.

---

### Meter block

## Status check

:::meter label="Tests" value=223 max=223
Every test in the suite passes.
:::

:::meter xp label="Contrast" value=60 max=60
5 palettes × 12 colour pairs meet WCAG AA.
:::

:::meter label="Coffee" value=3 max=10 unit=cups
:::

???
Meters are real `role="meter"` elements, so a screen reader says "Tests, 178 of 178".

---

### Gallery · camera

:::gallery grid caption="Photos are snapped to the palette's four shades, like a handheld camera. Try another palette under **Options**."
![Green hills under a low sun](media/hills.png)
![A city skyline at dusk with lit windows](media/city.png)
![A pixel-art game cartridge](media/cartridge.png)
![A pixel-art tree on a hill](media/tree.png)
:::

---

### Gallery · carousel

## One at a time

:::columns sidebar
Use the arrows under the picture. In the PDF, carousels print as a grid so nothing is lost.
+++
:::gallery carousel
![A pixel-art game cartridge](media/cartridge.png)
![Green hills under a low sun](media/hills.png)
![A pixel-art tree on a hill](media/tree.png)
:::
:::

---

### Video

:::columns sidebar
## Embeds, allow-listed

YouTube, Vimeo, or files in *media/* with captions. Anything else is refused.
+++
:::video https://www.youtube.com/watch?v=aqz-KE-bpKQ title="Big Buck Bunny, an open movie"
Embedded through youtube-nocookie.com.
:::
:::

---

### Access

## Built for every player

- Screen readers hear each slide's number and title
- **R** swaps pixel type for a readable face
- **C** switches to high contrast
- Motion follows your system setting
- A text version of the whole deck

???
The deck also has a lint: `python -m slidedeck check intro` lists missing alt text, untitled videos and slides with no heading.

---

### Validation

## What a mistake looks like

:::columns two
:::video https://evil.example.com/clip.mp4
:::
+++
:::callout shout
This variant does not exist.
:::
:::

???
Both of these are deliberate. `python -m slidedeck check intro` lists them from the terminal.

---

class: inverse

### Controls

## Driving the deck

| Key | Action |
| --- | --- |
| → Space | Next slide |
| ← Shift+Space | Previous slide |
| 7 then Enter | Jump to slide 7 |
| O · P · ? | Slides · options · help |
| R · C · M | Readable · contrast · sound |
| S · F | Presenter · fullscreen |

---

class: center

### Game over?

## Now make it *yours*.

Add a block: a model, a builder, a template. That is the whole contract.
````

**`slidedeck/__main__.py`** is what runs when you type `python -m slidedeck`. It uses `argparse` subcommands. Each command imports its heavy modules **inside** the function, so `check` works now even though `serve` needs the web app from step 11, `export` needs `pdf.py` from step 16, and so on. Typing the whole file now means you never edit it again.

```python
"""Command line.

    python -m slidedeck serve            # http://127.0.0.1:8000
    python -m slidedeck serve --dev      # + live reload while you edit decks
    python -m slidedeck export intro     # -> exports/intro.pdf
    python -m slidedeck export intro --theme night --readable
    python -m slidedeck check intro      # block errors + accessibility warnings
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

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
```

**`tests/test_lint.py`** tests step 8's helpers and rules on small decks, and checks that the sample deck has exactly its two deliberate errors.

```python
from slidedeck.lint import headings, lint_slide, links, plain_text, slide_title
from slidedeck.parser import parse_deck


def slide(source):
    return parse_deck(source).slides[0]


def codes(source):
    return [issue.code for issue in lint_slide(slide(source))]


# --- helpers ------------------------------------------------------------------

def test_headings_are_plain_text():
    assert headings("# Text in, *pixels* `out`\n\n### Kick") == [(1, "Text in, pixels out"), (3, "Kick")]


def test_plain_text_drops_markup():
    assert plain_text("Some **bold** and [a link](https://x.example).") == "Some bold and a link."


def test_links_returns_label_and_href():
    assert links("See [the docs](https://x.example/docs).") == [("the docs", "https://x.example/docs")]


# --- slide titles -----------------------------------------------------------------

def test_title_prefers_h1_over_kicker():
    assert slide("### Kicker\n\n# Real title\n").title == "Real title"


def test_title_found_inside_columns():
    assert slide(":::columns two\n## Left title\n+++\nRight\n:::\n").title == "Left title"


def test_title_falls_back_to_kicker():
    assert slide("### Gallery\n\n:::gallery\n![a](media/a.png)\n:::\n").title == "Gallery"


def test_title_falls_back_to_first_words():
    assert slide("one two three four five six seven eight nine ten\n").title == "one two three four five six seven eight…"


def test_title_of_empty_blocks_is_empty():
    assert slide_title([]) == ""


# --- rules -------------------------------------------------------------------------

def test_clean_slide_has_no_issues():
    assert codes("# Title\n\nShort text.\n") == []


def test_block_error_is_an_error():
    issues = lint_slide(slide("# T\n\n:::callout shout\nx\n:::\n"))
    assert [(i.level, i.code) for i in issues] == [("error", "block-error")]


def test_image_without_alt():
    assert codes("# T\n\n:::gallery\n![](media/a.png)\n![Fine](media/b.png)\n:::\n") == ["image-alt"]


def test_video_without_title():
    assert codes("# T\n\n:::video https://youtu.be/aqz-KE-bpKQ\n:::\n") == ["video-title"]


def test_local_video_without_captions():
    assert codes('# T\n\n:::video media/a.mp4 title="Demo"\n:::\n') == ["video-captions"]


def test_slide_without_heading():
    assert codes("Just words.\n") == ["slide-heading"]


def test_heading_inside_columns_counts():
    assert codes(":::columns two\n## Heading\n+++\nText\n:::\n") == []


def test_too_many_words():
    assert codes("# T\n\n" + "word " * 130) == ["word-count"]


def test_vague_link_text():
    assert codes("# T\n\nRead more [here](https://x.example).\n") == ["link-text"]


def test_bare_url_as_link_text():
    assert codes("# T\n\n<https://x.example/page>\n") == ["link-text"]


def test_issue_reads_well_as_a_line():
    issue = lint_slide(slide("Just words.\n"))[0]
    assert str(issue).startswith("slide 1: warning [slide-heading]")


def test_sample_deck_only_has_the_deliberate_errors():
    from pathlib import Path

    from slidedeck.lint import lint_deck

    deck = parse_deck((Path(__file__).parent.parent / "decks" / "intro.md").read_text(encoding="utf-8"))
    issues = lint_deck(deck)
    assert {i.code for i in issues} == {"block-error"}
    assert len(issues) == 2
```

**Check:**

```powershell
python -m pytest tests/test_lint.py
python -m slidedeck check intro
```

The tests show `20 passed`. The check prints the two deliberate mistakes on slide 13 and ends with `Text In, Pixels Out: 15 slides, 2 error(s), 0 warning(s)`. It exits with code 1 because of those errors, which is what a check should do. Then run `python -m pytest` with no file name: all **188 tests** so far should pass.

**Commit:** `git add .` then `git commit -m "Step 10: sample deck and command line"`

## Part 2: the web layer (steps 11 to 15)

Part 2 puts the engine on a web page. From now on most checks open a browser at `http://127.0.0.1:8000`. Keep the server running in one terminal (`python -m slidedeck serve --dev`) and use a second terminal, with the venv activated, for tests and Git. `--dev` turns on live reload: save a file and the open page reloads by itself.

### Step 11: The web app

You wrap the engine in FastAPI: a library page that lists decks, one URL per slide, a generated `/themes.css`, security headers, and live reload. This is the biggest step, so it comes in three parts: the app, the page templates, and the tests.

How it works:

- **URLs.** `/` is the library, `/deck/intro/7` is slide 7, `/deck/intro/7/presenter` the presenter view, `/deck/intro/print` and `/deck/intro/text` the print and text views. A bad number like `99`, `0`, `-4` or `007` is **redirected** to the one correct URL using step 3's functions, so every slide has exactly one address.
- **Safe deck names.** `DECK_NAME` only allows lowercase letters, digits and dashes, so `/deck/..%2Fapp/1` cannot read a file outside `decks/`.
- **Caching.** `load_deck` keeps each parsed deck with the file's modification time, and parses again only when the file changes.
- **Security headers.** The Content-Security-Policy is the browser-side half of step 4's allow-list: scripts and styles only from this server, frames only from YouTube's no-cookie host and Vimeo, and no inline styles or scripts at all.
- **Live reload.** With `--dev`, `watch_files` watches the decks, templates and static files, and `/events` sends a server-sent event to every open page, which then reloads (the page side comes in step 13).
- `?theme=night` overrides the deck's palette, but only with a name from step 2's list, so `?theme=<script>` is ignored.

First, the static folder. The app serves files from `slidedeck/static`, and the fonts are binary, so copy them now (set `$ZIP` again if this is a new terminal):

```powershell
mkdir slidedeck\static
Copy-Item -Recurse "$ZIP\slidedeck\static\fonts" slidedeck\static\
```

You now have `slidedeck\static\fonts` with 18 `.woff2` font files and `fonts.css`. The fonts are bundled instead of loaded from Google, so the app works offline and the security policy can stay strict.

**`slidedeck/app.py`**

```python
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
    return page("index.html", decks=decks, theme=DEFAULT_THEME, lang="en")


@app.get("/deck/{name}")
def deck_start(name: str, request: Request):
    load_deck(name)
    return RedirectResponse(f"/deck/{name}/1{_query(request)}", status_code=302)


@app.get("/deck/{name}/print", response_class=HTMLResponse)
def deck_print(name: str, request: Request):
    deck = load_deck(name)
    theme, _ = pick_theme(deck, request)
    return page("print.html", deck=deck, name=name, theme=theme, lang=deck.lang, mode="print")


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
```

The app already has routes for the presenter, print and text views. Their templates come in steps 14 and 15; until then those pages show an error.

Now the page templates. **`slidedeck/templates/base.html`** is the frame every page extends. It loads the fonts, the generated palette CSS, and `prefs.js` before the first paint (so a viewer's saved preferences never flash). At the bottom it draws the hidden SVG photo filter for each palette, using `lcd_table` from step 2. `{{ base }}` is empty on the server; the phone app in step 20 fills it in.

```html
<!doctype html>
<html lang="{{ lang | default('en') }}" class="theme-{{ theme }}" data-default-theme="{{ deck.theme if deck is defined else theme }}" data-themes="{{ themes | join(' ') }}" data-base="{{ base }}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Pixel Slides{% endblock %}</title>
  <link rel="stylesheet" href="{{ base }}/static/fonts/fonts.css">
  <link rel="stylesheet" href="{{ base }}/themes.css">
  <link rel="stylesheet" href="{{ base }}/static/theme.css">
  <link rel="stylesheet" href="{{ base }}/static/slides.css">
  {# Applies saved viewer preferences (readable font, motion...) before first paint. #}
  <script src="{{ base }}/static/prefs.js"></script>
  {% if desktop %}<meta name="desktop-token" content="{{ desktop.token }}">
  <script src="{{ base }}/static/desktop.js" defer></script>{% endif %}
  {% block head %}{% endblock %}
</head>
<body class="{% block body_class %}{% endblock %}" {% block body_attrs %}{% endblock %}>
{% block body %}{% endblock %}
{# The LCD photo filter, one per theme: grey the image, then snap it to 4 shades. #}
<svg class="lcd-filter-defs" aria-hidden="true" focusable="false" width="0" height="0">
  {% for theme_item in themes.values() %}
  {% set table = lcd_table(theme_item) %}
  <filter id="lcd-{{ theme_item.name }}" color-interpolation-filters="sRGB">
    <feColorMatrix type="saturate" values="0"/>
    <feComponentTransfer>
      <feFuncR type="discrete" tableValues="{{ table.R }}"/>
      <feFuncG type="discrete" tableValues="{{ table.G }}"/>
      <feFuncB type="discrete" tableValues="{{ table.B }}"/>
    </feComponentTransfer>
  </filter>
  {% endfor %}
</svg>
</body>
</html>
```

**`slidedeck/templates/index.html`** is the library. The `{% if desktop %}` parts only appear in the desktop app (step 18).

```html
{% extends "base.html" %}
{% block body_class %}library-view{% endblock %}
{% block body %}
<main class="library-list-container">
  <p class="library-list-kicker">Pixel Slides</p>
  <h1 class="library-list-header">Select a deck</h1>
  {% if desktop %}
  <div class="library-toolbar-row" role="toolbar" aria-label="Deck tools">
    <button type="button" class="library-toolbar-button" data-desktop-action="new-deck">New deck</button>
    <button type="button" class="library-toolbar-button" data-desktop-action="open-folder">Open decks folder</button>
  </div>
  <p class="library-toolbar-status" role="status" aria-live="polite" data-desktop-status>Decks live in {{ desktop.decks_dir }}. Edit a deck and the open slides reload.</p>
  {% endif %}
  <ul class="library-list-items">
  {% for item in decks %}
    <li class="library-list-item">
      <a class="library-list-item-link" href="{{ base }}/deck/{{ item.name }}/1">
        <span class="library-list-item-cursor" aria-hidden="true">&#9654;</span>
        <span class="library-list-item-title">{{ item.title }}</span>
        <span class="library-list-item-meta">
          {{ item.count }} slides · {{ item.theme.label }}
          <span class="deck-options-swatch theme-{{ item.theme.name }}" aria-hidden="true">{% for _ in range(4) %}<span class="deck-options-swatch-chip"></span>{% endfor %}</span>
        </span>
      </a>
      <a class="library-list-item-text" href="{{ base }}/deck/{{ item.name }}/text">Text version<span class="visually-hidden"> of {{ item.title }}</span></a>
      {% if desktop %}
      <button type="button" class="library-list-item-action" data-desktop-action="edit" data-deck="{{ item.name }}">Edit<span class="visually-hidden"> {{ item.title }}</span></button>
      <button type="button" class="library-list-item-action" data-desktop-action="export" data-deck="{{ item.name }}">Export PDF<span class="visually-hidden"> of {{ item.title }}</span></button>
      {% endif %}
    </li>
  {% else %}
    <li class="library-list-item">No decks yet. {% if desktop %}Press New deck.{% else %}Add a .md file to decks/.{% endif %}</li>
  {% endfor %}
  </ul>
</main>
{% endblock %}
```

**`slidedeck/templates/_slide.html`** draws one slide. Each slide is a labelled group ("3 of 15: Dialog block"), which is how screen readers announce slides.

```html
<section class="slide-page-frame{% if slide.css_class %} slide-page-frame--{{ slide.css_class }}{% endif %}"
         id="slide-{{ slide.index + 1 }}" data-index="{{ slide.index }}" data-title="{{ slide.title }}"
         role="group" aria-roledescription="slide"
         aria-label="{{ slide.index + 1 }} of {{ deck.slides | length }}{% if slide.title %}: {{ slide.title }}{% endif %}">
  <div class="slide-page-content">
  {% for block in slide.blocks %}
    {{ render_block(block, mode) }}
  {% endfor %}
  </div>
  <footer class="slide-page-folio">
    <span class="slide-page-folio-title">{{ deck.title }}</span>
    <span class="slide-page-folio-number"><span class="visually-hidden">Slide </span>{{ "%02d" | format(slide.index + 1) }}<span class="slide-page-folio-total">/{{ "%02d" | format(deck.slides | length) }}</span></span>
  </footer>
</section>
```

**`slidedeck/templates/deck.html`** is the audience view. It renders **every** slide into the page, and step 13's script shows one at a time, so moving between slides needs no network request. The hidden `role="status"` paragraph is the live region that tells screen readers "Slide 4 of 15".

```html
{% extends "base.html" %}
{% block title %}{{ deck.slides[index].title or deck.title }} · {{ index + 1 }}/{{ deck.slides | length }} · {{ deck.title }}{% endblock %}
{% block body_class %}deck-view{% endblock %}
{% block body_attrs %}data-deck="{{ name }}" data-deck-title="{{ deck.title }}" data-index="{{ index }}" data-count="{{ deck.slides | length }}" data-theme-query="{{ theme_query }}"{% if deck.boot %} data-boot{% endif %}{% if dev %} data-dev{% endif %}{% endblock %}
{% block body %}
<nav class="deck-skip-nav" aria-label="Skip link"><a class="deck-skip-link" href="{{ base }}/deck/{{ name }}/text{{ theme_query }}#slide-{{ index + 1 }}">Skip to the text version of this deck</a></nav>
<main class="deck-stage-viewport" aria-label="{{ deck.title }}">
  <div class="deck-stage-canvas">
  {% for slide in deck.slides %}
    {% include "_slide.html" %}
  {% endfor %}
  </div>
</main>
{# Screen readers hear "Slide 4 of 12: title" after every move. #}
<p class="visually-hidden" role="status" aria-live="polite" aria-atomic="true" data-live></p>

<div class="deck-progress-track" aria-hidden="true">
  {% for slide in deck.slides %}<span class="deck-progress-track-segment" data-segment="{{ slide.index }}"></span>{% endfor %}
</div>

<nav class="deck-nav-bar" aria-label="Slide navigation">
  <a class="deck-nav-bar-link" href="{{ base }}/">Decks</a>
  <span class="deck-nav-bar-divider" aria-hidden="true"></span>
  <button type="button" class="deck-nav-bar-button" data-step="-1" aria-label="Previous slide" aria-keyshortcuts="ArrowLeft">&#9664;</button>
  <span class="deck-nav-bar-counter"><span data-current>{{ index + 1 }}</span>/{{ deck.slides | length }}</span>
  <button type="button" class="deck-nav-bar-button" data-step="1" aria-label="Next slide" aria-keyshortcuts="ArrowRight">&#9654;</button>
  <span class="deck-nav-bar-divider" aria-hidden="true"></span>
  <button type="button" class="deck-nav-bar-link" data-open-dialog="outline" aria-keyshortcuts="O" aria-haspopup="dialog">Slides</button>
  <button type="button" class="deck-nav-bar-link" data-open-dialog="options" aria-keyshortcuts="P" aria-haspopup="dialog">Options</button>
  <button type="button" class="deck-nav-bar-link" data-open-dialog="help" aria-keyshortcuts="Shift+?" aria-haspopup="dialog" aria-label="Keyboard help">?</button>
  <span class="deck-nav-bar-divider" aria-hidden="true"></span>
  <a class="deck-nav-bar-link" href="{{ base }}/deck/{{ name }}/{{ index + 1 }}/presenter{{ theme_query }}" data-presenter-link target="_blank" rel="noopener">Presenter</a>
  <a class="deck-nav-bar-link" href="{{ base }}/deck/{{ name }}/text{{ theme_query }}" data-text-link>Text</a>
  <a class="deck-nav-bar-link" href="{{ base }}/deck/{{ name }}/print{{ theme_query }}" data-print-link target="_blank" rel="noopener">Print</a>
</nav>

{% include "_dialogs.html" %}

{% if deck.boot %}
<div class="deck-boot-screen" aria-hidden="true" hidden data-boot-screen>
  <p class="deck-boot-screen-logo">{{ deck.title }}</p>
  <p class="deck-boot-screen-hint">Press any key</p>
</div>
{% endif %}
<script src="{{ base }}/static/deck.js" defer></script>
{% endblock %}
```

**`slidedeck/templates/_dialogs.html`** holds the three menus: the slide list, Options, and keyboard help. They are native `<dialog>` elements, so the browser traps focus inside and Escape closes them, with no extra code.

```html
{# Native <dialog>: focus is trapped and Escape closes, without extra code. #}
<dialog class="deck-menu-window" data-dialog="outline" aria-labelledby="outline-heading">
  <div class="deck-menu-window-header">
    <h2 class="deck-menu-window-title" id="outline-heading">Slides</h2>
    <button type="button" class="deck-menu-window-close" data-close-dialog aria-label="Close">&times;</button>
  </div>
  <ol class="deck-outline-list">
  {% for slide in deck.slides %}
    <li class="deck-outline-list-item">
      <button type="button" class="deck-outline-list-button" data-goto="{{ slide.index }}">
        <span class="deck-outline-list-number">{{ "%02d" | format(slide.index + 1) }}</span>
        <span class="deck-outline-list-title">{{ slide.title or "Untitled slide" }}</span>
      </button>
    </li>
  {% endfor %}
  </ol>
</dialog>

<dialog class="deck-menu-window" data-dialog="options" aria-labelledby="options-heading">
  <div class="deck-menu-window-header">
    <h2 class="deck-menu-window-title" id="options-heading">Options</h2>
    <button type="button" class="deck-menu-window-close" data-close-dialog aria-label="Close">&times;</button>
  </div>
  <form class="deck-options-form" data-options-form>
    <fieldset class="deck-options-group">
      <legend class="deck-options-group-legend">Palette</legend>
      <label class="deck-options-choice">
        <input type="radio" name="theme" value="">
        <span class="deck-options-choice-label">Deck default</span>
      </label>
      {% for theme_item in themes.values() %}
      <label class="deck-options-choice">
        <input type="radio" name="theme" value="{{ theme_item.name }}">
        <span class="deck-options-swatch theme-{{ theme_item.name }}" aria-hidden="true">
          {% for _ in range(4) %}<span class="deck-options-swatch-chip"></span>{% endfor %}
        </span>
        <span class="deck-options-choice-label">{{ theme_item.label }}</span>
      </label>
      {% endfor %}
    </fieldset>
    <fieldset class="deck-options-group">
      <legend class="deck-options-group-legend">Lettering</legend>
      <label class="deck-options-choice"><input type="radio" name="font" value="pixel"><span class="deck-options-choice-label">Pixel</span></label>
      <label class="deck-options-choice"><input type="radio" name="font" value="readable"><span class="deck-options-choice-label">Readable (Atkinson Hyperlegible)</span></label>
    </fieldset>
    <fieldset class="deck-options-group">
      <legend class="deck-options-group-legend">Motion</legend>
      <label class="deck-options-choice"><input type="radio" name="motion" value="full"><span class="deck-options-choice-label">Animate</span></label>
      <label class="deck-options-choice"><input type="radio" name="motion" value="reduce"><span class="deck-options-choice-label">Reduce motion</span></label>
    </fieldset>
    <fieldset class="deck-options-group">
      <legend class="deck-options-group-legend">Screen effect</legend>
      <label class="deck-options-choice"><input type="radio" name="lcd" value="on"><span class="deck-options-choice-label">LCD pixel grid</span></label>
      <label class="deck-options-choice"><input type="radio" name="lcd" value="off"><span class="deck-options-choice-label">Flat</span></label>
    </fieldset>
    <fieldset class="deck-options-group">
      <legend class="deck-options-group-legend">Sound</legend>
      <label class="deck-options-choice"><input type="radio" name="sound" value="off"><span class="deck-options-choice-label">Off</span></label>
      <label class="deck-options-choice"><input type="radio" name="sound" value="on"><span class="deck-options-choice-label">Blips on navigation</span></label>
    </fieldset>
    <p class="deck-options-note">Saved in this browser. Your system's reduced-motion and high-contrast settings are followed until you choose here.</p>
  </form>
</dialog>

<dialog class="deck-menu-window" data-dialog="help" aria-labelledby="help-heading">
  <div class="deck-menu-window-header">
    <h2 class="deck-menu-window-title" id="help-heading">Controls</h2>
    <button type="button" class="deck-menu-window-close" data-close-dialog aria-label="Close">&times;</button>
  </div>
  <table class="deck-help-table">
    <caption class="visually-hidden">Keyboard shortcuts</caption>
    <thead><tr><th scope="col">Key</th><th scope="col">Action</th></tr></thead>
    <tbody>
      <tr><td><kbd>&rarr;</kbd> <kbd>Space</kbd> <kbd>PgDn</kbd></td><td>Next slide</td></tr>
      <tr><td><kbd>&larr;</kbd> <kbd>Shift</kbd>+<kbd>Space</kbd> <kbd>PgUp</kbd></td><td>Previous slide</td></tr>
      <tr><td><kbd>Home</kbd> <kbd>End</kbd></td><td>First or last slide</td></tr>
      <tr><td><kbd>7</kbd> then <kbd>Enter</kbd></td><td>Jump to slide 7</td></tr>
      <tr><td><kbd>O</kbd></td><td>List of slides</td></tr>
      <tr><td><kbd>P</kbd></td><td>Options</td></tr>
      <tr><td><kbd>R</kbd></td><td>Readable lettering on or off</td></tr>
      <tr><td><kbd>C</kbd></td><td>High contrast on or off</td></tr>
      <tr><td><kbd>M</kbd></td><td>Sound on or off</td></tr>
      <tr><td><kbd>S</kbd></td><td>Presenter view</td></tr>
      <tr><td><kbd>F</kbd></td><td>Fullscreen</td></tr>
      <tr><td><kbd>?</kbd></td><td>This help</td></tr>
    </tbody>
  </table>
</dialog>
```

**`tests/test_app.py`** drives the app through FastAPI's `TestClient`, with no real server. Type the whole file now: a few tests need the presenter, print and text templates, so for now you leave those out with `-k`.

```python
import pytest
from fastapi.testclient import TestClient

from slidedeck.app import app

client = TestClient(app)
LAST = 15  # slides in decks/intro.md


def location(response):
    return response.headers["location"]


def test_library_lists_decks():
    response = client.get("/")
    assert response.status_code == 200
    assert "Text In, Pixels Out" in response.text


def test_first_slide_renders():
    response = client.get("/deck/intro/1")
    assert response.status_code == 200
    assert 'data-index="0"' in response.text
    assert f'data-count="{LAST}"' in response.text


def test_last_slide_renders_without_redirect():
    response = client.get(f"/deck/intro/{LAST}", follow_redirects=False)
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("number", "expected"),
    [("99", f"/deck/intro/{LAST}"), (str(LAST + 1), f"/deck/intro/{LAST}"),
     ("0", "/deck/intro/1"), ("-4", "/deck/intro/1"), ("007", "/deck/intro/7")],
)
def test_out_of_range_numbers_redirect_to_a_real_slide(number, expected):
    response = client.get(f"/deck/intro/{number}", follow_redirects=False)
    assert response.status_code == 302
    assert location(response) == expected


def test_presenter_clamps_too_and_keeps_theme():
    response = client.get("/deck/intro/99/presenter?theme=night", follow_redirects=False)
    assert location(response) == f"/deck/intro/{LAST}/presenter?theme=night"


def test_deck_root_goes_to_slide_one():
    assert location(client.get("/deck/intro", follow_redirects=False)) == "/deck/intro/1"


@pytest.mark.parametrize("path", ["/deck/intro/abc", "/deck/intro/1.5", "/deck/nope/1",
                                  "/deck/..%2Fapp/1", "/deck/INTRO/1"])
def test_bad_paths_are_404(path):
    assert client.get(path, follow_redirects=False).status_code == 404


def test_theme_override_is_allow_listed():
    assert 'class="theme-night"' in client.get("/deck/intro/1?theme=night").text
    assert 'class="theme-dmg"' in client.get("/deck/intro/1?theme=<script>").text


def test_print_view_has_every_slide_and_no_iframes():
    html = client.get("/deck/intro/print").text
    assert html.count('class="slide-page-frame') == LAST
    assert "<iframe" not in html


def test_security_headers():
    response = client.get("/deck/intro/1")
    csp = response.headers["content-security-policy"]
    assert "frame-src https://www.youtube-nocookie.com https://player.vimeo.com" in csp
    assert "script-src 'self'" in csp


def test_raw_html_in_a_deck_is_escaped(tmp_path, monkeypatch):
    from slidedeck import app as app_module

    (tmp_path / "evil.md").write_text("# Hi\n\n<script>alert(1)</script>\n", encoding="utf-8")
    monkeypatch.setattr(app_module, "DECKS_DIR", tmp_path)
    app_module._cache.clear()
    html = client.get("/deck/evil/1").text
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_empty_deck_is_a_clear_error_not_a_crash(tmp_path, monkeypatch):
    from slidedeck import app as app_module

    (tmp_path / "empty.md").write_text("", encoding="utf-8")
    monkeypatch.setattr(app_module, "DECKS_DIR", tmp_path)
    app_module._cache.clear()
    response = client.get("/deck/empty/1")
    assert response.status_code == 422
    assert "no slides" in response.text


# --- pixel engine additions -------------------------------------------------------

def test_html_lang_comes_from_the_deck():
    assert '<html lang="en"' in client.get("/deck/intro/1").text


def test_themes_stylesheet_is_generated():
    response = client.get("/themes.css")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
    assert ".theme-contrast {" in response.text


def test_every_page_carries_the_lcd_filters():
    html = client.get("/deck/intro/1").text
    for name in ("dmg", "pocket", "berry", "night", "contrast"):
        assert f'<filter id="lcd-{name}"' in html


def test_slide_page_has_live_region_menus_and_skip_link():
    html = client.get("/deck/intro/1").text
    assert 'aria-live="polite"' in html
    assert 'data-dialog="outline"' in html and 'data-dialog="options"' in html and 'data-dialog="help"' in html
    assert 'class="deck-skip-link" href="/deck/intro/text#slide-1"' in html
    assert 'aria-roledescription="slide"' in html


def test_tab_title_names_the_slide():
    assert "<title>Pixel art, typed in · 7/15" in client.get("/deck/intro/7").text


def test_outline_lists_every_slide_title():
    html = client.get("/deck/intro/1").text
    assert html.count('class="deck-outline-list-button"') == LAST
    assert "Status check" in html


def test_text_view_has_every_slide_and_no_frames():
    response = client.get("/deck/intro/text")
    assert response.status_code == 200
    html = response.text
    assert html.count('class="text-view-slide"') == LAST
    assert "<iframe" not in html
    assert "data-carousel" not in html
    # Slide headings sit under the page's h1 and each slide's h2.
    assert html.count("<h1") == 1
    assert '<h3>Text in, <em>pixels</em> out.</h3>' in html


def test_text_view_notes_are_opt_in():
    assert "Speaker notes</p>" not in client.get("/deck/intro/text").text
    assert "Speaker notes</p>" in client.get("/deck/intro/text?notes=1").text


def test_text_view_keeps_theme():
    assert 'class="theme-berry"' in client.get("/deck/intro/text?theme=berry").text


def test_presenter_shows_access_check_for_broken_slide():
    html = client.get("/deck/intro/13/presenter").text
    assert "Access check · 2" in html
    assert "presenter-lint-list-item--error" in html


def test_boot_screen_only_when_deck_asks(tmp_path, monkeypatch):
    from slidedeck import app as app_module

    assert "data-boot-screen" in client.get("/deck/intro/1").text
    (tmp_path / "plain.md").write_text("# Hi\n", encoding="utf-8")
    monkeypatch.setattr(app_module, "DECKS_DIR", tmp_path)
    app_module._cache.clear()
    assert "data-boot-screen" not in client.get("/deck/plain/1").text


def test_library_shows_palette_and_text_link():
    html = client.get("/").text
    assert "DMG green" in html
    assert 'href="/deck/intro/text"' in html


def test_no_inline_styles_anywhere():
    # The CSP has no 'unsafe-inline', so an inline style would silently break.
    for path in ("/", "/deck/intro/8", "/deck/intro/8/presenter", "/deck/intro/print", "/deck/intro/text"):
        assert "style=" not in client.get(path).text, path


def test_text_view_kicker_is_a_label_not_a_heading():
    html = client.get("/deck/intro/text").text
    assert '<p class="text-view-kicker-label">Pixel Slides · World 1-1</p>' in html
    assert "<h5" not in html


def test_presenter_has_a_main_landmark():
    assert '<main class="presenter-layout-grid">' in client.get("/deck/intro/1/presenter").text
```

**Check:**

```powershell
python -m pytest tests/test_app.py -k "not print and not text_view and not presenter and not inline_styles"
```

You should see `26 passed, 9 deselected`. Then start the server and look:

```powershell
python -m slidedeck serve --dev
```

Open `http://127.0.0.1:8000`. You see "Select a deck" and "Text In, Pixels Out · 15 slides · DMG green". Click it: every slide shows at once, one under the other, in plain black-on-white HTML. That is correct, because there is no stylesheet or script yet. Try `http://127.0.0.1:8000/deck/intro/99` and watch the address bar change to `/deck/intro/15`. Stop the server with Ctrl+C.

**Commit:** `git add .` then `git commit -m "Step 11: FastAPI app, library and slide pages"`

### Step 12: The Game Boy look

You write the two stylesheets that turn plain HTML into a handheld screen. There is no Python in this step, and no tests: the check is your eyes.

How it works:

- **Tokens only.** Colours come from `/themes.css`, which step 2 generates. Sizes and fonts come from `theme.css`. Components never use a raw colour or size, so switching palette or lettering restyles everything at once.
- **Two lettering modes share one set of token names.** `:root[data-font="readable"]` swaps the pixel fonts for Atkinson Hyperlegible with its own type scale. Step 13's script sets that attribute.
- **A fixed canvas.** Every slide is laid out at 1600 × 900 pixels and scaled to fit the window, so a slide looks the same on any screen.
- **The 8-bit details are pure CSS:** four hard `box-shadow`s draw a notched pixel frame, a 6-pixel background grid is the LCD, `steps()` makes animations jump like a console, and `image-rendering: pixelated` keeps pixel art sharp. The photo filter from step 2 is applied with `filter: var(--lcd-filter)`.
- **Accessibility in CSS:** `.visually-hidden` hides text from eyes but not screen readers, the warning callout has hazard stripes so it reads without colour, and generated text like the "PRESS → TO START" prompt uses `content: "..." / ""` so screen readers skip it.

**`slidedeck/static/theme.css`**

```css
/* ==========================================================================
   Layout and type tokens. Colours live in /themes.css, generated from
   slidedeck/themes.py, so that palettes can be contrast-checked by tests.

   Two lettering modes share one set of token names:
     pixel    - Press Start 2P headlines, VT323 text, Silkscreen labels
     readable - Atkinson Hyperlegible, for anyone who finds pixel type hard
   Components only ever use the tokens, so switching mode restyles the deck.
   ========================================================================== */

:root {
  /* Canvas: slides are laid out at a fixed 1600x900 and scaled to fit. */
  --canvas-width: 1600px;
  --canvas-height: 900px;
  --page-margin-x: 112px;
  --page-margin-y: 80px;

  /* One "pixel" of the design grid. Borders, steps and shadows are
     multiples of it, which is what keeps everything looking 8-bit. */
  --px: 4px;

  --space-1: 8px;
  --space-2: 16px;
  --space-3: 24px;
  --space-4: 40px;
  --space-5: 64px;

  --measure: 30em;
  --step-ease: steps(4, end);
}

/* --- Pixel lettering (default) ------------------------------------------- */
/* Press Start 2P is drawn on an 8px grid, so its sizes are multiples of 8. */

:root,
:root[data-font="pixel"] {
  --font-display: "Press Start 2P", "Courier New", monospace;
  --font-text: "VT323", "Courier New", monospace;
  --font-label: "Silkscreen", "Courier New", monospace;
  --font-mono: "VT323", "Courier New", monospace;

  --size-label: 24px;
  --size-small: 32px;
  --size-body: 42px;
  --size-lead: 50px;
  --size-h3: 24px;
  --size-h2: 40px;
  --size-h1: 56px;
  --size-hero: 72px;
  --size-giant: 96px;

  --leading-display: 1.35;
  --leading-body: 1.12;
  --label-tracking: .06em;
}

/* --- Readable lettering --------------------------------------------------- */

:root[data-font="readable"] {
  --font-display: "Atkinson Hyperlegible", Verdana, sans-serif;
  --font-text: "Atkinson Hyperlegible", Verdana, sans-serif;
  --font-label: "Atkinson Hyperlegible", Verdana, sans-serif;
  --font-mono: "Atkinson Hyperlegible Mono", Consolas, monospace;

  --size-label: 22px;
  --size-small: 26px;
  --size-body: 34px;
  --size-lead: 40px;
  --size-h3: 24px;
  --size-h2: 56px;
  --size-h1: 72px;
  --size-hero: 96px;
  --size-giant: 136px;

  --leading-display: 1.1;
  --leading-body: 1.4;
  --label-tracking: .12em;
}
```

**`slidedeck/static/slides.css`** is the longest file in the project (about 900 lines), so the guide shows it in two parts. Type part 1, then carry straight on with part 2 in the **same file**. Class names follow `(page)-(thing)-(role)`.

`slides.css`, part 1 of 2: the page, prose, slide classes and blocks.

```css
/* ==========================================================================
   Layout and components. Values come from tokens only: colours from
   /themes.css, sizes and fonts from theme.css.
   Class names follow (page)-(thing)-(role):
     slide-*     anything inside a slide (same on every view)
     deck-*      the audience view chrome
     presenter-* the presenter view
     print-*     the print/PDF view
     text-view-* the text-only view
     library-*   the deck list
   ========================================================================== */

*, *::before, *::after { box-sizing: border-box; }
html, body { margin: 0; }
body { background: var(--chrome); color: var(--ink); font-family: var(--font-text); }
img, video, iframe, svg { display: block; max-width: 100%; }
button { font: inherit; color: inherit; }

.visually-hidden {
  position: absolute !important;
  width: 1px; height: 1px;
  margin: -1px; padding: 0;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
  border: 0;
}
.lcd-filter-defs { position: absolute; width: 0; height: 0; overflow: hidden; }

/* --- Pixel frames ----------------------------------------------------------
   Four hard box-shadows draw a border with the corner pixel missing: the
   notched window every handheld RPG menu uses. Each component sets
   --frame-color; the second shadow set is a solid drop shadow. */

.slide-callout-card, .slide-dialog-box, .slide-error-card, .slide-gallery-grid-item,
.slide-gallery-carousel-item, .slide-video-frame-player, .slide-video-frame-placeholder,
.deck-nav-bar, .deck-menu-window, .presenter-notes-panel, .deck-boot-screen-logo,
:where(.slide-page-frame) pre, .text-view-slide {
  --frame-color: var(--ink);
  box-shadow:
    0 calc(-1 * var(--px)) 0 0 var(--frame-color),
    0 var(--px) 0 0 var(--frame-color),
    calc(-1 * var(--px)) 0 0 0 var(--frame-color),
    var(--px) 0 0 0 var(--frame-color),
    calc(2 * var(--px)) calc(3 * var(--px)) 0 0 var(--frame-shadow, transparent);
}

/* --- The slide page ------------------------------------------------------- */

.slide-page-frame {
  position: relative;
  width: var(--canvas-width);
  height: var(--canvas-height);
  padding: var(--page-margin-y) var(--page-margin-x) calc(var(--page-margin-y) - 32px);
  display: flex;
  flex-direction: column;
  background: var(--paper);
  color: var(--ink);
  overflow: hidden;
  font-family: var(--font-text);
  font-size: var(--size-body);
  line-height: var(--leading-body);
  -webkit-font-smoothing: none;
  font-smooth: never;
}
:root[data-font="readable"] .slide-page-frame { -webkit-font-smoothing: auto; }

/* The LCD: a faint grid of pixel gaps over the whole screen. Off in the
   high-contrast palette, in print, and when the viewer turns it off. */
.slide-page-frame::after {
  content: "";
  position: absolute; inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(to right, color-mix(in srgb, var(--paper) 82%, var(--ink)) 1px, transparent 1px),
    linear-gradient(to bottom, color-mix(in srgb, var(--paper) 82%, var(--ink)) 1px, transparent 1px);
  background-size: 6px 6px;
  opacity: calc(var(--lcd-grid) * .35);
  mix-blend-mode: multiply;
}
.theme-night .slide-page-frame::after { mix-blend-mode: screen; opacity: calc(var(--lcd-grid) * .18); }
:root[data-lcd="off"] .slide-page-frame::after { display: none; }

.slide-page-content {
  position: relative;
  z-index: 1;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: var(--space-4);
}

/* Status bar along the bottom: deck title left, slide number right. */
.slide-page-folio {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: var(--space-2);
  border-top: var(--px) dotted var(--rule);
  font-family: var(--font-label);
  font-size: var(--size-label);
  letter-spacing: var(--label-tracking);
  text-transform: uppercase;
  color: var(--muted);
}
.slide-page-folio-number { color: var(--accent); font-variant-numeric: tabular-nums; }
.slide-page-folio-total { color: var(--muted); }

/* --- Prose (plain Markdown) ------------------------------------------------ */
/* :where() keeps these base rules at zero specificity, so any component
   class (callout figure, error card...) wins without !important. */

.slide-prose-body > :first-child { margin-top: 0; }
.slide-prose-body > :last-child { margin-bottom: 0; }

:where(.slide-page-frame) :is(h1, h2) {
  font-family: var(--font-display);
  font-weight: 400;
  line-height: var(--leading-display);
  text-wrap: balance;
  margin: 0 0 var(--space-3);
}
:root[data-font="readable"] :where(.slide-page-frame) :is(h1, h2) { font-weight: 700; letter-spacing: -.01em; }
:where(.slide-page-frame) h1 { font-size: var(--size-h1); }
:where(.slide-page-frame) h2 { font-size: var(--size-h2); }
:where(.slide-page-frame) :is(h1, h2) em {
  font-style: normal;
  color: var(--accent-ink);
  background: var(--accent);
  padding: 0 .18em;
  box-decoration-break: clone;
  -webkit-box-decoration-break: clone;
}

/* h3 is the kicker: a small inverse label, like a menu tab. */
:where(.slide-page-frame) h3 {
  display: inline-block;
  align-self: flex-start;
  margin: 0 0 var(--space-3);
  padding: 6px 12px 4px;
  font-family: var(--font-label);
  font-size: var(--size-h3);
  font-weight: 700;
  letter-spacing: var(--label-tracking);
  text-transform: uppercase;
  line-height: 1.2;
  color: var(--accent-ink);
  background: var(--accent);
}
:where(.slide-page-frame) h4 {
  font-family: var(--font-label);
  font-size: var(--size-small);
  font-weight: 700;
  margin: 0 0 var(--space-1);
  color: var(--accent);
}

:where(.slide-page-frame) p { margin: 0 0 var(--space-3); max-width: var(--measure); text-wrap: pretty; }
.slide-prose-body > p { font-size: var(--size-lead); }
:where(.slide-page-frame) strong { font-weight: 700; color: var(--accent); }
:root[data-font="pixel"] :where(.slide-page-frame) strong { text-decoration: underline; text-decoration-thickness: var(--px); text-underline-offset: .12em; }
:where(.slide-page-frame) a { color: var(--accent); text-decoration-thickness: var(--px); text-underline-offset: .15em; }

/* Lists are menus: the bullet is the selection cursor. */
:where(.slide-page-frame) :is(ul, ol) { margin: 0 0 var(--space-3); padding: 0; max-width: var(--measure); }
:where(.slide-page-frame) li { margin-bottom: var(--space-1); }
:where(.slide-page-frame) ul > li { list-style: none; padding-left: 1.3em; position: relative; }
:where(.slide-page-frame) ul > li::before {
  content: "\25B6" / "";
  position: absolute; left: 0; top: .02em;
  font-size: .7em;
  line-height: 1.6;
  color: var(--accent);
}
:where(.slide-page-frame) ol { padding-left: 1.6em; }
:where(.slide-page-frame) ol > li::marker { font-family: var(--font-label); color: var(--accent); }

:where(.slide-page-frame) blockquote {
  margin: 0 0 var(--space-3);
  padding-left: var(--space-4);
  border-left: calc(2 * var(--px)) solid var(--accent);
  font-size: var(--size-lead);
}

:where(.slide-page-frame) code {
  font-family: var(--font-mono);
  font-size: 1em;
  padding: 0 .25em;
  background: var(--raised);
  color: var(--ink);
}
:where(.slide-page-frame) pre {
  margin: var(--px) var(--px) var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--raised);
  font-size: var(--size-small);
  line-height: 1.2;
  overflow: hidden;
  --frame-shadow: var(--rule);
}
:where(.slide-page-frame) pre code { padding: 0; background: none; font-size: inherit; }

:where(.slide-page-frame) hr { border: 0; border-top: var(--px) dotted var(--rule); margin: var(--space-3) 0; }

:where(.slide-page-frame) table { border-collapse: collapse; font-size: var(--size-small); }
:where(.slide-page-frame) :is(th, td) { text-align: left; padding: var(--space-1) var(--space-4) var(--space-1) 0; border-bottom: var(--px) dotted var(--rule); }
:where(.slide-page-frame) th { font-family: var(--font-label); text-transform: uppercase; letter-spacing: var(--label-tracking); font-size: var(--size-label); color: var(--muted); }

/* --- Slide classes (class: name on the first line of a slide) ------------- */

/* Title: a dithered band across the top, like a cartridge label. */
.slide-page-frame--title .slide-page-content { justify-content: flex-end; padding-bottom: var(--space-4); }
.slide-page-frame--title h1 { font-size: var(--size-hero); max-width: 14em; margin-bottom: var(--space-4); }
.slide-page-frame--title .slide-prose-body > p { color: var(--muted); }
.slide-page-frame--title .slide-page-content::before {
  content: "";
  position: absolute; top: 0; left: 0; right: 0;
  height: 96px;
  background-image: conic-gradient(var(--shade-1) 25%, var(--shade-2) 0 50%, var(--shade-1) 0 75%, var(--shade-2) 0);
  background-size: calc(2 * var(--px)) calc(2 * var(--px));
  box-shadow: 0 calc(2 * var(--px)) 0 0 var(--ink), 0 calc(-2 * var(--px)) 0 0 var(--ink);
}
/* "Press start" prompt. The "/ ''" alt text keeps it out of screen readers. */
.slide-page-frame--title .slide-page-content::after {
  content: "\25B6  PRESS \2192  TO START" / "";
  font-family: var(--font-label);
  font-size: var(--size-label);
  letter-spacing: var(--label-tracking);
  color: var(--accent);
  animation: slide-title-blink 1.2s steps(1, end) infinite;
}
@keyframes slide-title-blink { 50% { visibility: hidden; } }

.slide-page-frame--feature .slide-page-content { justify-content: flex-start; }
.slide-page-frame--feature .slide-prose-body { column-count: 2; column-gap: var(--space-5); column-rule: var(--px) dotted var(--rule); }
.slide-page-frame--feature .slide-prose-body > :is(h1, h2, h3) { column-span: all; }
.slide-page-frame--feature .slide-prose-body > p { font-size: var(--size-body); max-width: none; }

.slide-page-frame--center .slide-page-content { align-items: center; text-align: center; }
.slide-page-frame--center :is(p, ul, ol) { margin-inline: auto; }
.slide-page-frame--center h3 { align-self: center; }

.slide-page-frame--inverse {
  --paper: var(--inverse-paper);
  --ink: var(--inverse-ink);
  --muted: var(--inverse-muted);
  --accent: var(--inverse-accent);
  --accent-ink: var(--inverse-paper);
  --raised: color-mix(in srgb, var(--inverse-paper) 88%, var(--inverse-ink));
  --rule: var(--inverse-muted);
}

/* --- Callout cards ---------------------------------------------------------- */

.slide-callout-card {
  max-width: 40em;
  margin: var(--px);
  padding: var(--space-3) var(--space-4);
  background: var(--raised);
  --frame-shadow: var(--rule);
}
.slide-callout-card--warning {
  /* Hazard stripes along the left edge: the warning reads without colour. */
  background:
    repeating-linear-gradient(-45deg, var(--ink) 0 8px, transparent 8px 16px) left / 16px 100% no-repeat,
    var(--raised);
  padding-left: calc(var(--space-4) + 16px);
}

.slide-callout-card-header { display: flex; align-items: baseline; flex-wrap: wrap; gap: var(--space-2); margin: 0 0 var(--space-2); max-width: none; }
.slide-callout-card-label {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 4px 10px 2px;
  font-family: var(--font-label);
  font-size: var(--size-label);
  font-weight: 700;
  letter-spacing: var(--label-tracking);
  text-transform: uppercase;
  color: var(--accent-ink);
  background: var(--accent);
}
.slide-callout-card-icon {
  display: inline-grid; place-items: center;
  width: 1.1em; height: 1.1em;
  background: var(--accent-ink); color: var(--accent);
  font-family: var(--font-display); font-size: .7em; line-height: 1;
}
.slide-callout-card-title { font-family: var(--font-display); font-size: var(--size-label); line-height: 1.4; }
:root[data-font="readable"] .slide-callout-card-title { font-size: var(--size-small); font-weight: 700; }
.slide-callout-card-body { font-size: var(--size-body); }
.slide-callout-card-body > :last-child { margin-bottom: 0; }

.slide-callout-card--stat, .slide-callout-card--quote { background: none; box-shadow: none; padding: 0; margin: 0; }
.slide-callout-card-figure {
  font-family: var(--font-display);
  font-size: var(--size-giant);
  line-height: 1.05;
  color: var(--accent);
  margin: 0 0 var(--space-3);
  text-shadow: var(--px) var(--px) 0 var(--rule);
}
.slide-callout-card--stat .slide-callout-card-body { font-size: var(--size-lead); color: var(--muted); }

.slide-callout-card--quote { position: relative; padding-top: var(--space-5); }
.slide-callout-card--quote::before {
  content: "\201C" / "";
  position: absolute; left: 0; top: 0;
  font-family: var(--font-display);
  font-size: var(--size-hero);
  line-height: 1;
  color: var(--accent);
}
.slide-callout-card-quote { margin: 0; padding: 0; border: 0; font-family: var(--font-display); font-size: var(--size-h2); line-height: var(--leading-display); }
:root[data-font="readable"] .slide-callout-card-quote { font-style: italic; font-weight: 700; }
.slide-callout-card-quote p { max-width: 16em; margin: 0; }
.slide-callout-card-cite {
  margin: var(--space-3) 0 0;
  font-family: var(--font-label);
  font-size: var(--size-label);
  letter-spacing: var(--label-tracking);
  text-transform: uppercase;
  color: var(--muted);
}
.slide-callout-card-cite::before { content: "\2014\00a0" / ""; color: var(--accent); }

/* --- Columns ------------------------------------------------------------------ */

.slide-columns-grid { display: grid; gap: var(--space-5); align-items: start; }
.slide-columns-grid--two { grid-template-columns: 1fr 1fr; }
.slide-columns-grid--three { grid-template-columns: repeat(3, 1fr); gap: var(--space-4); }
.slide-columns-grid--sidebar { grid-template-columns: 1fr 2fr; }
.slide-columns-grid--split { grid-template-columns: 1fr 1fr; gap: 0; }
.slide-columns-grid--split > .slide-columns-grid-cell { padding-inline: var(--space-5); }
.slide-columns-grid--split > .slide-columns-grid-cell:first-child { padding-left: 0; }
.slide-columns-grid--split > .slide-columns-grid-cell + .slide-columns-grid-cell {
  padding-right: 0;
  /* A dotted pixel divider, drawn as a background so it stays crisp. */
  background: linear-gradient(var(--rule) 50%, transparent 0) left top / var(--px) calc(4 * var(--px)) repeat-y;
}

.slide-columns-grid-cell { min-width: 0; }
.slide-columns-grid-cell > :first-child { margin-top: 0; }
.slide-columns-grid-cell > :last-child { margin-bottom: 0; }
.slide-columns-grid-cell > .slide-prose-body p { font-size: var(--size-body); }
.slide-columns-grid--sidebar > .slide-columns-grid-cell:first-child > .slide-prose-body p { font-size: var(--size-small); color: var(--muted); }
.slide-columns-grid-cell > * + * { margin-top: var(--space-4); }

/* --- Galleries ---------------------------------------------------------------- */

.slide-gallery-frame { margin: 0; min-height: 0; }
.slide-gallery-grid-track { display: grid; grid-template-columns: repeat(auto-fit, minmax(0, 1fr)); grid-auto-flow: column; gap: var(--space-4); padding: var(--px); }
.slide-gallery-grid-item, .slide-gallery-carousel-item { --frame-shadow: var(--rule); background: var(--raised); }
.slide-gallery-grid-image, .slide-gallery-carousel-image {
  width: 100%;
  object-fit: cover;
  /* Scale pixel art with hard edges instead of blurring it. */
  image-rendering: pixelated;
}
.slide-gallery-frame[data-filter="lcd"] img { filter: var(--lcd-filter); }
.slide-gallery-grid-image { aspect-ratio: 1; max-height: 460px; }

.slide-gallery-carousel-track {
  display: flex;
  gap: var(--space-4);
  padding: var(--px) var(--px) calc(4 * var(--px));
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  scroll-behavior: smooth;
  scrollbar-width: none;
}
.slide-gallery-carousel-track::-webkit-scrollbar { display: none; }
.slide-gallery-carousel-item { flex: 0 0 calc(100% - 2 * var(--px)); scroll-snap-align: start; }
.slide-gallery-carousel-image { height: 420px; }

.slide-gallery-carousel-controls {
  display: flex; align-items: center; gap: var(--space-2);
  margin-top: var(--space-2);
  font-family: var(--font-label); font-size: var(--size-label);
}
.slide-gallery-carousel-button {
  width: 56px; height: 56px;
  border: 0;
  background: var(--ink);
  color: var(--paper);
  cursor: pointer;
  font-size: 20px;
}
.slide-gallery-carousel-button:hover { background: var(--accent); color: var(--accent-ink); }
.slide-gallery-carousel-counter { font-variant-numeric: tabular-nums; color: var(--muted); min-width: 4em; text-align: center; }

.slide-gallery-frame-caption, .slide-video-frame-caption, .slide-sprite-frame-caption {
  margin-top: var(--space-3);
  font-size: var(--size-small);
  color: var(--muted);
}

/* --- Video --------------------------------------------------------------------- */

.slide-video-frame { margin: 0; width: min(calc(100% - 2 * var(--px)), 900px); margin-left: var(--px); }
.slide-video-frame-player, .slide-video-frame-placeholder { width: 100%; aspect-ratio: 16 / 9; border: 0; background: var(--ink); --frame-shadow: var(--rule); }
.slide-video-frame-placeholder {
  display: flex; flex-direction: column; justify-content: center; align-items: center; gap: var(--space-2);
  background: var(--raised);
  font-family: var(--font-label);
}
.slide-video-frame-icon { font-size: var(--size-hero); color: var(--accent); line-height: 1; }
.slide-video-frame-title { font-family: var(--font-display); font-size: var(--size-label); }
.slide-video-frame-source { font-size: var(--size-label); color: var(--muted); font-family: var(--font-mono); }

/* --- Sprites (pixel art typed into the deck) ------------------------------- */

.slide-sprite-frame { margin: 0; }
.slide-sprite-frame-art { max-width: 100%; height: auto; }
.slide-sprite-frame-pixel--0 { fill: var(--shade-0); }
.slide-sprite-frame-pixel--1 { fill: var(--shade-1); }
.slide-sprite-frame-pixel--2 { fill: var(--shade-2); }
.slide-sprite-frame-pixel--3 { fill: var(--shade-3); }
:root[data-motion="full"] .is-active .slide-sprite-frame-art { animation: slide-sprite-bob 1s steps(2, jump-none) infinite; }
@keyframes slide-sprite-bob { from { transform: translateY(0); } to { transform: translateY(calc(-2 * var(--px))); } }

/* --- Dialog box (RPG text window) ---------------------------------------- */

.slide-dialog-box {
  position: relative;
  margin: var(--space-3) var(--px) var(--px);
  padding: var(--space-4) var(--space-5) var(--space-4) var(--space-4);
  background: var(--paper);
  /* inner line: the double frame of a classic text window */
  outline: var(--px) solid var(--ink);
  outline-offset: calc(-3 * var(--px));
  --frame-shadow: var(--rule);
}
.slide-dialog-box-speaker {
  position: absolute; left: var(--space-4); top: 0;
  transform: translateY(-60%);
  margin: 0;
  padding: 6px 14px 4px;
  font-family: var(--font-label);
  font-size: var(--size-label);
  letter-spacing: var(--label-tracking);
  text-transform: uppercase;
  color: var(--paper);
  background: var(--ink);
}
.slide-dialog-box-body { font-size: var(--size-lead); }
.slide-dialog-box-body > :last-child { margin-bottom: 0; }
.slide-dialog-box-body p { max-width: none; }
.slide-dialog-box-cursor {
  position: absolute; right: var(--space-3); bottom: var(--space-2);
  font-size: 20px; color: var(--accent);
  animation: slide-title-blink .8s steps(1, end) infinite;
}
/* While typing: the real text is kept for assistive tech, a copy is shown. */
.slide-dialog-box-typed { font-size: var(--size-lead); }
.slide-dialog-box-typed > :last-child { margin-bottom: 0; }
.slide-dialog-box-typed p { max-width: none; }
```

`slides.css`, part 2 of 2: meters, errors, the audience view, menus, the presenter, print, text and library views, and motion. Type it directly under part 1.

```css
.slide-dialog-box.is-typing .slide-dialog-box-cursor { visibility: hidden; animation: none; }

/* --- Meter (HP / XP bar) --------------------------------------------------------- */

.slide-meter-bar {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  column-gap: var(--space-3);
  row-gap: var(--space-1);
  max-width: 1100px;
}
.slide-meter-bar-label {
  margin: 0;
  font-family: var(--font-label);
  font-size: var(--size-label);
  font-weight: 700;
  letter-spacing: var(--label-tracking);
  text-transform: uppercase;
  min-width: 6em;
}
.slide-meter-bar-track {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 1fr;
  gap: var(--px);
  height: 36px;
  padding: var(--px);
  background: var(--ink);
}
.slide-meter-bar-segment { background: var(--paper); }
.slide-meter-bar-segment.is-filled { background: var(--accent); }
/* XP fills with a dither, so the two bars differ by pattern, not colour alone. */
.slide-meter-bar--xp .slide-meter-bar-segment.is-filled {
  background: conic-gradient(var(--accent) 25%, var(--paper) 0 50%, var(--accent) 0 75%, var(--paper) 0) 0 0 / calc(2 * var(--px)) calc(2 * var(--px));
}
.slide-meter-bar-value { margin: 0; font-family: var(--font-display); font-size: var(--size-label); font-variant-numeric: tabular-nums; }
.slide-meter-bar-max { color: var(--muted); }
.slide-meter-bar-note { grid-column: 2 / -1; font-size: var(--size-small); color: var(--muted); }
.slide-meter-bar-note > :last-child { margin-bottom: 0; }
.slide-meter-bar + .slide-meter-bar { margin-top: var(--space-3); }

/* --- Block errors ------------------------------------------------------------------ */

.slide-error-card {
  margin: var(--px);
  padding: var(--space-3);
  background: var(--paper);
  font-size: var(--size-small);
  max-width: 44em;
  --frame-color: var(--error);
  outline: var(--px) dashed var(--error);
  outline-offset: calc(-3 * var(--px));
}
.slide-error-card-header { margin: 0 0 var(--space-1); font-family: var(--font-label); font-size: var(--size-label); font-weight: 700; color: var(--error); max-width: none; }
.slide-error-card-icon { display: inline-grid; place-items: center; width: 1.3em; height: 1.3em; background: var(--error); color: var(--paper); }
.slide-error-card-message { margin: 0 0 var(--space-2); max-width: none; }
.slide-error-card-source { margin: 0; font-size: var(--size-label); background: var(--raised); box-shadow: none; padding: var(--space-2); white-space: pre-wrap; overflow-wrap: anywhere; }

/* --- Audience view chrome ------------------------------------------------------- */

.deck-view { height: 100vh; overflow: hidden; }
.deck-stage-viewport { position: relative; width: 100%; height: 100%; overflow: hidden; }
.deck-view > .deck-stage-viewport { height: 100vh; }
.deck-stage-canvas {
  position: absolute;
  left: 50%; top: 50%;
  width: var(--canvas-width);
  height: var(--canvas-height);
  transform: translate(-50%, -50%) scale(var(--stage-scale, .5));
  transform-origin: center;
}
.deck-stage-canvas > .slide-page-frame {
  position: absolute; inset: 0;
  visibility: hidden;
}
.deck-stage-canvas > .slide-page-frame.is-active { visibility: visible; }
/* The handheld "fade": palette steps instead of a smooth blend. */
:root[data-motion="full"] .deck-view .deck-stage-canvas > .slide-page-frame.is-active { animation: deck-stage-fade 240ms steps(3, end); }
@keyframes deck-stage-fade { from { filter: brightness(1.6) contrast(.4); } to { filter: none; } }
.deck-stage-viewport[data-empty] .deck-stage-canvas { visibility: hidden; }
.deck-stage-viewport[data-empty]::after {
  content: "End of deck";
  position: absolute; inset: 0;
  display: grid; place-items: center;
  font-family: var(--font-label); font-size: 16px; text-transform: uppercase;
  color: var(--paper);
  background: var(--ink);
}

.deck-skip-nav { position: fixed; z-index: 30; }
.deck-skip-link {
  position: fixed; left: 16px; top: -100px;
  z-index: 30;
  padding: 12px 16px;
  font-family: var(--font-label); font-size: 16px;
  color: var(--accent-ink); background: var(--accent);
}
.deck-skip-link:focus { top: 16px; }

/* Progress: one pixel segment per slide along the top edge. */
.deck-progress-track {
  position: fixed; left: 0; right: 0; top: 0;
  display: flex; gap: 2px;
  height: 8px;
  z-index: 10;
}
.deck-progress-track-segment { flex: 1; background: color-mix(in srgb, var(--chrome) 70%, var(--paper)); }
.deck-progress-track-segment.is-done { background: var(--accent); }
.deck-progress-track-segment.is-current { background: var(--ink); }

.deck-nav-bar {
  position: fixed;
  left: 50%; bottom: 20px;
  transform: translateX(-50%);
  display: flex; align-items: center; gap: 4px;
  padding: 6px 8px;
  background: var(--paper);
  font-family: var(--font-label);
  font-size: 16px;
  color: var(--ink);
  z-index: 10;
  --frame-shadow: rgb(0 0 0 / .35);
}
/* Phones: the bar wraps onto two rows instead of running off the screen. */
@media (max-width: 720px) {
  .deck-nav-bar { flex-wrap: wrap; justify-content: center; width: max-content; max-width: calc(100vw - 16px); bottom: 8px; font-size: 13px; }
  .deck-nav-bar-button, .deck-nav-bar-link { padding: 0 8px; }
  .deck-nav-bar-divider { display: none; }
}
.deck-view.is-idle .deck-nav-bar { opacity: 0; pointer-events: none; }
.deck-view.is-idle { cursor: none; }
/* Keyboard users always see the bar while focus is in it. */
.deck-view .deck-nav-bar:focus-within { opacity: 1; pointer-events: auto; }
.deck-nav-bar-button, .deck-nav-bar-link {
  min-width: 44px; min-height: 44px;  /* WCAG target size */
  display: inline-grid; place-items: center;
  padding: 0 12px;
  border: 0;
  background: transparent;
  color: var(--ink);
  text-decoration: none;
  text-transform: uppercase;
  font-family: var(--font-label);
  font-size: 16px;
  cursor: pointer;
}
.deck-nav-bar-button:hover:not(:disabled), .deck-nav-bar-link:hover { background: var(--ink); color: var(--paper); }
.deck-nav-bar-button:disabled { color: var(--muted); cursor: default; opacity: .55; }
.deck-nav-bar-counter { min-width: 72px; text-align: center; font-variant-numeric: tabular-nums; font-family: var(--font-display); font-size: 14px; }
.deck-nav-bar-divider { width: var(--px); height: 28px; background: var(--rule); margin: 0 4px; }

:focus-visible {
  outline: var(--px) solid var(--accent);
  outline-offset: var(--px);
  box-shadow: 0 0 0 calc(2 * var(--px)) var(--paper);
}

/* --- Menus (native <dialog>) ------------------------------------------------ */

.deck-menu-window {
  width: min(680px, calc(100vw - 48px));
  max-height: calc(100vh - 96px);
  padding: 0;
  border: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: var(--font-text);
  font-size: 26px;
  --frame-shadow: rgb(0 0 0 / .4);
}
:root[data-font="readable"] .deck-menu-window { font-size: 20px; }
.deck-menu-window::backdrop { background: color-mix(in srgb, var(--chrome) 75%, transparent); }
.deck-menu-window-header {
  position: sticky; top: 0;
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 12px 12px 24px;
  background: var(--ink); color: var(--paper);
}
.deck-menu-window-title { margin: 0; font-family: var(--font-display); font-size: 16px; font-weight: 400; text-transform: uppercase; }
:root[data-font="readable"] .deck-menu-window-title { font-size: 20px; font-weight: 700; }
.deck-menu-window-close {
  width: 44px; height: 44px;
  border: 0; background: var(--paper); color: var(--ink);
  font-family: var(--font-display); font-size: 18px; cursor: pointer;
}

.deck-outline-list { list-style: none; margin: 0; padding: 12px; }
.deck-outline-list-button {
  display: flex; align-items: baseline; gap: 16px;
  width: 100%;
  padding: 8px 12px 8px 36px;
  border: 0; background: none; text-align: left; cursor: pointer;
  position: relative;
}
.deck-outline-list-button:hover, .deck-outline-list-button:focus-visible, .deck-outline-list-button[aria-current="true"] { background: var(--raised); }
.deck-outline-list-button:is(:hover, :focus-visible, [aria-current="true"])::before {
  content: "\25B6" / "";
  position: absolute; left: 12px;
  font-size: 14px; color: var(--accent);
}
.deck-outline-list-number { font-family: var(--font-label); font-size: 16px; color: var(--muted); }

.deck-options-form { padding: 8px 24px 24px; }
.deck-options-group { border: 0; margin: 0 0 12px; padding: 0; display: flex; flex-wrap: wrap; gap: 4px 8px; }
.deck-options-group-legend {
  width: 100%;
  padding: 12px 0 6px;
  font-family: var(--font-label); font-size: 14px; font-weight: 700;
  text-transform: uppercase; letter-spacing: .06em;
  color: var(--accent);
}
.deck-options-choice {
  display: inline-flex; align-items: center; gap: 8px;
  min-height: 44px;
  padding: 4px 12px 4px 8px;
  cursor: pointer;
}
.deck-options-choice:has(input:checked) { background: var(--ink); color: var(--paper); }
.deck-options-choice input { width: 20px; height: 20px; margin: 0; accent-color: var(--accent); }
.deck-options-swatch { display: inline-flex; padding: 2px; background: var(--ink); gap: 2px; vertical-align: middle; }
.deck-options-swatch-chip { width: 12px; height: 16px; }
.deck-options-swatch-chip:nth-child(1) { background: var(--shade-0); }
.deck-options-swatch-chip:nth-child(2) { background: var(--shade-1); }
.deck-options-swatch-chip:nth-child(3) { background: var(--shade-2); }
.deck-options-swatch-chip:nth-child(4) { background: var(--shade-3); }
.deck-options-note { margin: 12px 0 0; font-size: .8em; color: var(--muted); }

.deck-help-table { width: calc(100% - 48px); margin: 16px 24px 24px; border-collapse: collapse; }
.deck-help-table :is(th, td) { text-align: left; padding: 8px 12px 8px 0; border-bottom: 2px dotted var(--rule); }
.deck-help-table th { font-family: var(--font-label); font-size: 14px; text-transform: uppercase; color: var(--muted); }
kbd {
  display: inline-block;
  min-width: 1.6em;
  padding: 0 6px;
  font-family: var(--font-text); font-size: .9em; text-align: center;
  background: var(--raised);
  box-shadow: 0 2px 0 var(--ink), inset 0 0 0 2px var(--ink);
}

/* --- Boot screen ------------------------------------------------------------- */

.deck-boot-screen {
  position: fixed; inset: 0; z-index: 40;
  display: grid; place-content: center; justify-items: center; gap: 48px;
  background: var(--paper);
  cursor: pointer;
}
.deck-boot-screen[hidden] { display: none; }
.deck-boot-screen-logo {
  margin: 0;
  padding: 20px 28px;
  font-family: var(--font-display);
  font-size: clamp(18px, 3.4vw, 40px);
  color: var(--ink);
  background: var(--paper);
  text-align: center;
  animation: deck-boot-drop 1.6s steps(16, end) both;
}
.deck-boot-screen-hint {
  margin: 0;
  font-family: var(--font-label); font-size: 18px; text-transform: uppercase;
  color: var(--muted);
  animation: slide-title-blink 1s steps(1, end) 1.6s infinite;
}
@keyframes deck-boot-drop { from { transform: translateY(-40vh); } to { transform: translateY(0); } }
.deck-boot-screen.is-leaving { animation: deck-stage-fade 300ms steps(3, end) reverse forwards; }

/* --- Presenter view ----------------------------------------------------------- */

.presenter-view { min-height: 100vh; font-family: var(--font-text); }
.presenter-layout-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(0, 1fr);
  grid-template-rows: auto minmax(0, 1fr) auto;
  grid-template-areas:
    "current next"
    "current notes"
    "clock   notes";
  gap: 24px;
  padding: 24px;
  height: 100vh;
}
.presenter-current-panel { grid-area: current; display: flex; flex-direction: column; min-height: 0; }
.presenter-next-panel { grid-area: next; }
.presenter-notes-panel { grid-area: notes; overflow: auto; padding: 20px 24px; background: var(--paper); margin: 4px; }
.presenter-clock-panel { grid-area: clock; display: flex; align-items: center; gap: 24px; flex-wrap: wrap; }
.presenter-panel-label {
  margin: 0 0 10px;
  font-family: var(--font-label);
  font-size: 14px; font-weight: 700;
  text-transform: uppercase;
  color: var(--chrome-ink);
}
.presenter-notes-panel .presenter-panel-label { color: var(--muted); }
.presenter-current-stage { aspect-ratio: 16 / 9; height: auto; }
.presenter-next-stage { aspect-ratio: 16 / 9; height: auto; }
.presenter-notes-panel-body { font-size: 28px; line-height: 1.25; }
:root[data-font="readable"] .presenter-notes-panel-body { font-size: 20px; line-height: 1.5; }
.presenter-notes-panel-body p { margin: 0 0 12px; }
.presenter-notes-panel-empty { color: var(--muted); }
.presenter-clock-panel .presenter-panel-label { margin: 0; }
.presenter-clock-panel-time { margin: 0; font-family: var(--font-display); font-size: 32px; color: var(--chrome-ink); font-variant-numeric: tabular-nums; }
.presenter-clock-panel-actions { display: flex; gap: 8px; align-items: center; }
.presenter-clock-panel-actions .deck-nav-bar-button { background: var(--paper); }
.presenter-clock-panel-reset {
  min-height: 44px; padding: 0 16px;
  border: 0; background: var(--paper);
  cursor: pointer;
  font-family: var(--font-label); font-size: 14px; text-transform: uppercase;
}

.presenter-lint-list { margin-top: 20px; padding-top: 12px; border-top: 4px dotted var(--rule); }
.presenter-lint-list-header { margin: 0 0 8px; font-family: var(--font-label); font-size: 14px; text-transform: uppercase; color: var(--accent); }
.presenter-lint-list-items { list-style: none; margin: 0; padding: 0; font-size: .85em; }
.presenter-lint-list-item { margin-bottom: 8px; }
.presenter-lint-list-level {
  display: inline-block; padding: 0 6px;
  font-family: var(--font-label); font-size: 12px; text-transform: uppercase;
  color: var(--paper); background: var(--muted);
}
.presenter-lint-list-item--error .presenter-lint-list-level { background: var(--error); }

/* --- Print / PDF view ------------------------------------------------------- */

@page { size: 1600px 900px; margin: 0; }
.print-pages-stack { display: flex; flex-direction: column; align-items: center; gap: 32px; padding: 32px 0; }

@media print {
  html, body { background: var(--paper); }
  .print-pages-stack { display: block; padding: 0; }
  .print-pages-stack > .slide-page-frame { break-after: page; }
  .print-pages-stack > .slide-page-frame:last-child { break-after: auto; }
  .slide-page-frame::after { display: none; }
  .slide-page-frame--title .slide-page-content::after { display: none; }
  * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}

/* --- Text view: the deck as one readable page --------------------------------- */

.text-view { background: var(--paper); color: var(--ink); font-family: var(--font-text); font-size: 26px; line-height: 1.3; }
:root[data-font="readable"] .text-view { font-size: 20px; line-height: 1.55; }
.text-view-header, .text-view-contents, .text-view-body { max-width: 860px; margin: 0 auto; padding: 0 24px; }
.text-view-header { padding-top: 64px; }
.text-view-kicker { margin: 0 0 12px; font-family: var(--font-label); font-size: 16px; text-transform: uppercase; color: var(--accent); }
.text-view-title { margin: 0 0 16px; font-family: var(--font-display); font-size: clamp(24px, 5vw, 40px); font-weight: 400; line-height: 1.4; }
:root[data-font="readable"] .text-view-title { font-weight: 700; }
.text-view-meta { margin: 0 0 40px; color: var(--muted); }
.text-view a { color: var(--accent); text-decoration-thickness: 2px; }
.text-view-contents { margin-bottom: 48px; }
.text-view-contents-header, .text-view-slide-notes-label { font-family: var(--font-label); font-size: 16px; text-transform: uppercase; color: var(--muted); margin: 0 0 8px; }
.text-view-contents-list { margin: 0; padding-left: 1.6em; }
.text-view-slide { margin: 0 0 48px; padding: 24px 28px; background: var(--paper); --frame-shadow: var(--rule); }
.text-view-slide-label { margin: 0 0 16px; font-family: var(--font-label); font-size: 16px; font-weight: 700; text-transform: uppercase; color: var(--accent); }
.text-view-slide-content > * + * { margin-top: 20px; }
.text-view-slide-content :is(h3, h4, h5, h6) { font-family: var(--font-display); font-weight: 400; line-height: 1.4; margin: 0 0 12px; }
.text-view-slide-content h3 { font-size: 22px; }
.text-view-slide-content :is(h4, h5, h6) { font-size: 14px; }
:root[data-font="readable"] .text-view-slide-content :is(h3, h4, h5, h6) { font-weight: 700; }
:root[data-font="readable"] .text-view-slide-content h3 { font-size: 30px; }
:root[data-font="readable"] .text-view-slide-content :is(h4, h5, h6) { font-size: 20px; }
.text-view-slide-content img { max-height: 320px; image-rendering: pixelated; }
.text-view-slide-content .slide-gallery-grid-track { display: flex; flex-wrap: wrap; gap: 12px; }
.text-view-slide-content .slide-gallery-grid-item { box-shadow: none; background: none; }
.text-view-slide-content .slide-gallery-grid-image { width: 180px; height: 180px; }
.text-view-slide-content pre { background: var(--raised); padding: 16px; white-space: pre-wrap; overflow-wrap: anywhere; }
.text-view-kicker-label { margin: 0 0 4px; font-family: var(--font-label); font-size: 14px; text-transform: uppercase; color: var(--muted); }
.text-view-slide-content table { border-collapse: collapse; }
.text-view-slide-content :is(th, td) { text-align: left; padding: 6px 16px 6px 0; border-bottom: 2px dotted var(--rule); }
.text-view-slide-content .slide-callout-card { padding: 12px 16px; background: var(--raised); box-shadow: none; }
.text-view-slide-content .slide-callout-card-label { font-family: var(--font-label); font-size: 14px; text-transform: uppercase; padding: 2px 8px; background: var(--accent); color: var(--accent-ink); }
.text-view-slide-content .slide-callout-card-figure { font-family: var(--font-display); font-size: 32px; margin: 0; }
.text-view-slide-content .slide-columns-grid { display: grid; gap: 20px; }
.text-view-slide-content .slide-dialog-box { padding: 16px; background: var(--raised); }
.text-view-slide-content .slide-dialog-box-speaker { margin: 0 0 8px; font-family: var(--font-label); font-size: 14px; text-transform: uppercase; }
.text-view-slide-content .slide-dialog-box-cursor { display: none; }
.text-view-slide-content .slide-meter-bar { display: grid; grid-template-columns: auto 1fr auto; gap: 12px; align-items: center; }
.text-view-slide-content .slide-meter-bar-label { font-family: var(--font-label); font-size: 14px; text-transform: uppercase; margin: 0; }
.text-view-slide-content .slide-meter-bar-track { display: grid; grid-auto-flow: column; gap: 2px; height: 16px; padding: 2px; background: var(--ink); }
.text-view-slide-content .slide-meter-bar-segment { background: var(--paper); }
.text-view-slide-content .slide-meter-bar-segment.is-filled { background: var(--accent); }
.text-view-slide-content .slide-meter-bar-value { margin: 0; }
.text-view-slide-content .slide-error-card { box-shadow: none; outline: 2px dashed var(--error); padding: 12px; }
.text-view-slide-notes { margin-top: 20px; padding: 12px 16px; background: var(--raised); }
.text-view .slide-gallery-frame[data-filter="lcd"] img { filter: var(--lcd-filter); }

/* --- Library (deck list) ---------------------------------------------------- */

.library-view { min-height: 100vh; background: var(--paper); font-family: var(--font-text); font-size: 26px; }
.library-list-container { max-width: 820px; margin: 0 auto; padding: 96px 24px; }
.library-list-kicker {
  display: inline-block;
  margin: 0 0 20px; padding: 6px 12px 4px;
  font-family: var(--font-label); font-size: 16px; text-transform: uppercase;
  color: var(--accent-ink); background: var(--accent);
}
.library-list-header {
  margin: 0 0 40px;
  padding-bottom: 24px;
  border-bottom: 8px solid var(--ink);
  font-family: var(--font-display); font-weight: 400;
  font-size: clamp(22px, 5vw, 44px); line-height: 1.4;
}
.library-list-items { list-style: none; margin: 0; padding: 0; }
.library-list-item { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 24px; border-bottom: 4px dotted var(--rule); padding: 16px 0; }
.library-list-item-link {
  flex: 1;
  display: grid; grid-template-columns: 32px 1fr; gap: 4px 12px; align-items: baseline;
  padding: 8px 0;
  color: var(--ink); text-decoration: none;
}
.library-list-item-cursor { font-size: 18px; color: var(--accent); visibility: hidden; }
.library-list-item-link:is(:hover, :focus-visible) .library-list-item-cursor { visibility: visible; }
.library-list-item-title { font-family: var(--font-display); font-size: clamp(16px, 2.6vw, 22px); line-height: 1.5; }
.library-list-item-meta { grid-column: 2; display: flex; align-items: center; gap: 12px; font-family: var(--font-label); font-size: 14px; text-transform: uppercase; color: var(--muted); }
.library-list-item-text { font-family: var(--font-label); font-size: 14px; text-transform: uppercase; color: var(--accent); }
.library-list-item:only-child:not(:has(a)) { font-family: var(--font-text); }

/* Desktop and mobile app: tools above the list and on each deck. */
.library-toolbar-row { display: flex; flex-wrap: wrap; gap: 12px; margin: 0 0 16px; }
.library-toolbar-button, .library-list-item-action {
  min-height: 44px; padding: 8px 16px;
  border: var(--px) solid var(--ink); background: var(--paper); color: var(--ink);
  font-family: var(--font-label); font-size: 14px; text-transform: uppercase; cursor: pointer;
}
.library-toolbar-button { background: var(--ink); color: var(--paper); }
.library-toolbar-button:hover, .library-list-item-action:hover { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); }
.library-toolbar-button:disabled, .library-list-item-action:disabled { opacity: .55; cursor: progress; }
.library-toolbar-status { margin: 0 0 32px; font-size: 22px; color: var(--muted); overflow-wrap: anywhere; }
@media (max-width: 600px) {
  .library-view { font-size: 22px; }
  .library-list-container { padding: 40px 16px; }
  .library-list-item-link { flex-basis: 100%; }
}

/* --- Motion ------------------------------------------------------------------ */
/* data-motion follows the system setting until the viewer picks one. */

:root[data-motion="reduce"] *, :root[data-motion="reduce"] *::before, :root[data-motion="reduce"] *::after {
  animation: none !important;
  transition: none !important;
  scroll-behavior: auto !important;
}
@media (prefers-reduced-motion: reduce) {
  :root:not([data-motion="full"]) *, :root:not([data-motion="full"]) *::before, :root:not([data-motion="full"]) *::after {
    animation: none !important;
    transition: none !important;
    scroll-behavior: auto !important;
  }
}

/* Windows high contrast / forced colours: let the system palette win, but
   keep borders so the pixel windows are still visible. */
@media (forced-colors: active) {
  .slide-callout-card, .slide-dialog-box, .slide-error-card, .deck-nav-bar, .deck-menu-window { border: 2px solid CanvasText; }
  .slide-meter-bar-segment.is-filled { background: Highlight; forced-color-adjust: none; }
}
```

**Check:** start the server (`python -m slidedeck serve --dev`) and open `http://127.0.0.1:8000`. The library is now pea-green with pixel lettering and a palette swatch next to the deck. Open the deck: you see the dark-green surround, the progress strip along the top and the pixel menu bar at the bottom, but **no slide**. That is right: every slide is hidden until a script marks one as active, and that script is step 13.

**Commit:** `git add .` then `git commit -m "Step 12: Game Boy stylesheets"`

### Step 13: Make it move

You write the two scripts that bring the deck to life: saved viewer preferences, and everything that happens when someone presses a key. This is the only JavaScript in the core app, and it has no libraries.

How it works:

- **`prefs.js`** loads in `<head>`, before the page is drawn. It reads the viewer's saved choices from `localStorage` and sets attributes on `<html>` (`class="theme-night"`, `data-font="readable"`, `data-motion="reduce"`...). The CSS from step 12 reacts to those attributes. With no saved choice it follows the system: high contrast or reduced motion turned on in Windows are respected automatically.
- **`deck.js`** uses the **same clamp rule** as step 3, so keys, buttons, swipes and presenter sync can never leave `0 .. count-1`.
- It scales the 1600 × 900 canvas to the window with a `ResizeObserver`, shows only the current slide, and marks every other slide `inert` and `aria-hidden` so screen readers only read the current one.
- After each move it announces "Slide 4 of 15: title" in the live region, and at either end it says "Already at the last slide" instead of silently doing nothing.
- `history.replaceState` keeps the URL on the current slide, so a reload lands in the same place without filling the Back button.
- A `BroadcastChannel` keeps the audience tab and the presenter tab (step 14) on the same slide.
- The extras: the dialog typewriter (a visual copy is animated while the real text stays in the page for screen readers), square-wave sound blips with the Web Audio API (off by default), the boot screen, carousels, the presenter timer, and the live-reload listener for `--dev`.

**`slidedeck/static/prefs.js`**

```javascript
// Viewer preferences: palette, lettering, motion, screen effect, sound.
// Loaded in <head> so they apply before the first paint (no flash of the
// wrong palette). Stored per browser; the page works the same without them.
(() => {
  "use strict";

  const KEY = "pixel-slides:prefs";
  const root = document.documentElement;
  const media = (query) => window.matchMedia && window.matchMedia(query).matches;

  function read() {
    try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch { return {}; }
  }
  function write(prefs) {
    try { localStorage.setItem(KEY, JSON.stringify(prefs)); } catch { /* private mode: keep for this page only */ }
  }

  // What the page should use right now: an explicit choice, else the system
  // setting, else the deck's own default.
  function effective(prefs = read()) {
    const known = (root.dataset.themes || "").split(" ");
    const urlTheme = new URLSearchParams(location.search).get("theme");
    let theme = root.dataset.defaultTheme;
    if (known.includes(urlTheme)) theme = urlTheme;  // a shared ?theme= link wins
    else if (known.includes(prefs.theme)) theme = prefs.theme;
    else if (media("(prefers-contrast: more)") || media("(forced-colors: active)")) theme = "contrast";
    return {
      theme,
      font: prefs.font || "pixel",
      motion: prefs.motion || (media("(prefers-reduced-motion: reduce)") ? "reduce" : "full"),
      lcd: prefs.lcd || "on",
      sound: prefs.sound || "off",
    };
  }

  function apply(prefs = read()) {
    const now = effective(prefs);
    for (const name of [...root.classList]) if (name.startsWith("theme-")) root.classList.remove(name);
    root.classList.add(`theme-${now.theme}`);
    root.dataset.font = now.font;
    root.dataset.motion = now.motion;
    root.dataset.lcd = now.lcd;
    root.dataset.sound = now.sound;
    return now;
  }

  function set(name, value) {
    const prefs = read();
    if (value) prefs[name] = value; else delete prefs[name];
    write(prefs);
    return apply(prefs);
  }

  window.PixelPrefs = { KEY, read, effective, apply, set };
  apply();
})();
```

**`slidedeck/static/deck.js`**

```javascript
// Audience + presenter navigation, menus, preferences and the 8-bit extras.
// The server already clamps URLs; this file clamps keyboard, button, swipe
// and sync input with the same rule, so the index can never leave 0..count-1.
(() => {
  "use strict";

  const body = document.body;
  const root = document.documentElement;
  const prefs = window.PixelPrefs;
  const deckName = body.dataset.deck;
  // URL prefix: empty on the server, the install folder in the mobile app.
  const base = root.dataset.base || "";
  const deckTitle = body.dataset.deckTitle || "";
  const count = Number(body.dataset.count);
  let themeQuery = body.dataset.themeQuery || "";
  const isPresenter = body.hasAttribute("data-presenter");
  const CANVAS_W = 1600;
  const CANVAS_H = 900;

  const clamp = (i, n) => (Number.isFinite(i) ? Math.max(0, Math.min(Math.trunc(i), n - 1)) : 0);
  const reducedMotion = () => root.dataset.motion === "reduce";

  let current = clamp(Number(body.dataset.index), count);
  const titles = [...document.querySelectorAll(".deck-stage-canvas")[0]?.children || []]
    .map((slide) => slide.dataset.title || "");

  // --- Screen reader announcements ----------------------------------------
  const live = document.querySelector("[data-live]");
  function announce(text) {
    if (!live) return;
    // Clear first so the same message twice is still read out.
    live.textContent = "";
    requestAnimationFrame(() => { live.textContent = text; });
  }
  const describe = (i) => `Slide ${i + 1} of ${count}${titles[i] ? `: ${titles[i]}` : ""}`;

  // --- Sound: square-wave blips, off unless the viewer turns them on --------
  let audio = null;
  function blip(kind) {
    if (root.dataset.sound !== "on") return;
    try {
      audio = audio || new AudioContext();
      const notes = { next: [988, 1319], back: [784, 587], edge: [131, 98], toggle: [1568] }[kind] || [880];
      notes.forEach((freq, n) => {
        const osc = audio.createOscillator();
        const gain = audio.createGain();
        const start = audio.currentTime + n * 0.06;
        osc.type = "square";
        osc.frequency.setValueAtTime(freq, start);
        gain.gain.setValueAtTime(0.06, start);
        gain.gain.exponentialRampToValueAtTime(0.001, start + 0.07);
        osc.connect(gain).connect(audio.destination);
        osc.start(start);
        osc.stop(start + 0.08);
      });
    } catch { /* no audio: stay silent */ }
  }

  // --- Scale the fixed 1600x900 canvas to whatever box it sits in ---------
  const viewports = [...document.querySelectorAll(".deck-stage-viewport")];
  const fit = (viewport) => {
    const scale = Math.min(viewport.clientWidth / CANVAS_W, viewport.clientHeight / CANVAS_H);
    viewport.querySelector(".deck-stage-canvas").style.setProperty("--stage-scale", String(scale));
  };
  const resizer = new ResizeObserver((entries) => entries.forEach((e) => fit(e.target)));
  viewports.forEach((v) => { fit(v); resizer.observe(v); });

  // --- Show the right slide everywhere -------------------------------------
  function render() {
    for (const viewport of viewports) {
      const target = current + Number(viewport.dataset.offset || 0);
      const inRange = target >= 0 && target < count;
      viewport.toggleAttribute("data-empty", !inRange);
      for (const slide of viewport.querySelectorAll(".slide-page-frame")) {
        const active = inRange && Number(slide.dataset.index) === target;
        slide.classList.toggle("is-active", active);
        slide.inert = !active;
        // Hidden slides must not be read out; only the current one is exposed.
        slide.setAttribute("aria-hidden", String(!active));
      }
    }
    document.querySelectorAll("[data-current]").forEach((el) => { el.textContent = String(current + 1); });
    document.querySelectorAll("[data-step='-1']").forEach((b) => { b.disabled = current === 0; });
    document.querySelectorAll("[data-step='1']").forEach((b) => { b.disabled = current === count - 1; });
    document.querySelectorAll("[data-notes-for]").forEach((n) => { n.hidden = Number(n.dataset.notesFor) !== current; });
    document.querySelectorAll("[data-segment]").forEach((s) => {
      const i = Number(s.dataset.segment);
      s.classList.toggle("is-done", i < current);
      s.classList.toggle("is-current", i === current);
    });
    document.querySelectorAll("[data-goto]").forEach((b) => {
      b.setAttribute("aria-current", String(Number(b.dataset.goto) === current));
    });
    updateLinks();
    if (!isPresenter) {
      document.title = `${titles[current] || deckTitle} · ${current + 1}/${count} · ${deckTitle}`;
    }
    typeDialogs();
  }

  function updateLinks() {
    document.querySelectorAll("[data-presenter-link]").forEach((a) => {
      a.href = `${base}/deck/${deckName}/${current + 1}/presenter${themeQuery}`;
    });
    document.querySelectorAll("[data-text-link]").forEach((a) => { a.href = `${base}/deck/${deckName}/text${themeQuery}#slide-${current + 1}`; });
    document.querySelectorAll("[data-print-link]").forEach((a) => { a.href = `${base}/deck/${deckName}/print${themeQuery}`; });
    const skip = document.querySelector(".deck-skip-link");
    if (skip) skip.href = `${base}/deck/${deckName}/text${themeQuery}#slide-${current + 1}`;
  }

  function stopMedia(index) {
    document.querySelectorAll(`.slide-page-frame[data-index="${index}"]`).forEach((slide) => {
      slide.querySelectorAll("video").forEach((v) => v.pause());
      // Re-setting an iframe's src is the provider-neutral way to stop playback.
      slide.querySelectorAll("iframe").forEach((f) => { if (!isPresenter) f.src = f.src; });
    });
  }

  // --- Dialog boxes type themselves out -------------------------------------
  const typingTimers = new Map();
  function typeDialogs() {
    typingTimers.forEach((timer) => clearInterval(timer));
    typingTimers.clear();
    document.querySelectorAll(".slide-dialog-box-typed").forEach((copy) => copy.remove());
    document.querySelectorAll(".slide-dialog-box.is-typing").forEach((box) => box.classList.remove("is-typing"));
    document.querySelectorAll("[data-typewriter-source]").forEach((source) => { source.classList.remove("visually-hidden"); });
    if (reducedMotion() || isPresenter) return;

    const viewport = document.querySelector(".deck-view > .deck-stage-viewport");
    if (!viewport) return;
    viewport.querySelectorAll(".slide-page-frame.is-active [data-typewriter]").forEach((box) => {
      const source = box.querySelector("[data-typewriter-source]");
      // The copy is visual only. The real text is still in the page,
      // visually hidden, so screen readers read it whole and at once.
      const copy = source.cloneNode(true);
      copy.removeAttribute("data-typewriter-source");
      copy.className = "slide-dialog-box-typed";
      copy.setAttribute("aria-hidden", "true");
      const texts = [];
      const walker = document.createTreeWalker(copy, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) texts.push({ node: walker.currentNode, full: walker.currentNode.textContent });
      texts.forEach((t) => { t.node.textContent = ""; });
      source.classList.add("visually-hidden");
      source.after(copy);
      box.classList.add("is-typing");

      let part = 0;
      let shown = 0;
      const finish = () => {
        clearInterval(typingTimers.get(box));
        texts.forEach((t) => { t.node.textContent = t.full; });
        box.classList.remove("is-typing");
      };
      box.addEventListener("click", finish, { once: true });
      typingTimers.set(box, setInterval(() => {
        if (part >= texts.length) return finish();
        shown += 2;
        texts[part].node.textContent = texts[part].full.slice(0, shown);
        if (shown >= texts[part].full.length) { part += 1; shown = 0; }
      }, 28));
    });
  }

  // --- Navigation ----------------------------------------------------------
  const channel = "BroadcastChannel" in window ? new BroadcastChannel(`pixel-slides:${deckName}`) : null;

  function go(index, { broadcast = true, quiet = false } = {}) {
    const next = clamp(index, count);
    if (next === current) {
      // Pressing past either end: say so, instead of silently doing nothing.
      if (!quiet && Number.isFinite(index) && index !== current) {
        blip("edge");
        announce(index < 0 ? "Already at the first slide" : "Already at the last slide");
      }
      return;
    }
    blip(next > current ? "next" : "back");
    stopMedia(current);
    current = next;
    render();
    // replaceState: the URL always names the current slide, so a reload or a
    // shared link lands in the same place, without flooding the back button.
    const suffix = isPresenter ? "/presenter" : "";
    history.replaceState(null, "", `${base}/deck/${deckName}/${current + 1}${suffix}${themeQuery}`);
    announce(describe(current));
    if (broadcast && channel) channel.postMessage({ index: current });
  }

  const step = (delta) => go(current + delta);

  if (channel) {
    channel.onmessage = (event) => {
      const index = Number(event.data && event.data.index);
      if (Number.isFinite(index)) go(index, { broadcast: false, quiet: true });
    };
  }

  // --- Menus ------------------------------------------------------------------
  const dialogs = Object.fromEntries(
    [...document.querySelectorAll("dialog[data-dialog]")].map((d) => [d.dataset.dialog, d]),
  );
  const openDialog = () => Object.values(dialogs).find((d) => d.open);

  function toggleDialog(name) {
    const dialog = dialogs[name];
    if (!dialog) return;
    const already = openDialog();
    if (already) already.close();
    if (already === dialog) return;
    if (name === "options") syncOptionsForm();
    dialog.showModal();
    if (name === "outline") dialog.querySelector(`[data-goto="${current}"]`)?.focus();
  }

  document.querySelectorAll("[data-open-dialog]").forEach((button) => {
    button.addEventListener("click", () => toggleDialog(button.dataset.openDialog));
  });
  document.querySelectorAll("[data-close-dialog]").forEach((button) => {
    button.addEventListener("click", () => button.closest("dialog").close());
  });
  // Click on the backdrop closes a menu.
  Object.values(dialogs).forEach((dialog) => {
    dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
  });
  document.querySelectorAll("[data-goto]").forEach((button) => {
    button.addEventListener("click", () => {
      button.closest("dialog")?.close();
      go(Number(button.dataset.goto));
    });
  });

  // --- Options ----------------------------------------------------------------
  const form = document.querySelector("[data-options-form]");

  function syncOptionsForm() {
    if (!form) return;
    const stored = prefs.read();
    const now = prefs.effective(stored);
    const values = { theme: stored.theme || "", font: now.font, motion: now.motion, lcd: now.lcd, sound: now.sound };
    for (const [name, value] of Object.entries(values)) {
      const input = form.querySelector(`input[name="${name}"][value="${value}"]`);
      if (input) input.checked = true;
    }
  }

  function applyPrefs(changed) {
    // A palette picked here is saved, so the URL's ?theme= must go, or it
    // would win again on the next load.
    if (changed === "theme") {
      themeQuery = "";
      const url = new URL(location.href);
      url.searchParams.delete("theme");
      history.replaceState(null, "", url);
      updateLinks();
    }
    const now = prefs.apply();
    if (changed === "motion") typeDialogs();
    return now;
  }

  form?.addEventListener("change", (event) => {
    const { name, value } = event.target;
    prefs.set(name, value);
    applyPrefs(name);
    blip("toggle");
  });

  function quickToggle(name, on, off, label) {
    const now = prefs.effective();
    const value = now[name] === on ? off : on;
    prefs.set(name, value);
    const applied = applyPrefs(name);
    syncOptionsForm();
    blip("toggle");
    announce(label(applied));
  }

  // Other tabs (the presenter view, say) follow preference changes.
  window.addEventListener("storage", (event) => {
    if (event.key === prefs.KEY) { applyPrefs(); syncOptionsForm(); typeDialogs(); }
  });

  // --- Keyboard ------------------------------------------------------------------
  // Type a slide number then Enter to jump there.
  let typed = "";
  let typedTimer = 0;

  document.addEventListener("keydown", (event) => {
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    if (openDialog()) return;  // menus handle their own keys (Escape closes)
    if (event.target.closest("input, textarea, select, button, a, [contenteditable]") && [" ", "Enter"].includes(event.key)) return;

    if (/^[0-9]$/.test(event.key)) {
      typed = (typed + event.key).slice(-4);
      clearTimeout(typedTimer);
      typedTimer = setTimeout(() => { typed = ""; }, 1500);
      return;
    }
    switch (event.key) {
      case "Enter":
        if (!typed) return;
        go(Number(typed) - 1);
        typed = "";
        break;
      case "ArrowRight": case "ArrowDown": case "PageDown": case "n":
        step(1); break;
      case " ":
        step(event.shiftKey ? -1 : 1); break;
      case "ArrowLeft": case "ArrowUp": case "PageUp": case "b":
        step(-1); break;
      case "Home": go(0); break;
      case "End": go(count - 1); break;
      case "f":
        if (document.fullscreenElement) document.exitFullscreen();
        else document.documentElement.requestFullscreen?.();
        break;
      case "s":
        if (!isPresenter) window.open(`${base}/deck/${deckName}/${current + 1}/presenter${themeQuery}`, "_blank", "noopener");
        break;
      case "o": toggleDialog("outline"); break;
      case "p": toggleDialog("options"); break;
      case "?": toggleDialog("help"); break;
      case "r":
        quickToggle("font", "readable", "pixel", (p) => (p.font === "readable" ? "Readable lettering on" : "Pixel lettering on"));
        break;
      case "c":
        quickToggle("theme", "contrast", root.dataset.defaultTheme, (p) => (p.theme === "contrast" ? "High contrast on" : "High contrast off"));
        break;
      case "m":
        quickToggle("sound", "on", "off", (p) => (p.sound === "on" ? "Sound on" : "Sound off"));
        break;
      default:
        return;
    }
    event.preventDefault();
  });

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-step]");
    if (button) step(Number(button.dataset.step));
  });

  // Swipe on touch screens (but let carousels scroll on their own).
  let swipeX = null;
  document.addEventListener("pointerdown", (e) => {
    swipeX = e.pointerType === "touch" && !e.target.closest(".slide-gallery-carousel-track, dialog") ? e.clientX : null;
  });
  document.addEventListener("pointerup", (e) => {
    if (swipeX === null) return;
    const dx = e.clientX - swipeX;
    if (Math.abs(dx) > 60) step(dx < 0 ? 1 : -1);
    swipeX = null;
  });

  // Hide the nav bar and cursor when the mouse rests (keyboard focus keeps it).
  if (!isPresenter && deckName) {
    let idleTimer = 0;
    const wake = () => {
      body.classList.remove("is-idle");
      clearTimeout(idleTimer);
      idleTimer = setTimeout(() => body.classList.add("is-idle"), 2500);
    };
    document.addEventListener("pointermove", wake);
    wake();
  }

  // --- Carousels -----------------------------------------------------------------
  document.querySelectorAll("[data-carousel]").forEach((carousel) => {
    const track = carousel.querySelector(".slide-gallery-carousel-track");
    const counter = carousel.querySelector("[data-carousel-counter]");
    const items = [...track.children];
    const total = items.length;
    const position = () => clamp(Math.round(track.scrollLeft / (items[0].offsetWidth || 1)), total);
    const update = () => {
      const at = position();
      counter.textContent = `${at + 1} / ${total}`;
      items.forEach((item, i) => item.setAttribute("aria-hidden", String(i !== at)));
    };
    carousel.querySelectorAll("[data-carousel-step]").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        const target = clamp(position() + Number(button.dataset.carouselStep), total);
        items[target].scrollIntoView({ block: "nearest", inline: "start", behavior: reducedMotion() ? "auto" : "smooth" });
      });
    });
    track.addEventListener("scroll", update, { passive: true });
    update();
  });

  // --- Presenter timer -----------------------------------------------------------
  const timer = document.querySelector("[data-timer]");
  if (timer) {
    let started = Date.now();
    const pad = (n) => String(n).padStart(2, "0");
    const tick = () => {
      const seconds = Math.floor((Date.now() - started) / 1000);
      const h = Math.floor(seconds / 3600);
      const m = Math.floor((seconds % 3600) / 60);
      timer.textContent = `${h ? `${h}:` : ""}${pad(m)}:${pad(seconds % 60)}`;
    };
    setInterval(tick, 1000);
    document.querySelector("[data-timer-reset]")?.addEventListener("click", () => { started = Date.now(); tick(); });
  }

  // --- Boot screen (front matter `boot: true`), once per browser session ------
  const boot = document.querySelector("[data-boot-screen]");
  if (boot && current === 0 && !reducedMotion()) {
    let seen = false;
    try { seen = sessionStorage.getItem(`pixel-slides:booted:${deckName}`) === "1"; } catch { /* ignore */ }
    if (!seen) {
      boot.hidden = false;
      let done = false;
      const dismiss = () => {
        if (done) return;
        done = true;
        try { sessionStorage.setItem(`pixel-slides:booted:${deckName}`, "1"); } catch { /* ignore */ }
        boot.classList.add("is-leaving");
        setTimeout(() => { boot.hidden = true; }, 300);
        document.removeEventListener("keydown", onKey, true);
      };
      const onKey = (event) => { event.preventDefault(); event.stopImmediatePropagation(); dismiss(); };
      document.addEventListener("keydown", onKey, true);
      boot.addEventListener("click", dismiss);
      setTimeout(dismiss, 3200);
      setTimeout(() => blip("toggle"), 1600);
    }
  }

  // --- Live reload (only when the server runs with --dev) -----------------------
  if (body.hasAttribute("data-dev") && "EventSource" in window) {
    new EventSource(`${base}/events`).onmessage = (e) => { if (e.data === "reload") location.reload(); };
  }

  render();
})();
```

**Check:** with the server running (`python -m slidedeck serve --dev`), open the deck. Work through this list:

- [ ] The boot screen drops in with the deck title, then the title slide appears with a blinking "PRESS → TO START".
- [ ] → and ← move between slides, and the counter and progress strip follow. At slide 15, → does nothing visible (a screen reader hears "Already at the last slide").
- [ ] Typing `7` then Enter jumps to "Pixel art, typed in", and the address bar says `/deck/intro/7`.
- [ ] On slide 3 the SAGE dialog types itself out; clicking it finishes the text at once.
- [ ] O opens the slide list, P opens Options, ? opens help, and Escape closes each.
- [ ] R switches to readable lettering, C to high contrast, and both survive a reload.
- [ ] Edit a word in `decks\intro.md` and save: the open page reloads by itself.

Presenter, Text and Print in the menu bar still show errors. That is the next two steps.

**Commit:** `git add .` then `git commit -m "Step 13: navigation, preferences and 8-bit extras"`

### Step 14: The presenter view

You add the second screen a speaker looks at: the current slide, the next slide, the speaker notes, a timer, and the accessibility warnings for the slide on screen.

How it works:

- The template draws all slides **twice**, in two viewports. `deck.js` shows slide `current` in the first and `current + 1` in the second (`data-offset="1"`). After the last slide the second viewport says "End of deck".
- `app.py` from step 11 already runs `lint_deck` for this page and passes the issues per slide, so the speaker sees "Access check · 2" on slide 13 before the audience does.
- Press **S** in the audience tab to open it. Both tabs share step 13's `BroadcastChannel`, so moving in either tab moves the other.

**`slidedeck/templates/presenter.html`**

```html
{% extends "base.html" %}
{% block title %}Presenter · {{ deck.title }}{% endblock %}
{% block body_class %}presenter-view{% endblock %}
{% block body_attrs %}data-deck="{{ name }}" data-deck-title="{{ deck.title }}" data-index="{{ index }}" data-count="{{ deck.slides | length }}" data-theme-query="{{ theme_query }}" data-presenter{% if dev %} data-dev{% endif %}{% endblock %}
{% block body %}
<main class="presenter-layout-grid">
  <h1 class="visually-hidden">Presenter view: {{ deck.title }}</h1>
  <section class="presenter-current-panel" aria-labelledby="presenter-now">
    <h2 class="presenter-panel-label" id="presenter-now">Now · <span data-current>{{ index + 1 }}</span>/{{ deck.slides | length }}</h2>
    <div class="presenter-current-stage deck-stage-viewport">
      <div class="deck-stage-canvas">
      {% for slide in deck.slides %}{% include "_slide.html" %}{% endfor %}
      </div>
    </div>
  </section>
  <section class="presenter-next-panel" aria-labelledby="presenter-next">
    <h2 class="presenter-panel-label" id="presenter-next">Next</h2>
    <div class="presenter-next-stage deck-stage-viewport" data-offset="1" aria-hidden="true">
      <div class="deck-stage-canvas">
      {% for slide in deck.slides %}{% include "_slide.html" %}{% endfor %}
      </div>
    </div>
  </section>
  <section class="presenter-notes-panel" aria-labelledby="presenter-notes">
    <h2 class="presenter-panel-label" id="presenter-notes">Notes</h2>
    {% for slide in deck.slides %}
    <div class="presenter-notes-panel-body" data-notes-for="{{ slide.index }}" hidden>
      {% if slide.notes %}{{ slide.notes | md }}{% else %}<p class="presenter-notes-panel-empty">No notes for this slide.</p>{% endif %}
      {% set slide_issues = issues.get(slide.index, []) %}
      {% if slide_issues %}
      <div class="presenter-lint-list">
        <h3 class="presenter-lint-list-header">Access check · {{ slide_issues | length }}</h3>
        <ul class="presenter-lint-list-items">
        {% for issue in slide_issues %}
          <li class="presenter-lint-list-item presenter-lint-list-item--{{ issue.level }}">
            <span class="presenter-lint-list-level">{{ issue.level }}</span> {{ issue.message }}
          </li>
        {% endfor %}
        </ul>
      </div>
      {% endif %}
    </div>
    {% endfor %}
  </section>
  <section class="presenter-clock-panel" aria-labelledby="presenter-clock">
    <h2 class="presenter-panel-label" id="presenter-clock">Elapsed</h2>
    <p class="presenter-clock-panel-time" data-timer role="timer" aria-live="off">00:00</p>
    <div class="presenter-clock-panel-actions">
      <button type="button" class="deck-nav-bar-button" data-step="-1" aria-label="Previous slide">&#9664;</button>
      <button type="button" class="deck-nav-bar-button" data-step="1" aria-label="Next slide">&#9654;</button>
      <button type="button" class="presenter-clock-panel-reset" data-timer-reset>Reset timer</button>
    </div>
  </section>
</main>
<p class="visually-hidden" role="status" aria-live="polite" aria-atomic="true" data-live></p>
<script src="{{ base }}/static/deck.js" defer></script>
{% endblock %}
```

**Check:**

```powershell
python -m pytest tests/test_app.py -k "not print and not text_view and not inline_styles"
```

You should see `29 passed, 6 deselected`: the three presenter tests now pass. In the browser, open the deck, press S, and put the two windows side by side. Press → in either one and both move. On slide 13 the notes panel lists the two deliberate errors.

**Commit:** `git add .` then `git commit -m "Step 14: presenter view with notes, timer and access check"`

### Step 15: The print and text views

You add the last two views. The print view lays every slide out as one page each, for PDF export in step 16. The text view is the whole deck as one plain, well-structured page: for screen readers, for zooming, for handouts, and for anyone who would rather read than watch.

How it works:

- Both views pass a different `mode` to the block templates from step 7: in `print` a carousel becomes a grid and a video becomes a placeholder, in `text` a video becomes a link.
- The text view has one `<h1>` for the deck and one `<h2>` per slide, and `render_text_block` (step 7) moves each slide's own headings below that, so the outline a screen reader shows is correct.
- Speaker notes appear only with `?notes=1`.

**`slidedeck/templates/print.html`**

```html
{% extends "base.html" %}
{% block title %}{{ deck.title }} (print){% endblock %}
{% block body_class %}print-view{% endblock %}
{% block body %}
<main class="print-pages-stack" aria-label="{{ deck.title }}">
{% for slide in deck.slides %}
  {% include "_slide.html" %}
{% endfor %}
</main>
{% endblock %}
```

**`slidedeck/templates/text.html`**

```html
{% extends "base.html" %}
{% block title %}{{ deck.title }} (text version){% endblock %}
{% block body_class %}text-view{% endblock %}
{% block body %}
<header class="text-view-header">
  <p class="text-view-kicker">Text version</p>
  <h1 class="text-view-title">{{ deck.title }}</h1>
  <p class="text-view-meta">{% if deck.author %}By {{ deck.author }} · {% endif %}{{ deck.slides | length }} slides ·
    <a href="{{ base }}/deck/{{ name }}/1{{ theme_query }}">Open as slides</a> ·
    <a href="{{ base }}/">All decks</a> ·
    {% if show_notes %}<a href="{{ base }}/deck/{{ name }}/text{{ theme_query }}">Hide speaker notes</a>
    {% else %}<a href="{{ base }}/deck/{{ name }}/text{{ theme_query }}{{ '&' if theme_query else '?' }}notes=1">Show speaker notes</a>{% endif %}
  </p>
</header>
<nav class="text-view-contents" aria-labelledby="contents-heading">
  <h2 class="text-view-contents-header" id="contents-heading">Contents</h2>
  <ol class="text-view-contents-list">
  {% for slide in deck.slides %}
    <li><a href="#slide-{{ slide.index + 1 }}">{{ slide.title or "Untitled slide" }}</a></li>
  {% endfor %}
  </ol>
</nav>
<main class="text-view-body">
{% for slide in deck.slides %}
  <article class="text-view-slide" id="slide-{{ slide.index + 1 }}" aria-labelledby="slide-{{ slide.index + 1 }}-label">
    <h2 class="text-view-slide-label" id="slide-{{ slide.index + 1 }}-label">Slide {{ slide.index + 1 }} of {{ deck.slides | length }}{% if slide.title %}: {{ slide.title }}{% endif %}</h2>
    <div class="text-view-slide-content">
    {% for block in slide.blocks %}
      {{ render_text_block(block) }}
    {% endfor %}
    </div>
    {% if show_notes and slide.notes %}
    <aside class="text-view-slide-notes" aria-label="Speaker notes">
      <p class="text-view-slide-notes-label">Speaker notes</p>
      {{ slide.notes | md }}
    </aside>
    {% endif %}
  </article>
{% endfor %}
</main>
{% endblock %}
```

**Check:**

```powershell
python -m pytest
```

No `-k` this time: the whole suite should pass, **223 tests**. In the browser, click **Text** in the deck's menu bar: you get one long readable page with a contents list. Click **Print**: every slide is laid out one under another; Ctrl+P shows one slide per page. The web app is complete.

**Commit:** `git add .` then `git commit -m "Step 15: print and text views"`

## Part 3: export and apps (steps 16 to 21)

Part 3 turns the web app into things you can hand to other people: a PDF, a desktop app with an install wizard, and a phone app that works offline. The engine and the templates do not change again; each step adds one new way to run them.

### Step 16: PDF export

You print the print view from step 15 to a PDF with a headless browser, using Playwright.

How it works:

- `python -m slidedeck export intro` (written in step 10) starts a throwaway server on a free port, and `print_pdf` opens `/deck/intro/print` in a browser with no window, waits for the fonts, and prints at exactly 1600 × 900 pixels per page.
- `_launch` tries **Microsoft Edge first on Windows**. Edge is always installed, so there is no 150 MB browser download, and Edge is signed by Microsoft, so Application Control lets it run. Elsewhere it uses Playwright's own Chromium.
- `--readable` sets the same `localStorage` switch a viewer flips in Options before the page loads, so the PDF uses Atkinson Hyperlegible.

**`slidedeck/pdf.py`**

```python
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
```

**Check:** stop the dev server first if it is running, then:

```powershell
python -m slidedeck export intro
python -m slidedeck export intro --theme night --readable -o exports\intro-night.pdf
```

Each prints `Wrote exports\...pdf`. Open the PDFs: 15 pages, one slide each, the second one dark with readable lettering. The `exports` folder is in `.gitignore`, so the PDFs are not committed.

**Commit:** `git add .` then `git commit -m "Step 16: PDF export through Edge"`

### Step 17: Render a deck without a server

You write `site.py`, which renders every page of a deck once and returns them all as one JSON string. The phone app in step 20 runs this file inside the browser, where there is no server.

How it works:

- It uses the **same templates** as the server, so a deck looks and behaves the same on a phone as on the PC.
- `_render` sets the URL `base` (for example `/pixel-slides` when the app lives in a folder) for one render, then puts it back to empty in a `finally`, so the server is never affected.
- `build` never raises: a broken deck comes back as `{"ok": false, "error": "..."}`, which is easy to show in a phone app.

**`slidedeck/site.py`**

```python
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
    pages[f"/deck/{name}/print"] = _render("print.html", base, mode="print", **common)
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
```

**Check:** the tests for this file arrive with the phone app in step 20. For now:

```powershell
python -c "import json; from slidedeck import site; r = json.loads(site.build('intro', open('decks/intro.md', encoding='utf-8').read())); print(r['ok'], r['summary']['count'], len(r['pages']))"
```

It prints `True 15 33`: 15 slides, and 33 pages (15 slide pages, 15 presenter pages, the text view with and without notes, and the print view).

**Commit:** `git add .` then `git commit -m "Step 17: render a deck without a server"`

### Step 18: The desktop app

You write `python -m slidedeck app`: the slide server in its own window, with buttons in the library for New deck, Edit, Open decks folder and Export PDF.

How it works:

- **Where decks live.** `Documents\Pixel Slides\decks`, found through the Windows API so it still works when OneDrive has moved Documents. The first start copies the sample deck there. Updating or uninstalling the app never touches it.
- **The window** is the first of three that works: a native window (`pywebview`, which uses Edge WebView2), Edge or Chrome in `--app` mode (a plain window, no tabs), or a normal browser tab. `FallbackHost` tries them in order, because pywebview can install fine and still fail when it starts.
- **The desktop API** (`/desktop/...`) can open files and folders on your PC, so it is protected by a random **token**. The token is written into the pages this app serves, and every call must send it in an `X-Desktop-Token` header. Another website cannot read the token, and a custom header makes the browser block its requests anyway.
- **Live reload is always on**, so you edit a deck in any editor, save, and the open slides update.
- `render.py`'s `desktop` global (step 7) is set here, which switches on the `{% if desktop %}` parts of `base.html` and `index.html` (step 11).

**`requirements-desktop.txt`**

```text
# The desktop app: the engine, a native window, and PDF export through Edge.
fastapi>=0.110
uvicorn>=0.29
jinja2>=3.1
markdown-it-py>=3.0
pydantic>=2.6
pyyaml>=6.0
watchfiles>=0.21
playwright>=1.42
pywebview>=5.0
```

**`slidedeck/desktop.py`**

```python
"""The desktop app: the slide server in its own window.

    python -m slidedeck app                 # what the Start menu shortcut runs
    python -m slidedeck app --window edge   # force a window type (see WINDOWS)

Decks live in Documents/Pixel Slides/decks, so they survive updates and
uninstalls. The first start copies the sample deck there. The server runs on
127.0.0.1 only, with live reload on, so saving a deck in any editor updates
the open slides.

The window is the first of these that works:
  webview  a native window (pywebview: Edge WebView2 on Windows)
  edge     Edge or Chrome in app mode: its own window, no tabs or address bar
  browser  a tab in the default browser
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

APP_NAME = "Pixel Slides"
# A fixed port keeps the page origin stable, so viewer preferences (palette,
# lettering, motion) saved in the window's storage survive a restart.
PREFERRED_PORT = 47823
WINDOWS = ("auto", "webview", "edge", "browser", "none")

NEW_DECK = """---
title: {title}
theme: dmg
lang: en
---
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
"""


# --- Folders ---------------------------------------------------------------------


def documents_dir() -> Path:
    """The user's Documents folder, wherever Windows has moved it (OneDrive)."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        buffer = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        CSIDL_PERSONAL = 5
        if ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, 0, buffer) == 0:
            return Path(buffer.value)
    return Path.home() / "Documents"


def data_dir() -> Path:
    """App state that is not the user's work: window storage, logs."""
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = root / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def bundled(*parts: str) -> Path:
    """A file shipped with the app: next to the package, or inside the
    PyInstaller bundle when frozen."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return root.joinpath(*parts)


def seed_decks(decks_dir: Path) -> None:
    """First start: give the user the sample deck to look at and copy from."""
    decks_dir.mkdir(parents=True, exist_ok=True)
    if any(decks_dir.glob("*.md")):
        return
    samples = bundled("decks")
    if samples.is_dir():
        shutil.copytree(samples, decks_dir, dirs_exist_ok=True)


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48].strip("-")
    return slug or "deck"


def open_path(path: Path, reveal: bool = False) -> bool:
    """Open a file or folder with the system's default app. False if there is none."""
    try:
        if sys.platform == "win32":
            if reveal:
                subprocess.Popen(["explorer", "/select,", str(path)])
            else:
                os.startfile(path)  # noqa: S606 - the user's own file
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(path)] if reveal else ["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path.parent if reveal else path)])
    except OSError:
        return False
    return True


# --- Server ----------------------------------------------------------------------


def port_is_free(port: int) -> bool:
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def running_instance(port: int) -> bool:
    """Is Pixel Slides already serving on this port? Then reuse it."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/desktop/ping", timeout=1) as response:
            return json.load(response).get("app") == "pixel-slides"
    except (OSError, ValueError):
        return False


def make_router(decks_dir: Path, exports_dir: Path, token: str, host: "WindowHost"):
    from fastapi import APIRouter, Body, Depends, Header, HTTPException

    from .app import DECK_NAME

    def check_token(x_desktop_token: str = Header("")):
        # A custom header forces a CORS preflight, which other sites fail,
        # and the token is only in pages served by this app.
        if not secrets.compare_digest(x_desktop_token, token):
            raise HTTPException(403, "Bad token")

    def deck_path(name: str) -> Path:
        path = decks_dir / f"{name}.md"
        if not DECK_NAME.match(name) or not path.is_file():
            raise HTTPException(404, "No such deck")
        return path

    public = APIRouter(prefix="/desktop")
    router = APIRouter(prefix="/desktop", dependencies=[Depends(check_token)])

    @public.get("/ping")
    def ping():
        return {"app": "pixel-slides"}

    @router.post("/new-deck")
    def new_deck(title: str = Body("My talk", embed=True)):
        title = " ".join(title.split())[:120] or "My talk"
        slug, n = slugify(title), 2
        name = slug
        while (decks_dir / f"{name}.md").exists():
            name, n = f"{slug}-{n}", n + 1
        path = decks_dir / f"{name}.md"
        path.write_text(NEW_DECK.format(title=title.replace('"', "'")), encoding="utf-8")
        open_path(path)
        return {"name": name}

    @router.post("/edit/{name}")
    def edit(name: str):
        open_path(deck_path(name))
        return {"ok": True}

    @router.post("/open-folder")
    def open_folder():
        open_path(decks_dir)
        return {"ok": True}

    @router.post("/export/{name}")
    def export(name: str):
        from .pdf import PdfUnavailable, print_pdf

        deck_path(name)
        output = exports_dir / f"{name}.pdf"
        try:
            print_pdf(f"{host.origin}/deck/{name}/print", output)
        except PdfUnavailable:
            return {"path": None}
        open_path(output, reveal=True)
        return {"path": str(output)}

    @router.post("/window")
    def window(url: str = Body(..., embed=True)):
        if not url.startswith("/") or url.startswith("//"):
            raise HTTPException(400, "Only this app's pages")
        return {"opened": host.open_window(url)}

    return public, router


# --- Windows ---------------------------------------------------------------------


class WindowHost:
    """Shows the app's pages. Subclasses pick how."""

    kind = "none"

    def __init__(self, origin: str):
        self.origin = origin

    def open_window(self, path: str) -> bool:
        return False  # let the page open it itself

    def run(self, stop: threading.Event) -> None:
        stop.wait()


class WebviewHost(WindowHost):
    kind = "webview"

    def __init__(self, origin: str):
        super().__init__(origin)
        import webview  # noqa: F401 - fail here, so "auto" can fall back

        self.webview = webview

    def open_window(self, path: str) -> bool:
        title = "Presenter" if path.endswith("/presenter") or "/presenter?" in path else APP_NAME
        self.webview.create_window(f"{title} · {APP_NAME}", self.origin + path, width=1280, height=800)
        return True

    def run(self, stop: threading.Event) -> None:
        self.webview.create_window(APP_NAME, self.origin + "/", width=1280, height=820, min_size=(480, 360))
        # Not private: keep localStorage (the viewer's preferences) between runs.
        self.webview.start(private_mode=False, storage_path=str(data_dir() / "webview"))


def find_app_browser() -> str | None:
    names = ["msedge", "chrome", "google-chrome", "chromium", "chromium-browser"]
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    if sys.platform == "win32":
        for root in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"),
                     os.environ.get("LOCALAPPDATA")):
            for rel in (r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe"):
                if root and (Path(root) / rel).is_file():
                    return str(Path(root) / rel)
    return None


class AppBrowserHost(WindowHost):
    """Edge or Chrome with --app: a plain window with no browser chrome.
    A separate profile means this process lives exactly as long as the window."""

    kind = "edge"

    def __init__(self, origin: str):
        super().__init__(origin)
        self.exe = find_app_browser()
        if not self.exe:
            raise RuntimeError("No Edge or Chrome found")

    def run(self, stop: threading.Event) -> None:
        profile = data_dir() / "browser-profile"
        subprocess.run([self.exe, f"--app={self.origin}/", f"--user-data-dir={profile}",
                        "--no-first-run", "--no-default-browser-check", "--window-size=1280,820"],
                       check=False)


class BrowserHost(WindowHost):
    kind = "browser"

    def run(self, stop: threading.Event) -> None:
        webbrowser.open(self.origin + "/")
        stop.wait()  # no way to see the tab close: run until the process ends


HOSTS = {"webview": WebviewHost, "edge": AppBrowserHost, "browser": BrowserHost, "none": WindowHost}


def candidate_hosts(choice: str, origin: str):
    """The window types to try, best first. "auto" falls back step by step."""
    order = ["webview", "edge", "browser"] if choice == "auto" else [choice]
    for kind in order:
        try:
            yield HOSTS[kind](origin)
        except Exception as exc:  # noqa: BLE001 - try the next kind of window
            print(f"{kind} window unavailable: {exc}", file=sys.stderr)
    if order[-1] != "browser" and choice != "none":
        yield BrowserHost(origin)


class FallbackHost(WindowHost):
    """Runs the first window type that works. pywebview can import fine and
    still fail on start (no WebView2 runtime, blocked .NET), so failures in
    run() move on to the next type too."""

    def __init__(self, choice: str, origin: str):
        super().__init__(origin)
        self.choice = choice
        self.current: WindowHost = WindowHost(origin)

    @property
    def kind(self) -> str:  # type: ignore[override]
        return self.current.kind

    def open_window(self, path: str) -> bool:
        return self.current.open_window(path)

    def run(self, stop: threading.Event) -> None:
        for host in candidate_hosts(self.choice, self.origin):
            self.current = host
            try:
                host.run(stop)
                return
            except Exception as exc:  # noqa: BLE001
                print(f"{host.kind} window failed: {exc}", file=sys.stderr)
        self.current = WindowHost(self.origin)


# --- Main ------------------------------------------------------------------------


def quiet_streams() -> None:
    """A windowed app (pythonw, or the frozen .exe) has no console:
    sys.stdout is None and uvicorn's logging would crash on it."""
    if sys.stdout is None or sys.stderr is None:
        log = open(data_dir() / "pixel-slides.log", "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        sys.stdout = sys.stdout or log
        sys.stderr = sys.stderr or log


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="slidedeck app", description=f"Run {APP_NAME} as a desktop app.")
    parser.add_argument("--decks", type=Path, help="deck folder (default: Documents/Pixel Slides/decks)")
    parser.add_argument("--window", choices=WINDOWS, default=os.environ.get("PIXEL_SLIDES_WINDOW", "auto"))
    parser.add_argument("--port", type=int, default=PREFERRED_PORT)
    args = parser.parse_args(argv)
    quiet_streams()

    if running_instance(args.port):
        # Already running: open another window onto it, then leave.
        if args.window != "none":
            FallbackHost("edge" if args.window in ("auto", "webview") else args.window,
                         f"http://127.0.0.1:{args.port}").run(threading.Event())
        return

    home = documents_dir() / APP_NAME
    decks_dir = (args.decks or home / "decks").resolve()
    exports_dir = home / "exports"
    seed_decks(decks_dir)

    # The app module reads these when it is imported.
    os.environ["SLIDES_DECKS_DIR"] = str(decks_dir)
    os.environ["SLIDES_DEV"] = "1"  # live reload: save a deck, the slides update

    import uvicorn

    from .app import app
    from .render import env

    port = args.port if port_is_free(args.port) else free_port()
    origin = f"http://127.0.0.1:{port}"
    token = secrets.token_urlsafe(24)
    host = FallbackHost(args.window, origin)
    public, router = make_router(decks_dir, exports_dir, token, host)
    app.include_router(public)
    app.include_router(router)
    env.globals["desktop"] = {"token": token, "decks_dir": str(decks_dir)}

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        if not thread.is_alive():
            sys.exit("The slide server could not start")
        time.sleep(0.05)
    print(f"{APP_NAME} at {origin}, decks in {decks_dir}", flush=True)

    stop = threading.Event()
    try:
        host.run(stop)
    except KeyboardInterrupt:
        pass
    finally:
        server.should_exit = True
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
```

**`slidedeck/static/desktop.js`** is only loaded in the desktop app. It wires the library's buttons to the desktop API, always sending the token, and opens the presenter in an app window instead of the system browser so it stays in sync.

```javascript
// Desktop app only: the deck list's tools, and new windows for the presenter.
// Every call carries the token from the page, so other local pages cannot
// drive these endpoints.
(() => {
  "use strict";

  const base = document.documentElement.dataset.base || "";
  const token = document.querySelector('meta[name="desktop-token"]')?.content || "";
  const status = document.querySelector("[data-desktop-status]");

  async function call(path, payload = {}) {
    const response = await fetch(`${base}/desktop/${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Desktop-Token": token },
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    return data;
  }

  const say = (text) => { if (status) status.textContent = text; };

  // Presenter and print open in their own app window, not the system browser,
  // so the presenter stays in sync with the slides (same storage, same channel).
  async function openWindow(url) {
    const target = new URL(url, location.href);
    try {
      const { opened } = await call("window", { url: target.pathname + target.search });
      return opened;
    } catch {
      return false;
    }
  }
  const nativeOpen = window.open.bind(window);
  window.open = (url, target, features) => {
    openWindow(url).then((opened) => { if (!opened) nativeOpen(url, target, features); });
    return null;
  };
  document.addEventListener("click", (event) => {
    const link = event.target.closest?.('a[target="_blank"]');
    if (!link || new URL(link.href).origin !== location.origin) return;
    event.preventDefault();
    window.open(link.href, "_blank");
  });

  const actions = {
    async "new-deck"() {
      const title = window.prompt("Title of the new deck", "My talk");
      if (!title) return;
      const { name } = await call("new-deck", { title });
      say(`Created ${name}.md and opened it in your editor. Save it to see the slides.`);
      setTimeout(() => location.reload(), 600);
    },
    async "open-folder"() {
      await call("open-folder");
    },
    async edit(button) {
      await call(`edit/${button.dataset.deck}`);
      say(`Opened ${button.dataset.deck}.md. Save it and open slides reload on their own.`);
    },
    async export(button) {
      say(`Exporting ${button.dataset.deck} to PDF…`);
      const result = await call(`export/${button.dataset.deck}`);
      if (result.path) {
        say(`Saved ${result.path}`);
      } else {
        // No PDF engine: the print view and the system's "Save as PDF" do the same job.
        say("Choose “Save as PDF” in the print dialog.");
        await openWindow(`${base}/deck/${button.dataset.deck}/print?autoprint=1`);
      }
    },
  };

  document.addEventListener("click", async (event) => {
    const button = event.target.closest?.("[data-desktop-action]");
    if (!button) return;
    button.disabled = true;
    try {
      await actions[button.dataset.desktopAction](button);
    } catch (error) {
      say(`Could not do that: ${error.message}`);
    } finally {
      button.disabled = false;
    }
  });

  if (document.body.classList.contains("print-view") && new URLSearchParams(location.search).has("autoprint")) {
    document.fonts.ready.then(() => setTimeout(() => window.print(), 300));
  }
})();
```

**Check:**

```powershell
python -m pip install -r requirements-desktop.txt
python -m slidedeck app
```

A window called Pixel Slides opens on the library, now with **New deck** and **Open decks folder** buttons, and **Edit** and **Export PDF** next to the deck. The terminal prints where the decks live (your `Documents\Pixel Slides\decks`). Press **Edit**, change a word, save: the slides update. If the native window cannot start, the app falls back to an Edge window by itself, and the terminal says why. Close the window to stop the app.

**Commit:** `git add .` then `git commit -m "Step 18: desktop app with a native window"`

### Step 19: The Windows install wizard

You write an installer that gets past Smart App Control: a Python wizard with Start menu and desktop shortcuts, an entry in Settings > Apps, and an uninstaller.

How it works:

- **Why Python and not Setup.exe.** Application control blocks programs that are not signed by a publisher Windows knows, and a home-built Setup.exe is not. The wizard only ever runs Python's own signed programs (`python.exe`, `pythonw.exe`) and always uses `python -m pip`, so it gets through.
- **Per user, no admin.** The app goes to `%LOCALAPPDATA%\Programs\Pixel Slides` with its own `venv`. Decks stay in `Documents\Pixel Slides` (step 18) and are never removed.
- **Shortcuts without PowerShell.** The usual ways to make a `.lnk` file (PowerShell's `WScript.Shell`, pywin32) are blocked or missing under application control, so `winlink.py` writes the shortcut file format directly.
- **The window stays responsive.** The install runs in a thread and talks to the window through a queue, because Tk widgets may only be touched from the window's own thread.
- **The icon** is 32x32 pixel art drawn in code and scaled up with nearest-neighbour, so the pixels stay crisp at every size.

Create `packaging/winlink.py`:

```python
"""Write a Windows shortcut (.lnk) in pure Python.

The usual ways (PowerShell's WScript.Shell, pywin32) are blocked or missing
on PCs with Smart App Control or other application control policies, which
put PowerShell in Constrained Language Mode. This writes the file format
directly (MS-SHLLINK): a LinkInfo block with the target path, plus the
working folder, arguments and icon as strings. Explorer resolves the rest.
"""
from __future__ import annotations

import struct
import uuid
from pathlib import PureWindowsPath

HAS_LINK_INFO = 0x02
HAS_NAME = 0x04
HAS_WORKING_DIR = 0x10
HAS_ARGUMENTS = 0x20
HAS_ICON_LOCATION = 0x40
IS_UNICODE = 0x80
SHELL_LINK_CLSID = uuid.UUID("00021401-0000-0000-C000-000000000046").bytes_le
SW_SHOWNORMAL = 1


def _string(text: str) -> bytes:
    data = text.encode("utf-16-le")
    return struct.pack("<H", len(data) // 2) + data


def _link_info(target: str) -> bytes:
    # VolumeID for a fixed drive with an empty label.
    volume = struct.pack("<IIII", 0x11, 3, 0, 0x10) + b"\x00"
    header_size = 0x24  # includes the Unicode path offsets
    try:
        ansi_path = target.encode("mbcs", "replace") + b"\x00"  # the system code page, on Windows
    except LookupError:
        ansi_path = target.encode("ascii", "replace") + b"\x00"
    suffix = b"\x00"
    unicode_path = target.encode("utf-16-le") + b"\x00\x00"
    unicode_suffix = b"\x00\x00"

    volume_offset = header_size
    path_offset = volume_offset + len(volume)
    suffix_offset = path_offset + len(ansi_path)
    unicode_path_offset = suffix_offset + len(suffix)
    unicode_suffix_offset = unicode_path_offset + len(unicode_path)
    size = unicode_suffix_offset + len(unicode_suffix)
    header = struct.pack("<IIIIIIIII", size, header_size, 0x1, volume_offset, path_offset, 0,
                         suffix_offset, unicode_path_offset, unicode_suffix_offset)
    return header + volume + ansi_path + suffix + unicode_path + unicode_suffix


def shortcut_bytes(target: str, arguments: str = "", working_dir: str = "",
                   icon: str = "", description: str = "") -> bytes:
    target = str(PureWindowsPath(target))
    flags = HAS_LINK_INFO | IS_UNICODE | HAS_NAME | HAS_WORKING_DIR | HAS_ARGUMENTS | HAS_ICON_LOCATION
    header = struct.pack("<I16sII", 0x4C, SHELL_LINK_CLSID, flags, 0x20)  # FILE_ATTRIBUTE_ARCHIVE
    header += b"\x00" * 24  # creation, access, write times: unknown
    header += struct.pack("<IiIHHII", 0, 0, SW_SHOWNORMAL, 0, 0, 0, 0)
    assert len(header) == 0x4C
    strings = b"".join(_string(s) for s in (description, working_dir, arguments, icon or target))
    return header + _link_info(target) + strings + b"\x00\x00\x00\x00"


def write_shortcut(path, target: str, arguments: str = "", working_dir: str = "",
                   icon: str = "", description: str = "") -> None:
    with open(path, "wb") as f:
        f.write(shortcut_bytes(target, arguments, working_dir, icon, description))
```

Create `packaging/make_icons.py`:

```python
"""Draw the app icon as 32x32 pixel art and export it at every size needed.

    python packaging/make_icons.py      # -> packaging/icons/*.png, pixel-slides.ico
"""
from pathlib import Path

from PIL import Image

OUT = Path(__file__).parent / "icons"
DARK, MID, LIGHT, PAPER = "#0f380f", "#306230", "#8bac0f", "#c4d88a"

# A slide on an LCD: a dark body, a light screen with a title bar, lines of
# text, a play arrow and a row of "progress" pips. Rectangles on a 32x32 grid.
SHAPES = [
    (MID, 2, 3, 30, 27),     # screen bezel
    (PAPER, 3, 4, 29, 26),   # screen
    (LIGHT, 5, 6, 27, 8),    # title bar
    (DARK, 5, 10, 15, 12),   # heading
    (DARK, 5, 13, 20, 14),   # text lines
    (DARK, 5, 16, 17, 17),
    (DARK, 5, 19, 22, 20),
    (LIGHT, 5, 22, 9, 24),   # progress pips
    (LIGHT, 10, 22, 14, 24),
    (LIGHT, 15, 22, 19, 24),
]
ARROW = [(23, 12, 1), (23, 13, 2), (23, 14, 3), (23, 15, 4), (23, 16, 3), (23, 17, 2), (23, 18, 1)]


def draw() -> Image.Image:
    image = Image.new("RGB", (32, 32), DARK)
    for colour, x0, y0, x1, y1 in SHAPES:
        image.paste(colour, (x0, y0, x1, y1))
    for x, y, width in ARROW:
        image.paste(DARK, (x, y, x + width, y + 1))
    return image.convert("RGBA")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    art = draw()
    big = lambda n: art.resize((n, n), Image.NEAREST)  # noqa: E731 - crisp pixels, no smoothing
    for n in (16, 32, 48, 180, 192, 256, 512):
        big(n).save(OUT / f"icon-{n}.png")
    # Maskable: the art inside the 80% safe zone, on the dark body colour.
    for n in (192, 512):
        canvas = Image.new("RGBA", (n, n), DARK)
        inner = round(n * 0.75)
        canvas.paste(big(inner), ((n - inner) // 2, (n - inner) // 2))
        canvas.save(OUT / f"maskable-{n}.png")
    big(256).save(OUT / "pixel-slides.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


if __name__ == "__main__":
    main()
```

Run it once to make the icons (Pillow is the only extra it needs):

```powershell
python -m pip install pillow
python packaging/make_icons.py
```

You get ten files in `packaging\icons`: `icon-16.png` to `icon-512.png`, two `maskable-*.png` files for the phone app in step 20, and `pixel-slides.ico`.

Create `packaging/after-install.txt`:

```text
Pixel Slides is installed.

Your decks live in Documents\Pixel Slides\decks. The sample deck is copied
there the first time the app starts.

- Press "Edit" next to a deck to open it in your text editor. Save the file
  and the open slides reload on their own.
- "Export PDF" saves to Documents\Pixel Slides\exports, using Microsoft Edge
  in the background (nothing extra to download).
- In a deck, press ? for every keyboard shortcut.

Uninstalling keeps your decks.
```

Create `packaging/uninstall.pyw`. The wizard copies it into the install folder and registers it with Windows:

```python
"""Removes Pixel Slides (installed by the Python wizard). Decks are kept."""
from __future__ import annotations

import shutil
import tkinter as tk
import winreg
from pathlib import Path
from tkinter import messagebox

APP = "Pixel Slides"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\PixelSlides"
HERE = Path(__file__).resolve().parent


def shell_folder(csidl: int) -> Path:
    import ctypes
    from ctypes import wintypes

    buffer = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
    ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buffer)
    return Path(buffer.value)


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    if not messagebox.askyesno(f"Uninstall {APP}", f"Remove {APP} from this PC?\n\n"
                                                    "Your decks in Documents\\Pixel Slides are kept."):
        return
    for place in (shell_folder(2), shell_folder(0)):  # Start menu programs, desktop
        (place / f"{APP}.lnk").unlink(missing_ok=True)
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    except OSError:
        pass
    # This script runs from the base Python, not the app's venv, so the
    # whole folder (venv included) can go.
    shutil.rmtree(HERE, ignore_errors=True)
    messagebox.showinfo(f"Uninstall {APP}", f"{APP} was removed.")


if __name__ == "__main__":
    main()
```

Create `packaging/install_wizard.pyw`. It looks long, but each page is a short method, and the real work is in `install()` near the end:

```python
"""Pixel Slides install wizard for Windows, written in Python.

Double-click "Install Pixel Slides.pyw" (or run: python "Install Pixel Slides.pyw").

Why a Python wizard as well as Setup.exe? Smart App Control and other
application control policies block programs that are not signed by a
publisher Windows knows, and a home-built Setup.exe is not. This wizard only
ever runs Python's own signed programs (python.exe, pythonw.exe), and it
uses "python -m pip" instead of pip.exe, so it gets through.

It installs per user (no admin prompt):
  %LOCALAPPDATA%\\Programs\\Pixel Slides     the app and its own Python environment
  Start menu and desktop shortcuts         run pythonw.exe -m slidedeck app
  Settings > Apps                          lists it, with an uninstaller
Decks stay in Documents\\Pixel Slides and are never removed.
"""
from __future__ import annotations

import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP = "Pixel Slides"
VERSION = "0.3.0"
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "packaging"))
from winlink import write_shortcut  # noqa: E402

UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\PixelSlides"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
COPY = ["slidedeck", "decks", "packaging", "requirements-desktop.txt", "README.md", "INSTALL.md"]
DARK, PAPER, MID = "#0f380f", "#c4d88a", "#306230"


def base_python(windowed: bool = False) -> Path:
    """The installed Python (not a venv), console or windowed."""
    exe = Path(sys._base_executable if hasattr(sys, "_base_executable") else sys.executable)
    name = "pythonw.exe" if windowed else "python.exe"
    return exe.with_name(name) if exe.with_name(name).exists() else exe


def shell_folder(csidl: int) -> Path:
    import ctypes
    from ctypes import wintypes

    buffer = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
    ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buffer)
    return Path(buffer.value)


def start_menu() -> Path:
    return shell_folder(2)  # CSIDL_PROGRAMS


def desktop() -> Path:
    return shell_folder(0)  # CSIDL_DESKTOP


class Wizard(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP} Setup")
        self.geometry("620x440")
        self.resizable(False, False)
        self.configure(bg=PAPER)
        icon = HERE / "packaging" / "icons" / "icon-48.png"
        if icon.exists():
            self.iconphoto(True, tk.PhotoImage(file=str(icon)))

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=PAPER, foreground=DARK, font=("Segoe UI", 10))
        style.configure("TButton", background=DARK, foreground=PAPER, padding=(14, 6), borderwidth=0)
        style.map("TButton", background=[("active", MID), ("disabled", "#8bac0f")])
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 16))
        style.configure("TCheckbutton", background=PAPER)
        style.configure("Horizontal.TProgressbar", background=DARK, troughcolor="#b3cb6f")

        self.folder = tk.StringVar(value=str(Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Programs" / APP))
        self.want_desktop = tk.BooleanVar(value=True)
        self.want_pdf = tk.BooleanVar(value=True)
        self.want_launch = tk.BooleanVar(value=True)
        self.events: queue.Queue = queue.Queue()

        banner = tk.Frame(self, bg=DARK, height=56)
        banner.pack(fill="x")
        tk.Label(banner, text=f"  {APP}", bg=DARK, fg=PAPER, font=("Consolas", 18, "bold")).pack(side="left", pady=10)
        tk.Label(banner, text=f"v{VERSION}  ", bg=DARK, fg="#8bac0f", font=("Consolas", 10)).pack(side="right")

        self.body = ttk.Frame(self, padding=24)
        self.body.pack(fill="both", expand=True)
        nav = ttk.Frame(self, padding=(24, 0, 24, 18))
        nav.pack(fill="x")
        self.cancel_button = ttk.Button(nav, text="Cancel", command=self.destroy)
        self.cancel_button.pack(side="right")
        self.next_button = ttk.Button(nav, text="Next >", command=self.next)
        self.next_button.pack(side="right", padx=8)
        self.back_button = ttk.Button(nav, text="< Back", command=self.back)
        self.back_button.pack(side="right")

        self.pages = [self.page_welcome, self.page_folder, self.page_options, self.page_install, self.page_done]
        self.step = 0
        self.show()

    # --- Pages -----------------------------------------------------------------------

    def heading(self, title: str, text: str) -> None:
        ttk.Label(self.body, text=title, style="Title.TLabel").pack(anchor="w")
        ttk.Label(self.body, text=text, wraplength=560, justify="left").pack(anchor="w", pady=(8, 16))

    def page_welcome(self) -> None:
        self.heading(f"Welcome to {APP}",
                     "This wizard installs Pixel Slides for you only, with no admin rights needed.\n\n"
                     "It sets up a private Python environment for the app, downloads what it needs "
                     "(about 60 MB, so stay online), and adds Start menu and desktop shortcuts.\n\n"
                     f"Using Python {sys.version.split()[0]} from {base_python()}.")
        if sys.version_info < (3, 11):
            ttk.Label(self.body, text="Pixel Slides needs Python 3.11 or newer. Install it from python.org first.",
                      foreground="#5a1414").pack(anchor="w")
            self.next_button.state(["disabled"])

    def page_folder(self) -> None:
        self.heading("Install folder", "Pixel Slides will be installed here. Your decks are kept separately, "
                                       "in Documents\\Pixel Slides.")
        row = ttk.Frame(self.body)
        row.pack(fill="x")
        ttk.Entry(row, textvariable=self.folder).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Browse…", command=self.browse).pack(side="left", padx=(8, 0))

    def browse(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self.folder.get())
        if chosen:
            self.folder.set(str(Path(chosen) / APP) if Path(chosen).name != APP else chosen)

    def page_options(self) -> None:
        self.heading("Options", "Choose what to add.")
        ttk.Checkbutton(self.body, text="Desktop shortcut", variable=self.want_desktop).pack(anchor="w", pady=4)
        ttk.Checkbutton(self.body, text="PDF export (uses Microsoft Edge in the background, about 50 MB)",
                        variable=self.want_pdf).pack(anchor="w", pady=4)
        ttk.Label(self.body, text="\nA Start menu shortcut is always added. Press Install to begin.",
                  wraplength=560).pack(anchor="w")

    def page_install(self) -> None:
        self.heading("Installing", "This takes a minute or two.")
        self.progress = ttk.Progressbar(self.body, mode="determinate", maximum=100)
        self.progress.pack(fill="x")
        self.log = tk.Text(self.body, height=10, bg="#b3cb6f", fg=DARK, relief="flat", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, pady=(12, 0))
        for button in (self.back_button, self.next_button, self.cancel_button):
            button.state(["disabled"])
        # Tk variables belong to the window's thread: read them here, not in the worker.
        options = {"target": Path(self.folder.get()), "desktop": self.want_desktop.get(), "pdf": self.want_pdf.get()}
        threading.Thread(target=self.install, args=(options,), daemon=True).start()
        self.after(100, self.poll)

    def page_done(self) -> None:
        self.heading("Done", f"{APP} is installed. Find it in the Start menu"
                             f"{' and on your desktop' if self.want_desktop.get() else ''}.\n\n"
                             "Your decks are in Documents\\Pixel Slides\\decks. Press Edit next to a deck "
                             "to open it in your text editor; the slides reload when you save.\n\n"
                             "To remove it later: Settings > Apps > Installed apps > Pixel Slides.")
        ttk.Checkbutton(self.body, text=f"Start {APP} now", variable=self.want_launch).pack(anchor="w")
        self.next_button.configure(text="Finish")
        self.back_button.state(["disabled"])
        self.cancel_button.state(["disabled"])

    # --- Navigation ------------------------------------------------------------------

    def show(self) -> None:
        for child in self.body.winfo_children():
            child.destroy()
        self.back_button.state(["!disabled"] if 0 < self.step < 3 else ["disabled"])
        self.next_button.state(["!disabled"])
        self.next_button.configure(text="Install" if self.step == 2 else "Next >")
        self.pages[self.step]()

    def next(self) -> None:
        if self.step == len(self.pages) - 1:
            if self.want_launch.get():
                self.launch()
            self.destroy()
            return
        self.step += 1
        self.show()

    def back(self) -> None:
        self.step = max(0, self.step - 1)
        self.show()

    # --- Work (in a thread; talks to the window through a queue) ---------------------

    def say(self, text: str, percent: int | None = None) -> None:
        self.events.put(("log", text, percent))

    def poll(self) -> None:
        try:
            while True:
                kind, text, percent = self.events.get_nowait()
                if kind == "log":
                    self.log.insert("end", text + "\n")
                    self.log.see("end")
                    if percent is not None:
                        self.progress["value"] = percent
                elif kind == "done":
                    self.step += 1
                    self.show()
                    return
                elif kind == "failed":
                    messagebox.showerror(f"{APP} Setup", text)
                    self.cancel_button.state(["!disabled"])
                    return
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def run(self, *args: str) -> None:
        self.say("> " + " ".join(Path(a).name if os.sep in a else a for a in args))
        result = subprocess.run(args, capture_output=True, text=True, creationflags=NO_WINDOW)
        tail = (result.stdout + result.stderr).strip().splitlines()[-3:]
        for line in tail:
            self.say("  " + line)
        if result.returncode:
            raise RuntimeError(f"This step failed:\n{' '.join(args[1:])}\n\n" + "\n".join(tail))

    def install(self, options: dict) -> None:
        try:
            target = options["target"]
            target.mkdir(parents=True, exist_ok=True)
            self.say(f"Copying the app to {target}", 5)
            for name in COPY:
                source = HERE / name
                if source.is_dir():
                    shutil.copytree(source, target / name, dirs_exist_ok=True,
                                    ignore=shutil.ignore_patterns("__pycache__"))
                elif source.exists():
                    shutil.copy2(source, target / name)
            shutil.copy2(HERE / "packaging" / "uninstall.pyw", target / "uninstall.pyw")

            venv = target / "venv"
            self.say("Creating the app's Python environment", 15)
            if not (venv / "Scripts" / "python.exe").exists():
                self.run(str(base_python()), "-m", "venv", str(venv))
            py = str(venv / "Scripts" / "python.exe")
            self.say("Updating pip", 25)
            self.run(py, "-m", "pip", "install", "--upgrade", "--disable-pip-version-check", "pip")
            self.say("Installing the slide engine (FastAPI, Pydantic, Jinja2, markdown-it)", 35)
            core = [line for line in (target / "requirements-desktop.txt").read_text().splitlines()
                    if line and not line.startswith("#") and not line.startswith(("playwright", "pywebview"))]
            self.run(py, "-m", "pip", "install", "--disable-pip-version-check", *core)

            self.say("Installing the native window (pywebview)", 60)
            try:
                self.run(py, "-m", "pip", "install", "--disable-pip-version-check", "pywebview>=5.0")
            except RuntimeError:
                self.say("  No native window for this Python; the app will open in an Edge app window instead.")
            if options["pdf"]:
                self.say("Installing PDF export (Playwright, drives Edge)", 75)
                self.run(py, "-m", "pip", "install", "--disable-pip-version-check", "playwright>=1.42")

            self.say("Adding shortcuts", 90)
            pythonw = str(venv / "Scripts" / "pythonw.exe")
            icon = str(target / "packaging" / "icons" / "pixel-slides.ico")
            places = [start_menu()] + ([desktop()] if options["desktop"] else [])
            for place in places:
                write_shortcut(place / f"{APP}.lnk", pythonw, "-m slidedeck app", str(target), icon,
                               "Markdown in, handheld-console slides out")
            self.register(target, icon)
            self.say("Finished.", 100)
            self.events.put(("done", "", None))
        except Exception as exc:  # noqa: BLE001 - show every failure to the user
            self.events.put(("failed", f"Setup could not finish.\n\n{exc}", None))

    def register(self, target: Path, icon: str) -> None:
        """List the app in Settings > Apps, with an uninstaller."""
        import winreg

        uninstall = f'"{base_python(windowed=True)}" "{target / "uninstall.pyw"}"'
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
            for name, value in {"DisplayName": APP, "DisplayVersion": VERSION, "Publisher": "TCsM",
                                "DisplayIcon": icon, "InstallLocation": str(target),
                                "UninstallString": uninstall}.items():
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)

    def launch(self) -> None:
        target = Path(self.folder.get())
        subprocess.Popen([str(target / "venv" / "Scripts" / "pythonw.exe"), "-m", "slidedeck", "app"],
                         cwd=target, creationflags=NO_WINDOW)


if __name__ == "__main__":
    if sys.platform != "win32":
        sys.exit("This wizard is for Windows. Elsewhere: python -m slidedeck app")
    Wizard().mainloop()
```

The wizard finds the app relative to its own file (`HERE / "packaging"`, `HERE / "slidedeck"`), so the copy you double-click must sit in the project root. Make that copy with a friendly name:

```powershell
Copy-Item packaging\install_wizard.pyw "Install Pixel Slides.pyw"
```

The `COPY` list also names `README.md` and `INSTALL.md`. Any file on it that does not exist is skipped, so they are optional.

**Check:** double-click `Install Pixel Slides.pyw` in Explorer, or run `python "Install Pixel Slides.pyw"`. A green wizard window opens. Click through it: Install shows a progress bar and a log of each `python -m pip` call, and Finish starts the app. You should find **Pixel Slides** in the Start menu (with the pixel-art icon) and in **Settings > Apps > Installed apps**. Uninstall it from there to check the other half: the shortcuts and the install folder go, and `Documents\Pixel Slides\decks` stays.

**Commit:** `git add .` then `git commit -m "Step 19: Windows install wizard"`

### Step 20: The mobile app

You write `python -m slidedeck mobile`: an installable web app (a PWA) that works offline on a phone, with a deck list, an editor, picture import and sharing.

How it works:

- **The same Python engine runs on the phone.** Pyodide is Python compiled to WebAssembly. The build packs `slidedeck` (engine modules only: no server, no desktop window, no PDF printer) and its pure-Python dependencies into `engine.zip`. Pydantic's compiled core comes as a WebAssembly wheel from PyPI, checked against its SHA-256.
- **Render once, serve from the cache.** When you save a deck, the app calls `site.build` from step 17 in Pyodide and stores every page in the browser's cache. A **service worker** then plays the server's part: it serves those pages, clamps slide numbers like step 3 does, and adds the same security headers as `app.py`.
- **Offline from the first launch.** The build writes `build.json` listing every file, and the service worker stores them all when it installs. The version is a hash of the files, so any change makes phones fetch the update and render their decks again.
- **Same look, no inline code.** The shell reuses `static/` (fonts, CSS, `prefs.js`) and the theme CSS, under a strict Content-Security-Policy.

Create `slidedeck/mobile.py`. `__main__.py` from step 10 already has the `mobile` command and imports this module only when you run it:

```python
"""Build the mobile app: an installable, offline web app (PWA).

    python -m slidedeck mobile                  # -> dist/mobile
    python -m slidedeck mobile --pyodide DIR    # use a Pyodide you already have

The same Python engine runs on the phone, inside Pyodide (Python compiled to
WebAssembly). The app renders a deck's pages once, keeps them in the
browser's cache, and a service worker serves them, so slides open instantly
and work in flight mode. Host the folder on any HTTPS static host (GitHub
Pages, Netlify, Cloudflare Pages), open it on the phone, and choose
"Install app" (Android) or Share > "Add to Home Screen" (iPhone).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import io
import json
import shutil
import tarfile
import urllib.request
import zipfile
from pathlib import Path

from .themes import theme_css

PACKAGE_DIR = Path(__file__).parent
SHELL_DIR = PACKAGE_DIR / "mobile_shell"
PYODIDE_VERSION = "314.0.7"  # Python 3.14, wheels tagged pyemscripten_2026_0
PYODIDE_TARBALL = f"https://registry.npmjs.org/pyodide/-/pyodide-{PYODIDE_VERSION}.tgz"
PYODIDE_FILES = ["pyodide.js", "pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"]
WHEEL_PLATFORM = "pyemscripten_2026_0_wasm32"

# The engine's pure-Python dependencies, copied from this environment.
# pydantic-core is compiled, so it comes as a WebAssembly wheel from PyPI.
PURE_DISTRIBUTIONS = ["pydantic", "typing_extensions", "annotated_types", "typing-inspection",
                      "jinja2", "markupsafe", "markdown-it-py", "mdurl", "pyyaml"]
# The modules the phone needs: no server, no desktop window, no PDF printer.
ENGINE_MODULES = ["__init__.py", "blocks.py", "embeds.py", "lint.py", "models.py", "navigation.py",
                  "parser.py", "render.py", "site.py", "themes.py"]


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310 - fixed https URLs
        return response.read()


def copy_pyodide(target: Path, source: str | None) -> None:
    target.mkdir(parents=True, exist_ok=True)
    if source:
        for name in PYODIDE_FILES:
            shutil.copy2(Path(source) / name, target / name)
        return
    print(f"Downloading Pyodide {PYODIDE_VERSION} (13 MB)…")
    with tarfile.open(fileobj=io.BytesIO(fetch(PYODIDE_TARBALL)), mode="r:gz") as tar:
        for name in PYODIDE_FILES:
            member = tar.extractfile(f"package/{name}")
            (target / name).write_bytes(member.read())


def pydantic_core_wheel(target: Path) -> str:
    """The WebAssembly build of the pydantic-core version pydantic pins."""
    version = metadata.version("pydantic_core")
    index = json.loads(fetch(f"https://pypi.org/pypi/pydantic-core/{version}/json"))
    for file in index["urls"]:
        if file["filename"].endswith(f"-cp314-cp314-{WHEEL_PLATFORM}.whl"):
            data = fetch(file["url"])
            if hashlib.sha256(data).hexdigest() != file["digests"]["sha256"]:
                raise SystemExit(f"Checksum mismatch for {file['filename']}")
            (target / file["filename"]).write_bytes(data)
            return file["filename"]
    raise SystemExit(f"pydantic-core {version} has no {WHEEL_PLATFORM} wheel. "
                     "Upgrade pydantic (python -m pip install -U pydantic) and build again.")


def engine_zip(target: Path) -> None:
    """slidedeck (engine only) plus its pure-Python dependencies, as one zip
    that Pyodide unpacks into its virtual file system."""
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in ENGINE_MODULES:
            zf.write(PACKAGE_DIR / name, f"slidedeck/{name}")
        for path in sorted((PACKAGE_DIR / "templates").rglob("*.html")):
            zf.write(path, f"slidedeck/{path.relative_to(PACKAGE_DIR).as_posix()}")
        for dist_name in PURE_DISTRIBUTIONS:
            dist = metadata.distribution(dist_name)
            for file in dist.files or []:
                parts = file.parts
                if parts[0] in ("..",) or parts[0].endswith(".dist-info") or "__pycache__" in parts:
                    continue
                if file.suffix not in (".py", ".typed", ".pyi") or parts[0] == "bin":
                    continue  # skip compiled speedups: the pure versions are used instead
                zf.write(file.locate(), file.as_posix())


def build(args: argparse.Namespace) -> None:
    out = Path(args.output)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    for path in SHELL_DIR.iterdir():
        if path.is_file():
            shutil.copy2(path, out / path.name)
    shutil.copytree(PACKAGE_DIR / "static", out / "static", ignore=shutil.ignore_patterns("desktop.js"))
    (out / "themes.css").write_text(theme_css(), encoding="utf-8")

    icons = Path(__file__).resolve().parent.parent / "packaging" / "icons"
    (out / "icons").mkdir()
    for name in ["icon-180.png", "icon-192.png", "icon-512.png", "maskable-192.png", "maskable-512.png", "icon-32.png"]:
        shutil.copy2(icons / name, out / "icons" / name)

    decks = Path(__file__).resolve().parent.parent / "decks"
    (out / "samples").mkdir()
    for path in sorted(decks.glob("*.md")):
        shutil.copy2(path, out / "samples" / path.name)
    if (decks / "media").is_dir():
        shutil.copytree(decks / "media", out / "media")

    copy_pyodide(out / "pyodide", args.pyodide)
    wheel = pydantic_core_wheel(out / "pyodide")
    engine_zip(out / "engine.zip")

    # Everything the service worker stores at install time, so the app works
    # offline from the first launch. The version changes whenever a file does,
    # which makes phones fetch the update and re-render their decks.
    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    digest = hashlib.sha256()
    for name in files:
        digest.update(name.encode())
        digest.update((out / name).read_bytes())
    version = digest.hexdigest()[:12]
    manifest = {"version": version, "files": ["./" if f == "index.html" else f for f in files],
                "samples": sorted(p.name for p in (out / "samples").glob("*.md")),
                "wheel": f"pyodide/{wheel}"}
    (out / "build.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    sw = (out / "sw.js").read_text(encoding="utf-8").replace("__VERSION__", version)
    (out / "sw.js").write_text(sw, encoding="utf-8")

    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"Wrote {out} ({len(files)} files, {size / 1e6:.1f} MB, version {version})")
```

The rest of this step is the app shell, five files in a new folder, `slidedeck/mobile_shell`.

Create `slidedeck/mobile_shell/manifest.webmanifest`. It gives the app its name, colours and home-screen icons:

```json
{
  "name": "Pixel Slides",
  "short_name": "Pixel Slides",
  "description": "Markdown in, handheld-console slides out. Works offline.",
  "id": "./",
  "start_url": "./",
  "scope": "./",
  "display": "standalone",
  "orientation": "any",
  "background_color": "#0f380f",
  "theme_color": "#0f380f",
  "categories": ["productivity", "education"],
  "icons": [
    { "src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "icons/maskable-192.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable" },
    { "src": "icons/maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ]
}
```

Create `slidedeck/mobile_shell/index.html`. It reuses the library's class names from step 11, so `slides.css` already styles most of it:

```html
<!doctype html>
<html lang="en" class="theme-dmg" data-default-theme="dmg" data-themes="dmg pocket berry night contrast">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; font-src 'self'; img-src 'self' data: blob:; connect-src 'self'; worker-src 'self'; object-src 'none'; base-uri 'none'">
  <title>Pixel Slides</title>
  <link rel="manifest" href="manifest.webmanifest">
  <meta name="theme-color" content="#0f380f">
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-title" content="Pixel Slides">
  <link rel="apple-touch-icon" href="icons/icon-180.png">
  <link rel="icon" href="icons/icon-32.png">
  <link rel="stylesheet" href="static/fonts/fonts.css">
  <link rel="stylesheet" href="themes.css">
  <link rel="stylesheet" href="static/theme.css">
  <link rel="stylesheet" href="static/slides.css">
  <link rel="stylesheet" href="app.css">
  <script src="static/prefs.js"></script>
  <script src="app.js" type="module"></script>
</head>
<body class="library-view">
<main class="library-list-container">
  <p class="library-list-kicker">Pixel Slides</p>

  <section data-view="library" aria-labelledby="library-heading">
    <h1 class="library-list-header" id="library-heading">Select a deck</h1>
    <div class="library-toolbar-row" role="toolbar" aria-label="Deck tools">
      <button type="button" class="library-toolbar-button" data-action="new">New deck</button>
      <label class="library-toolbar-button">Import .md<input type="file" class="visually-hidden" accept=".md,.markdown,.txt,text/markdown,text/plain" data-import></label>
      <button type="button" class="library-toolbar-button" data-action="install" hidden>Install app</button>
    </div>
    <ul class="library-list-items" data-deck-list>
      <li class="library-list-item">Loading…</li>
    </ul>
  </section>

  <section data-view="editor" aria-labelledby="editor-heading" hidden>
    <h1 class="library-list-header" id="editor-heading" data-editor-title>Edit deck</h1>
    <div class="library-toolbar-row" role="toolbar" aria-label="Editor tools">
      <button type="button" class="library-toolbar-button" data-action="play">Save and play</button>
      <button type="button" class="library-list-item-action" data-action="save">Save</button>
      <label class="library-list-item-action">Add picture<input type="file" class="visually-hidden" accept="image/png,image/jpeg,image/gif,image/webp,image/avif,image/svg+xml" data-picture></label>
      <button type="button" class="library-list-item-action" data-action="share">Share .md</button>
      <button type="button" class="library-list-item-action" data-action="back">Back</button>
    </div>
    <label class="editor-pane-label" for="editor-source">Deck in Markdown. A <code>---</code> line with a blank line before it starts a new slide.</label>
    <textarea class="editor-pane-source" id="editor-source" spellcheck="false" autocapitalize="off" autocomplete="off" data-source></textarea>
    <div class="editor-pane-report" data-report></div>
    <p><button type="button" class="library-list-item-action editor-pane-delete" data-action="delete">Delete this deck</button></p>
  </section>

  <p class="library-toolbar-status" role="status" aria-live="polite" data-status></p>
</main>

<div class="engine-boot-screen" data-boot hidden>
  <p class="engine-boot-screen-logo">Pixel Slides</p>
  <p class="engine-boot-screen-hint" data-boot-text>Starting the engine…</p>
</div>
</body>
</html>
```

Create `slidedeck/mobile_shell/app.css`, the styles only the phone app needs:

```css
/* Mobile app only: the editor and the engine start-up screen. */

.library-view { padding: env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left); }
label.library-toolbar-button, label.library-list-item-action { display: inline-grid; place-items: center; }
label.library-toolbar-button:focus-within, label.library-list-item-action:focus-within { outline: var(--px) solid var(--accent); outline-offset: var(--px); }

.editor-pane-label { display: block; margin: 0 0 8px; font-size: 20px; color: var(--muted); }
.editor-pane-label code { font-family: var(--font-mono); color: var(--ink); }
.editor-pane-source {
  box-sizing: border-box;
  width: 100%; min-height: 55vh;
  padding: 12px;
  border: var(--px) solid var(--ink);
  background: var(--raised); color: var(--ink);
  font-family: "Atkinson Hyperlegible Mono", Consolas, monospace; font-size: 16px; line-height: 1.5;
  resize: vertical;
}
.editor-pane-source:focus-visible { outline: var(--px) solid var(--accent); outline-offset: var(--px); }
.editor-pane-report { margin: 16px 0; font-size: 22px; }
.editor-pane-report p { margin: 0 0 8px; }
.editor-pane-error { color: var(--error); }
.editor-pane-issues { margin: 0; padding-left: 1.2em; }
.editor-pane-issue.is-error { color: var(--error); }
.editor-pane-delete { border-color: var(--error); color: var(--error); }

.engine-boot-screen {
  position: fixed; inset: 0; z-index: 100;
  display: grid; place-content: center; gap: 24px; text-align: center;
  background: var(--inverse-paper); color: var(--inverse-ink);
}
.engine-boot-screen[hidden] { display: none; }
.engine-boot-screen-logo { margin: 0; font-family: var(--font-display); font-size: clamp(18px, 6vw, 32px); }
.engine-boot-screen-hint { margin: 0; font-family: var(--font-label); font-size: 14px; text-transform: uppercase; animation: engine-blink 1s steps(2, end) infinite; }
@keyframes engine-blink { 50% { opacity: 0; } }
```

Create `slidedeck/mobile_shell/sw.js`, the service worker. `__VERSION__` is a placeholder that `mobile.py` fills in at build time:

```javascript
// Service worker for the mobile app. It plays the server's part:
//  - the app's own files come from a cache filled at install (works offline);
//  - deck pages come from a second cache, which the app fills when it
//    renders a deck with the Python engine;
//  - it clamps slide numbers and adds the same security headers as the server.
"use strict";

const VERSION = "__VERSION__";
const SHELL = `pixel-slides-shell-${VERSION}`;
const USER = "pixel-slides-user";  // decks, their rendered pages, added pictures
const base = new URL(self.registration.scope).pathname.replace(/\/$/, "");

const CSP = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self'",
  "font-src 'self'",
  "img-src 'self' https: data: blob:",
  "media-src 'self'",
  "frame-src https://www.youtube-nocookie.com https://player.vimeo.com",
  "connect-src 'self'",
  "object-src 'none'",
  "base-uri 'none'",
].join("; ");

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const build = await (await fetch("build.json", { cache: "reload" })).json();
    const cache = await caches.open(SHELL);
    await cache.addAll(["build.json", ...build.files].map((file) => new Request(file, { cache: "reload" })));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    for (const name of await caches.keys()) {
      if (name.startsWith("pixel-slides-shell-") && name !== SHELL) await caches.delete(name);
    }
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== location.origin) return;
  if (!(url.pathname + "/").startsWith(base + "/")) return;
  event.respondWith(handle(event.request, url, url.pathname.slice(base.length) || "/"));
});

async function handle(request, url, path) {
  const user = await caches.open(USER);
  if (path.startsWith("/deck/")) return deckPage(user, url, path);
  if (path.startsWith("/media/")) {
    const added = await user.match(url.origin + url.pathname);
    if (added) return added;
  }
  const shell = await (await caches.open(SHELL)).match(request, { ignoreSearch: true });
  if (shell) return shell;
  try {
    return await fetch(request);
  } catch {
    return page(404, "Not found", "This page is not stored on this device.");
  }
}

const userKey = (url, path) => `${url.origin}${base}${path}`;

async function deckPage(user, url, path) {
  const match = path.match(/^\/deck\/([a-z0-9][a-z0-9-]{0,63})(?:\/(.*))?$/);
  if (!match) return page(404, "No such deck", "Deck names use a to z, 0 to 9 and dashes.");
  const [, name, rest = ""] = match;

  // ?theme= is applied in the page itself, so it never changes the stored page.
  let key = userKey(url, `/deck/${name}${rest ? `/${rest}` : ""}`);
  if (rest === "text" && url.searchParams.get("notes") === "1") key += "?notes=1";
  const stored = await user.match(key);
  if (stored) return withHeaders(stored);

  const summary = await user.match(userKey(url, `/__decks/${name}.json`));
  if (!summary) return page(404, "No such deck", "It may have been deleted on this device.");
  const { count } = await summary.json();

  // The same rule as the server: one URL per slide, always in range.
  const number = rest.match(/^(-?\d+)(\/presenter)?$/);
  if (rest === "" || number) {
    const wanted = number ? Number(number[1]) : 1;
    const clamped = Math.max(1, Math.min(Number.isFinite(wanted) ? wanted : 1, count));
    const target = new URL(`${base}/deck/${name}/${clamped}${number?.[2] || ""}`, url);
    target.search = url.search;
    return Response.redirect(target.href, 302);
  }
  return page(404, "Not found", `'${rest}' is not a page of this deck.`);
}

function withHeaders(response) {
  const headers = new Headers(response.headers);
  headers.set("Content-Type", "text/html; charset=utf-8");
  headers.set("Content-Security-Policy", CSP);
  headers.set("X-Content-Type-Options", "nosniff");
  headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  return new Response(response.body, { status: response.status, headers });
}

function page(status, title, text) {
  const escape = (s) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const body = `<!doctype html><html lang="en" class="theme-dmg"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>${escape(title)}</title>
<link rel="stylesheet" href="${base}/static/fonts/fonts.css"><link rel="stylesheet" href="${base}/themes.css">
<link rel="stylesheet" href="${base}/static/theme.css"><link rel="stylesheet" href="${base}/static/slides.css">
<body class="library-view"><main class="library-list-container"><p class="library-list-kicker">Error ${status}</p>
<h1 class="library-list-header">${escape(title)}</h1><p>${escape(text)}</p>
<p><a class="library-list-item-link" href="${base}/">Back to decks</a></p></main>`;
  return withHeaders(new Response(body, { status }));
}
```

Create `slidedeck/mobile_shell/app.js`, the deck list and editor. Read it in its four parts: storage, the engine, the library, then the editor and its buttons:

```javascript
// The mobile app's deck list and editor. Decks are rendered by the same Python
// engine as the desktop (in Pyodide), and the pages are stored in the
// browser's cache, where the service worker serves them, offline included.

const base = new URL(".", location.href).pathname.replace(/\/$/, "");
const USER = "pixel-slides-user";
const IMAGE_TYPES = { "image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/webp": "webp", "image/avif": "avif", "image/svg+xml": "svg" };

const $ = (selector) => document.querySelector(selector);
const statusLine = $("[data-status]");
const say = (text) => { statusLine.textContent = text; };
const key = (path) => `${location.origin}${base}${path}`;
const store = () => caches.open(USER);

// --- Storage ----------------------------------------------------------------------

async function readJson(path) {
  const hit = await (await store()).match(key(path));
  return hit ? hit.json() : null;
}

async function writeFile(path, body, type) {
  await (await store()).put(key(path), new Response(body, { headers: { "Content-Type": type } }));
}

async function listDecks() {
  const cache = await store();
  const names = (await cache.keys())
    .map((request) => new URL(request.url).pathname.match(/\/__decks\/([a-z0-9-]+)\.json$/)?.[1])
    .filter(Boolean);
  const decks = await Promise.all(names.map((name) => readJson(`/__decks/${name}.json`)));
  return decks.filter(Boolean).sort((a, b) => a.title.localeCompare(b.title));
}

async function readSource(name) {
  const hit = await (await store()).match(key(`/__decks/${name}.md`));
  return hit ? hit.text() : "";
}

async function deleteDeck(name) {
  const cache = await store();
  for (const request of await cache.keys()) {
    const path = new URL(request.url).pathname.slice(base.length);
    if (path.startsWith(`/deck/${name}/`) || path === `/__decks/${name}.md` || path === `/__decks/${name}.json`) {
      await cache.delete(request);
    }
  }
}

// --- The engine (Python in WebAssembly), loaded on first use -------------------------

let engine = null;

async function loadEngine() {
  if (engine) return engine;
  const boot = $("[data-boot]");
  boot.hidden = false;
  try {
    const build = await (await fetch(`${base}/build.json`)).json();
    const { loadPyodide } = await import(`${base}/pyodide/pyodide.mjs`);
    const py = await loadPyodide({ indexURL: `${base}/pyodide/` });
    await py.loadPackage(`${base}/${build.wheel}`, { messageCallback: () => {} });
    const zip = await (await fetch(`${base}/engine.zip`)).arrayBuffer();
    py.unpackArchive(new Uint8Array(zip), "zip", { extractDir: "/engine" });
    py.runPython("import sys; sys.path.insert(0, '/engine')");
    $("[data-boot-text]").textContent = "Loading the slide engine…";
    engine = py.pyimport("slidedeck.site");
    return engine;
  } finally {
    boot.hidden = true;
  }
}

async function renderDeck(name, source) {
  const site = await loadEngine();
  const result = JSON.parse(site.build(name, source, base));
  await writeFile(`/__decks/${name}.md`, source, "text/markdown; charset=utf-8");
  if (!result.ok) return result;
  const cache = await store();
  const keep = new Set(Object.keys(result.pages).map(key));
  for (const request of await cache.keys()) {
    const path = new URL(request.url).pathname.slice(base.length);
    if (path.startsWith(`/deck/${name}/`) && !keep.has(request.url)) await cache.delete(request);
  }
  await Promise.all(Object.entries(result.pages).map(([path, html]) =>
    cache.put(key(path), new Response(html, { headers: { "Content-Type": "text/html; charset=utf-8" } }))));
  await writeFile(`/__decks/${name}.json`, JSON.stringify(result.summary), "application/json");
  return result;
}

// First start: the sample decks. After an app update: render every deck again,
// since the templates may have changed.
async function syncWithBuild() {
  const build = await (await fetch(`${base}/build.json`)).json();
  const meta = (await readJson("/__meta.json")) || {};
  if (meta.version === build.version) return;
  const names = new Set((await listDecks()).map((deck) => deck.name));
  if (!meta.version) {
    for (const file of build.samples) {
      const name = file.replace(/\.md$/, "");
      if (!names.has(name)) await writeFile(`/__decks/${name}.md`, await (await fetch(`${base}/samples/${file}`)).text(), "text/markdown");
      names.add(name);
    }
  }
  for (const name of names) {
    say(`Preparing ${name}…`);
    await renderDeck(name, await readSource(name));
  }
  await writeFile("/__meta.json", JSON.stringify({ version: build.version }), "application/json");
  say("");
}

// --- Library ----------------------------------------------------------------------

function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children.filter((child) => child !== null && child !== undefined));
  return node;
}
const hidden = (text) => el("span", { className: "visually-hidden", textContent: text });

async function showLibrary() {
  showView("library");
  const list = $("[data-deck-list]");
  const decks = await listDecks();
  list.replaceChildren(...decks.map((deck) => el("li", { className: "library-list-item" },
    el("a", { className: "library-list-item-link", href: `${base}/deck/${deck.name}/1` },
      el("span", { className: "library-list-item-cursor", ariaHidden: "true", textContent: "▶" }),
      el("span", { className: "library-list-item-title", textContent: deck.title }),
      el("span", { className: "library-list-item-meta", textContent: `${deck.count} slides · ${deck.theme_label}` })),
    el("a", { className: "library-list-item-text", href: `${base}/deck/${deck.name}/text` }, "Text version", hidden(` of ${deck.title}`)),
    el("button", { type: "button", className: "library-list-item-action", onclick: () => openEditor(deck.name) }, "Edit", hidden(` ${deck.title}`)),
  )));
  if (!decks.length) list.append(el("li", { className: "library-list-item", textContent: "No decks yet. Press New deck." }));
}

function showView(name) {
  for (const view of document.querySelectorAll("[data-view]")) view.hidden = view.dataset.view !== name;
  document.title = name === "editor" ? "Edit deck · Pixel Slides" : "Pixel Slides";
}

const slugify = (text) => text.toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 48).replace(/-+$/, "") || "deck";

async function freeName(wanted) {
  const taken = new Set((await listDecks()).map((deck) => deck.name));
  let name = slugify(wanted);
  for (let n = 2; taken.has(name); n += 1) name = `${slugify(wanted)}-${n}`;
  return name;
}

const NEW_DECK = (title) => `---
title: ${title}
theme: dmg
lang: en
---
class: title

### New deck
# ${title}

Tap Save and play to see it.

???
Speaker notes go after three question marks.

---

## A second slide

:::dialog GUIDE
Blocks start with three colons.
:::
`;

// --- Editor -----------------------------------------------------------------------

let editing = null;
const source = $("[data-source]");

async function openEditor(name) {
  editing = name;
  source.value = await readSource(name);
  $("[data-editor-title]").textContent = `Edit ${name}`;
  $("[data-report]").replaceChildren();
  showView("editor");
  say("");
  source.focus();
}

function report(result) {
  const box = $("[data-report]");
  if (!result.ok) {
    box.replaceChildren(el("p", { className: "editor-pane-error", textContent: `Not saved as slides: ${result.error}` }));
    return;
  }
  const issues = result.summary.issues;
  box.replaceChildren(
    el("p", { textContent: `${result.summary.count} slides. ${issues.length ? `${issues.length} thing(s) to check:` : "No problems found."}` }),
    issues.length ? el("ul", { className: "editor-pane-issues" }, ...issues.map((issue) =>
      el("li", { className: `editor-pane-issue is-${issue.level}`, textContent: `Slide ${issue.slide}: ${issue.message}` }))) : null,
  );
}

async function save() {
  say("Rendering…");
  const result = await renderDeck(editing, source.value);
  report(result);
  say(result.ok ? "Saved." : "Saved the text, but the deck has an error.");
  return result;
}

async function addPicture(file) {
  const ext = IMAGE_TYPES[file.type];
  if (!ext) return say("That picture type is not supported.");
  const name = `${slugify(file.name.replace(/\.[^.]+$/, ""))}.${ext}`;
  await writeFile(`/media/${name}`, file, file.type);
  const snippet = `\n:::gallery\n![Describe the picture](media/${name})\n:::\n`;
  const at = source.selectionEnd ?? source.value.length;
  source.setRangeText(snippet, at, at, "end");
  source.focus();
  say(`Added ${name}. Describe it in the brackets: that text is read to people who cannot see it.`);
}

async function share() {
  const file = new File([source.value], `${editing}.md`, { type: "text/markdown" });
  if (navigator.canShare?.({ files: [file] })) {
    try { await navigator.share({ files: [file], title: editing }); } catch { /* cancelled */ }
    return;
  }
  const link = el("a", { href: URL.createObjectURL(file), download: file.name });
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

// --- Wiring -------------------------------------------------------------------------

const actions = {
  async new() {
    const title = (prompt("Title of the new deck", "My talk") || "").trim();
    if (!title) return;
    const name = await freeName(title);
    await writeFile(`/__decks/${name}.md`, NEW_DECK(title.replace(/\n/g, " ")), "text/markdown");
    await openEditor(name);
  },
  async play() {
    const result = await save();
    if (result.ok) location.href = `${base}/deck/${editing}/1`;
  },
  save,
  share,
  async back() { await showLibrary(); },
  async delete() {
    if (!confirm(`Delete ${editing}? This cannot be undone.`)) return;
    await deleteDeck(editing);
    say(`Deleted ${editing}.`);
    await showLibrary();
  },
  async install() {
    installPrompt?.prompt();
    installPrompt = null;
    $('[data-action="install"]').hidden = true;
  },
};

document.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  button.disabled = true;
  try {
    await actions[button.dataset.action]();
  } catch (error) {
    say(`Something went wrong: ${error.message}`);
  } finally {
    button.disabled = false;
  }
});

$("[data-import]").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  event.target.value = "";
  if (!file) return;
  const name = await freeName(file.name.replace(/\.[^.]+$/, ""));
  const result = await renderDeck(name, await file.text());
  await showLibrary();
  say(result.ok ? `Imported ${name}.` : `Imported ${name}, but it has an error: ${result.error}`);
});

$("[data-picture]").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  event.target.value = "";
  if (file) await addPicture(file);
});

let installPrompt = null;
addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  installPrompt = event;
  $('[data-action="install"]').hidden = false;
});

async function start() {
  if (!("serviceWorker" in navigator) || !("caches" in window)) {
    say("This browser cannot run Pixel Slides offline. Open it in Chrome, Edge, Safari or Firefox over https.");
    return;
  }
  await navigator.serviceWorker.register(`${base}/sw.js`);
  if (!navigator.serviceWorker.controller) {
    // First visit: wait until the worker has stored the app and taken over.
    say("Installing for offline use…");
    await new Promise((resolve) => navigator.serviceWorker.addEventListener("controllerchange", resolve, { once: true }));
  }
  await syncWithBuild();
  await showLibrary();
}

start().catch((error) => say(`Could not start: ${error.message}`));
```

Finally, the tests for steps 17 to 20 together. Create `tests/test_apps.py`:

```python
"""The desktop and mobile packaging: static rendering, URL base, desktop API, shortcuts."""
import json
import re
import sys
import zipfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from slidedeck import site
from slidedeck.desktop import NEW_DECK, WindowHost, make_router, slugify
from slidedeck.render import env

ROOT = Path(__file__).parent.parent
INTRO = (ROOT / "decks" / "intro.md").read_text(encoding="utf-8")
sys.path.insert(0, str(ROOT / "packaging"))


# --- Static rendering (the mobile app) ---------------------------------------------


def test_build_renders_every_page():
    result = json.loads(site.build("intro", INTRO))
    count = result["summary"]["count"]
    pages = result["pages"]
    assert result["ok"] and count == 15
    for n in range(1, count + 1):
        assert f"/deck/intro/{n}" in pages and f"/deck/intro/{n}/presenter" in pages
    assert {"/deck/intro/text", "/deck/intro/text?notes=1", "/deck/intro/print"} <= pages.keys()
    assert 'data-index="2"' in pages["/deck/intro/3"]


def test_build_reports_deck_errors_instead_of_raising():
    result = json.loads(site.build("bad", "---\ntheme: nope\n---\n# Hi\n"))
    assert result == {"ok": False, "error": result["error"]} and "unknown theme" in result["error"]


def test_base_prefixes_every_site_link():
    pages = json.loads(site.build("intro", INTRO, "/pixel-slides"))["pages"]
    for html in pages.values():
        links = re.findall(r'(?:href|src)="(/[^"]*)"', html)
        assert links and all(link.startswith("/pixel-slides/") for link in links)
    assert env.globals["base"] == ""  # reset for the server afterwards


def test_no_external_fonts_or_inline_styles():
    for html in json.loads(site.build("intro", INTRO))["pages"].values():
        assert "fonts.googleapis.com" not in html
        assert " style=" not in html


def test_bundled_fonts_exist():
    css = (ROOT / "slidedeck" / "static" / "fonts" / "fonts.css").read_text()
    files = re.findall(r"url\(([^)]+)\)", css)
    assert len(files) >= 9
    for name in files:
        assert (ROOT / "slidedeck" / "static" / "fonts" / name).is_file()


def test_engine_zip_has_engine_but_no_server(tmp_path):
    from slidedeck.mobile import engine_zip

    engine_zip(tmp_path / "engine.zip")
    names = set(zipfile.ZipFile(tmp_path / "engine.zip").namelist())
    assert {"slidedeck/site.py", "slidedeck/templates/deck.html", "jinja2/__init__.py",
            "markdown_it/__init__.py", "pydantic/__init__.py", "yaml/__init__.py"} <= names
    assert "slidedeck/app.py" not in names and "slidedeck/desktop.py" not in names
    assert not any(name.endswith((".so", ".pyd")) for name in names)


# --- Desktop API -------------------------------------------------------------------------


@pytest.fixture
def desktop(tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr("slidedeck.desktop.open_path", lambda path, reveal=False: opened.append(path) or True)
    decks = tmp_path / "decks"
    decks.mkdir()
    (decks / "intro.md").write_text(INTRO, encoding="utf-8")
    app = FastAPI()
    public, router = make_router(decks, tmp_path / "exports", "secret", WindowHost("http://x"))
    app.include_router(public)
    app.include_router(router)
    return TestClient(app), decks, opened


def test_desktop_api_needs_the_token(desktop):
    client, _, opened = desktop
    assert client.get("/desktop/ping").json() == {"app": "pixel-slides"}
    assert client.post("/desktop/open-folder").status_code == 403
    assert client.post("/desktop/open-folder", headers={"X-Desktop-Token": "wrong"}).status_code == 403
    assert client.post("/desktop/open-folder", headers={"X-Desktop-Token": "secret"}).status_code == 200
    assert len(opened) == 1


def test_new_deck_gets_a_free_name_and_parses(desktop):
    client, decks, _ = desktop
    headers = {"X-Desktop-Token": "secret"}
    first = client.post("/desktop/new-deck", json={"title": "My Talk!"}, headers=headers).json()
    second = client.post("/desktop/new-deck", json={"title": "My Talk!"}, headers=headers).json()
    assert (first["name"], second["name"]) == ("my-talk", "my-talk-2")
    assert json.loads(site.build("my-talk", (decks / "my-talk.md").read_text()))["ok"]


def test_desktop_api_rejects_bad_names_and_urls(desktop):
    client, _, _ = desktop
    headers = {"X-Desktop-Token": "secret"}
    assert client.post("/desktop/edit/..%2Fsecrets", headers=headers).status_code == 404
    assert client.post("/desktop/edit/missing", headers=headers).status_code == 404
    assert client.post("/desktop/window", json={"url": "https://evil.example"}, headers=headers).status_code == 400
    assert client.post("/desktop/window", json={"url": "//evil.example"}, headers=headers).status_code == 400
    assert client.post("/desktop/window", json={"url": "/deck/intro/1"}, headers=headers).json() == {"opened": False}


@pytest.mark.parametrize("title, slug", [("Hello World", "hello-world"), ("  ", "deck"), ("Ça va?", "a-va"), ("x" * 80, "x" * 48)])
def test_slugify(title, slug):
    assert slugify(title) == slug


def test_new_deck_template_is_valid():
    assert json.loads(site.build("t", NEW_DECK.format(title="T")))["ok"]


# --- Windows shortcut writer ---------------------------------------------------------------


def test_shortcut_layout():
    from winlink import shortcut_bytes

    data = shortcut_bytes(r"C:\App\venv\Scripts\pythonw.exe", "-m slidedeck app", r"C:\App", r"C:\App\icon.ico", "Pixel Slides")
    assert data[:4] == b"\x4c\x00\x00\x00"
    link_info_size = int.from_bytes(data[0x4C:0x50], "little")
    strings = data[0x4C + link_info_size:]
    assert "-m slidedeck app".encode("utf-16-le") in strings
    assert strings.endswith(b"\x00\x00\x00\x00")
    assert r"C:\App\venv\Scripts\pythonw.exe".encode("utf-16-le") in data[0x4C:0x4C + link_info_size]
```

**Check:**

```powershell
python -m pytest tests/test_apps.py
```

You should see **15 passed**. Then build the phone app and try it in your browser (the first build downloads Pyodide, about 13 MB, so stay online):

```powershell
python -m slidedeck mobile
python -m http.server 8080 --directory dist/mobile
```

Open http://localhost:8080 in Edge or Chrome. It says "Installing for offline use", then "Starting the engine" while Python loads, and then lists the sample deck. Press **Edit**, change a word and press **Save and play**. Stop the server with Ctrl+C and reload: everything still works, because it is all in the browser's cache now. To use it on a phone, put `dist/mobile` on any HTTPS static host (GitHub Pages, Netlify or Cloudflare Pages), open it on the phone, and choose **Install app** (Android) or **Share > Add to Home Screen** (iPhone).

**Commit:** add `dist/` to `.gitignore` if it is not there yet, then `git add .` and `git commit -m "Step 20: offline mobile app"`

### Step 21: Setup.exe and automatic builds (optional)

You add the classic route for other PCs: a one-folder `Pixel Slides.exe` built with PyInstaller, a `PixelSlides-Setup.exe` built with Inno Setup, and a GitHub Actions workflow that runs the tests, builds the installer and publishes the phone app to GitHub Pages on every push.

This step is optional, and on your own PC it is mostly for other people. A home-built exe is not signed by a publisher Windows knows, so **Smart App Control blocks it on a PC like yours**. That is why step 19 exists. Setup.exe is for PCs without application control, and the workflow builds it on GitHub's machines, so you never have to run it locally.

How it works:

- **`launch.py`** is the entry point for the frozen app. It only calls `desktop.main()` from step 18.
- **The spec file** tells PyInstaller what to bundle: the templates, the static files and the sample decks as data, plus the uvicorn modules it loads by name (PyInstaller cannot see those imports).
- **The Inno Setup script** installs per user into `%LOCALAPPDATA%\Programs\Pixel Slides`, like the Python wizard, and shows `after-install.txt` at the end.
- **`build-windows.ps1`** does it all in order, in its own `.venv-build`, and always with `python -m pip`.

Create `packaging/launch.py`:

```python
"""Entry point for the frozen desktop app (PyInstaller)."""
from slidedeck.desktop import main

if __name__ == "__main__":
    main()
```

Create `packaging/pixel-slides.spec`:

```python
# PyInstaller recipe for the desktop app: python -m PyInstaller packaging/pixel-slides.spec
# Builds dist/Pixel Slides/ (one folder: starts faster than a one-file exe and
# is what the installer wizard copies).
from pathlib import Path

ROOT = Path(SPECPATH).parent

a = Analysis(
    [str(ROOT / "packaging" / "launch.py")],
    pathex=[str(ROOT)],
    datas=[
        (str(ROOT / "slidedeck" / "templates"), "slidedeck/templates"),
        (str(ROOT / "slidedeck" / "static"), "slidedeck/static"),
        (str(ROOT / "decks"), "decks"),
    ],
    hiddenimports=["slidedeck.app", "uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.auto",
                   "uvicorn.protocols.websockets.auto", "uvicorn.lifespan.on"],
    excludes=["tkinter", "pytest"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="Pixel Slides",
    icon=str(ROOT / "packaging" / "icons" / "pixel-slides.ico"),
    console=False,
    version=None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Pixel Slides")
```

Create `packaging/pixel-slides.iss`:

```text
; Inno Setup script: the classic Windows install wizard for Pixel Slides.
; Build the app first (packaging\build-windows.ps1 does both), then:
;   iscc packaging\pixel-slides.iss      -> dist\installer\PixelSlides-Setup-<version>.exe
;
; Installs per user (no admin prompt) into %LOCALAPPDATA%\Programs\Pixel Slides.
; Decks live in Documents\Pixel Slides and are kept on uninstall.

#define AppName "Pixel Slides"
#ifndef AppVersion
  #define AppVersion "0.3.0"
#endif

[Setup]
AppId={{6B1E3A52-4C1D-4E59-9C1B-50F1A6D2E8C3}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=TCsM
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=yes
InfoAfterFile=after-install.txt
OutputDir=..\dist\installer
OutputBaseFilename=PixelSlides-Setup-{#AppVersion}
SetupIconFile=icons\pixel-slides.ico
UninstallDisplayIcon={app}\Pixel Slides.exe
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\Pixel Slides\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\Pixel Slides.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Pixel Slides.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Pixel Slides.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
```

Create `packaging/build-windows.ps1`:

```powershell
# Builds the Windows app and its Setup wizard:
#   dist\Pixel Slides\Pixel Slides.exe            (the app, one folder)
#   dist\installer\PixelSlides-Setup-<ver>.exe    (the install wizard)
#
# Run from anywhere:  powershell -ExecutionPolicy Bypass -File packaging\build-windows.ps1
# Needs Python 3.11+ and Inno Setup 6 (winget install JRSoftware.InnoSetup).
# Uses "python -m pip" throughout, never pip.exe, so Smart App Control is happy.
param([string]$Version = "0.3.0")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path ".venv-build")) { python -m venv .venv-build }
$py = ".venv-build\Scripts\python.exe"
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements-desktop.txt pyinstaller pillow
if ($LASTEXITCODE) { throw "pip install failed" }

& $py packaging\make_icons.py
& $py -m PyInstaller --noconfirm --clean --distpath dist --workpath build packaging\pixel-slides.spec
if ($LASTEXITCODE) { throw "PyInstaller failed" }

$iscc = (Get-Command iscc -ErrorAction SilentlyContinue).Source
foreach ($candidate in @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
                         "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe")) {
    if (-not $iscc -and (Test-Path $candidate)) { $iscc = $candidate }
}
if (-not $iscc) {
    Write-Warning "Inno Setup not found. The app is built in dist\Pixel Slides. For the wizard: winget install JRSoftware.InnoSetup, then run this again."
    exit 0
}
& $iscc "/DAppVersion=$Version" packaging\pixel-slides.iss
if ($LASTEXITCODE) { throw "Inno Setup failed" }
Write-Host "Done: dist\installer\PixelSlides-Setup-$Version.exe"
```

Create `.github/workflows/build-apps.yml` (two new folders, `.github` and `workflows` inside it):

```yaml
# Builds the Windows installer and publishes the mobile app.
#   - Every push: tests, then PixelSlides-Setup.exe as a downloadable artifact.
#   - Push to main: the mobile app goes to GitHub Pages
#     (Settings > Pages > Source: GitHub Actions, once).
name: Build apps

on:
  push:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: python -m pip install -r requirements.txt
      - run: python -m pytest -q

  windows-installer:
    needs: test
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      # Inno Setup is preinstalled on GitHub's Windows images.
      - run: powershell -ExecutionPolicy Bypass -File packaging\build-windows.ps1
      - uses: actions/upload-artifact@v4
        with:
          name: PixelSlides-Setup
          path: dist/installer/*.exe

  mobile:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: python -m pip install -r requirements.txt pillow
      - run: python packaging/make_icons.py
      - run: python -m slidedeck mobile -o dist/mobile
      - uses: actions/upload-pages-artifact@v3
        with: { path: dist/mobile }

  pages:
    if: github.ref == 'refs/heads/main'
    needs: mobile
    runs-on: ubuntu-latest
    permissions: { pages: write, id-token: write }
    environment: { name: github-pages, url: "${{ steps.deploy.outputs.page_url }}" }
    steps:
      - id: deploy
        uses: actions/deploy-pages@v4
```

**Check:** the last full test run.

```powershell
python -m pytest
```

You should see **238 passed**: every test in the project, from step 2's themes to step 20's shortcut writer. If you push the project to GitHub, the **Actions** tab shows the Build apps workflow, and once it finishes, `PixelSlides-Setup` is a download on the run's page. Building locally works too (`powershell -ExecutionPolicy Bypass -File packaging\build-windows.ps1`), but on a PC with Smart App Control the exe it makes will be blocked, as explained above.

**Commit:** `git add .` then `git commit -m "Step 21: Setup.exe and automatic builds"`

## You built it

That is the whole of Pixel Slides: an engine that turns Markdown into checked, typed slides; a web app with themes, a presenter view, print and text views; PDF export; a desktop app with its own installer; and a phone app that runs the same Python offline. Your `git log` has one commit per step, so `git diff` between any two steps shows exactly what that step added.

Good next projects, each a small step of its own: add a sixth theme in `themes.py` (step 2) and watch it appear everywhere, add a block type (a model in step 5, a parser rule in step 6, a template in step 7), or write your own deck in `decks/` and give a talk with it.

## Troubleshooting on Windows

| What you see | Why | Fix |
| --- | --- | --- |
| `pip` is blocked, or "This app has been blocked by your system administrator" | Application control blocks `pip.exe`, a launcher Python does not sign | Always write `python -m pip ...`. The same goes for `pytest`, `uvicorn` and `playwright`: use `python -m pytest` and so on. |
| `.venv\Scripts\Activate.ps1 cannot be loaded` | PowerShell's execution policy, or Constrained Language Mode | Run `.venv\Scripts\activate.bat` from Command Prompt instead, or skip activating and call `.venv\Scripts\python.exe -m ...` directly. |
| `ModuleNotFoundError: No module named 'slidedeck'` | The terminal is not in the project root, or the venv is not active | `cd` to the folder that holds `pyproject.toml` and check that the prompt starts with `(.venv)`. |
| A different number of tests passes than the step says | A test from a later step ran early, or a file was typed with a small difference | Use the exact `-k` filter the step gives. If a test fails, read its assert line: it names the value that differs. |
| `[Errno 10048]` or "address already in use" | Another server is still running on port 8000 | Stop the old one with Ctrl+C, or start on another port: `python -m slidedeck serve --port 8001`. |
| The slides show no styles, and the browser console mentions Content-Security-Policy | A template has an inline `style="..."` or `<script>` block | Move it into `slides.css` or a `.js` file. `test_no_inline_styles`\_anywhere and `test_no_external_fonts_or_inline_styles` point to the page. |
| `Export PDF` says no browser was found | Playwright drives Microsoft Edge, and it is missing or in an odd place | Install or update Edge. On a PC without Edge, `python -m playwright install chromium` downloads a browser for it. |
| `python -m slidedeck app` opens an Edge window, not a native one | pywebview could not start (often on a Python too new for its wheels) | Nothing to fix: the fallback window works the same. The terminal prints the reason. |
| The install wizard shows "Setup could not finish" | One `python -m pip` call failed, usually from no internet | Read the last lines in the message, check the connection and run the wizard again: it keeps what is done. |
| `python -m slidedeck mobile` stops with "has no pyemscripten wheel" | The installed pydantic is newer or older than the Pyodide build supports | `python -m pip install -U pydantic`, then build again. |
| The phone app shows an old version | The service worker is still serving the previous build | Close every tab or the installed app and open it again. Each build has a new version, so the update downloads on the next start. |
