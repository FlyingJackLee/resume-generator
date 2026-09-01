import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from build import load_data, render_html  # noqa: E402


def test_lang_toggle_present_and_crosslinks():
    zh = render_html(load_data(), "zh")
    assert "resume.en.html" in zh
    en = render_html(load_data(), "en")
    assert "resume.zh.html" in en


def test_font_face_bundled():
    html = render_html(load_data(), "zh")
    assert "@font-face" in html
    assert "Roboto-Regular.ttf" in html
