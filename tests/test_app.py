import pytest
from fastapi.testclient import TestClient

from slidedeck.app import app

client = TestClient(app)
LAST = 15  # slides in decks/intro.md


def location(response):
    return response.headers["location"]


def test_library_lists_decks():
    response = client.get("/")
    assert response.status_code == 200
    assert "Text In, Pixels Out" in response.text


def test_first_slide_renders():
    response = client.get("/deck/intro/1")
    assert response.status_code == 200
    assert 'data-index="0"' in response.text
    assert f'data-count="{LAST}"' in response.text


def test_last_slide_renders_without_redirect():
    response = client.get(f"/deck/intro/{LAST}", follow_redirects=False)
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("number", "expected"),
    [("99", f"/deck/intro/{LAST}"), (str(LAST + 1), f"/deck/intro/{LAST}"),
     ("0", "/deck/intro/1"), ("-4", "/deck/intro/1"), ("007", "/deck/intro/7")],
)
def test_out_of_range_numbers_redirect_to_a_real_slide(number, expected):
    response = client.get(f"/deck/intro/{number}", follow_redirects=False)
    assert response.status_code == 302
    assert location(response) == expected


def test_presenter_clamps_too_and_keeps_theme():
    response = client.get("/deck/intro/99/presenter?theme=night", follow_redirects=False)
    assert location(response) == f"/deck/intro/{LAST}/presenter?theme=night"


def test_deck_root_goes_to_slide_one():
    assert location(client.get("/deck/intro", follow_redirects=False)) == "/deck/intro/1"


@pytest.mark.parametrize("path", ["/deck/intro/abc", "/deck/intro/1.5", "/deck/nope/1",
                                  "/deck/..%2Fapp/1", "/deck/INTRO/1"])
def test_bad_paths_are_404(path):
    assert client.get(path, follow_redirects=False).status_code == 404


def test_theme_override_is_allow_listed():
    assert 'class="theme-night"' in client.get("/deck/intro/1?theme=night").text
    assert 'class="theme-dmg"' in client.get("/deck/intro/1?theme=<script>").text


def test_print_view_has_every_slide_and_no_iframes():
    html = client.get("/deck/intro/print").text
    assert html.count('class="slide-page-frame') == LAST
    assert "<iframe" not in html


def test_security_headers():
    response = client.get("/deck/intro/1")
    csp = response.headers["content-security-policy"]
    assert "frame-src https://www.youtube-nocookie.com https://player.vimeo.com" in csp
    assert "script-src 'self'" in csp


def test_raw_html_in_a_deck_is_escaped(tmp_path, monkeypatch):
    from slidedeck import app as app_module

    (tmp_path / "evil.md").write_text("# Hi\n\n<script>alert(1)</script>\n", encoding="utf-8")
    monkeypatch.setattr(app_module, "DECKS_DIR", tmp_path)
    app_module._cache.clear()
    html = client.get("/deck/evil/1").text
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_empty_deck_is_a_clear_error_not_a_crash(tmp_path, monkeypatch):
    from slidedeck import app as app_module

    (tmp_path / "empty.md").write_text("", encoding="utf-8")
    monkeypatch.setattr(app_module, "DECKS_DIR", tmp_path)
    app_module._cache.clear()
    response = client.get("/deck/empty/1")
    assert response.status_code == 422
    assert "no slides" in response.text


# --- pixel engine additions -------------------------------------------------------

def test_html_lang_comes_from_the_deck():
    assert '<html lang="en"' in client.get("/deck/intro/1").text


def test_themes_stylesheet_is_generated():
    response = client.get("/themes.css")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
    assert ".theme-contrast {" in response.text


def test_every_page_carries_the_lcd_filters():
    html = client.get("/deck/intro/1").text
    for name in ("dmg", "pocket", "berry", "night", "contrast"):
        assert f'<filter id="lcd-{name}"' in html


def test_slide_page_has_live_region_menus_and_skip_link():
    html = client.get("/deck/intro/1").text
    assert 'aria-live="polite"' in html
    assert 'data-dialog="outline"' in html and 'data-dialog="options"' in html and 'data-dialog="help"' in html
    assert 'class="deck-skip-link" href="/deck/intro/text#slide-1"' in html
    assert 'aria-roledescription="slide"' in html


def test_tab_title_names_the_slide():
    assert "<title>Pixel art, typed in · 7/15" in client.get("/deck/intro/7").text


def test_outline_lists_every_slide_title():
    html = client.get("/deck/intro/1").text
    assert html.count('class="deck-outline-list-button"') == LAST
    assert "Status check" in html


def test_text_view_has_every_slide_and_no_frames():
    response = client.get("/deck/intro/text")
    assert response.status_code == 200
    html = response.text
    assert html.count('class="text-view-slide"') == LAST
    assert "<iframe" not in html
    assert "data-carousel" not in html
    # Slide headings sit under the page's h1 and each slide's h2.
    assert html.count("<h1") == 1
    assert '<h3>Text in, <em>pixels</em> out.</h3>' in html


def test_text_view_notes_are_opt_in():
    assert "Speaker notes</p>" not in client.get("/deck/intro/text").text
    assert "Speaker notes</p>" in client.get("/deck/intro/text?notes=1").text


def test_text_view_keeps_theme():
    assert 'class="theme-berry"' in client.get("/deck/intro/text?theme=berry").text


def test_presenter_shows_access_check_for_broken_slide():
    html = client.get("/deck/intro/13/presenter").text
    assert "Access check · 2" in html
    assert "presenter-lint-list-item--error" in html


def test_boot_screen_only_when_deck_asks(tmp_path, monkeypatch):
    from slidedeck import app as app_module

    assert "data-boot-screen" in client.get("/deck/intro/1").text
    (tmp_path / "plain.md").write_text("# Hi\n", encoding="utf-8")
    monkeypatch.setattr(app_module, "DECKS_DIR", tmp_path)
    app_module._cache.clear()
    assert "data-boot-screen" not in client.get("/deck/plain/1").text


def test_library_shows_palette_and_text_link():
    html = client.get("/").text
    assert "DMG green" in html
    assert 'href="/deck/intro/text"' in html


def test_no_inline_styles_anywhere():
    # The CSP has no 'unsafe-inline', so an inline style would silently break.
    for path in ("/", "/deck/intro/8", "/deck/intro/8/presenter", "/deck/intro/print", "/deck/intro/text"):
        assert "style=" not in client.get(path).text, path


def test_text_view_kicker_is_a_label_not_a_heading():
    html = client.get("/deck/intro/text").text
    assert '<p class="text-view-kicker-label">Pixel Slides · World 1-1</p>' in html
    assert "<h5" not in html


def test_presenter_has_a_main_landmark():
    assert '<main class="presenter-layout-grid">' in client.get("/deck/intro/1/presenter").text
