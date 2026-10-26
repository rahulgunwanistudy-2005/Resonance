PYTHON := .venv/bin/python

.PHONY: setup check test eval eval-stabilization report-preview probe models verify-cool demo run web bench mcp-check infra-synth release report
setup:
	UV_PROJECT_ENVIRONMENT=../.venv uv sync --project engine --extra local --extra service --extra report --extra cloud --frozen

check:
	.venv/bin/ruff check engine api worker mcp scripts eval bench infra
	.venv/bin/ruff format --check engine api worker mcp scripts eval bench infra
	.venv/bin/mypy --config-file engine/pyproject.toml engine api
	$(PYTHON) -m pytest -c engine/pyproject.toml engine/tests api/tests
	$(PYTHON) scripts/check_no_hardcoded_metrics.py

test:
	$(PYTHON) -m pytest -c engine/pyproject.toml engine/tests

eval:
	$(PYTHON) -m eval.synthetic
	$(PYTHON) -m eval.failure_cases
	$(PYTHON) -m eval.agent

demo:
	$(PYTHON) -m scripts.seed_demo

run:
	$(PYTHON) -m scripts.run_local

web:
	pnpm --dir web install --frozen-lockfile
	pnpm --dir web build

bench:
	$(PYTHON) -m bench.run_bench

mcp-check:
	$(PYTHON) -m scripts.mcp_smoke

infra-synth:
	JSII_RUNTIME_PACKAGE_CACHE_ROOT=/private/tmp/resonance-jsii $(PYTHON) infra/app.py

release:
	$(PYTHON) -m scripts.package_release

report:
	$(PYTHON) -m scripts.build_report

eval-stabilization:
	$(PYTHON) -m eval.stabilization

report-preview:
	$(PYTHON) -m scripts.render_metrics docs/evaluation.md --output outputs/evaluation.md

probe:
	$(PYTHON) scripts/probe_opencv.py

models:
	$(PYTHON) scripts/download_models.py

verify-cool:
	$(PYTHON) scripts/verify_cool.py
