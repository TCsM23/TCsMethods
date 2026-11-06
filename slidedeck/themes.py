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
        # QR codes are always dark on light, whatever the palette: many
        # phone scanners cannot read an inverted code.
        darkest, *_, lightest = theme.shades_by_luminance
        lines.append(f"  --qr-dark: {darkest};")
        lines.append(f"  --qr-light: {lightest};")
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
