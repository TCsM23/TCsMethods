// The mobile app's deck list and editor. Decks are rendered by the same Python
// engine as the desktop (in Pyodide), and the pages are stored in the
// browser's cache, where the service worker serves them, offline included.

const base = new URL(".", location.href).pathname.replace(/\/$/, "");
const USER = "pixel-slides-user";
const IMAGE_TYPES = { "image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/webp": "webp", "image/avif": "avif", "image/svg+xml": "svg" };

const $ = (selector) => document.querySelector(selector);
const statusLine = $("[data-status]");
const say = (text) => { statusLine.textContent = text; };
const key = (path) => `${location.origin}${base}${path}`;
const store = () => caches.open(USER);

// --- Storage ----------------------------------------------------------------------

async function readJson(path) {
  const hit = await (await store()).match(key(path));
  return hit ? hit.json() : null;
}

async function writeFile(path, body, type) {
  await (await store()).put(key(path), new Response(body, { headers: { "Content-Type": type } }));
}

async function listDecks() {
  const cache = await store();
  const names = (await cache.keys())
    .map((request) => new URL(request.url).pathname.match(/\/__decks\/([a-z0-9-]+)\.json$/)?.[1])
    .filter(Boolean);
  const decks = await Promise.all(names.map((name) => readJson(`/__decks/${name}.json`)));
  return decks.filter(Boolean).sort((a, b) => a.title.localeCompare(b.title));
}

async function readSource(name) {
  const hit = await (await store()).match(key(`/__decks/${name}.md`));
  return hit ? hit.text() : "";
}

async function deleteDeck(name) {
  const cache = await store();
  for (const request of await cache.keys()) {
    const path = new URL(request.url).pathname.slice(base.length);
    if (path.startsWith(`/deck/${name}/`) || path === `/__decks/${name}.md` || path === `/__decks/${name}.json`) {
      await cache.delete(request);
    }
  }
}

// --- The engine (Python in WebAssembly), loaded on first use -------------------------

let engine = null;

async function loadEngine() {
  if (engine) return engine;
  const boot = $("[data-boot]");
  boot.hidden = false;
  try {
    const build = await (await fetch(`${base}/build.json`)).json();
    const { loadPyodide } = await import(`${base}/pyodide/pyodide.mjs`);
    const py = await loadPyodide({ indexURL: `${base}/pyodide/` });
    await py.loadPackage(`${base}/${build.wheel}`, { messageCallback: () => {} });
    const zip = await (await fetch(`${base}/engine.zip`)).arrayBuffer();
    py.unpackArchive(new Uint8Array(zip), "zip", { extractDir: "/engine" });
    py.runPython("import sys; sys.path.insert(0, '/engine')");
    $("[data-boot-text]").textContent = "Loading the slide engine…";
    engine = py.pyimport("slidedeck.site");
    return engine;
  } finally {
    boot.hidden = true;
  }
}

async function renderDeck(name, source) {
  const site = await loadEngine();
  const result = JSON.parse(site.build(name, source, base));
  await writeFile(`/__decks/${name}.md`, source, "text/markdown; charset=utf-8");
  if (!result.ok) return result;
  const cache = await store();
  const keep = new Set(Object.keys(result.pages).map(key));
  for (const request of await cache.keys()) {
    const path = new URL(request.url).pathname.slice(base.length);
    if (path.startsWith(`/deck/${name}/`) && !keep.has(request.url)) await cache.delete(request);
  }
  await Promise.all(Object.entries(result.pages).map(([path, html]) =>
    cache.put(key(path), new Response(html, { headers: { "Content-Type": "text/html; charset=utf-8" } }))));
  await writeFile(`/__decks/${name}.json`, JSON.stringify(result.summary), "application/json");
  return result;
}

// First start: the sample decks. After an app update: render every deck again,
// since the templates may have changed.
async function syncWithBuild() {
  const build = await (await fetch(`${base}/build.json`)).json();
  const meta = (await readJson("/__meta.json")) || {};
  if (meta.version === build.version) return;
  const names = new Set((await listDecks()).map((deck) => deck.name));
  // Each sample deck is offered once: all on the first start, then only the
  // ones an update brings. A sample you deleted stays deleted.
  const offered = new Set(meta.samples || (meta.version ? ["intro.md"] : []));
  for (const file of build.samples) {
    const name = file.replace(/\.md$/, "");
    if (!offered.has(file) && !names.has(name)) {
      await writeFile(`/__decks/${name}.md`, await (await fetch(`${base}/samples/${file}`)).text(), "text/markdown");
      names.add(name);
    }
    offered.add(file);
  }
  for (const name of names) {
    say(`Preparing ${name}…`);
    await renderDeck(name, await readSource(name));
  }
  await writeFile("/__meta.json", JSON.stringify({ version: build.version, samples: [...offered] }), "application/json");
  say("");
}

// --- Library ----------------------------------------------------------------------

function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children.filter((child) => child !== null && child !== undefined));
  return node;
}
const hidden = (text) => el("span", { className: "visually-hidden", textContent: text });

