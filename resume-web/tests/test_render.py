import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import build as buildmod  # noqa: E402
from build import load_data, render_html  # noqa: E402


def _strip_tags(html):
    return re.sub(r"<[^>]+>", "", html)


def test_render_zh_contains_key_content():
    html = render_html(load_data(), "zh")
    text = _strip_tags(html)
    assert "李祖民" in html
    assert "个人介绍" in text
    assert "技术合伙人" in html
    assert "麒霖通信有限公司" in html
    assert 'class="hl"' in html  # 段标题着色
    assert '<span class="hl">个</span>' in html  # 中文标题高亮边界（1 字）


def test_render_en_contains_key_content():
    html = render_html(load_data(), "en")
    text = _strip_tags(html)
    assert "Zumin Li" in html
    assert "Introduction" in text
    assert "Technical Lead" in html
    assert '<span class="hl">Int</span>' in html  # 英文标题高亮边界（3 字）


def test_render_includes_inline_css_and_icons():
    html = render_html(load_data(), "zh")
    assert "--awesome: #DC3522" in html
    assert "<svg" in html  # 内联图标
    assert '"Roboto"' in html  # 内联 CSS 未被转义


def test_skills_items_render_not_method_repr():
    html = render_html(load_data(), "zh")
    assert "Mybatis" in html          # real skills text present
    assert "Spring Cloud" in html
    assert "built-in method" not in html   # dict.items method repr must NOT leak


def test_photo_src_is_build_relative_when_present(tmp_path):
    photo = buildmod.ROOT / "assets" / "photo.jpg"
    created = False
    if not photo.exists():
        photo.write_bytes(b"\xff\xd8\xff\xd9")  # minimal JPEG-ish bytes
        created = True
    try:
        html = render_html(load_data(), "zh")
        assert 'src="../assets/photo.jpg"' in html
    finally:
        if created:
            photo.unlink()
