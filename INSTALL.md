# Installing Pixel Slides

Pixel Slides comes in two forms built from the same Python engine:

| | Desktop app (Windows, also Mac and Linux) | Mobile app (Android, iPhone, iPad) |
| --- | --- | --- |
| What it is | A native window running the slide server on your PC | An installable web app (PWA) that runs the engine on the phone itself, in WebAssembly |
| Install | A setup wizard | "Install app" / "Add to Home Screen" from the browser |
| Edit decks | In any text editor; open slides reload when you save | In the app's built-in editor |
| PDF export | One click (uses Edge in the background) | Print view, then the phone's Share > Print > Save as PDF |
| Offline | Yes | Yes, after the first launch |

## New in 0.4

- **Four new blocks**: `:::steps` (points that appear one press at a time), `:::chart` (pixel bar charts), `:::quiz` (multiple choice, press A to reveal) and `:::qr` (QR codes drawn as pixel art).
- **Presenting**: a countdown and pace guide when the deck has `duration: 20`, a pause-screen key (`.`), a pause button for the timer, and a search box in the slide list (O).
- **Handouts**: slides with their speaker notes and space to write, as a PDF.
- **Starters**: New deck asks for a starter (Basic, Talk or Lesson) on the desktop and the phone.
- **Desktop**: Duplicate and Handout PDF next to each deck.
- **Phone**: Insert block in the editor (no typing `:::` on a phone keyboard), and Duplicate.
- A new sample deck, **What's New in 0.4**, shows all of it. See the README for the syntax.

## Updating from 0.3

Your decks are never touched by an update. They stay in `Documents\Pixel Slides\decks`.

- **Desktop:** close Pixel Slides, unzip the new `pixel-slides-app.zip`, and run **`Install Pixel Slides.pyw`** again. Keep the same install folder. It reuses the existing Python environment, so it is quicker than the first time. The next start adds the new sample deck once (if you delete it, it stays deleted).
- **Phone:** publish the new `mobile` folder to the same place (drag it onto Netlify Drop for the same site, or push to GitHub Pages). Open the app once while online: it picks up the new version, re-renders your decks with the new engine, and adds the new sample deck.

## Windows: the install wizard

Your PC has Smart App Control (or a similar policy) turned on. It blocked `pip.exe` because that file is not signed by a publisher Microsoft knows. A home-built `Setup.exe` or `Pixel Slides.exe` is not signed either, so **it would be blocked too**. That is why there are two wizards.

### Option A: the Python wizard (works with Smart App Control)

It only runs Python's own signed programs and uses `python -m pip`, so it gets through.

1. Install Python 3.11 or newer from python.org if you have not already (you have, since you made a venv). Tick "Add python.exe to PATH".
2. Unzip `pixel-slides-app.zip` anywhere, for example into Downloads.
3. Double-click **`Install Pixel Slides.pyw`**. If Windows asks what to open it with, pick Python. Or, in a terminal in that folder:

   ```
   python "Install Pixel Slides.pyw"
   ```

4. Click through: Welcome, Install folder, Options (desktop shortcut, PDF export), Install, Finish. It downloads about 60 MB, so stay online.

You get a Start menu entry, an optional desktop shortcut, and an entry in **Settings > Apps > Installed apps** with a working Uninstall. It installs for your user only, with no admin prompt, into `%LOCALAPPDATA%\Programs\Pixel Slides`. Your decks go in `Documents\Pixel Slides\decks`, and uninstalling never removes them.

### Option B: a real Setup.exe (for PCs without Smart App Control, or once it is signed)

This is the classic Inno Setup wizard (Welcome, folder, shortcuts, Finish, "Launch Pixel Slides") with a self-contained app that needs no Python.

Build it on Windows:

```
winget install JRSoftware.InnoSetup
powershell -ExecutionPolicy Bypass -File packaging\build-windows.ps1
```

