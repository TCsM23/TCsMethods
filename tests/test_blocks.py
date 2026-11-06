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
