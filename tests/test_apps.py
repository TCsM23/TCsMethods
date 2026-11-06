"""The desktop and mobile packaging: static rendering, URL base, desktop API, shortcuts."""
import json
import re
import sys
import zipfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from slidedeck import site
from slidedeck.desktop import NEW_DECK, WindowHost, make_router, slugify
from slidedeck.render import env

ROOT = Path(__file__).parent.parent
INTRO = (ROOT / "decks" / "intro.md").read_text(encoding="utf-8")
sys.path.insert(0, str(ROOT / "packaging"))


# --- Static rendering (the mobile app) ---------------------------------------------


def test_build_renders_every_page():
    result = json.loads(site.build("intro", INTRO))
    count = result["summary"]["count"]
    pages = result["pages"]
    assert result["ok"] and count == 15
    for n in range(1, count + 1):
        assert f"/deck/intro/{n}" in pages and f"/deck/intro/{n}/presenter" in pages
    assert {"/deck/intro/text", "/deck/intro/text?notes=1", "/deck/intro/print"} <= pages.keys()
    assert 'data-index="2"' in pages["/deck/intro/3"]


def test_build_reports_deck_errors_instead_of_raising():
    result = json.loads(site.build("bad", "---\ntheme: nope\n---\n# Hi\n"))
    assert result == {"ok": False, "error": result["error"]} and "unknown theme" in result["error"]


def test_base_prefixes_every_site_link():
    pages = json.loads(site.build("intro", INTRO, "/pixel-slides"))["pages"]
    for html in pages.values():
        links = re.findall(r'(?:href|src)="(/[^"]*)"', html)
        assert links and all(link.startswith("/pixel-slides/") for link in links)
    assert env.globals["base"] == ""  # reset for the server afterwards


def test_no_external_fonts_or_inline_styles():
    for html in json.loads(site.build("intro", INTRO))["pages"].values():
        assert "fonts.googleapis.com" not in html
        assert " style=" not in html


def test_bundled_fonts_exist():
    css = (ROOT / "slidedeck" / "static" / "fonts" / "fonts.css").read_text()
    files = re.findall(r"url\(([^)]+)\)", css)
    assert len(files) >= 9
    for name in files:
        assert (ROOT / "slidedeck" / "static" / "fonts" / name).is_file()


def test_engine_zip_has_engine_but_no_server(tmp_path):
    from slidedeck.mobile import engine_zip

    engine_zip(tmp_path / "engine.zip")
    names = set(zipfile.ZipFile(tmp_path / "engine.zip").namelist())
    assert {"slidedeck/site.py", "slidedeck/templates/deck.html", "jinja2/__init__.py",
            "markdown_it/__init__.py", "pydantic/__init__.py", "yaml/__init__.py"} <= names
    assert "slidedeck/app.py" not in names and "slidedeck/desktop.py" not in names
    assert not any(name.endswith((".so", ".pyd")) for name in names)


# --- Desktop API -------------------------------------------------------------------------


@pytest.fixture
def desktop(tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr("slidedeck.desktop.open_path", lambda path, reveal=False: opened.append(path) or True)
    decks = tmp_path / "decks"
    decks.mkdir()
    (decks / "intro.md").write_text(INTRO, encoding="utf-8")
    app = FastAPI()
    public, router = make_router(decks, tmp_path / "exports", "secret", WindowHost("http://x"))
    app.include_router(public)
    app.include_router(router)
    return TestClient(app), decks, opened


def test_desktop_api_needs_the_token(desktop):
    client, _, opened = desktop
    assert client.get("/desktop/ping").json() == {"app": "pixel-slides"}
    assert client.post("/desktop/open-folder").status_code == 403
    assert client.post("/desktop/open-folder", headers={"X-Desktop-Token": "wrong"}).status_code == 403
    assert client.post("/desktop/open-folder", headers={"X-Desktop-Token": "secret"}).status_code == 200
    assert len(opened) == 1


def test_new_deck_gets_a_free_name_and_parses(desktop):
    client, decks, _ = desktop
    headers = {"X-Desktop-Token": "secret"}
    first = client.post("/desktop/new-deck", json={"title": "My Talk!"}, headers=headers).json()
    second = client.post("/desktop/new-deck", json={"title": "My Talk!"}, headers=headers).json()
    assert (first["name"], second["name"]) == ("my-talk", "my-talk-2")
    assert json.loads(site.build("my-talk", (decks / "my-talk.md").read_text()))["ok"]


def test_desktop_api_rejects_bad_names_and_urls(desktop):
    client, _, _ = desktop
    headers = {"X-Desktop-Token": "secret"}
    assert client.post("/desktop/edit/..%2Fsecrets", headers=headers).status_code == 404
    assert client.post("/desktop/edit/missing", headers=headers).status_code == 404
    assert client.post("/desktop/window", json={"url": "https://evil.example"}, headers=headers).status_code == 400
    assert client.post("/desktop/window", json={"url": "//evil.example"}, headers=headers).status_code == 400
    assert client.post("/desktop/window", json={"url": "/deck/intro/1"}, headers=headers).json() == {"opened": False}


@pytest.mark.parametrize("title, slug", [("Hello World", "hello-world"), ("  ", "deck"), ("Ça va?", "a-va"), ("x" * 80, "x" * 48)])
def test_slugify(title, slug):
    assert slugify(title) == slug


def test_new_deck_template_is_valid():
    assert json.loads(site.build("t", NEW_DECK.format(title="T")))["ok"]


# --- Windows shortcut writer ---------------------------------------------------------------


def test_shortcut_layout():
    from winlink import shortcut_bytes

    data = shortcut_bytes(r"C:\App\venv\Scripts\pythonw.exe", "-m slidedeck app", r"C:\App", r"C:\App\icon.ico", "Pixel Slides")
    assert data[:4] == b"\x4c\x00\x00\x00"
    link_info_size = int.from_bytes(data[0x4C:0x50], "little")
    strings = data[0x4C + link_info_size:]
    assert "-m slidedeck app".encode("utf-16-le") in strings
    assert strings.endswith(b"\x00\x00\x00\x00")
    assert r"C:\App\venv\Scripts\pythonw.exe".encode("utf-16-le") in data[0x4C:0x4C + link_info_size]
