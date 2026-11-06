"""Version 0.4: steps, chart, quiz and QR blocks, talk length, handouts, starters."""
import json
import re
import zipfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from slidedeck import qr, site, starters
from slidedeck.blocks import parse_blocks
from slidedeck.desktop import WindowHost, make_router
from slidedeck.lint import lint_deck, walk
from slidedeck.models import QR_QUIET_ZONE
from slidedeck.parser import DeckError, parse_deck
from slidedeck.render import render_block, render_text_block

ROOT = Path(__file__).parent.parent
WHATS_NEW = (ROOT / "decks" / "whats-new.md").read_text(encoding="utf-8")


def one(source):
    blocks = parse_blocks(source)
    assert len(blocks) == 1, blocks
    return blocks[0]


# --- QR encoder ------------------------------------------------------------------


def test_reed_solomon_matches_the_standard_example():
    # "HELLO WORLD", version 1-M, from the worked example of the QR standard.
    data = [32, 91, 11, 120, 209, 114, 220, 77, 67, 64, 236, 17, 236, 17, 236, 17]
    assert qr.ec_codewords(data, 10) == [196, 35, 39, 119, 235, 215, 231, 226, 93, 23]


@pytest.mark.parametrize("mask, bits", [
    (0, "101010000010010"), (1, "101000100100101"), (2, "101111001111100"), (3, "101101101001011"),
    (4, "100010111111001"), (5, "100000011001110"), (6, "100111110010111"), (7, "100101010100000"),
])
def test_format_bits_for_level_m(mask, bits):
    assert format(qr.format_bits(mask), "015b") == bits


def test_version_information_bits():
    assert qr.version_bits(7) == 0x07C94
    assert qr.version_bits(10) == 0x0A4D3


@pytest.mark.parametrize("length, version", [(1, 1), (14, 1), (15, 2), (26, 2), (27, 3), (213, 10)])
def test_smallest_version_that_fits(length, version):
    assert qr.pick_version(length) == version


def test_too_long_is_an_error():
    with pytest.raises(qr.QrTooLong):
        qr.pick_version(214)


def test_grid_has_finders_timing_and_size():
    matrix = qr.encode("https://example.com")
    size = len(matrix)
    assert size == 25 and all(len(row) == size for row in matrix)  # version 2
    for top, left in ((0, 0), (0, size - 7), (size - 7, 0)):
        assert all(matrix[top][left + i] for i in range(7))      # finder's top edge
        assert not matrix[top + 1][left + 1] and matrix[top + 3][left + 3]
    assert [matrix[6][c] for c in range(8, size - 8)] == [c % 2 == 0 for c in range(8, size - 8)]
    assert matrix[size - 8][8]  # the dark module


def test_every_mask_gives_the_same_function_patterns():
    grids = [qr.encode("Pixel Slides", mask) for mask in range(8)]
    assert len({g[0][0] for g in grids}) == 1
    assert len({tuple(map(tuple, g)) for g in grids}) == 8  # but different data


# --- Blocks -----------------------------------------------------------------------


def test_steps_from_a_bullet_list():
    block = one(":::steps\n- One\n- Two **bold**\n  still two\n- Three\n:::")
    assert block.type == "steps" and block.style == "bullet" and len(block.items) == 3
    assert "still two" in block.items[1][0].source


def test_steps_from_a_numbered_list_and_from_parts():
    assert one(":::steps\n1. A\n2. B\n:::").style == "number"
    block = one(":::steps\n:::callout note\nA\n:::\n+++\nPlain text\n:::")
    assert block.style == "blocks" and [item[0].type for item in block.items] == ["callout", "markdown"]


def test_steps_render_for_screen_but_not_print():
    block = one(":::steps\n- One\n- Two\n:::")
    screen = str(render_block(block, "screen"))
    assert screen.count("data-step-item") == 2 and screen.startswith("<ul")
    assert "data-step" not in str(render_block(block, "print"))


