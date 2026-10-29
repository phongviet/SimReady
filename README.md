# SimReady

Implemented scope: **Milestone M0 only**. `PLAN.md` is the project
specification. Reconstruction, scene editing, perception evaluation, simulation,
and review workflows are planned in later milestones and are not implemented.

M0 provides a CPU-only RGB-D import/validation package, explicit camera
conventions, an analytic fixture with known metric geometry, frozen dataset
splits, and a React/TypeScript shell. See [progress](docs/PROGRESS.md) and the
[acceptance checklist](docs/M0_CHECKLIST.md) for actual verification evidence.

## Setup

Run from the repository root. Python 3.12, uv and npm are required. Node 20.20.2
is tested (Vite also supports compatible Node 22.12+). No GPU is required.

```bash
make setup
make test
make demo
make storage
```

`make setup` installs exact locked dependencies. `make test` runs CPU pytest,
Ruff lint/format checks, the frontend scope test and production build. It uses
the official sample if present; otherwise that one test skips explicitly.
`make demo` generates/validates only the eight-frame synthetic fixture and is
safe to repeat. It is not a reconstruction demo.

## Real RGB-D integration smoke test

```bash
make fetch-example      # optional network access; official ZIP is about 3.8 MB
make import-example     # import five real RGB-D pairs and supplied odometry
make test-real          # require the official sample and run its integration test
```

Equivalent CLI commands (new output directories required for creation):

```bash
uv run --frozen simready data synthetic --out data/scenes/my_fixture
uv run --frozen simready data fetch --out data/raw/redwood
uv run --frozen simready data import --source data/raw/redwood --format open3d_redwood_sample --out data/scenes/redwood
uv run --frozen simready data validate --scene data/scenes/redwood
uv run --frozen simready data split --scene data/scenes/redwood
```

Imports generate `manifest.json`, `frames.jsonl`, `splits.json`, RGB and depth
files, and source calibration/provenance. Metadata is versioned and read-only;
validation detects content/hash changes, split overlap, bad images, calibration,
poses and timestamps. `data split` **verifies the frozen split**, without creating
a new partition. A new dataset version requires a new output directory.

The real sample has 2 train / 1 validation / 1 candidate / 1 test frame. Its
adjacent views, supplied estimated odometry, nominal world-up and frame-index
timestamps make this an import check, not credible held-out scientific evaluation.
See [dataset protocol](docs/DATASET_PROTOCOL.md) for conventions and limitations.

## Frontend shell

```bash
make frontend
```

Open [the local shell](http://127.0.0.1:5173). It states the M0 scope and CLI
entry point. It has no backend, scene viewer, fake metrics or editing controls.

## Storage and provenance

The environment is locked in `uv.lock` and `frontend/package-lock.json`.
`make` keeps subsequent uv/npm caches inside the project. Raw data, local
dependencies, caches and builds are ignored by Git. The full working project
has a **30,000,000,000-byte** budget. `make storage` accounts conservatively for
logical/allocated file sizes, hidden files and directories; acquisition performs
budget preflight checks. Downloads are capped at 20 MB and extraction at 25 MB.
This is a guard, not an OS disk quota; check before and after external installs.

The official sample is fetched from the [Open3D release](https://github.com/isl-org/open3d_downloads/releases/tag/20220301-data)
and verified by pinned SHA-256. Dataset redistribution terms remain unverified;
data is kept local and excluded from Git. The generated analytic fixture is CC0.
The project code's distribution license has not been selected.

Git author and committer dates for the initial M0 commits are intentionally
assigned across June–October 2026 at the user's request. Development and
verification actually occurred on October 29, 2026; dates are not evidence of
months of work. See [decisions](docs/DECISIONS.md), [environment](docs/ENVIRONMENT.md)
and [limitations](docs/LIMITATIONS.md). Local CI-equivalent commands are verified;
hosted GitHub Actions has not run because no remote is configured.

The next milestone, M1, requires a real reconstruction backend and measured
provenance on compatible compute. It has not been started.
