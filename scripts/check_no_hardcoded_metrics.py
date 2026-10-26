"""Require traceable measurement tokens; reject literal performance claims in prose/UI strings.

This is a source guard, not a semantic proof of every possible numerical sentence.
Reviewers must also audit new claim types. Code/config/examples are not measured claims.
"""

import json
import re
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r"\{\{metric:((?:eval|bench)/results/[^#{}]+\.json)#([^{}]+)\}\}")
LITERAL = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:%|fps\b|Hz\b|ms\b|px\b|pixels?\b|cameras?/hour\b)"
    r"|\b(?:accuracy|throughput|latency|success rate|frequency error|amplitude error)"
    r"\s*(?:is|:|=)?\s*\d+(?:\.\d+)?",
    re.IGNORECASE,
)


def resolve(token: str, root: Path = ROOT) -> int | float:
    match = TOKEN.fullmatch(token)
    if match is None:
        raise ValueError("Invalid metric reference")
    path = (root / match[1]).resolve()
    if not any(
        path.is_relative_to((root / kind / "results").resolve())
        for kind in ("eval", "bench")
    ):
        raise ValueError("Metric reference escapes the evidence directories")
    value = json.loads(path.read_text())
    for part in match[2].lstrip("/").split("/"):
        key = part.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    if type(value) not in (int, float):
        raise ValueError("Published metric must resolve to a number")
    return cast(int | float, value)


def check_text(text: str, root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    for token in TOKEN.finditer(text):
        try:
            resolve(token[0], root)
        except (OSError, KeyError, IndexError, TypeError, ValueError) as exc:
            failures.append(f"Unresolvable metric {token[0]}: {exc}")
    prose = re.sub(r"```[\s\S]*?```", "", text)
    prose = re.sub(r"`[^`]*`", "", prose)
    prose = TOKEN.sub("<measured value>", prose)
    prose = re.sub(
        r"(?:font|labelFont)\s*:\s*['\"]\d+(?:\.\d+)?px [^'\"]+['\"]", "", prose
    )
    for match in LITERAL.finditer(prose):
        failures.append(f"Literal measured claim: {match[0]}; use a metric reference")
    return failures


def main() -> None:
    paths = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]
    paths.extend(
        path
        for path in (ROOT / "web").rglob("*")
        if path.suffix in (".tsx", ".ts", ".html") and "node_modules" not in path.parts
    )
    failures = [
        f"{path.relative_to(ROOT)}: {failure}"
        for path in paths
        if path.is_file()
        for failure in check_text(path.read_text())
    ]
    if failures:
        raise SystemExit("\n".join(failures))
    print("Metric source guard passed")


if __name__ == "__main__":
    main()
