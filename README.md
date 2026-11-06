# Pixel Slides

Markdown in, handheld-console slides out. A slide engine in Python (FastAPI, Pydantic, Jinja2, markdown-it-py) that draws every deck as a four-shade LCD screen, with presenter view, live reload, PDF export and an accessibility layer built in.

## Install it as an app

Pixel Slides installs as a **desktop app** (Windows install wizard, native window, one-click PDF) and a **mobile app** (installable and offline, with the Python engine running on the phone). See [INSTALL.md](INSTALL.md).

```
python -m slidedeck app        # the desktop app, from source
python -m slidedeck mobile     # build the mobile app into dist/mobile
```

## Run it (Windows)

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m playwright install chromium     # only needed for PDF export

python -m slidedeck serve --dev           # http://127.0.0.1:8000, reloads as you edit
python -m slidedeck export intro          # -> exports/intro.pdf
python -m slidedeck export intro --theme night --readable -o exports/intro-night.pdf
python -m slidedeck check intro           # block errors + accessibility warnings
python -m slidedeck check intro --strict  # fail on warnings too (for CI)
python -m slidedeck new "My talk" --starter talk   # basic, talk or lesson
pytest
```

Open `decks/intro.md` next to the browser and edit it: the page reloads on save.

## Keys

| Key | Action |
| --- | --- |
| → · Space · PgDn · N | Next step, or next slide |
| ← · Shift+Space · PgUp · B | Previous step, or previous slide |
| Home · End | First · last |
| 7 then Enter | Jump to slide 7 |
| O | List of slides, with a search box that finds any word on any slide |
| . | Pause screen: blank it for a question or a break; any key brings it back |
| A | Show the answer to the quiz on this slide (in every synced window) |
| P | Options (palette, lettering, motion, screen effect, sound) |
| R | Readable lettering on/off |
| C | High contrast on/off |
| M | Sound on/off |
| S | Presenter view (synced with the audience tab) |
| F | Fullscreen |
| ? | Help |

## Palettes

Every palette has four shades, like the original screens, plus named colour roles. They live in `slidedeck/themes.py`, which generates `/themes.css` and the photo filters.

| Name | Look |
| --- | --- |
| `dmg` (default) | The pea-green LCD |
| `pocket` | Grey-green, like the slimmer handheld |
| `berry` | Cream, berry and purple, like a colour handheld |
| `night` | Dark backlit screen for dim rooms |
| `contrast` | Black, white and yellow, no screen effects |

Set one in front matter (`theme: night`), in the URL (`?theme=night`), or under Options. The original greens fail WCAG for small text, so the palettes are tuned, and **a test checks 12 colour pairs in every palette against WCAG AA**. A palette edit that makes text hard to read fails the build.

## Accessibility

- **Screen readers** hear "Slide 4 of 15: title" after each move, and "Already at the last slide" at the edges. Only the current slide is exposed. Each slide is a labelled group, and the tab title names the slide.
- **Readable lettering** (R, or Options) swaps the pixel fonts for Atkinson Hyperlegible, with its own type scale.
- **High contrast** (C) switches palettes. It is picked automatically when the system asks for more contrast, until the viewer chooses.
- **Reduced motion** follows the system setting and can be changed in Options. It turns off the boot screen, the typewriter, the blinking and the transitions.
- **Text version** at `/deck/<name>/text`: the whole deck as one semantic page, with contents, headings nested under the page, alt text and video links. Add `?notes=1` for the speaker notes. A skip link on every slide points there.
- **Menus** are native `<dialog>` elements, so focus stays inside and Escape closes them. Every control is reachable by keyboard, and targets are at least 44px.
- **Captions**: `captions=media/talk.vtt` on local videos.
- **Lint**: `check` and the presenter view flag missing alt text, untitled videos, local videos without captions, slides with no heading, slides over 120 words, two slides with the same title, and links like "click here".
- **Steps** are announced as they appear ("Step 2 of 4: …"), and arriving on a slide says how many are still to come. **Quiz** results and answers are announced too, and right and wrong differ by a mark and a pattern, not only colour.
- **Charts** are drawn for the eye and given to screen readers as a real data table. **QR codes** always print their link as text underneath, and are always dark on light so phones can scan them in every palette.
- `lang:` in front matter sets the page language, so screen readers pronounce it correctly.

## Deck syntax

```markdown
---
title: My Talk
theme: dmg              # dmg, pocket, berry, night, contrast
lang: en
boot: true              # start-up screen when the deck opens
duration: 20            # minutes: the presenter view counts down and shows your pace
---
class: title            # optional: title, feature, center, inverse

### Kicker
# Headline

???
Speaker notes (presenter view only).

---

:::callout warning title="Heads up"
Body in **Markdown**.
:::

:::columns two          # two, three, sidebar, split; columns split by +++
Left
+++
:::callout stat title=42
Blocks nest inside columns.
:::
:::

:::gallery carousel     # or grid; filter=none keeps original colours
![Alt text](media/photo.jpg)
:::

:::video https://youtu.be/VIDEO_ID title="Demo"
:::

:::sprite alt="A heart" scale=12
.33.33.
3223223
.32223.
..323..
...3...
:::

:::dialog SAGE
Text that types itself out, in an RPG text box.
:::

:::meter label="Tests" value=96 max=100
Optional note under the bar. Add `xp` for a dithered bar, `unit=cups` for units.
:::

:::steps                # one item per press of Next
- First point
- Second point
:::

:::chart title="Coins per world" unit=coins
World 1: 40
World 2: 65
:::

