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
