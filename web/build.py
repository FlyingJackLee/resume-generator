from pathlib import Path

from resume_render import ROOT, load_data, localize, render_html

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
        try:
            page = browser.new_page()
            page.goto(html_path.as_uri())
            page.evaluate("() => document.fonts.ready")
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
        finally:
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
    ap.add_argument("--watch", action="store_true", help="起本地服务并监听改动重建 HTML")
    args = ap.parse_args()
    langs = ["zh", "en"] if args.lang == "all" else [args.lang]
    for lang in langs:
        html_path, pdf_path = build_one(lang, html_only=args.html_only)
        print(f"[{lang}] {html_path.name}" + ("" if args.html_only else f" + {pdf_path.name}"))

    if args.watch:
        _serve_and_watch(langs)


def _serve_and_watch(langs):
    import http.server, socketserver, functools
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    def rebuild():
        for lang in langs:
            build_one(lang, html_only=True)
        print("rebuilt:", ", ".join(langs))

    class H(FileSystemEventHandler):
        def on_any_event(self, e):
            if str(e.src_path).endswith((".yaml", ".j2", ".css")):
                try:
                    rebuild()
                except Exception as ex:
                    print("build error:", ex)

    obs = Observer()
    for d in ("data", "templates", "styles"):
        obs.schedule(H(), str(ROOT / d), recursive=True)
    obs.start()

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", 8000), handler)
    url = f"http://127.0.0.1:8000/build/resume.{langs[0]}.html"
    print(f"serving {url}  (Ctrl-C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        obs.stop()
        obs.join()


if __name__ == "__main__":
    main()
