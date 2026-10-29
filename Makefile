export UV_CACHE_DIR := $(CURDIR)/.cache/uv
export npm_config_cache := $(CURDIR)/frontend/.npm-cache

.PHONY: setup storage lint test test-real demo frontend fetch-example import-example

storage:
	PYTHONPATH=src python3 -m simready.storage

setup: storage
	uv sync --frozen
	npm --prefix frontend ci --no-audit --no-fund
	$(MAKE) storage

lint:
	uv run --frozen ruff check .
	uv run --frozen ruff format --check src tests scripts

test: storage lint
	uv run --frozen pytest -q
	npm --prefix frontend test
	npm --prefix frontend run build
	$(MAKE) storage

demo:
	@if [ ! -d data/scenes/synthetic ]; then uv run --frozen simready data synthetic --out data/scenes/synthetic; fi
	uv run --frozen simready data validate --scene data/scenes/synthetic

frontend:
	npm --prefix frontend run dev

fetch-example: storage
	@if [ ! -d data/raw/redwood ]; then uv run --frozen python scripts/fetch_example_data.py --out data/raw/redwood; fi

import-example: fetch-example
	@if [ ! -d data/scenes/redwood ]; then uv run --frozen simready data import --source data/raw/redwood --format open3d_redwood_sample --out data/scenes/redwood; fi
	uv run --frozen simready data validate --scene data/scenes/redwood

test-real: import-example
	SIMREADY_REAL_SAMPLE=data/raw/redwood uv run --frozen pytest -q -m real_data
