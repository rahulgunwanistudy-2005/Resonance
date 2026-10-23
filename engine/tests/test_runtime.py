from pathlib import Path

import pytest

from resonance.runtime import provenance


def test_runtime_records_actual_build() -> None:
    result = provenance()
    assert result.cv2_version.startswith("5.")
    assert Path(result.cv2_path).exists()
    assert len(result.build_info_sha) == 64


def test_local_pip_runtime_cannot_pass_as_cool() -> None:
    if provenance().cool_verified:
        pytest.skip("This test specifically exercises a non-COOL interpreter")
    with pytest.raises(RuntimeError, match="outside /opt/cool"):
        provenance(require_cool=True)
