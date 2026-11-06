// Viewer preferences: palette, lettering, motion, screen effect, sound.
// Loaded in <head> so they apply before the first paint (no flash of the
// wrong palette). Stored per browser; the page works the same without them.
(() => {
  "use strict";

  const KEY = "pixel-slides:prefs";
  const root = document.documentElement;
  const media = (query) => window.matchMedia && window.matchMedia(query).matches;

  function read() {
    try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch { return {}; }
  }
  function write(prefs) {
    try { localStorage.setItem(KEY, JSON.stringify(prefs)); } catch { /* private mode: keep for this page only */ }
  }

  // What the page should use right now: an explicit choice, else the system
  // setting, else the deck's own default.
  function effective(prefs = read()) {
    const known = (root.dataset.themes || "").split(" ");
    const urlTheme = new URLSearchParams(location.search).get("theme");
    let theme = root.dataset.defaultTheme;
    if (known.includes(urlTheme)) theme = urlTheme;  // a shared ?theme= link wins
    else if (known.includes(prefs.theme)) theme = prefs.theme;
    else if (media("(prefers-contrast: more)") || media("(forced-colors: active)")) theme = "contrast";
    return {
      theme,
      font: prefs.font || "pixel",
      motion: prefs.motion || (media("(prefers-reduced-motion: reduce)") ? "reduce" : "full"),
      lcd: prefs.lcd || "on",
      sound: prefs.sound || "off",
    };
  }

  function apply(prefs = read()) {
    const now = effective(prefs);
    for (const name of [...root.classList]) if (name.startsWith("theme-")) root.classList.remove(name);
    root.classList.add(`theme-${now.theme}`);
    root.dataset.font = now.font;
    root.dataset.motion = now.motion;
    root.dataset.lcd = now.lcd;
    root.dataset.sound = now.sound;
    return now;
  }

  function set(name, value) {
    const prefs = read();
    if (value) prefs[name] = value; else delete prefs[name];
    write(prefs);
    return apply(prefs);
  }

  window.PixelPrefs = { KEY, read, effective, apply, set };
  apply();
})();
