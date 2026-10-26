"""Build and exercise a clean local container without copying workstation outputs."""

import http.client
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

from eval.synthetic import source_tree_sha256


def main() -> None:
    folder = Path("outputs")
    folder.mkdir(exist_ok=True)
    name = "resonance-quickstart-" + uuid4().hex[:8]
    token = folder / "container-qa-token"
    source_sha = source_tree_sha256()
    started = time.perf_counter()
    with (folder / "quickstart-build.log").open("w") as log:
        subprocess.run(
            [
                "docker",
                "build",
                "--pull=false",
                "-t",
                "resonance-local:verification",
                ".",
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
            timeout=600,
        )
    build_seconds = time.perf_counter() - started
    image = json.loads(
        subprocess.check_output(
            ["docker", "image", "inspect", "resonance-local:verification"]
        )
    )[0]
    try:
        subprocess.run(
            [
                "docker",
                "run",
                "--detach",
                "--rm",
                "--name",
                name,
                "--publish",
                "127.0.0.1:8001:8000",
                "resonance-local:verification",
            ],
            stdout=subprocess.DEVNULL,
            check=True,
        )
        deadline = time.perf_counter() + 300
        while True:
            try:
                with urllib.request.urlopen(
                    "http://127.0.0.1:8001/api/health", timeout=2
                ) as response:
                    if response.status == 200:
                        break
            except (
                urllib.error.URLError,
                TimeoutError,
                http.client.RemoteDisconnected,
                ConnectionResetError,
            ):
                if time.perf_counter() > deadline:
                    raise RuntimeError(
                        "Clean container did not become ready within its startup bound"
                    ) from None
            time.sleep(0.5)
        ready_seconds = time.perf_counter() - started
        subprocess.run(
            ["docker", "cp", f"{name}:/app/outputs/local-admin-token", str(token)],
            check=True,
        )
        token.chmod(0o600)
        subprocess.run(
            [
                ".venv/bin/python",
                "-m",
                "scripts.browser_qa",
                "--base-url",
                "http://127.0.0.1:8001",
                "--token-file",
                str(token),
                "--output",
                "eval/results/container_browser.json",
            ],
            check=True,
            timeout=240,
        )
        if source_tree_sha256() != source_sha:
            raise RuntimeError(
                "Engine/evaluator source changed during verification; rerun against the final snapshot"
            )
        Path("eval/results/quickstart.json").write_text(
            json.dumps(
                {
                    "kind": "executed_clean_container_quickstart",
                    "verified": True,
                    "source_tree_sha256": source_sha,
                    "image_id": image["Id"],
                    "architecture": image["Architecture"],
                    "build_seconds": build_seconds,
                    "build_and_seed_to_ready_seconds": ready_seconds,
                    "build_seed_and_browser_seconds": time.perf_counter() - started,
                    "browser_results": "eval/results/container_browser.json",
                    "conditions": [
                        "Fresh application container with no copied outputs, weights, private inputs or credentials",
                        "Docker base images and dependency build layers may be cached; this is not a cold-network installation claim",
                        "Local pip OpenCV runtime; no AWS or COOL execution",
                    ],
                },
                indent=2,
            )
            + "\n"
        )
        print(
            "Fresh container, generated demo, upload, baseline, WebSocket and protected review verified"
        )
    finally:
        token.unlink(missing_ok=True)
        subprocess.run(
            ["docker", "rm", "--force", name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


if __name__ == "__main__":
    main()
