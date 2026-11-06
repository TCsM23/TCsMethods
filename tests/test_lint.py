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
