export UV_CACHE_DIR := $(CURDIR)/.cache/uv
export npm_config_cache := $(CURDIR)/frontend/.npm-cache
export PLAYWRIGHT_BROWSERS_PATH := $(CURDIR)/.cache/playwright

.PHONY: setup setup-geometry storage lint test test-real test-official demo studio frontend fetch-example import-example gpu-setup test-gpu test-browser browser-setup

storage:
	PYTHONPATH=src python3 -m simready.storage

setup: storage
	PYTHONPATH=src python3 -c 'from simready.storage import check_budget; check_budget(1500000000)'
	uv sync --frozen
	npm --prefix frontend ci --no-audit --no-fund
	$(MAKE) storage

setup-geometry: storage
	PYTHONPATH=src python3 -c 'from simready.storage import check_budget; check_budget(2500000000)'
	uv sync --frozen --extra geometry

lint:
	uv run --frozen ruff check .
	uv run --frozen ruff format --check src tests scripts workers

test: storage lint
	uv run --frozen pytest -q
	npm --prefix frontend test
	npm --prefix frontend run build
	$(MAKE) storage

demo:
	@if [ ! -d data/scenes/synthetic ]; then uv run --frozen simready data synthetic --out data/scenes/synthetic; fi
	uv run --frozen simready data validate --scene data/scenes/synthetic
	uv run --frozen simready recon smoke
	uv run --frozen simready scene demo

studio:
	npm --prefix frontend run build
	uv run --frozen simready api serve --demo

browser-setup: storage
	PYTHONPATH=src python3 -c 'from simready.storage import check_budget; check_budget(1200000000)'
	cd frontend && npx playwright install chromium
	$(MAKE) storage

test-browser:
	npm --prefix frontend run build
	cd frontend && npx playwright test

frontend:
	npm --prefix frontend run dev

fetch-example: storage
	@if [ ! -d data/raw/redwood ]; then uv run --frozen python scripts/fetch_example_data.py --out data/raw/redwood; fi

import-example: fetch-example
	@if [ ! -d data/scenes/redwood-synthetic-v2 ]; then uv run --frozen simready data import --source data/raw/redwood --format open3d_redwood_sample --out data/scenes/redwood-synthetic-v2; fi
	uv run --frozen simready data validate --scene data/scenes/redwood-synthetic-v2

test-official: fetch-example
	SIMREADY_OFFICIAL_SAMPLE=data/raw/redwood uv run --frozen pytest -q -m official_data

test-real:
	SIMREADY_TUM_SCENE=data/scenes/tum-fr1-desk uv run --frozen pytest -q -m real_data

gpu-setup: storage
	uv run --frozen python scripts/setup_gpu.py

test-gpu:
	SIMREADY_GPU_TESTS=1 uv run --frozen pytest -q -m gpu

# Requires the real TUM model/renders and the validated isolated GPU environment.
benchmark: storage
	uv run --frozen python scripts/run_benchmark.py --out experiments/m6-benchmark-1
	$(MAKE) storage