def test_nested_blocks_in_steps_are_linted_and_titled():
    deck = parse_deck(":::steps\n## Inside a step\n+++\n:::gallery\n![](media/a.png)\n:::\n:::\n")
    assert deck.slides[0].title == "Inside a step"
    assert [b.type for b in walk(deck.slides[0].blocks)] == ["steps", "markdown", "gallery"]
    assert any(issue.code == "image-alt" for issue in lint_deck(deck))


def test_chart_parses_bars():
    block = one(':::chart title="Coins" unit=coins\nWorld 1: 40\nWorld 2: 1,250\n:::')
    assert [(b.label, b.value) for b in block.bars] == [("World 1", 40), ("World 2", 1250)]
    assert block.filled(block.bars[1]) == 16 and block.filled(block.bars[0]) == 1


def test_chart_title_can_be_positional():
    assert one(":::chart Coins\nA: 1\n:::").title == "Coins"


@pytest.mark.parametrize("source, message", [
    (":::chart\nA: 1\n:::", "title"),
    (":::chart title=X\nnot a bar\n:::", "Label: 42"),
    (":::chart title=X\nA: -3\n:::", "greater than or equal"),
    (":::chart title=X max=10\nA: 30\n:::", "above max"),
    (":::chart title=X\n" + "".join(f"B{i}: 1\n" for i in range(13)) + ":::", "at most 12"),
])
def test_chart_errors(source, message):
    block = one(source)
    assert block.type == "error" and message in block.message


def test_chart_has_a_table_for_screen_readers():
    block = one(':::chart title="Coins"\nA: 1\nB: 2\n:::')
    screen = str(render_block(block, "screen"))
    assert 'aria-hidden="true"' in screen and "visually-hidden" in screen and "<th scope=\"row\">B</th>" in screen
    assert "slide-chart-frame-plot" not in str(render_text_block(block))


def test_quiz_parses_question_options_and_explanation():
    block = one(":::quiz title=Check\nWhich?\n- [ ] no\n- [x] **yes**\n- [ ] no\nBecause.\n:::")
    assert block.question == "Which?" and block.answer == 1 and block.explain == "Because."
    assert block.title == "Check"


@pytest.mark.parametrize("source, message", [
    (":::quiz\nQ?\n- [ ] a\n- [ ] b\n:::", "exactly one"),
    (":::quiz\nQ?\n- [x] a\n- [x] b\n:::", "exactly one"),
    (":::quiz\nQ?\n- [x] a\n:::", "at least 2"),
    (":::quiz\nQ?\n:::", "needs options"),
    (":::quiz\nQ?\n- [x] a\nstray\n- [ ] b\n:::", "together"),
])
def test_quiz_errors(source, message):
    block = one(source)
    assert block.type == "error" and message in block.message


def test_quiz_renders_buttons_on_screen_and_the_answer_in_text():
    block = one(":::quiz\nQ?\n- [ ] a\n- [x] b\n:::")
    screen = str(render_block(block, "screen"))
    assert screen.count("<button") == 2 and 'data-answer="1"' in screen and screen.count("data-correct") == 1
    text = str(render_text_block(block))
    assert "<button" not in text and "<details" in text and "B:" in text
    printed = str(render_block(block, "print"))
    assert "<details" not in printed and "data-correct" not in printed  # handouts don't give it away


def test_qr_block_draws_the_code_with_a_quiet_zone():
    block = one(":::qr https://example.com\nScan me\n:::")
    assert block.type == "qr" and block.caption == "Scan me" and block.is_link
    assert block.size == 25 + 2 * QR_QUIET_ZONE
    assert min(run.x for run in block.runs) == QR_QUIET_ZONE
    html = str(render_block(block))
    assert 'aria-label="QR code for the link: https://example.com"' in html
    assert 'href="https://example.com"' in html


def test_qr_text_that_is_not_a_link_is_not_linked():
    html = str(render_block(one(":::qr javascript:alert(1)\n:::")))
    assert "href" not in html


