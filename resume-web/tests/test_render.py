import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from build import load_data, render_html  # noqa: E402


def test_render_zh_contains_key_content():
    html = render_html(load_data(), "zh")
    assert "李祖民" in html
    assert "个人介绍" in html
    assert "技术合伙人" in html
    assert "麒霖通信有限公司" in html
    assert 'class="hl"' in html  # 段标题着色


def test_render_en_contains_key_content():
    html = render_html(load_data(), "en")
    assert "Zumin Li" in html
    assert "Introduction" in html
    assert "Technical Lead" in html


def test_render_includes_inline_css_and_icons():
    html = render_html(load_data(), "zh")
    assert "--awesome: #DC3522" in html
    assert "<svg" in html  # 内联图标
