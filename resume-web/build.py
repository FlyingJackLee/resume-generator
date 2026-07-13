from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent


def load_data(path="data/resume.yaml"):
    """读取并解析简历 YAML，返回 dict。"""
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def localize(node, lang):
    """若 node 是含 zh/en 的 dict 则取对应语言，否则原样返回。"""
    if isinstance(node, dict) and "zh" in node and "en" in node:
        return node[lang]
    return node


ICONS = {
    "phone": '<svg viewBox="0 0 512 512"><path d="M164 32 32 96c0 212 152 384 384 384l64-132-108-44-40 48c-72-32-128-88-160-160l48-40L164 32z"/></svg>',
    "email": '<svg viewBox="0 0 512 512"><path d="M48 96h416v320H48z" fill="none"/><path d="M48 96l208 160L464 96H48zm0 40v280h416V136L256 296 48 136z"/></svg>',
    "home": '<svg viewBox="0 0 576 512"><path d="M288 48 32 256h64v208h128V336h128v128h128V256h64L288 48z"/></svg>',
    "github": '<svg viewBox="0 0 496 512"><path d="M248 24C111 24 0 135 0 272c0 110 71 203 170 236 12 2 17-5 17-12v-42c-69 15-84-33-84-33-11-29-28-37-28-37-23-16 2-16 2-16 25 2 38 26 38 26 22 38 59 27 73 21 2-16 9-27 16-33-55-6-113-27-113-122 0-27 10-49 26-67-3-6-11-31 2-65 0 0 21-7 69 26 20-6 41-9 62-9s42 3 62 9c48-33 69-26 69-26 13 34 5 59 2 65 16 18 26 40 26 67 0 95-58 116-113 122 9 8 17 23 17 47v69c0 7 5 14 17 12 99-33 170-126 170-236 0-137-111-248-248-248z"/></svg>',
    "wechat": '<svg viewBox="0 0 576 512"><path d="M385 118C230 118 111 219 111 344c0 45 15 87 41 121l-16 62 72-37c26 8 54 12 84 12 155 0 274-101 274-226S540 118 385 118z"/></svg>',
}


def icon(name):
    return Markup(ICONS.get(name, ""))


def make_section_title(data):
    """返回一个渲染段标题的函数：标题的前 N 个字符包在 <span class="hl"> 内
    并通过 CSS 着色为红色，实现 Awesome-CV 标志性的双色段标题。N 的取值
    取决于首字符是否为 CJK 表意文字：中文用 section_highlight_cjk（默认 1），
    英文/其他用 section_highlight_latin（默认 3）。
    """

    def _title(text):
        text = str(text)
        if not text:
            return Markup("")
        first = text[0]
        if "一" <= first <= "鿿":
            n = data.get("section_highlight_cjk", 1)
        else:
            n = data.get("section_highlight_latin", 3)
        head, tail = text[:n], text[n:]
        return Markup('<span class="hl">{}</span>{}').format(head, tail)

    return _title


def render_html(data, lang):
    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=select_autoescape(["html", "j2"]),
    )
    env.filters["L"] = lambda node: localize(node, lang)
    env.globals["icon"] = icon
    env.globals["section_title"] = make_section_title(data)
    css = Markup((ROOT / "styles" / "awesome-cv.css").read_text(encoding="utf-8"))
    photo = data["meta"].get("photo")
    photo_exists = bool(photo) and (ROOT / photo).exists()
    tpl = env.get_template("resume.html.j2")
    return tpl.render(
        lang=lang, css=css, photo_exists=photo_exists,
        meta=data["meta"], sections=data["sections"],
        footer_more=data["meta"]["footer_more"],
    )


import argparse
from playwright.sync_api import sync_playwright

BUILD_DIR = ROOT / "build"

FOOTER_HTML = (
    '<div style="width:100%;font-size:7pt;color:#999;'
    'font-variant:small-caps;padding:0 1.4cm;display:flex;'
    'justify-content:space-between;align-items:center;">'
    '<span></span><span>{label}</span>'
    '<span class="pageNumber"></span></div>'
)


def export_pdf(html_path: Path, pdf_path: Path, footer_label: str):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_path.as_uri())
        page.emulate_media(media="print")
        page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template="<div></div>",
            footer_template=FOOTER_HTML.format(label=footer_label),
            margin={"top": "0.8cm", "right": "1.4cm", "bottom": "1.8cm", "left": "1.4cm"},
        )
        browser.close()


def build_one(lang: str, html_only: bool = False):
    data = load_data()
    BUILD_DIR.mkdir(exist_ok=True)
    html = render_html(data, lang)
    html_path = BUILD_DIR / f"resume.{lang}.html"
    html_path.write_text(html, encoding="utf-8")
    pdf_path = BUILD_DIR / f"resume.{lang}.pdf"
    if not html_only:
        label = localize(data["meta"]["footer_label"], lang)
        export_pdf(html_path, pdf_path, label)
    return html_path, pdf_path


def main():
    ap = argparse.ArgumentParser(description="Build resume PDF/HTML from resume.yaml")
    ap.add_argument("--lang", choices=["zh", "en", "all"], default="all")
    ap.add_argument("--html-only", action="store_true")
    args = ap.parse_args()
    langs = ["zh", "en"] if args.lang == "all" else [args.lang]
    for lang in langs:
        html_path, pdf_path = build_one(lang, html_only=args.html_only)
        print(f"[{lang}] {html_path.name}" + ("" if args.html_only else f" + {pdf_path.name}"))


if __name__ == "__main__":
    main()
