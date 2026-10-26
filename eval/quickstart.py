"""Build and exercise a clean local container without copying workstation outputs."""

import hashlib
import http.client
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

from eval.synthetic import source_tree_sha256


def application_sha256() -> str:
    paths = [
        Path("Dockerfile"),
        Path("engine/pyproject.toml"),
        Path("engine/uv.lock"),
        *Path("engine/resonance").rglob("*.py"),
    ]
    for folder in ("api", "worker", "mcp", "scripts"):
        paths.extend(Path(folder).rglob("*.py"))
    paths.extend(path for path in Path("web").iterdir() if path.is_file())
    paths.extend(path for path in Path("web/src").rglob("*") if path.is_file())
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> None:
    folder = Path("outputs")
    folder.mkdir(exist_ok=True)
    name = "resonance-quickstart-" + uuid4().hex[:8]
    token = folder / "container-qa-token"
    source_sha = source_tree_sha256()
    application_sha = application_sha256()
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
        if (
            source_tree_sha256() != source_sha
            or application_sha256() != application_sha
        ):
            raise RuntimeError(
                "Application/evaluator source changed during verification; rerun against the final snapshot"
            )
        Path("eval/results/quickstart.json").write_text(
            json.dumps(
                {
                    "kind": "executed_clean_container_quickstart",
                    "verified": True,
                    "source_tree_sha256": source_sha,
                    "application_source_sha256": application_sha,
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
