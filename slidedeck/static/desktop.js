// Desktop app only: the deck list's tools, and new windows for the presenter.
// Every call carries the token from the page, so other local pages cannot
// drive these endpoints.
(() => {
  "use strict";

  const base = document.documentElement.dataset.base || "";
  const token = document.querySelector('meta[name="desktop-token"]')?.content || "";
  const status = document.querySelector("[data-desktop-status]");

  async function call(path, payload = {}) {
    const response = await fetch(`${base}/desktop/${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Desktop-Token": token },
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    return data;
  }

  const say = (text) => { if (status) status.textContent = text; };

  // Presenter and print open in their own app window, not the system browser,
  // so the presenter stays in sync with the slides (same storage, same channel).
  async function openWindow(url) {
    const target = new URL(url, location.href);
    try {
      const { opened } = await call("window", { url: target.pathname + target.search });
      return opened;
    } catch {
      return false;
    }
  }
  const nativeOpen = window.open.bind(window);
  window.open = (url, target, features) => {
    openWindow(url).then((opened) => { if (!opened) nativeOpen(url, target, features); });
    return null;
  };
  document.addEventListener("click", (event) => {
    const link = event.target.closest?.('a[target="_blank"]');
    if (!link || new URL(link.href).origin !== location.origin) return;
    event.preventDefault();
    window.open(link.href, "_blank");
  });

  // New deck: a title and a starter, in a native dialog.
  const newDialog = document.querySelector("[data-new-deck-dialog]");
  const newForm = document.querySelector("[data-new-deck-form]");
  document.querySelector("[data-close-new-deck]")?.addEventListener("click", () => newDialog.close());
  newForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(newForm);
    newDialog.close();
    try {
      const { name } = await call("new-deck", { title: data.get("title"), starter: data.get("starter") });
      say(`Created ${name}.md and opened it in your editor. Save it to see the slides.`);
      setTimeout(() => location.reload(), 600);
    } catch (error) {
      say(`Could not do that: ${error.message}`);
    }
  });

  async function exportPdf(deck, handout) {
    const kind = handout ? "handout" : "PDF";
    say(`Exporting ${deck} as a ${kind}…`);
    const result = await call(`export/${deck}`, { handout });
    if (result.path) {
      say(`Saved ${result.path}`);
    } else {
      // No PDF engine: the print view and the system's "Save as PDF" do the same job.
      say("Choose “Save as PDF” in the print dialog.");
      await openWindow(`${base}/deck/${deck}/print?${handout ? "notes=1&" : ""}autoprint=1`);
    }
  }

  const actions = {
    async "new-deck"() {
      if (newDialog) {
        newDialog.showModal();
        newDialog.querySelector("input[name=title]")?.select();
        return;
      }
      const title = window.prompt("Title of the new deck", "My talk");
      if (!title) return;
      const { name } = await call("new-deck", { title });
      say(`Created ${name}.md and opened it in your editor. Save it to see the slides.`);
      setTimeout(() => location.reload(), 600);
    },
    async duplicate(button) {
      const { name } = await call(`duplicate/${button.dataset.deck}`);
      say(`Copied to ${name}.md.`);
      setTimeout(() => location.reload(), 600);
    },
    async handout(button) {
      await exportPdf(button.dataset.deck, true);
    },
    async "open-folder"() {
      await call("open-folder");
    },
    async edit(button) {
      await call(`edit/${button.dataset.deck}`);
      say(`Opened ${button.dataset.deck}.md. Save it and open slides reload on their own.`);
    },
    async export(button) {
      await exportPdf(button.dataset.deck, false);
    },
  };

  document.addEventListener("click", async (event) => {
    const button = event.target.closest?.("[data-desktop-action]");
    if (!button) return;
    button.disabled = true;
    try {
      await actions[button.dataset.desktopAction](button);
    } catch (error) {
      say(`Could not do that: ${error.message}`);
    } finally {
      button.disabled = false;
    }
  });

  if (document.body.classList.contains("print-view") && new URLSearchParams(location.search).has("autoprint")) {
    document.fonts.ready.then(() => setTimeout(() => window.print(), 300));
  }
})();
