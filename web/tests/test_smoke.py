def test_dependencies_importable():
    import jinja2  # noqa: F401
    import yaml  # noqa: F401
    from playwright.sync_api import sync_playwright  # noqa: F401


def test_chromium_launches():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content("<h1>ok</h1>")
        assert page.inner_text("h1") == "ok"
        browser.close()
