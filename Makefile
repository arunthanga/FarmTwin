# FarmTwin — developer convenience targets
# Run from repo root.

.PHONY: help install lint format test test-unit test-tdd test-regression \
        validate-schema baselines clean upload

PYTHON      ?= python3
PIP         ?= $(PYTHON) -m pip
ENGINE_DIR   = engine
TESTS_DIR    = engine/tests

help:
	@echo ""
	@echo "FarmTwin Makefile targets:"
	@echo "  make install          Install engine package and dev dependencies"
	@echo "  make lint             Run Ruff check + format check"
	@echo "  make format           Auto-format with Ruff"
	@echo "  make test             Run all unit tests (TDD mode OFF)"
	@echo "  make test-unit        Unit tests only"
	@echo "  make test-tdd         TDD stub tests (expect failures)"
	@echo "  make test-regression  Regression tests against baselines"
	@echo "  make validate-schema  Validate FTS example against JSON schema"
	@echo "  make baselines        Regenerate regression baselines"
	@echo "  make clean            Remove build artefacts"
	@echo "  make upload           Upload to GitHub (needs GITHUB_TOKEN)"
	@echo ""

install:
	$(PIP) install -e ".[dev]"

lint:
	$(PYTHON) -m ruff check $(ENGINE_DIR)/FarmTwin $(ENGINE_DIR)/tests --output-format full
	$(PYTHON) -m ruff format --check $(ENGINE_DIR)/

format:
	$(PYTHON) -m ruff check $(ENGINE_DIR)/ --fix
	$(PYTHON) -m ruff format $(ENGINE_DIR)/

test: test-unit

test-unit:
	FARMTWIN_TDD_MODE=off \
	$(PYTHON) -m pytest $(TESTS_DIR)/ -m "unit and not tdd" \
	  --cov=FarmTwin --cov-report=term-missing --tb=short -v

test-tdd:
	FARMTWIN_TDD_MODE=on \
	$(PYTHON) -m pytest $(TESTS_DIR)/ -m tdd \
	  --tb=short -v; \
	echo "TDD mode: failures above are expected (red phase)"

test-regression:
	FARMTWIN_TDD_MODE=off \
	$(PYTHON) -m pytest $(TESTS_DIR)/ -m regression --tb=long -v

validate-schema:
	$(PYTHON) scripts/validate_schema.py \
	  --schema $(ENGINE_DIR)/FarmTwin/schemas/fts_survey_schema.json \
	  --docs   docs/examples/eruthempathy_pilot.fts.json

baselines:
	$(PYTHON) scripts/generate_baselines.py --all

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
	find . -name "coverage.xml" -delete 2>/dev/null || true
	find . -name "*.xml" -path "*/tests/*" -delete 2>/dev/null || true

upload:
	@if [ -z "$$GITHUB_TOKEN" ]; then \
	  echo "ERROR: export GITHUB_TOKEN=ghp_... first"; exit 1; fi
	$(PYTHON) scripts/upload_to_github.py
