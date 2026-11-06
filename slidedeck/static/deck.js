// Audience + presenter navigation, menus, preferences and the 8-bit extras.
// The server already clamps URLs; this file clamps keyboard, button, swipe
// and sync input with the same rule, so the index can never leave 0..count-1.
(() => {
  "use strict";

  const body = document.body;
  const root = document.documentElement;
  const prefs = window.PixelPrefs;
  const deckName = body.dataset.deck;
  // URL prefix: empty on the server, the install folder in the mobile app.
  const base = root.dataset.base || "";
  const deckTitle = body.dataset.deckTitle || "";
  const count = Number(body.dataset.count);
  let themeQuery = body.dataset.themeQuery || "";
  const isPresenter = body.hasAttribute("data-presenter");
  const CANVAS_W = 1600;
  const CANVAS_H = 900;

  const clamp = (i, n) => (Number.isFinite(i) ? Math.max(0, Math.min(Math.trunc(i), n - 1)) : 0);
  const reducedMotion = () => root.dataset.motion === "reduce";

  let current = clamp(Number(body.dataset.index), count);
  // Steps (:::steps) shown so far on the current slide, and the pause screen.
  let stepShown = 0;
  let blanked = false;
  const titles = [...document.querySelectorAll(".deck-stage-canvas")[0]?.children || []]
    .map((slide) => slide.dataset.title || "");

  // --- Screen reader announcements ----------------------------------------
  const live = document.querySelector("[data-live]");
  function announce(text) {
    if (!live) return;
    // Clear first so the same message twice is still read out.
    live.textContent = "";
    requestAnimationFrame(() => { live.textContent = text; });
  }
  const describe = (i) => `Slide ${i + 1} of ${count}${titles[i] ? `: ${titles[i]}` : ""}`;

  // --- Sound: square-wave blips, off unless the viewer turns them on --------
  let audio = null;
  function blip(kind) {
    if (root.dataset.sound !== "on") return;
    try {
      audio = audio || new AudioContext();
      const notes = { next: [988, 1319], back: [784, 587], edge: [131, 98], toggle: [1568],
        right: [1047, 1319, 1568], wrong: [196, 147], step: [1319] }[kind] || [880];
      notes.forEach((freq, n) => {
        const osc = audio.createOscillator();
        const gain = audio.createGain();
        const start = audio.currentTime + n * 0.06;
        osc.type = "square";
        osc.frequency.setValueAtTime(freq, start);
        gain.gain.setValueAtTime(0.06, start);
        gain.gain.exponentialRampToValueAtTime(0.001, start + 0.07);
        osc.connect(gain).connect(audio.destination);
        osc.start(start);
        osc.stop(start + 0.08);
      });
    } catch { /* no audio: stay silent */ }
  }

  // --- Scale the fixed 1600x900 canvas to whatever box it sits in ---------
  const viewports = [...document.querySelectorAll(".deck-stage-viewport")];
  const fit = (viewport) => {
    const scale = Math.min(viewport.clientWidth / CANVAS_W, viewport.clientHeight / CANVAS_H);
    viewport.querySelector(".deck-stage-canvas").style.setProperty("--stage-scale", String(scale));
  };
  const resizer = new ResizeObserver((entries) => entries.forEach((e) => fit(e.target)));
  viewports.forEach((v) => { fit(v); resizer.observe(v); });

  // --- Show the right slide everywhere -------------------------------------
  const slideIn = (index, scope = document) => scope.querySelector(`.slide-page-frame[data-index="${index}"]`);
  const stepItems = (index, scope = document) => [...(slideIn(index, scope)?.querySelectorAll("[data-step-item]") || [])];
  const stepCount = (index) => stepItems(index).length;

  function render(revealed = -1) {
    for (const viewport of viewports) {
      const offset = Number(viewport.dataset.offset || 0);
      const target = current + offset;
      const inRange = target >= 0 && target < count;
      viewport.toggleAttribute("data-empty", !inRange);
      for (const slide of viewport.querySelectorAll(".slide-page-frame")) {
        const active = inRange && Number(slide.dataset.index) === target;
        slide.classList.toggle("is-active", active);
        slide.inert = !active;
        // Hidden slides must not be read out; only the current one is exposed.
        slide.setAttribute("aria-hidden", String(!active));
        // Steps still to come are hidden on the current slide only; the
        // "next" preview in the presenter view shows its slide complete.
        const now = offset === 0 && Number(slide.dataset.index) === current;
        slide.querySelectorAll("[data-step-item]").forEach((item, i) => {
          item.classList.toggle("is-pending", now && i >= stepShown);
          item.classList.toggle("is-revealed", now && i === revealed);
        });
      }
    }
    const steps = stepCount(current);
    document.querySelectorAll("[data-step-label]").forEach((el) => {
      el.textContent = steps ? ` · step ${stepShown}/${steps}` : "";
    });
    document.querySelectorAll("[data-current]").forEach((el) => { el.textContent = String(current + 1); });
    document.querySelectorAll("[data-step='-1']").forEach((b) => { b.disabled = current === 0 && stepShown === 0; });
    document.querySelectorAll("[data-step='1']").forEach((b) => { b.disabled = current === count - 1 && stepShown >= steps; });
    document.querySelectorAll("[data-notes-for]").forEach((n) => { n.hidden = Number(n.dataset.notesFor) !== current; });
    document.querySelectorAll("[data-segment]").forEach((s) => {
      const i = Number(s.dataset.segment);
      s.classList.toggle("is-done", i < current);
      s.classList.toggle("is-current", i === current);
    });
    document.querySelectorAll("[data-goto]").forEach((b) => {
      b.setAttribute("aria-current", String(Number(b.dataset.goto) === current));
    });
    updateLinks();
    if (!isPresenter) {
      document.title = `${titles[current] || deckTitle} · ${current + 1}/${count} · ${deckTitle}`;
    }
    typeDialogs();
  }

  function updateLinks() {
    document.querySelectorAll("[data-presenter-link]").forEach((a) => {
      a.href = `${base}/deck/${deckName}/${current + 1}/presenter${themeQuery}`;
    });
    document.querySelectorAll("[data-text-link]").forEach((a) => { a.href = `${base}/deck/${deckName}/text${themeQuery}#slide-${current + 1}`; });
    document.querySelectorAll("[data-print-link]").forEach((a) => { a.href = `${base}/deck/${deckName}/print${themeQuery}`; });
    const skip = document.querySelector(".deck-skip-link");
    if (skip) skip.href = `${base}/deck/${deckName}/text${themeQuery}#slide-${current + 1}`;
  }

  function stopMedia(index) {
    document.querySelectorAll(`.slide-page-frame[data-index="${index}"]`).forEach((slide) => {
      slide.querySelectorAll("video").forEach((v) => v.pause());
      // Re-setting an iframe's src is the provider-neutral way to stop playback.
      slide.querySelectorAll("iframe").forEach((f) => { if (!isPresenter) f.src = f.src; });
    });
  }

  // --- Dialog boxes type themselves out -------------------------------------
  const typingTimers = new Map();
  function typeDialogs() {
    typingTimers.forEach((timer) => clearInterval(timer));
    typingTimers.clear();
    document.querySelectorAll(".slide-dialog-box-typed").forEach((copy) => copy.remove());
    document.querySelectorAll(".slide-dialog-box.is-typing").forEach((box) => box.classList.remove("is-typing"));
    document.querySelectorAll("[data-typewriter-source]").forEach((source) => { source.classList.remove("visually-hidden"); });
    if (reducedMotion() || isPresenter) return;

    const viewport = document.querySelector(".deck-view > .deck-stage-viewport");
    if (!viewport) return;
    viewport.querySelectorAll(".slide-page-frame.is-active [data-typewriter]").forEach((box) => {
      const source = box.querySelector("[data-typewriter-source]");
      // The copy is visual only. The real text is still in the page,
      // visually hidden, so screen readers read it whole and at once.
      const copy = source.cloneNode(true);
      copy.removeAttribute("data-typewriter-source");
      copy.className = "slide-dialog-box-typed";
      copy.setAttribute("aria-hidden", "true");
      const texts = [];
      const walker = document.createTreeWalker(copy, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) texts.push({ node: walker.currentNode, full: walker.currentNode.textContent });
      texts.forEach((t) => { t.node.textContent = ""; });
      source.classList.add("visually-hidden");
      source.after(copy);
      box.classList.add("is-typing");

      let part = 0;
      let shown = 0;
      const finish = () => {
        clearInterval(typingTimers.get(box));
        texts.forEach((t) => { t.node.textContent = t.full; });
        box.classList.remove("is-typing");
      };
      box.addEventListener("click", finish, { once: true });
      typingTimers.set(box, setInterval(() => {
        if (part >= texts.length) return finish();
        shown += 2;
        texts[part].node.textContent = texts[part].full.slice(0, shown);
        if (shown >= texts[part].full.length) { part += 1; shown = 0; }
      }, 28));
    });
  }

  // --- Navigation ----------------------------------------------------------
  const channel = "BroadcastChannel" in window ? new BroadcastChannel(`pixel-slides:${deckName}`) : null;

  function post() {
    if (channel) channel.postMessage({ index: current, step: stepShown, blank: blanked });
  }

  // arrive: "start" shows none of the next slide's steps, "end" shows them all
  // (stepping back onto a slide lands where you left it).
  function go(index, { broadcast = true, quiet = false, arrive = "start" } = {}) {
    const next = clamp(index, count);
    if (next === current) {
      // Pressing past either end: say so, instead of silently doing nothing.
      if (!quiet && Number.isFinite(index) && index !== current) {
        blip("edge");
        announce(index < 0 ? "Already at the first slide" : "Already at the last slide");
      }
      return;
    }
    blip(next > current ? "next" : "back");
    stopMedia(current);
    resetQuizzes(current);
    current = next;
    stepShown = arrive === "end" ? stepCount(current) : 0;
    render();
    // replaceState: the URL always names the current slide, so a reload or a
    // shared link lands in the same place, without flooding the back button.
    const suffix = isPresenter ? "/presenter" : "";
    history.replaceState(null, "", `${base}/deck/${deckName}/${current + 1}${suffix}${themeQuery}`);
    const steps = stepCount(current);
    const pending = steps - stepShown;
    announce(describe(current) + (pending ? `. ${pending} more ${pending === 1 ? "step" : "steps"} to show` : ""));
    if (broadcast) post();
  }

  function setStep(n, { broadcast = true, quiet = false } = {}) {
    const total = stepCount(current);
    const next = Math.max(0, Math.min(n, total));
    if (next === stepShown) return;
    const forward = next > stepShown;
    stepShown = next;
    render(forward ? next - 1 : -1);
    if (!quiet) {
      blip(forward ? "step" : "back");
      const item = stepItems(current)[next - 1];
      const words = (item?.textContent || "").replace(/\s+/g, " ").trim().slice(0, 240);
      announce(forward ? `Step ${next} of ${total}: ${words}` : `Back to step ${next} of ${total}`);
    }
    if (broadcast) post();
  }

  function step(delta) {
    // Next first brings the screen back from a pause, like a key press on a paused game.
    if (blanked) { setBlank(false); return; }
    const total = stepCount(current);
    if (delta > 0 && stepShown < total) return setStep(stepShown + 1);
    if (delta < 0 && stepShown > 0) return setStep(stepShown - 1);
    go(current + delta, { arrive: delta < 0 ? "end" : "start" });
  }

  // --- Pause screen ("." blanks the audience screen) -------------------------------
  const blankScreen = document.querySelector("[data-blank-screen]");
  function setBlank(on, { broadcast = true, quiet = false } = {}) {
    if (on === blanked) return;
    blanked = on;
    if (blankScreen) blankScreen.hidden = !on;
    body.classList.toggle("is-blanked", on);
    document.querySelectorAll("[data-blank-toggle]").forEach((b) => b.setAttribute("aria-pressed", String(on)));
    document.querySelectorAll("[data-blank-badge]").forEach((b) => { b.hidden = !on; });
    if (!quiet) {
      blip("toggle");
      announce(on ? "Screen paused. Press period to bring it back." : `Screen back. ${describe(current)}`);
    }
    if (broadcast) post();
  }
  document.querySelectorAll("[data-blank-toggle]").forEach((b) => b.addEventListener("click", () => setBlank(!blanked)));
  blankScreen?.addEventListener("click", () => setBlank(false));

  // --- Quizzes ------------------------------------------------------------------------
  function answerQuiz(quiz, picked) {
    if (quiz.dataset.answered) return;
    quiz.dataset.answered = "1";
    const answer = Number(quiz.dataset.answer);
    const options = [...quiz.querySelectorAll("[data-quiz-option]")];
    options.forEach((option, i) => {
      option.setAttribute("aria-disabled", "true");
      option.classList.toggle("is-correct", i === answer);
      option.classList.toggle("is-wrong", i === picked && picked !== answer);
    });
    const letter = options[answer]?.querySelector(".slide-quiz-card-letter")?.textContent || "";
    const text = picked === null ? `The answer is ${letter}.`
      : picked === answer ? "Correct!" : `Not quite. The answer is ${letter}.`;
    quiz.querySelector("[data-quiz-result]").textContent = text;
    const explain = quiz.querySelector("[data-quiz-explain]");
    if (explain) explain.hidden = false;
    const answerText = options[answer]?.querySelector(".slide-quiz-card-text")?.textContent.trim() || "";
    announce(`${text} ${letter}: ${answerText}. ${explain ? explain.textContent.trim() : ""}`.trim());
    blip(picked === null || picked === answer ? "right" : "wrong");
  }

  function resetQuizzes(index) {
    document.querySelectorAll(`.slide-page-frame[data-index="${index}"] [data-quiz]`).forEach((quiz) => {
      delete quiz.dataset.answered;
      quiz.querySelectorAll("[data-quiz-option]").forEach((o) => {
        o.removeAttribute("aria-disabled");
        o.classList.remove("is-correct", "is-wrong");
      });
      quiz.querySelector("[data-quiz-result]").textContent = "";
      const explain = quiz.querySelector("[data-quiz-explain]");
      if (explain) explain.hidden = true;
    });
  }

  // "A" shows the answers on the current slide, in every synced window.
  function revealQuizzes({ broadcast = true } = {}) {
    const quizzes = document.querySelectorAll(`.slide-page-frame[data-index="${current}"] [data-quiz]`);
    if (!quizzes.length) { announce("No quiz on this slide"); return; }
    quizzes.forEach((quiz) => answerQuiz(quiz, null));
    if (broadcast && channel) channel.postMessage({ reveal: current });
  }

  document.addEventListener("click", (event) => {
    const option = event.target.closest("[data-quiz-option]");
    if (!option) return;
    answerQuiz(option.closest("[data-quiz]"), Number(option.dataset.quizOption));
  });

  if (channel) {
    channel.onmessage = (event) => {
      const data = event.data || {};
      if (Number.isFinite(Number(data.reveal))) {
        if (Number(data.reveal) === current) revealQuizzes({ broadcast: false });
        return;
      }
      const index = Number(data.index);
      if (!Number.isFinite(index)) return;
      if (clamp(index, count) !== current) go(index, { broadcast: false, quiet: true });
      setStep(Number(data.step) || 0, { broadcast: false, quiet: true });
      setBlank(Boolean(data.blank), { broadcast: false, quiet: true });
    };
  }

  // --- Menus ------------------------------------------------------------------
  const dialogs = Object.fromEntries(
    [...document.querySelectorAll("dialog[data-dialog]")].map((d) => [d.dataset.dialog, d]),
  );
  const openDialog = () => Object.values(dialogs).find((d) => d.open);

  function toggleDialog(name) {
    const dialog = dialogs[name];
    if (!dialog) return;
    const already = openDialog();
    if (already) already.close();
    if (already === dialog) return;
    if (name === "options") syncOptionsForm();
    dialog.showModal();
    if (name === "outline") dialog.querySelector(`[data-goto="${current}"]`)?.focus();
  }

  document.querySelectorAll("[data-open-dialog]").forEach((button) => {
    button.addEventListener("click", () => toggleDialog(button.dataset.openDialog));
  });
  document.querySelectorAll("[data-close-dialog]").forEach((button) => {
    button.addEventListener("click", () => button.closest("dialog").close());
  });
  // Click on the backdrop closes a menu.
  Object.values(dialogs).forEach((dialog) => {
    dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
  });
  // Find a slide: matches its title and every word on it.
  const filter = document.querySelector("[data-outline-filter]");
  const filterStatus = document.querySelector("[data-outline-status]");
  const firstStage = document.querySelector(".deck-stage-canvas");
  const slideWords = (i) => (slideIn(i, firstStage || document)?.textContent || "").toLowerCase();
  filter?.addEventListener("input", () => {
    const query = filter.value.trim().toLowerCase();
    let shown = 0;
    document.querySelectorAll("[data-outline-item]").forEach((item) => {
      const i = Number(item.dataset.outlineItem);
      const match = !query || item.textContent.toLowerCase().includes(query) || slideWords(i).includes(query);
      item.hidden = !match;
      shown += match;
    });
    filterStatus.textContent = query ? `${shown} of ${count} slides match` : "";
  });
  filter?.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    document.querySelector("[data-outline-item]:not([hidden]) [data-goto]")?.click();
  });

  document.querySelectorAll("[data-goto]").forEach((button) => {
    button.addEventListener("click", () => {
      button.closest("dialog")?.close();
      go(Number(button.dataset.goto));
    });
  });

  // --- Options ----------------------------------------------------------------
  const form = document.querySelector("[data-options-form]");

  function syncOptionsForm() {
    if (!form) return;
    const stored = prefs.read();
    const now = prefs.effective(stored);
    const values = { theme: stored.theme || "", font: now.font, motion: now.motion, lcd: now.lcd, sound: now.sound };
    for (const [name, value] of Object.entries(values)) {
      const input = form.querySelector(`input[name="${name}"][value="${value}"]`);
      if (input) input.checked = true;
    }
  }

  function applyPrefs(changed) {
    // A palette picked here is saved, so the URL's ?theme= must go, or it
    // would win again on the next load.
    if (changed === "theme") {
      themeQuery = "";
      const url = new URL(location.href);
      url.searchParams.delete("theme");
      history.replaceState(null, "", url);
      updateLinks();
    }
    const now = prefs.apply();
    if (changed === "motion") typeDialogs();
    return now;
  }

  form?.addEventListener("change", (event) => {
    const { name, value } = event.target;
    prefs.set(name, value);
    applyPrefs(name);
    blip("toggle");
  });

  function quickToggle(name, on, off, label) {
    const now = prefs.effective();
    const value = now[name] === on ? off : on;
    prefs.set(name, value);
    const applied = applyPrefs(name);
    syncOptionsForm();
    blip("toggle");
    announce(label(applied));
  }

  // Other tabs (the presenter view, say) follow preference changes.
  window.addEventListener("storage", (event) => {
    if (event.key === prefs.KEY) { applyPrefs(); syncOptionsForm(); typeDialogs(); }
  });

  // --- Keyboard ------------------------------------------------------------------
  // Type a slide number then Enter to jump there.
  let typed = "";
  let typedTimer = 0;

  document.addEventListener("keydown", (event) => {
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    if (openDialog()) return;  // menus handle their own keys (Escape closes)
    if (event.target.closest("input, textarea, select, button, a, [contenteditable]") && [" ", "Enter"].includes(event.key)) return;

    if (/^[0-9]$/.test(event.key)) {
      typed = (typed + event.key).slice(-4);
      clearTimeout(typedTimer);
      typedTimer = setTimeout(() => { typed = ""; }, 1500);
      return;
    }
    switch (event.key) {
      case "Enter":
        if (!typed) return;
        go(Number(typed) - 1);
        typed = "";
        break;
      case "ArrowRight": case "ArrowDown": case "PageDown": case "n":
        step(1); break;
      case " ":
        step(event.shiftKey ? -1 : 1); break;
      case "ArrowLeft": case "ArrowUp": case "PageUp": case "b":
        step(-1); break;
      case "Home": go(0); break;
      case "End": go(count - 1); break;
      case "f":
        if (document.fullscreenElement) document.exitFullscreen();
        else document.documentElement.requestFullscreen?.();
        break;
      case "s":
        if (!isPresenter) window.open(`${base}/deck/${deckName}/${current + 1}/presenter${themeQuery}`, "_blank", "noopener");
        break;
      case "o": toggleDialog("outline"); break;
      case ".": setBlank(!blanked); break;
      case "a": revealQuizzes(); break;
      case "p": toggleDialog("options"); break;
      case "?": toggleDialog("help"); break;
      case "r":
        quickToggle("font", "readable", "pixel", (p) => (p.font === "readable" ? "Readable lettering on" : "Pixel lettering on"));
        break;
      case "c":
        quickToggle("theme", "contrast", root.dataset.defaultTheme, (p) => (p.theme === "contrast" ? "High contrast on" : "High contrast off"));
        break;
      case "m":
        quickToggle("sound", "on", "off", (p) => (p.sound === "on" ? "Sound on" : "Sound off"));
        break;
      default:
        return;
    }
    event.preventDefault();
  });

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-step]");
    if (button) step(Number(button.dataset.step));
  });

  // Swipe on touch screens (but let carousels scroll on their own).
  let swipeX = null;
  document.addEventListener("pointerdown", (e) => {
    swipeX = e.pointerType === "touch" && !e.target.closest(".slide-gallery-carousel-track, dialog") ? e.clientX : null;
  });
  document.addEventListener("pointerup", (e) => {
    if (swipeX === null) return;
    const dx = e.clientX - swipeX;
    if (Math.abs(dx) > 60) step(dx < 0 ? 1 : -1);
    swipeX = null;
  });

  // Hide the nav bar and cursor when the mouse rests (keyboard focus keeps it).
  if (!isPresenter && deckName) {
    let idleTimer = 0;
    const wake = () => {
      body.classList.remove("is-idle");
      clearTimeout(idleTimer);
      idleTimer = setTimeout(() => body.classList.add("is-idle"), 2500);
    };
    document.addEventListener("pointermove", wake);
    wake();
  }

  // --- Carousels -----------------------------------------------------------------
  document.querySelectorAll("[data-carousel]").forEach((carousel) => {
    const track = carousel.querySelector(".slide-gallery-carousel-track");
    const counter = carousel.querySelector("[data-carousel-counter]");
    const items = [...track.children];
    const total = items.length;
    const position = () => clamp(Math.round(track.scrollLeft / (items[0].offsetWidth || 1)), total);
    const update = () => {
      const at = position();
      counter.textContent = `${at + 1} / ${total}`;
      items.forEach((item, i) => item.setAttribute("aria-hidden", String(i !== at)));
    };
    carousel.querySelectorAll("[data-carousel-step]").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        const target = clamp(position() + Number(button.dataset.carouselStep), total);
        items[target].scrollIntoView({ block: "nearest", inline: "start", behavior: reducedMotion() ? "auto" : "smooth" });
      });
    });
    track.addEventListener("scroll", update, { passive: true });
    update();
  });

  // --- Presenter timer -----------------------------------------------------------
  const timer = document.querySelector("[data-timer]");
  if (timer) {
    let started = Date.now();
    let pausedAt = 0;
    let warned = new Set();
    const duration = (Number(body.dataset.duration) || 0) * 60;
    const left = document.querySelector("[data-time-left]");
    const pace = document.querySelector("[data-pace]");
    const panel = timer.closest(".presenter-clock-panel");
    const pad = (n) => String(n).padStart(2, "0");
    const clock = (total) => {
      const s = Math.max(0, Math.floor(total));
      const h = Math.floor(s / 3600);
      const m = Math.floor((s % 3600) / 60);
      return `${h ? `${h}:` : ""}${pad(m)}:${pad(s % 60)}`;
    };
    const tick = () => {
      const seconds = ((pausedAt || Date.now()) - started) / 1000;
      timer.textContent = clock(seconds);
      if (!duration) return;
      const remaining = duration - seconds;
      left.textContent = remaining >= 0 ? `${clock(remaining)} left` : `Over by ${clock(-remaining)}`;
      panel.classList.toggle("is-over", remaining < 0);
      panel.classList.toggle("is-late", remaining >= 0 && remaining <= 60);
      // The time this slide "should" come up, if every slide took the same
      // time, against the clock. Within one slide's worth counts as on pace.
      const perSlide = duration / count;
      const lead = current * perSlide - seconds;
      pace.textContent = remaining < 0 ? "Time is up"
        : Math.abs(lead) <= perSlide ? "On pace"
          : `${lead > 0 ? "Ahead" : "Behind"} by ${clock(Math.abs(lead))}`;
      for (const [mark, text] of [[300, "5 minutes left"], [60, "1 minute left"], [0, "Time is up"]]) {
        if (remaining <= mark && !warned.has(mark) && seconds > 1) {
          warned.add(mark);
          announce(text);
        }
      }
    };
    setInterval(tick, 1000);
    tick();
    const pauseButton = document.querySelector("[data-timer-pause]");
    pauseButton?.addEventListener("click", () => {
      if (pausedAt) { started += Date.now() - pausedAt; pausedAt = 0; } else { pausedAt = Date.now(); }
      pauseButton.setAttribute("aria-pressed", String(Boolean(pausedAt)));
      pauseButton.textContent = pausedAt ? "Resume timer" : "Pause timer";
      tick();
    });
    document.querySelector("[data-timer-reset]")?.addEventListener("click", () => {
      started = Date.now();
      if (pausedAt) pausedAt = started;
      warned = new Set();
      tick();
    });
  }

  // --- Boot screen (front matter `boot: true`), once per browser session ------
  const boot = document.querySelector("[data-boot-screen]");
  if (boot && current === 0 && !reducedMotion()) {
    let seen = false;
    try { seen = sessionStorage.getItem(`pixel-slides:booted:${deckName}`) === "1"; } catch { /* ignore */ }
    if (!seen) {
      boot.hidden = false;
      let done = false;
      const dismiss = () => {
        if (done) return;
        done = true;
        try { sessionStorage.setItem(`pixel-slides:booted:${deckName}`, "1"); } catch { /* ignore */ }
        boot.classList.add("is-leaving");
        setTimeout(() => { boot.hidden = true; }, 300);
        document.removeEventListener("keydown", onKey, true);
      };
      const onKey = (event) => { event.preventDefault(); event.stopImmediatePropagation(); dismiss(); };
      document.addEventListener("keydown", onKey, true);
      boot.addEventListener("click", dismiss);
      setTimeout(dismiss, 3200);
      setTimeout(() => blip("toggle"), 1600);
    }
  }

  // --- Live reload (only when the server runs with --dev) -----------------------
  if (body.hasAttribute("data-dev") && "EventSource" in window) {
    new EventSource(`${base}/events`).onmessage = (e) => { if (e.data === "reload") location.reload(); };
  }

  render();
})();
