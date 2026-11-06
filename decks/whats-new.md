---
title: What's New in 0.4
author: TCsM
theme: berry
lang: en
duration: 10
---
class: title

### Pixel Slides · World 1-2

# Four new *blocks*

Steps, charts, quizzes and QR codes. Press → to start.

???
This deck has `duration: 10` in its front matter, so the presenter view counts down from ten minutes and says whether you are ahead or behind.

---

### Steps

## One press, one point

:::steps
- **Steps** show one part per press of Next.
- Back hides them again, one at a time.
- Print, PDF and the text version show every step.
- Screen readers hear each step as it appears.
:::

???
In the presenter view the steps still to come are shown faintly, so you know what is next.

---

### Steps with blocks

## Parts can be anything

:::steps
:::callout note title="First part"
Split parts with `+++` on its own line.
:::
+++
:::meter label="Second part" value=2 max=3
A meter, a chart, a dialog: any block works.
:::
:::

---

### Chart

:::chart title="Coins per world" unit=coins
World 1: 40
World 2: 65
World 3: 30
World 4: 90
:::

???
The bars are a picture. Screen readers get the same numbers as a table, and the text version shows the table.

---

### Quiz

:::quiz title="Pop quiz"
Which line starts the speaker notes?
- [ ] `---`
- [x] `???`
- [ ] `+++`
Three question marks. Everything after them is for the presenter only.
:::

???
Let the room answer out loud, then press **A** to show the answer on every screen.

---

### Presenting

## New keys

:::columns two
:::callout note title="Pause screen"
Press **.** to blank the screen for a question or a break. Any key brings it back.
:::
+++
:::callout note title="Find a slide"
Press **O** and type: it searches every word on every slide.
:::
:::

---

### Handouts

## Slides with notes

The print view has a handout version: each slide at the left, its speaker notes and lines to write on at the right. In the desktop app it is one click, **Handout PDF**.

???
The URL is /deck/whats-new/print?notes=1.

---

class: center

### Thanks for playing

## Scan for the project

:::qr https://github.com/
The QR code is drawn as pixel art, always dark on light.
:::
