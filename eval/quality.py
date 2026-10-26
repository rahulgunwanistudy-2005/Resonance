"""Execute quality gates and save their actual status and JUnit counts."""

import json
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from eval.synthetic import git_revision, source_tree_sha256


def main() -> None:
    output = Path("outputs")
    output.mkdir(exist_ok=True)
    commands = [
        [
            ".venv/bin/ruff",
            "check",
            "engine",
            "api",
            "worker",
            "mcp",
            "scripts",
            "eval",
            "bench",
            "infra",
        ],
        [
            ".venv/bin/ruff",
            "format",
            "--check",
            "engine",
            "api",
            "worker",
            "mcp",
            "scripts",
            "eval",
            "bench",
            "infra",
        ],
        [".venv/bin/mypy", "--config-file", "engine/pyproject.toml", "engine", "api"],
        [
            ".venv/bin/python",
            "-m",
            "pytest",
            "-c",
            "engine/pyproject.toml",
            "engine/tests",
            "api/tests",
            "--junitxml=outputs/pytest.xml",
        ],
        [".venv/bin/python", "scripts/check_no_hardcoded_metrics.py"],
        ["pnpm", "--dir", "web", "build"],
    ]
    rows = []
    for index, command in enumerate(commands):
        start = time.perf_counter()
        with (output / f"quality-{index}.log").open("w") as stream:
            completed = subprocess.run(
                command, stdout=stream, stderr=subprocess.STDOUT, check=False
            )
        rows.append(
            {
                "command": command,
                "exit_code": completed.returncode,
                "elapsed_seconds": time.perf_counter() - start,
            }
        )
        if completed.returncode:
            raise RuntimeError(f"Quality gate failed; see outputs/quality-{index}.log")
    suite = ET.parse(output / "pytest.xml").getroot()
    tests = sum(int(item.attrib.get("tests", 0)) for item in suite.iter("testsuite"))
    failures = sum(
        int(item.attrib.get("failures", 0)) + int(item.attrib.get("errors", 0))
        for item in suite.iter("testsuite")
    )
    Path("eval/results/quality.json").write_text(
        json.dumps(
            {
                "kind": "executed_quality_gates",
                "git_revision": git_revision(),
                "source_tree_sha256": source_tree_sha256(),
                "gates": rows,
                "tests": tests,
                "test_failures": failures,
                "all_passed": True,
            },
            indent=2,
        )
        + "\n"
    )
    print("Quality gates passed and recorded in eval/results/quality.json")


if __name__ == "__main__":
    main()
