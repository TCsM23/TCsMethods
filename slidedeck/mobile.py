"""Build the mobile app: an installable, offline web app (PWA).

    python -m slidedeck mobile                  # -> dist/mobile
    python -m slidedeck mobile --pyodide DIR    # use a Pyodide you already have

The same Python engine runs on the phone, inside Pyodide (Python compiled to
WebAssembly). The app renders a deck's pages once, keeps them in the
browser's cache, and a service worker serves them, so slides open instantly
and work in flight mode. Host the folder on any HTTPS static host (GitHub
Pages, Netlify, Cloudflare Pages), open it on the phone, and choose
"Install app" (Android) or Share > "Add to Home Screen" (iPhone).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import io
import json
import shutil
import tarfile
import urllib.request
import zipfile
from pathlib import Path

from .themes import theme_css

PACKAGE_DIR = Path(__file__).parent
SHELL_DIR = PACKAGE_DIR / "mobile_shell"
PYODIDE_VERSION = "314.0.7"  # Python 3.14, wheels tagged pyemscripten_2026_0
PYODIDE_TARBALL = f"https://registry.npmjs.org/pyodide/-/pyodide-{PYODIDE_VERSION}.tgz"
PYODIDE_FILES = ["pyodide.js", "pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"]
WHEEL_PLATFORM = "pyemscripten_2026_0_wasm32"

# The engine's pure-Python dependencies, copied from this environment.
# pydantic-core is compiled, so it comes as a WebAssembly wheel from PyPI.
PURE_DISTRIBUTIONS = ["pydantic", "typing_extensions", "annotated_types", "typing-inspection",
                      "jinja2", "markupsafe", "markdown-it-py", "mdurl", "pyyaml"]
# The modules the phone needs: no server, no desktop window, no PDF printer.
ENGINE_MODULES = ["__init__.py", "blocks.py", "embeds.py", "lint.py", "models.py", "navigation.py",
                  "parser.py", "qr.py", "render.py", "site.py", "starters.py", "themes.py"]


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310 - fixed https URLs
        return response.read()


def copy_pyodide(target: Path, source: str | None) -> None:
    target.mkdir(parents=True, exist_ok=True)
    if source:
        for name in PYODIDE_FILES:
            shutil.copy2(Path(source) / name, target / name)
        return
    print(f"Downloading Pyodide {PYODIDE_VERSION} (13 MB)…")
    with tarfile.open(fileobj=io.BytesIO(fetch(PYODIDE_TARBALL)), mode="r:gz") as tar:
        for name in PYODIDE_FILES:
            member = tar.extractfile(f"package/{name}")
            (target / name).write_bytes(member.read())


def pydantic_core_wheel(target: Path) -> str:
    """The WebAssembly build of the pydantic-core version pydantic pins."""
    version = metadata.version("pydantic_core")
    index = json.loads(fetch(f"https://pypi.org/pypi/pydantic-core/{version}/json"))
    for file in index["urls"]:
        if file["filename"].endswith(f"-cp314-cp314-{WHEEL_PLATFORM}.whl"):
            data = fetch(file["url"])
            if hashlib.sha256(data).hexdigest() != file["digests"]["sha256"]:
                raise SystemExit(f"Checksum mismatch for {file['filename']}")
            (target / file["filename"]).write_bytes(data)
            return file["filename"]
    raise SystemExit(f"pydantic-core {version} has no {WHEEL_PLATFORM} wheel. "
                     "Upgrade pydantic (python -m pip install -U pydantic) and build again.")


def engine_zip(target: Path) -> None:
    """slidedeck (engine only) plus its pure-Python dependencies, as one zip
    that Pyodide unpacks into its virtual file system."""
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in ENGINE_MODULES:
            zf.write(PACKAGE_DIR / name, f"slidedeck/{name}")
        for path in sorted((PACKAGE_DIR / "templates").rglob("*.html")):
            zf.write(path, f"slidedeck/{path.relative_to(PACKAGE_DIR).as_posix()}")
        for dist_name in PURE_DISTRIBUTIONS:
            dist = metadata.distribution(dist_name)
            for file in dist.files or []:
                parts = file.parts
                if parts[0] in ("..",) or parts[0].endswith(".dist-info") or "__pycache__" in parts:
                    continue
                if file.suffix not in (".py", ".typed", ".pyi") or parts[0] == "bin":
                    continue  # skip compiled speedups: the pure versions are used instead
                zf.write(file.locate(), file.as_posix())


def build(args: argparse.Namespace) -> None:
    out = Path(args.output)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    for path in SHELL_DIR.iterdir():
        if path.is_file():
            shutil.copy2(path, out / path.name)
    shutil.copytree(PACKAGE_DIR / "static", out / "static", ignore=shutil.ignore_patterns("desktop.js"))
    (out / "themes.css").write_text(theme_css(), encoding="utf-8")

    icons = Path(__file__).resolve().parent.parent / "packaging" / "icons"
    (out / "icons").mkdir()
    for name in ["icon-180.png", "icon-192.png", "icon-512.png", "maskable-192.png", "maskable-512.png", "icon-32.png"]:
        shutil.copy2(icons / name, out / "icons" / name)

    decks = Path(__file__).resolve().parent.parent / "decks"
    (out / "samples").mkdir()
    for path in sorted(decks.glob("*.md")):
        shutil.copy2(path, out / "samples" / path.name)
    if (decks / "media").is_dir():
        shutil.copytree(decks / "media", out / "media")

    copy_pyodide(out / "pyodide", args.pyodide)
    wheel = pydantic_core_wheel(out / "pyodide")
    engine_zip(out / "engine.zip")

    # Everything the service worker stores at install time, so the app works
    # offline from the first launch. The version changes whenever a file does,
    # which makes phones fetch the update and re-render their decks.
    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    digest = hashlib.sha256()
    for name in files:
        digest.update(name.encode())
        digest.update((out / name).read_bytes())
    version = digest.hexdigest()[:12]
    manifest = {"version": version, "files": ["./" if f == "index.html" else f for f in files],
                "samples": sorted(p.name for p in (out / "samples").glob("*.md")),
                "wheel": f"pyodide/{wheel}"}
    (out / "build.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    sw = (out / "sw.js").read_text(encoding="utf-8").replace("__VERSION__", version)
    (out / "sw.js").write_text(sw, encoding="utf-8")

    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"Wrote {out} ({len(files)} files, {size / 1e6:.1f} MB, version {version})")
