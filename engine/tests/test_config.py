from pathlib import Path

import pytest

from resonance.config import Settings


def test_dotenv_loading_preserves_exported_environment_priority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "RESONANCE_HOST=127.0.0.2\n"
        "RESONANCE_PORT=8123\n"
        "RESONANCE_ADMIN_TOKEN=test-review-token-${NOT_A_REAL_VARIABLE}-literal\n"
        "RESONANCE_DATA_DIR\n"
    )
    for key in ("RESONANCE_PORT", "RESONANCE_ADMIN_TOKEN", "RESONANCE_DATA_DIR"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("NOT_A_REAL_VARIABLE", raising=False)
    monkeypatch.setenv("RESONANCE_HOST", "127.0.0.3")

    settings = Settings.from_env()

    assert settings.host == "127.0.0.3"
    assert settings.port == 8123
    assert settings.data_dir == Path("data")
    assert settings.admin_token == "test-review-token-${NOT_A_REAL_VARIABLE}-literal"
    assert "test-review-token" not in repr(settings)


def test_dotenv_is_optional(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RESONANCE_HOST", raising=False)
    assert Settings.from_env().host == "127.0.0.1"