:::quiz title="Pop quiz"
Which line starts the speaker notes?
- [ ] ---
- [x] ???
Shown after someone answers.
:::

:::qr https://example.com
Scan for the slides
:::
```

A slide break is a `---` line **with a blank line before it**, outside code fences and blocks.

### The new blocks

- **sprite**: pixel art typed into the deck. Digits `0` to `3` pick one of the palette's four shades, and `.` is empty. It is drawn as a crisp SVG that recolours with the palette. `alt` is required. Same-shade runs are merged into one `<rect>` each.
- **dialog**: an RPG text window with an optional speaker tag. On screen, the text types itself out. Screen readers get the whole text at once, and with reduced motion it simply appears.
- **meter**: an HP-style bar of 20 segments, exposed as `role="meter"`. A value above 0 always lights at least one segment, and a value below max never lights them all. A value outside 0..max is an error card, not a silent clamp.
- **steps**: a plain list becomes one step per item (bullets or numbers). Anything else is split into parts with `+++`, and each part can hold any blocks. Next shows the next step before it moves on; Back hides it again; stepping back onto a slide shows all its steps. The presenter view shows the steps still to come faintly and says "step 2/4". Print, PDF and the text version show every step.
- **chart**: a bar chart of up to 12 bars, `Label: value` per line, each bar a stack of 16 segments with its number on top. `max=` fixes the top of the scale; `unit=` names the numbers. Every other bar is dithered.
- **quiz**: a question, two to six options with exactly one `[x]`, and optional text after the options that shows once someone answers. Tap or click an option on screen; press **A** to reveal the answer for the room. Print and the handout list the options without the answer; the text version has it behind an "Answer" toggle.
- **qr**: a QR code drawn as pixel art by the engine itself (byte mode, error correction M, up to 213 bytes, no extra library). `scale=` sets the module size. The caption and the link text appear under it.
- **gallery** photos pass through a "camera" filter by default: turned grey, then snapped to the palette's four shades with an SVG `feComponentTransfer`. Images scale with `image-rendering: pixelated`.

## How it is built

```
slidedeck/
  parser.py      deck file -> slides (front matter, splitting, notes, class:, titles)
  blocks.py      the block lexer: ::: name + options + body -> dict -> Pydantic
  models.py      Pydantic models; Block is a discriminated union on `type`
  themes.py      palettes, WCAG contrast maths, generated CSS and photo filters
  lint.py        slide titles + accessibility checks
  embeds.py      video allow-list: extract an ID, rebuild the embed URL
  qr.py          a small QR code encoder (Reed-Solomon, masks, format bits)
  starters.py    the New deck starters (basic, talk, lesson)
  navigation.py  clamp + number<->index conversion (the off-by-one zone)
  render.py      markdown-it (raw HTML off) + one Jinja template per block
  app.py         FastAPI routes, canonical URL redirects, CSP, live reload (SSE)
  site.py        a deck as finished pages, no server (what the mobile app runs)
  desktop.py     the desktop app: server + window, deck tools API (token-checked)
  mobile.py      builds the mobile app: shell, Pyodide, engine.zip, service worker
  mobile_shell/  the mobile app's deck list, editor and service worker
  pdf.py         print view -> PDF with Playwright (Edge on Windows, no download)
  templates/     page templates + templates/blocks/<type>.html
  static/        theme.css (type + layout tokens), slides.css (components),
                 prefs.js (viewer preferences, applied before paint), deck.js
packaging/       icons, PyInstaller spec, Inno Setup wizard, Python wizard, build script
tests/           parser, blocks, new blocks, themes, lint, navigation, routes
```

### Presenting

- **Countdown**: with `duration:` in the front matter, the presenter view shows time left and your pace ("On pace", "Ahead by 1:30", "Behind by 2:10"), turns red when you run over, and announces 5 minutes, 1 minute and time up. **Pause timer** stops the clock for questions.
- **Pause screen** (`.` or the button in the presenter view) blanks the audience screen with a blinking PAUSE, in sync between windows.
- **Handout**: `/deck/<name>/print?notes=1` puts each slide at the left with its notes and lines to write on at the right. The desktop app's **Handout PDF** button exports it.
- **Starters**: New deck (desktop and phone) and `python -m slidedeck new` start from Basic, Talk or Lesson. Each one uses the blocks that suit it.

### Adding a block type

1. A model in `models.py` with `type: Literal["yourblock"]`, added to the `Block` union.
2. A builder in `blocks.py` that turns options and body into a dict, registered in `BUILDERS`.
3. A template at `templates/blocks/yourblock.html`, with classes like `slide-yourblock-card-header`. Handle `mode` (`screen`, `print`, `text`).
4. If it shows text, add it to `block_texts()` in `lint.py`, so titles and lint can see it.

### Safety decisions

- Raw HTML in decks is escaped (`html=False` in markdown-it).
- Video URLs never reach the page. Only a validated ID does, inside a URL the code builds. YouTube goes through `youtube-nocookie.com`.
- The Content-Security-Policy only allows frames from YouTube-nocookie and Vimeo, and allows no inline scripts or styles. A test checks that no page has a `style=` attribute.
- Images, caption files and local videos must be `media/...` (no `..`), each with an allowed extension.
- Deck names are checked against `^[a-z0-9-]+$` before touching the filesystem. `lang` is checked against a language-tag pattern.
- YAML is read with `safe_load`.

## Build guide

[docs/build-guide.md](docs/build-guide.md) walks through building the engine step by step. It was written for 0.3, so it does not cover the 0.4 blocks (steps, chart, quiz, QR), the talk countdown, the pause screen or handouts.