The output is `dist\installer\PixelSlides-Setup-0.4.0.exe`. If you put the project on GitHub, `.github/workflows/build-apps.yml` builds the same file on every push (download it under Actions > the run > Artifacts).

To run it on your own PC, Smart App Control has to accept it. There are two ways:

- **Sign it.** Microsoft's Azure Trusted Signing (about $10 a month) gives you a certificate that Smart App Control trusts. Add a `signtool sign` step after PyInstaller and after Inno Setup.
- **Turn Smart App Control off** under Windows Security > App & browser control. On some Windows 11 versions you cannot turn it back on without resetting Windows, so check what your version says before you do it. Option A avoids this.

### Run it without installing

From the unzipped folder, with your existing venv:

```
python -m pip install -r requirements-desktop.txt
python -m slidedeck app
```

## Using the desktop app

- The deck list has **New deck** (pick a title and a starter: Basic, Talk or Lesson), **Open decks folder**, and next to each deck **Edit** (opens the `.md` in your default editor), **Export PDF** and **Handout PDF** (slides with speaker notes; both save to `Documents\Pixel Slides\exports` and show the file in Explorer), and **Duplicate** (a copy titled "… (copy)", to try changes safely).
- Save a deck in your editor and every open slide window reloads.
- **S** or the Presenter button opens the presenter view in its own window, synced with the slides: steps, the pause screen (**.**) and quiz answers (**A**) follow from one window to the other. With `duration:` in the deck's front matter it counts down and shows your pace.
- The app picks the best window it can: a native window (pywebview, Edge WebView2), else an Edge app window with no tabs or address bar, else a browser tab. To force one: `python -m slidedeck app --window edge`.
- If something goes wrong, the log is at `%LOCALAPPDATA%\Pixel Slides\pixel-slides.log`.

## Mobile: install on a phone

A phone cannot run a Python server, so the mobile app works differently. It ships the Python engine compiled to WebAssembly (Pyodide), renders each deck once on the phone, and keeps the pages offline. It is the same parser, blocks, templates and accessibility checks as the desktop.

The app has to be served once over HTTPS so the phone can install it. After that it runs offline. Pick one:

- **Netlify Drop (no account setup, 2 minutes):** unzip `pixel-slides-mobile.zip`, go to app.netlify.com/drop, and drag the `mobile` folder onto the page. You get an `https://….netlify.app` link.
- **GitHub Pages:** push the project to GitHub, set Settings > Pages > Source to "GitHub Actions", and the workflow publishes it on every push to `main`.
- To build the folder yourself: `python -m slidedeck mobile` (writes `dist/mobile`).

Then on the phone, open the link and:

- **Android (Chrome):** tap **Install app** in the deck list, or menu ⋮ > Install app.
- **iPhone / iPad (Safari):** Share > **Add to Home Screen**.

It opens full screen like any app. The first launch downloads about 16 MB and takes a few seconds while the engine starts. After that, decks open instantly, in flight mode too.

On the phone you can open, present (swipe or tap the arrows), read the text version, answer quizzes by tapping, and **New deck** (with a starter), **Import .md**, **Edit**, **Insert block** (steps, chart, quiz, QR code and the rest, at the cursor), **Add picture**, **Share .md**, **Duplicate** and **Delete**. Turn the phone sideways for full-size slides.

### What does not carry over to mobile

- **PDF export** uses a headless browser, which phones cannot run. Use **Print** in the deck's bar, then the phone's own Share > Print > Save as PDF. For a handout, open `…/deck/<name>/print?notes=1` and print that.
- **Decks stay on the device.** There is no sync between phone and PC. Move a deck with Share .md on the phone and Import .md (or copy into the decks folder) on the other side.
- **Live reload while editing in another app** is desktop only. On the phone, press Save and play.
- **iPhone storage:** Safari can clear a website's data if it is not used for a few weeks. Adding it to the Home Screen protects it, and Share .md keeps a copy of anything important.
