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
