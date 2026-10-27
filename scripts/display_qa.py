"""Check every console route for blank values and exercise missing-data states."""

import copy
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUTPUT = Path("outputs/display-qa")


def check_values(page) -> None:
    values = page.locator("main td, main dd").all_text_contents()
    invalid = [
        v
        for v in values
        if v.strip() in {"", "-", "–", "—", "null", "undefined", "NaN"}
    ]
    assert not invalid, f"Blank or invalid display values: {invalid}"
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth"), (
        "Page overflows viewport"
    )


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    checks = []
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(reduced_motion="reduce")
        page.on("pageerror", lambda error: errors.append(str(error)))
        evidence = page.request.get(BASE + "/api/eval").json()
        capture = page.request.get(BASE + "/api/captures/demo-capture-4").json()
        for width in (1440, 390):
            page.set_viewport_size({"width": width, "height": 1000})
            for route in (
                "home",
                "console",
                "measure",
                "fleet",
                "desk",
                "agent",
                "bench",
                "methods",
            ):
                page.goto(BASE + "/#/" + route, wait_until="networkidle")
                check_values(page)
                checks.append({"route": route, "width": width, "passed": True})
                if route == "desk":
                    page.get_by_text("Simulated example data", exact=False).wait_for()
                    assert page.locator(".desk-table tbody tr").count() == 4
                    for row in page.locator(".desk-table tbody tr").all():
                        cells = row.locator("td").all_text_contents()
                        assert all(
                            any(ch.isdigit() for ch in cell) for cell in cells[:4]
                        )
                    page.get_by_role(
                        "button", name="Clamps loosened", exact=False
                    ).click()
                    page.get_by_text("After (clamps loosened)", exact=True).wait_for()
                    page.get_by_role("button", name="Compare", exact=False).click()
                    assert page.locator(".bar-row").count() == 4
                    check_values(page)
                    page.screenshot(
                        path=str(OUTPUT / f"desk-{width}.png"), full_page=True
                    )
                elif route == "console":
                    page.get_by_role("button", name="Show numeric table").first.click()
                    check_values(page)

        # Real trials take precedence, including a changed trial identical to the
        # healthy reference: the correct shift is zero, never a missing value.
        real = copy.deepcopy(evidence["desk_example"])
        real["kind"] = "desk_vs_accelerometer"
        real.pop("synthetic")
        real["captures"] = real["captures"][:2]
        real["captures"][1]["video_hz"] = real["captures"][0]["video_hz"]
        page.route(
            "**/api/eval", lambda route: route.fulfill(json={**evidence, "desk": real})
        )
        page.goto(BASE + "/#/desk", wait_until="networkidle")
        page.reload(wait_until="networkidle")
        assert page.get_by_text("Simulated example data", exact=False).count() == 0
        assert page.locator(".desk-table tbody tr").count() == 4
        assert (
            page.locator(".desk-table tbody tr").nth(1).locator("td").last.inner_text()
            == "+0.0%"
        )
        check_values(page)
        checks.append(
            {"scenario": "real_trials_precede_examples_and_zero_shift", "passed": True}
        )
        page.unroute("**/api/eval")

        # A valid spectrum can lack a confidence interval, temperature or chosen
        # extraction. Null trace values should never appear as the word null.
        missing = copy.deepcopy(capture)
        missing["capture"]["temperature_c"] = None
        missing["result"]["estimate"]["ci_hz"] = None
        missing["result"]["estimate"]["selected"] = None
        missing["result"]["trace"][0]["evidence"]["optional_reading"] = None
        page.route(
            "**/api/captures/demo-capture-4", lambda route: route.fulfill(json=missing)
        )
        page.goto(
            BASE + "/#/console?bridge=demo-bridge&capture=demo-capture-4",
            wait_until="networkidle",
        )
        page.reload(wait_until="networkidle")
        page.get_by_text("Interval could not be estimated", exact=False).wait_for()
        page.get_by_text("Temperature not recorded", exact=True).wait_for()
        page.get_by_text("No extraction selected", exact=True).wait_for()
        page.locator(".timeline details").first.locator("summary").click()
        page.get_by_text("Not recorded for this event", exact=True).wait_for()
        check_values(page)
        checks.append({"scenario": "missing_optional_measurements", "passed": True})

        page.route("**/api/bench", lambda route: route.fulfill(json={}))
        page.goto(BASE + "/#/bench", wait_until="networkidle")
        page.reload(wait_until="networkidle")
        check_values(page)
        assert all(
            page.locator("tbody").nth(i).inner_text().strip()
            for i in range(page.locator("tbody").count())
        )
        checks.append({"scenario": "empty_benchmark_sources", "passed": True})
        page.unroute("**/api/bench")
        page.route(
            "**/api/bench",
            lambda route: route.fulfill(
                status=503, json={"error": "Test service unavailable"}
            ),
        )
        page.goto(BASE + "/#/bench", wait_until="networkidle")
        page.reload(wait_until="networkidle")
        page.get_by_role("alert").filter(
            has_text="Benchmarks could not be loaded"
        ).wait_for(timeout=20000)
        check_values(page)
        checks.append({"scenario": "benchmark_api_failure", "passed": True})
        browser.close()
    assert not errors, errors
    (OUTPUT / "results.json").write_text(
        json.dumps({"checks": checks, "page_errors": errors}, indent=2) + "\n"
    )
    print(
        f"Passed {len(checks)} display checks; no blank values, dash placeholders or page errors"
    )


if __name__ == "__main__":
    main()
