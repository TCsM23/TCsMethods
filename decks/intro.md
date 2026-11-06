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
