"""分页线准确性守护：预览里的模拟分页必须与真实导出 PDF 的页数一致。

page-guides.js 里的 PAGE_H 硬编码自 @page / export_pdf 的 margin；若导出侧
改了纸张或边距而没同步脚本，本测试会红，提醒两者必须一起改。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from build import BUILD_DIR, build_one  # noqa: E402
from resume_render import load_data, localize, render_html  # noqa: E402

SAMPLE = "data/resume.sample.yaml"


def _write_guides_html(lang: str, data_path: str | Path = SAMPLE) -> Path:
    html = render_html(load_data(path=data_path), lang, show_page_guides=True)
    BUILD_DIR.mkdir(exist_ok=True)
    path = BUILD_DIR / f"resume.{lang}.guides.html"
    path.write_text(html, encoding="utf-8")
    return path


def test_guides_script_only_injected_when_requested():
    data = load_data(path=SAMPLE)
    assert "page-guides.js" in render_html(data, "zh", show_page_guides=True)
    assert "page-guides.js" not in render_html(data, "zh")


def _simulated_pages(lang: str, data_path: str | Path = SAMPLE) -> int:
    from playwright.sync_api import sync_playwright

    html_path = _write_guides_html(lang, data_path=data_path)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(html_path.as_uri())
            page.wait_for_function("window.__pageGuides !== undefined", timeout=10_000)
            return page.evaluate("window.__pageGuides.pages")
        finally:
            browser.close()


def _oversized_avoid_data(path: Path) -> Path:
    """构造超过一页高的 page_break_before 段：复制项目条目直到整段超过 27.1cm。"""
    import copy

    data = load_data(path=SAMPLE)
    projects = next(s for s in data["sections"] if s["title"]["en"] == "Projects")
    projects["page_break_before"] = True
    base = copy.deepcopy(projects["entries"])
    while len(projects["entries"]) < 12:
        projects["entries"].extend(copy.deepcopy(base))
    path.write_text(__import__("yaml").safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


def test_simulated_page_count_matches_pdf_zh():
    from pypdf import PdfReader

    # 真实页数走与下载端点相同的导出路径（无 guides 脚本的 HTML）
    _, pdf_path = build_one("zh", data_path=SAMPLE)
    real_pages = len(PdfReader(str(pdf_path)).pages)
    assert _simulated_pages("zh") == real_pages


def test_simulated_page_count_matches_pdf_en():
    from pypdf import PdfReader

    _, pdf_path = build_one("en", data_path=SAMPLE)
    real_pages = len(PdfReader(str(pdf_path)).pages)
    assert _simulated_pages("en") == real_pages


def test_simulated_page_count_matches_pdf_oversized_avoid_section(tmp_path):
    """超过一页高的 break-inside: avoid 段（page_break_before + 超长内容）：
    Chromium 打印时整段推到新页顶部再内部拆分，模拟分页必须与之一致。
    回归：修复前模拟器会就地拆分，把段首内容塞进上一页剩余空间，页数偏少。"""
    from pypdf import PdfReader

    data_path = _oversized_avoid_data(tmp_path / "resume.oversized.yaml")
    for lang in ("zh", "en"):
        _, pdf_path = build_one(lang, data_path=data_path)
        real_pages = len(PdfReader(str(pdf_path)).pages)
        assert real_pages >= 3  # 前置内容一页 + avoid 段自身超过一页
        assert _simulated_pages(lang, data_path=data_path) == real_pages, f"lang={lang}"
