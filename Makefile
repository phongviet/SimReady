export UV_CACHE_DIR := $(CURDIR)/.cache/uv
export npm_config_cache := $(CURDIR)/frontend/.npm-cache

.PHONY: setup storage lint test test-real test-official demo frontend fetch-example import-example gpu-setup test-gpu

storage:
	PYTHONPATH=src python3 -m simready.storage

setup: storage
	uv sync --frozen
	npm --prefix frontend ci --no-audit --no-fund
	$(MAKE) storage

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
