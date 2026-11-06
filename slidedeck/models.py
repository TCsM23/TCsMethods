"""Data shapes for a deck.

Each block type is its own Pydantic model with a literal `type` field.
`Block` is a discriminated union: Pydantic reads `type` first, then
validates against exactly one model, so error messages point at the
right fields instead of "none of 6 models matched".
"""
from __future__ import annotations

from functools import cached_property
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from .embeds import resolve_video, safe_media_path
from .qr import MAX_BYTES as QR_MAX_BYTES
from .qr import encode as qr_encode
from .themes import DEFAULT_THEME, THEMES

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".avif"}
CAPTION_EXTENSIONS = {".vtt"}
SPRITE_PALETTE = "0123"  # 0 = background tone ... 3 = ink tone
SPRITE_EMPTY = "."
SPRITE_MAX_SIDE = 64
METER_SEGMENTS = 20
CHART_SEGMENTS = 16
CHART_MAX_BARS = 12
QUIZ_MAX_OPTIONS = 6
QR_QUIET_ZONE = 4  # light modules around the code, as the standard asks


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


class StepsBlock(BaseModel):
    """Parts of a slide that appear one at a time as the presenter presses Next.

        :::steps
        - First point
        - Second point
        :::

    A plain list becomes one step per item. Anything else is split by +++,
    and each part can hold any blocks. Print and the text view show every
    step; so does a page without JavaScript.
    """
    type: Literal["steps"]
    # bullet / number: the steps are the items of one list. blocks: free parts.
    style: Literal["bullet", "number", "blocks"] = "blocks"
    items: list[list["Block"]] = Field(min_length=1)


class ChartBar(BaseModel):
    label: str = Field(min_length=1)
    value: float = Field(ge=0)


class ChartBlock(BaseModel):
    """A pixel bar chart. Each line is `Label: value`.

        :::chart title="Coins per world" unit=coins
        World 1: 40
        World 2: 65
        :::

    Bars are stacks of 16 segments, like the meter. The numbers are always
    printed too, and screen readers get a real data table.
    """
    type: Literal["chart"]
    title: str = Field(min_length=1)
    unit: str = ""
    max: float | None = Field(default=None, gt=0)
    caption: str | None = None
    bars: list[ChartBar] = Field(min_length=1, max_length=CHART_MAX_BARS)

    @model_validator(mode="after")
    def values_fit(self) -> "ChartBlock":
        top = max(bar.value for bar in self.bars)
        if self.max is not None and top > self.max:
            raise ValueError(f"a bar is {top:g}, above max={self.max:g}")
        return self

    @property
    def scale_max(self) -> float:
        return self.max if self.max is not None else (max(bar.value for bar in self.bars) or 1)

    @property
    def segments(self) -> int:
        return CHART_SEGMENTS

    def filled(self, bar: ChartBar) -> int:
        return filled_segments(bar.value, self.scale_max, CHART_SEGMENTS)

    def value_text(self, bar: ChartBar) -> str:
        return f"{bar.value:g}{f' {self.unit}' if self.unit else ''}"


class QuizOption(BaseModel):
    text: str = Field(min_length=1)
    correct: bool = False


class QuizBlock(BaseModel):
    """A multiple-choice question with one right answer.

        :::quiz
        Which line starts the speaker notes?
        - [ ] ---
        - [x] ???
        Text after the options is shown once someone answers.
        :::
    """
    type: Literal["quiz"]
    title: str = "Quiz"
    question: str = Field(min_length=1)
    options: list[QuizOption] = Field(min_length=2, max_length=QUIZ_MAX_OPTIONS)
    explain: str = ""

    @model_validator(mode="after")
    def one_answer(self) -> "QuizBlock":
        right = sum(option.correct for option in self.options)
        if right != 1:
            raise ValueError(f"mark exactly one option with [x] (found {right})")
        return self

    @property
    def answer(self) -> int:
        return next(i for i, option in enumerate(self.options) if option.correct)

    @staticmethod
    def letter(i: int) -> str:
        return "ABCDEF"[i]


class QrBlock(BaseModel):
    """A QR code drawn as pixel art: `:::qr https://example.com`.

    The text or link is always printed under the code too, for anyone who
    cannot scan it (and screen readers, which hear it as the label)."""
    type: Literal["qr"]
    data: str = Field(min_length=1)
    caption: str | None = None
    scale: int = Field(default=10, ge=4, le=20)

    @field_validator("data")
    @classmethod
    def fits(cls, data: str) -> str:
        data = data.strip()
        if len(data.encode("utf-8")) > QR_MAX_BYTES:
            raise ValueError(f"QR text is {len(data.encode('utf-8'))} bytes; at most {QR_MAX_BYTES} fit")
        return data

    @cached_property
    def matrix(self) -> list[list[bool]]:
        return qr_encode(self.data)

    @property
    def size(self) -> int:
        return len(self.matrix) + 2 * QR_QUIET_ZONE

    @property
    def runs(self) -> list[SpriteRun]:
        """Dark modules merged into horizontal runs, offset by the quiet zone."""
        runs: list[SpriteRun] = []
        for y, row in enumerate(self.matrix):
            x = 0
            while x < len(row):
                if row[x]:
                    end = x
                    while end < len(row) and row[end]:
                        end += 1
                    runs.append(SpriteRun(x=x + QR_QUIET_ZONE, y=y + QR_QUIET_ZONE, width=end - x, shade=3))
                    x = end
                else:
                    x += 1
        return runs

    @property
    def is_link(self) -> bool:
        return self.data.startswith(("https://", "http://"))


class ErrorBlock(BaseModel):
    """Shown in place of a block that failed to parse or validate."""
    type: Literal["error"] = "error"
    block_name: str
    message: str
    source: str = ""


Block = Annotated[
    Union[MarkdownBlock, CalloutBlock, ColumnsBlock, GalleryBlock, VideoBlock,
          SpriteBlock, DialogBlock, MeterBlock, StepsBlock, ChartBlock, QuizBlock, QrBlock,
          ErrorBlock],
    Field(discriminator="type"),
]

# ColumnsBlock and StepsBlock refer to Block before Block existed; resolve that now.
ColumnsBlock.model_rebuild()
StepsBlock.model_rebuild()

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
    # Planned length of the talk in minutes: the presenter view counts down
    # and says whether you are ahead of or behind the slides.
    duration: float | None = Field(default=None, gt=0, le=600)
    slides: list[Slide]

    @field_validator("theme")
    @classmethod
    def known_theme(cls, theme: str) -> str:
        if theme not in THEMES:
            raise ValueError(f"unknown theme {theme!r} (use {', '.join(THEMES)})")
        return theme
