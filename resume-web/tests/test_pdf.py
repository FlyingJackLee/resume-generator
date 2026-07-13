import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from build import build_one  # noqa: E402


def test_build_one_zh_creates_pdf_and_html():
    html_path, pdf_path = build_one("zh")
    assert html_path.exists()
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 20_000  # 非空 PDF（含 CJK）


def test_pdf_contains_text():
    from pypdf import PdfReader  # noqa
    _, pdf_path = build_one("en")
    reader = PdfReader(str(pdf_path))
    text = "".join(page.extract_text() or "" for page in reader.pages)
    assert "Zumin" in text
