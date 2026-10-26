from pathlib import Path

import pytest
from scripts.check_no_hardcoded_metrics import check_text, resolve


def test_metric_reference_reads_evaluation_json() -> None:
    token = "{{metric:eval/results/synthetic.json#/summary/experiments}}"
    assert resolve(token) > 0
    assert not check_text(token + " experiments")


def test_literal_performance_claim_is_rejected() -> None:
    assert check_text("Frequency error: 0.1%")
    assert check_text("We process 120 fps")
    assert not check_text("Use `fps=60` for this example")
    assert not check_text("font: '12px Overpass'")
    assert check_text("Measured displacement: 12px")


def test_missing_reference_or_directory_escape_is_rejected(tmp_path: Path) -> None:
    assert check_text("{{metric:eval/results/missing.json#/accuracy}}", tmp_path)
    with pytest.raises(ValueError, match="escapes"):
        resolve("{{metric:eval/results/../../../secrets.json#/number}}", tmp_path)