def test_qr_too_long_is_an_error_card():
    block = one(":::qr https://example.com/" + "a" * 220 + "\n:::")
    assert block.type == "error" and "at most 213" in block.message


# --- Deck and lint --------------------------------------------------------------------


def test_duration_in_front_matter():
    assert parse_deck("---\nduration: 20\n---\n# A\n").duration == 20
    with pytest.raises(DeckError):
        parse_deck("---\nduration: 0\n---\n# A\n")


def test_duplicate_titles_are_flagged():
    deck = parse_deck("# Same\n\n---\n\n# Other\n\n---\n\n# same\n")
    issues = [i for i in lint_deck(deck) if i.code == "slide-title-duplicate"]
    assert [(i.slide, "slide 1" in i.message) for i in issues] == [(3, True)]


def test_whats_new_deck_is_clean():
    deck = parse_deck(WHATS_NEW)
    assert deck.duration == 10 and lint_deck(deck) == []
    types = {block.type for slide in deck.slides for block in walk(slide.blocks)}
    assert {"steps", "chart", "quiz", "qr"} <= types


# --- Pages ----------------------------------------------------------------------------


def test_presenter_gets_duration_and_pause_controls():
    pages = json.loads(site.build("whats-new", WHATS_NEW))["pages"]
    presenter = pages["/deck/whats-new/1/presenter"]
    assert 'data-duration="10.0"' in presenter and "data-pace" in presenter and "data-blank-toggle" in presenter
    deck = pages["/deck/whats-new/1"]
    assert "data-blank-screen" in deck and "data-outline-filter" in deck


def test_handout_page_has_notes_next_to_each_slide():
    pages = json.loads(site.build("whats-new", WHATS_NEW))["pages"]
    handout = pages["/deck/whats-new/print?notes=1"]
    assert handout.count('class="print-handout-page"') == 8
    assert "duration: 10" in handout.replace("<code>", "").replace("</code>", "")
    assert "print-handout-page" not in pages["/deck/whats-new/print"]


def test_new_pages_have_no_inline_styles_and_unique_ids():
    for path, html in json.loads(site.build("whats-new", WHATS_NEW))["pages"].items():
        assert " style=" not in html, path
        if "/presenter" not in path:  # the presenter shows each slide twice (now + next)
            ids = re.findall(r'\bid="([^"]+)"', html)
            assert len(ids) == len(set(ids)), path


def test_server_handout_route():
    from slidedeck.app import app

    client = TestClient(app)
    assert "print-handout-page" in client.get("/deck/whats-new/print?notes=1").text
    assert "print-handout-page" not in client.get("/deck/whats-new/print").text


# --- Starters ----------------------------------------------------------------------------


@pytest.mark.parametrize("name", list(starters.STARTERS))
def test_every_starter_is_a_clean_deck(name):
    result = json.loads(site.build("x", starters.render('Talk: "quoted" {braces}', name)))
    assert result["ok"] and result["summary"]["title"] == 'Talk: "quoted" {braces}'
    assert result["summary"]["issues"] == []


def test_talk_starter_has_a_default_length():
    assert parse_deck(starters.render("T", "talk")).duration == 20
    assert parse_deck(starters.render("T", "basic")).duration is None
    assert parse_deck(starters.render("T", "basic", 5)).duration == 5


def test_site_exposes_starters_for_the_phone():
    names = [s["name"] for s in json.loads(site.starters())]
    assert names == list(starters.STARTERS)
    assert parse_deck(site.new_deck("Hi", "lesson")).title == "Hi"


def test_engine_zip_has_the_new_modules(tmp_path):
    from slidedeck.mobile import engine_zip

    engine_zip(tmp_path / "engine.zip")
    names = set(zipfile.ZipFile(tmp_path / "engine.zip").namelist())
    assert {"slidedeck/qr.py", "slidedeck/starters.py", "slidedeck/templates/blocks/quiz.html"} <= names