async function showLibrary() {
  showView("library");
  const list = $("[data-deck-list]");
  const decks = await listDecks();
  list.replaceChildren(...decks.map((deck) => el("li", { className: "library-list-item" },
    el("a", { className: "library-list-item-link", href: `${base}/deck/${deck.name}/1` },
      el("span", { className: "library-list-item-cursor", ariaHidden: "true", textContent: "▶" }),
      el("span", { className: "library-list-item-title", textContent: deck.title }),
      el("span", { className: "library-list-item-meta", textContent: `${deck.count} slides · ${deck.theme_label}` })),
    el("a", { className: "library-list-item-text", href: `${base}/deck/${deck.name}/text` }, "Text version", hidden(` of ${deck.title}`)),
    el("button", { type: "button", className: "library-list-item-action", onclick: () => openEditor(deck.name) }, "Edit", hidden(` ${deck.title}`)),
  )));
  if (!decks.length) list.append(el("li", { className: "library-list-item", textContent: "No decks yet. Press New deck." }));
}

function showView(name) {
  for (const view of document.querySelectorAll("[data-view]")) view.hidden = view.dataset.view !== name;
  document.title = name === "editor" ? "Edit deck · Pixel Slides" : "Pixel Slides";
}

const slugify = (text) => text.toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 48).replace(/-+$/, "") || "deck";

async function freeName(wanted) {
  const taken = new Set((await listDecks()).map((deck) => deck.name));
  let name = slugify(wanted);
  for (let n = 2; taken.has(name); n += 1) name = `${slugify(wanted)}-${n}`;
  return name;
}

// Snippets for Insert block: typing ::: on a phone keyboard is no fun.
const SNIPPETS = [
  ["New slide", "Starts the next slide", "\n\n---\n\n## New slide\n\n"],
  ["Steps", "A list that appears one line per tap", "\n:::steps\n- First point\n- Second point\n- Third point\n:::\n"],
  ["Chart", "A pixel bar chart", '\n:::chart title="My chart" unit=points\nFirst: 10\nSecond: 25\nThird: 18\n:::\n'],
  ["Quiz", "A question with one right answer", "\n:::quiz\nYour question?\n- [ ] A wrong answer\n- [x] The right answer\n- [ ] Another wrong answer\nWhy it is right (shown after an answer).\n:::\n"],
  ["QR code", "A link people can scan", "\n:::qr https://example.com\nScan for the slides\n:::\n"],
  ["Callout", "A note, warning, quote or big number", '\n:::callout note title="Heads up"\nYour text.\n:::\n'],
  ["Columns", "Two columns side by side", "\n:::columns two\nLeft side\n+++\nRight side\n:::\n"],
  ["Dialog", "An RPG text box that types itself", "\n:::dialog GUIDE\nWhat the guide says.\n:::\n"],
  ["Meter", "An HP-style bar", '\n:::meter label="Progress" value=3 max=5\n:::\n'],
  ["Sprite", "Pixel art from digits 0 to 3", '\n:::sprite alt="A heart" scale=12\n.33.33.\n3223223\n.32223.\n..323..\n...3...\n:::\n'],
  ["Video", "A YouTube or Vimeo video", '\n:::video https://youtu.be/VIDEO_ID title="What the video shows"\n:::\n'],
  ["Speaker notes", "Only you see these, in the presenter view", "\n???\nWhat to say on this slide.\n"],
];

// --- Editor -----------------------------------------------------------------------

let editing = null;
const source = $("[data-source]");

async function openEditor(name) {
  editing = name;
  source.value = await readSource(name);
  $("[data-editor-title]").textContent = `Edit ${name}`;
  $("[data-report]").replaceChildren();
  showView("editor");
  say("");
  source.focus();
}

function report(result) {
  const box = $("[data-report]");
  if (!result.ok) {
    box.replaceChildren(el("p", { className: "editor-pane-error", textContent: `Not saved as slides: ${result.error}` }));
    return;
  }
  const issues = result.summary.issues;
  box.replaceChildren(...[
    el("p", { textContent: `${result.summary.count} slides. ${issues.length ? `${issues.length} thing(s) to check:` : "No problems found."}` }),
    issues.length ? el("ul", { className: "editor-pane-issues" }, ...issues.map((issue) =>
      el("li", { className: `editor-pane-issue is-${issue.level}`, textContent: `Slide ${issue.slide}: ${issue.message}` }))) : null,
  ].filter(Boolean));
}

async function save() {
  say("Rendering…");
  const result = await renderDeck(editing, source.value);
  report(result);
  say(result.ok ? "Saved." : "Saved the text, but the deck has an error.");
  return result;
}

function insertSnippet(text) {
  const at = source.selectionEnd ?? source.value.length;
  source.setRangeText(text, at, at, "end");
  source.focus();
}

const insertDialog = $("[data-insert-dialog]");
$("[data-snippets]").replaceChildren(...SNIPPETS.map(([label, hint, text]) => el("li", { className: "editor-insert-item" },
  el("button", { type: "button", className: "editor-insert-button", onclick: () => { insertDialog.close(); insertSnippet(text); say(`Inserted ${label.toLowerCase()}.`); } },
    el("span", { className: "editor-insert-label", textContent: label }),
    el("span", { className: "editor-insert-hint-text", textContent: hint })))));

