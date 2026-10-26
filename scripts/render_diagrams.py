from pathlib import Path
from playwright.sync_api import sync_playwright


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1500, "height": 1100}, device_scale_factor=2
        )
        for path in Path("docs/diagrams").glob("*.mmd"):
            page.goto("http://127.0.0.1:5173/diagram.html", wait_until="networkidle")
            page.wait_for_function('typeof window.renderDiagram==="function"')
            svg = page.evaluate(
                "source=>window.renderDiagram(source)", path.read_text()
            )
            path.with_suffix(".svg").write_text(svg)
            page.locator("#figure svg").screenshot(path=str(path.with_suffix(".png")))
        browser.close()


if __name__ == "__main__":
    main()
