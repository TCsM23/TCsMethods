// Service worker for the mobile app. It plays the server's part:
//  - the app's own files come from a cache filled at install (works offline);
//  - deck pages come from a second cache, which the app fills when it
//    renders a deck with the Python engine;
//  - it clamps slide numbers and adds the same security headers as the server.
"use strict";

const VERSION = "__VERSION__";
const SHELL = `pixel-slides-shell-${VERSION}`;
const USER = "pixel-slides-user";  // decks, their rendered pages, added pictures
const base = new URL(self.registration.scope).pathname.replace(/\/$/, "");

const CSP = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self'",
  "font-src 'self'",
  "img-src 'self' https: data: blob:",
  "media-src 'self'",
  "frame-src https://www.youtube-nocookie.com https://player.vimeo.com",
  "connect-src 'self'",
  "object-src 'none'",
  "base-uri 'none'",
].join("; ");

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const build = await (await fetch("build.json", { cache: "reload" })).json();
    const cache = await caches.open(SHELL);
    await cache.addAll(["build.json", ...build.files].map((file) => new Request(file, { cache: "reload" })));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    for (const name of await caches.keys()) {
      if (name.startsWith("pixel-slides-shell-") && name !== SHELL) await caches.delete(name);
    }
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== location.origin) return;
  if (!(url.pathname + "/").startsWith(base + "/")) return;
  event.respondWith(handle(event.request, url, url.pathname.slice(base.length) || "/"));
});

async function handle(request, url, path) {
  const user = await caches.open(USER);
  if (path.startsWith("/deck/")) return deckPage(user, url, path);
  if (path.startsWith("/media/")) {
    const added = await user.match(url.origin + url.pathname);
    if (added) return added;
  }
  const shell = await (await caches.open(SHELL)).match(request, { ignoreSearch: true });
  if (shell) return shell;
  try {
    return await fetch(request);
  } catch {
    return page(404, "Not found", "This page is not stored on this device.");
  }
}

const userKey = (url, path) => `${url.origin}${base}${path}`;

async function deckPage(user, url, path) {
  const match = path.match(/^\/deck\/([a-z0-9][a-z0-9-]{0,63})(?:\/(.*))?$/);
  if (!match) return page(404, "No such deck", "Deck names use a to z, 0 to 9 and dashes.");
  const [, name, rest = ""] = match;

  // ?theme= is applied in the page itself, so it never changes the stored page.
  let key = userKey(url, `/deck/${name}${rest ? `/${rest}` : ""}`);
  if ((rest === "text" || rest === "print") && url.searchParams.get("notes") === "1") key += "?notes=1";
  const stored = await user.match(key);
  if (stored) return withHeaders(stored);

  const summary = await user.match(userKey(url, `/__decks/${name}.json`));
  if (!summary) return page(404, "No such deck", "It may have been deleted on this device.");
  const { count } = await summary.json();

  // The same rule as the server: one URL per slide, always in range.
  const number = rest.match(/^(-?\d+)(\/presenter)?$/);
  if (rest === "" || number) {
    const wanted = number ? Number(number[1]) : 1;
    const clamped = Math.max(1, Math.min(Number.isFinite(wanted) ? wanted : 1, count));
    const target = new URL(`${base}/deck/${name}/${clamped}${number?.[2] || ""}`, url);
    target.search = url.search;
    return Response.redirect(target.href, 302);
  }
  return page(404, "Not found", `'${rest}' is not a page of this deck.`);
}

function withHeaders(response) {
  const headers = new Headers(response.headers);
  headers.set("Content-Type", "text/html; charset=utf-8");
  headers.set("Content-Security-Policy", CSP);
  headers.set("X-Content-Type-Options", "nosniff");
  headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  return new Response(response.body, { status: response.status, headers });
}

function page(status, title, text) {
  const escape = (s) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const body = `<!doctype html><html lang="en" class="theme-dmg"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>${escape(title)}</title>
<link rel="stylesheet" href="${base}/static/fonts/fonts.css"><link rel="stylesheet" href="${base}/themes.css">
<link rel="stylesheet" href="${base}/static/theme.css"><link rel="stylesheet" href="${base}/static/slides.css">
<body class="library-view"><main class="library-list-container"><p class="library-list-kicker">Error ${status}</p>
<h1 class="library-list-header">${escape(title)}</h1><p>${escape(text)}</p>
<p><a class="library-list-item-link" href="${base}/">Back to decks</a></p></main>`;
  return withHeaders(new Response(body, { status }));
}
