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