def test_cli_new(tmp_path, monkeypatch, capsys):
    import sys

    from slidedeck.__main__ import main

    monkeypatch.setenv("SLIDES_DECKS_DIR", str(tmp_path))
    for _ in range(2):
        monkeypatch.setattr(sys, "argv", ["slidedeck", "new", "My Lesson", "--starter", "lesson"])
        main()
    assert sorted(p.name for p in tmp_path.glob("*.md")) == ["my-lesson-2.md", "my-lesson.md"]
    assert "Wrote" in capsys.readouterr().out


# --- Desktop API --------------------------------------------------------------------------


@pytest.fixture
def desktop(tmp_path, monkeypatch):
    monkeypatch.setattr("slidedeck.desktop.open_path", lambda path, reveal=False: True)
    printed = []
    monkeypatch.setattr("slidedeck.pdf.print_pdf", lambda url, output, readable=False: printed.append((url, output)))
    decks = tmp_path / "decks"
    decks.mkdir()
    (decks / "whats-new.md").write_text(WHATS_NEW, encoding="utf-8")
    app = FastAPI()
    public, router = make_router(decks, tmp_path / "exports", "secret", WindowHost("http://x"))
    app.include_router(public)
    app.include_router(router)
    return TestClient(app, headers={"X-Desktop-Token": "secret"}), decks, printed


def test_desktop_new_deck_from_a_starter(desktop):
    client, decks, _ = desktop
    assert [s["name"] for s in client.get("/desktop/starters").json()] == list(starters.STARTERS)
    name = client.post("/desktop/new-deck", json={"title": "Quiz night", "starter": "lesson"}).json()["name"]
    assert ":::quiz" in (decks / f"{name}.md").read_text()
    assert client.post("/desktop/new-deck", json={"title": "x", "starter": "nope"}).status_code == 400


def test_desktop_duplicate(desktop):
    client, decks, _ = desktop
    first = client.post("/desktop/duplicate/whats-new").json()["name"]
    second = client.post("/desktop/duplicate/whats-new").json()["name"]
    assert (first, second) == ("whats-new-copy", "whats-new-copy-2")
    copy = parse_deck((decks / "whats-new-copy.md").read_text())
    assert copy.title == "What's New in 0.4 (copy)" and len(copy.slides) == 8
    assert client.post("/desktop/duplicate/missing").status_code == 404


def test_desktop_handout_export(desktop):
    client, _, printed = desktop
    client.post("/desktop/export/whats-new", json={"handout": True})
    client.post("/desktop/export/whats-new", json={})
    assert [(url.endswith("?notes=1"), out.name) for url, out in printed] == [
        (True, "whats-new-handout.pdf"), (False, "whats-new.pdf")]


# --- Sample decks reach existing installs ---------------------------------------------------


def test_seed_gives_each_sample_once(tmp_path):
    from slidedeck.desktop import seed_decks

    samples = ROOT / "decks"
    fresh = tmp_path / "fresh"
    assert seed_decks(fresh, samples) == ["intro.md", "whats-new.md"]
    (fresh / "whats-new.md").unlink()
    assert seed_decks(fresh, samples) == []  # deleted stays deleted
    assert (fresh / "media" / "city.png").is_file()

    old = tmp_path / "from-0.3"  # a 0.3 install: intro was seeded, no record
    old.mkdir()
    (old / "my-talk.md").write_text("# Mine\n", encoding="utf-8")
    assert seed_decks(old, samples) == ["whats-new.md"]
    assert (old / "my-talk.md").read_text() == "# Mine\n"


@pytest.mark.parametrize("text, title", [
    ('---\ntitle: "A: b"\n---\n# x\n', "A: b (copy)"),
    ("---\ntitle: Plain\ntheme: dmg\n---\n# x\n", "Plain (copy)"),
    ("---\ntheme: dmg\n---\n# x\n", "Untitled deck"),
    ("# no front matter\n", "Untitled deck"),
])
def test_retitle(text, title):
    assert parse_deck(starters.retitle(text)).title == title