const newDialog = $("[data-new-dialog]");
const newForm = $("[data-new-form]");
document.querySelectorAll("dialog [data-close]").forEach((button) => button.addEventListener("click", () => button.closest("dialog").close()));
document.querySelectorAll("dialog").forEach((dialog) => dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); }));

async function showStarters() {
  const site = await loadEngine();
  const list = JSON.parse(site.starters());
  const group = $("[data-starters]");
  group.replaceChildren(group.querySelector("legend"), ...list.map((starter, i) => el("label", { className: "deck-options-choice library-new-deck-choice" },
    el("input", { type: "radio", name: "starter", value: starter.name, checked: i === 0 }),
    el("span", { className: "deck-options-choice-label" }, `${starter.label} `,
      el("span", { className: "library-new-deck-hint", textContent: starter.description })))));
  newDialog.showModal();
  newDialog.querySelector("input[name=title]").select();
}

newForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(newForm);
  newDialog.close();
  try {
    const title = String(data.get("title") || "").replace(/\s+/g, " ").trim() || "My talk";
    const site = await loadEngine();
    const name = await freeName(title);
    await writeFile(`/__decks/${name}.md`, site.new_deck(title, String(data.get("starter") || "basic")), "text/markdown");
    await openEditor(name);
  } catch (error) {
    say(`Something went wrong: ${error.message}`);
  }
});

async function addPicture(file) {
  const ext = IMAGE_TYPES[file.type];
  if (!ext) return say("That picture type is not supported.");
  const name = `${slugify(file.name.replace(/\.[^.]+$/, ""))}.${ext}`;
  await writeFile(`/media/${name}`, file, file.type);
  const snippet = `\n:::gallery\n![Describe the picture](media/${name})\n:::\n`;
  const at = source.selectionEnd ?? source.value.length;
  source.setRangeText(snippet, at, at, "end");
  source.focus();
  say(`Added ${name}. Describe it in the brackets: that text is read to people who cannot see it.`);
}

async function share() {
  const file = new File([source.value], `${editing}.md`, { type: "text/markdown" });
  if (navigator.canShare?.({ files: [file] })) {
    try { await navigator.share({ files: [file], title: editing }); } catch { /* cancelled */ }
    return;
  }
  const link = el("a", { href: URL.createObjectURL(file), download: file.name });
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

// --- Wiring -------------------------------------------------------------------------

const actions = {
  async new() {
    await showStarters();
  },
  async insert() {
    insertDialog.showModal();
    insertDialog.querySelector("button.editor-insert-button")?.focus();
  },
  async duplicate() {
    await save();
    const name = await freeName(`${editing}-copy`);
    const site = await loadEngine();
    const result = await renderDeck(name, site.duplicate(source.value));
    await openEditor(name);
    say(result.ok ? `Copied to ${name}. You are now editing the copy.` : `Copied to ${name}, but it has an error.`);
  },
  async play() {
    const result = await save();
    if (result.ok) location.href = `${base}/deck/${editing}/1`;
  },
  save,
  share,
  async back() { await showLibrary(); },
  async delete() {
    if (!confirm(`Delete ${editing}? This cannot be undone.`)) return;
    await deleteDeck(editing);
    say(`Deleted ${editing}.`);
    await showLibrary();
  },
  async install() {
    installPrompt?.prompt();
    installPrompt = null;
    $('[data-action="install"]').hidden = true;
  },
};

document.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  button.disabled = true;
  try {
    await actions[button.dataset.action]();
  } catch (error) {
    say(`Something went wrong: ${error.message}`);
  } finally {
    button.disabled = false;
  }
});

$("[data-import]").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  event.target.value = "";
  if (!file) return;
  const name = await freeName(file.name.replace(/\.[^.]+$/, ""));
  const result = await renderDeck(name, await file.text());
  await showLibrary();
  say(result.ok ? `Imported ${name}.` : `Imported ${name}, but it has an error: ${result.error}`);
});

$("[data-picture]").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  event.target.value = "";
  if (file) await addPicture(file);
});

let installPrompt = null;
addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  installPrompt = event;
  $('[data-action="install"]').hidden = false;
});

async function start() {
  if (!("serviceWorker" in navigator) || !("caches" in window)) {
    say("This browser cannot run Pixel Slides offline. Open it in Chrome, Edge, Safari or Firefox over https.");
    return;
  }
  await navigator.serviceWorker.register(`${base}/sw.js`);
  if (!navigator.serviceWorker.controller) {
    // First visit: wait until the worker has stored the app and taken over.
    say("Installing for offline use…");
    await new Promise((resolve) => navigator.serviceWorker.addEventListener("controllerchange", resolve, { once: true }));
  }
  await syncWithBuild();
  await showLibrary();
}

start().catch((error) => say(`Could not start: ${error.message}`));
