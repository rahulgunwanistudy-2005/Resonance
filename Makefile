PYTHON := .venv/bin/python

.PHONY: setup check test eval probe models verify-cool
setup:
	UV_PROJECT_ENVIRONMENT=../.venv uv sync --project engine --extra local --frozen

check:
	.venv/bin/ruff check engine scripts eval
	.venv/bin/ruff format --check engine scripts eval
	.venv/bin/mypy --config-file engine/pyproject.toml engine api
	$(PYTHON) -m pytest -c engine/pyproject.toml engine/tests
	$(PYTHON) scripts/check_no_hardcoded_metrics.py

test:
	$(PYTHON) -m pytest -c engine/pyproject.toml engine/tests

eval:
	$(PYTHON) -m eval.synthetic
	$(PYTHON) -m eval.failure_cases

probe:
	$(PYTHON) scripts/probe_opencv.py

models:
	$(PYTHON) scripts/download_models.py

verify-cool:
	$(PYTHON) scripts/verify_cool.py
