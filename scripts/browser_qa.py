import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--token-file", type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path("eval/results/browser.json")
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    output = Path("outputs/screenshots")
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1440, "height": 1000}, reduced_motion="reduce"
        )
        page.on("pageerror", lambda error: errors.append(str(error)))
        for width in (1440, 390):
            page.set_viewport_size(
                {"width": width, "height": 1000 if width == 1440 else 844}
            )
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
                page.goto(f"{base}/#/{route}", wait_until="networkidle")
                page.screenshot(
                    path=str(output / f"{route}-{width}.png"), full_page=True
                )
                rows.append(
                    {
                        "route": route,
                        "width": width,
                        "horizontal_overflow": page.evaluate(
                            "document.documentElement.scrollWidth>innerWidth"
                        ),
                    }
                )
        connected = page.evaluate(
            """base=>new Promise((resolve,reject)=>{const socket=new WebSocket(base.replace('http','ws')+'/ws/live/demo-bridge');const timeout=setTimeout(()=>{socket.close();reject(new Error('WebSocket snapshot timed out'))},10000);socket.onmessage=()=>{clearTimeout(timeout);socket.close();resolve(true)};socket.onerror=()=>reject(new Error('WebSocket transport failed'))})""",
            base,
        )
        rows.append({"scenario": "native_websocket_snapshot", "success": connected})
        if args.token_file:
            token = args.token_file.read_text().strip()
            page.goto(f"{base}/#/console", wait_until="networkidle")
            page.get_by_text(
                "Designate a healthy reference baseline", exact=True
            ).click()
            for index in range(3):
                page.get_by_label(f"demo-capture-{index} ·", exact=False).check()
            page.get_by_label(
                "I independently confirm that the selected captures represent a healthy reference condition.",
                exact=True,
            ).check()
            page.get_by_label("Reviewer token", exact=True).fill(token)
            page.get_by_role("button", name="Save healthy baseline", exact=True).click()
            page.get_by_text("Healthy baseline saved.", exact=False).wait_for()
            rows.append({"scenario": "protected_healthy_baseline", "success": True})
            page.goto(f"{base}/#/agent", wait_until="networkidle")
            page.get_by_label("Admin token", exact=True).fill(token)
            page.get_by_label("Review reason", exact=True).fill(
                "Generated container verification: reviewed trace and evidence. Local receipt only."
            )
            page.get_by_role(
                "button", name="Approve inspection request", exact=True
            ).first.click()
            page.get_by_text("Delivery: recorded locally", exact=True).wait_for(
                timeout=20000
            )
            rows.append({"scenario": "human_review_to_local_receipt", "success": True})
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.goto(f"{base}/#/measure", wait_until="networkidle")
        page.get_by_label("Choose a video").set_input_files(
            "outputs/uploads/demo-capture-4.webm"
        )
        page.wait_for_function('document.querySelector("video")?.videoWidth>0')
        page.get_by_label("Bridge or experiment name").fill(
            "Browser verification capture"
        )
        page.get_by_label(
            "I confirmed the camera acquisition rate, including slow-motion settings."
        ).check()
        page.get_by_role("button", name="Run measurement", exact=True).click()
        page.wait_for_url("**/#/console**")
        page.get_by_text("Dominant frequency", exact=True).wait_for(timeout=120000)
        page.get_by_role("button", name="Show numeric table").first.click()
        assert (
            page.locator("caption").filter(has_text="Deck displacement samples").count()
            == 1
        )
        page.screenshot(path=str(output / "upload-result.png"), full_page=True)
        rows.append({"scenario": "upload_to_worker_to_result", "success": True})
        bridges = page.request.get(base + "/api/bridges").json()
        bridge = next(
            item
            for item in bridges
            if not item["synthetic"]
            and item["bridge"]["name"] == "Browser verification capture"
        )
        page.goto(base + "/#/measure", wait_until="networkidle")
        page.get_by_label("Record for", exact=True).select_option(
            bridge["bridge"]["id"]
        )
        assert page.get_by_label("Bridge or experiment name").is_disabled()
        page.get_by_label("Choose a video").set_input_files(
            "outputs/uploads/demo-capture-4.webm"
        )
        page.wait_for_function('document.querySelector("video")?.videoWidth>0')
        page.get_by_label(
            "I confirmed the camera acquisition rate, including slow-motion settings."
        ).check()
        with page.expect_response(
            lambda response: response.url.endswith("/api/captures")
            and response.request.method == "POST"
        ) as uploaded:
            page.get_by_role("button", name="Run measurement", exact=True).click()
        repeated_id = uploaded.value.json()["capture_id"]
        page.get_by_text("Dominant frequency", exact=True).wait_for(timeout=120000)
        repeated = page.request.get(base + "/api/captures/" + repeated_id).json()
        assert repeated["capture"]["bridge_id"] == bridge["bridge"]["id"]
        assert repeated["result"]["estimate"]["outcome"] == "MEASURED"
        rows.append({"scenario": "repeated_trial_on_existing_bridge", "success": True})

        browser.close()
    args.output.write_text(
        json.dumps(
            {
                "base_url": base,
                "checks": rows,
                "page_errors": errors,
                "summary": {
                    "routes_checked": sum("route" in row for row in rows),
                    "overflow_failures": sum(
                        bool(row.get("horizontal_overflow")) for row in rows
                    ),
                    "page_errors": len(errors),
                    "upload_flow_passed": True,
                },
            },
            indent=2,
        )
        + "\n"
    )
    assert not errors
    assert not any(row.get("horizontal_overflow") for row in rows)
    print("Desktop/mobile routes and actual upload measurement verified")


if __name__ == "__main__":
    main()
