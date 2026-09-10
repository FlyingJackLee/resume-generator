import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import build as buildmod  # noqa: E402
from build import load_data, render_html  # noqa: E402


def _strip_tags(html):
    return re.sub(r"<[^>]+>", "", html)


def _sample():
    return load_data("data/resume.sample.yaml")


def test_render_zh_contains_key_content():
    html = render_html(_sample(), "zh")
    text = _strip_tags(html)
    assert "你的姓名" in html
    assert "个人介绍" in text
    assert "高级软件工程师" in html
    assert "示例科技有限公司" in html
    assert 'class="hl"' in html  # 段标题着色
    assert '<span class="hl">个</span>' in html  # 中文标题高亮边界（1 字）


def test_render_en_contains_key_content():
    html = render_html(_sample(), "en")
    text = _strip_tags(html)
    assert "Your Name" in html
    assert "Introduction" in text
    assert "Senior Software Engineer" in html
    assert '<span class="hl">Int</span>' in html  # 英文标题高亮边界（3 字）


def test_work_entries_render_company_before_role():
    zh = render_html(_sample(), "zh")
    assert zh.index("示例科技有限公司") < zh.index("高级软件工程师")
    en = render_html(_sample(), "en")
    assert en.index("Example Technology Co., Ltd.") < en.index("Senior Software Engineer")


def test_projects_render_summary_and_responsibilities():
    zh = render_html(_sample(), "zh")
    assert 'class="entry-meta"' in zh
    assert "项目简介" in zh
    assert "个人职责" in zh
    assert "面向团队协作的自动化工作流平台" in zh
    en = render_html(_sample(), "en")
    assert "Overview" in en
    assert "Responsibilities" in en


def test_render_includes_inline_css_and_icons():
    html = render_html(_sample(), "zh")
    assert "--awesome: #DC3522" in html
    assert "<svg" in html  # 内联图标
    assert '"Roboto"' in html  # 内联 CSS 未被转义


def test_skills_items_render_not_method_repr():
    html = render_html(_sample(), "zh")
    assert "FastAPI" in html
    assert "TypeScript" in html
    assert "built-in method" not in html   # dict.items method repr must NOT leak


def test_photo_src_is_build_relative_when_present(tmp_path):
    photo = buildmod.ROOT / "assets" / "photo.jpg"
    created = False
    if not photo.exists():
        photo.write_bytes(b"\xff\xd8\xff\xd9")  # minimal JPEG-ish bytes
        created = True
    try:
        data = _sample()
        data["meta"]["photo"] = "assets/photo.jpg"
        html = render_html(data, "zh")
        assert 'src="../assets/photo.jpg"' in html
    finally:
        if created:
            photo.unlink()
