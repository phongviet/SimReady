# Current command-line interfaces

Run from the repository root with `uv run --frozen simready ...`. Every command
below has argparse `--help`; paths/configs are explicit, and generated output
paths must be new. Configs are JSON rather than the illustrative YAML in PLAN.md.
`uv.lock` and frontend/package-lock.json pin the tested environments.

| Command | Main arguments / behavior |
|---|---|
|`storage`|`--root` optional; conservative 30 GB budget check|
|`data synthetic`|`--out`; eight analytic posed RGB-D frames with frozen splits|
|`data fetch`|`--out`; pinned official synthetic Redwood sample, bounded acquisition|
|`data import`|`--source --format tum_rgbd\|open3d_redwood_sample --out`; TUM `--max-frames` default 100|
|`data validate`|`--scene`; complete manifest/files/calibration/depth/split validation|
|`data split`|`--scene`; revalidate frozen splits; does not repartition an existing dataset|
|`recon train`|`--scene --out --preset smoke\|local_6gb`; optional `--config --python`; isolated GPU worker|
|`recon render`|`--artifact --scene --split train\|validation\|candidate\|test --out`; optional worker `--python`|
|`recon validate`|`--artifact`; validate checkpoint/PLY content and provenance|
|`recon smoke`|CPU validation of genuine saved analytic checkpoint/views; no live inference|
|`geometry build`|`--scene --out --method tsdf --voxel-size`; use `uv run --frozen --extra geometry`|
|`scene create`|`--id --name --dataset --artifact --geometry --renders`; optional registry `--root`|
|`scene demo`|`--root` optional; seed saved analytic scene/report and measured research snapshot|
|`scene attach-report`|`--id --run-id --run`; optional `--root`; verified report registration|
|`eval run`|`--scene --artifact --renders --out`; optional `--config --python`; fresh frozen-view GPU evaluation|
|`report build`|`--run`; validate and locate already generated HTML/Markdown, never invent a report|
|`sim save`|`--scene` registered ID, `--config`; optional `--root`; save versioned scenario|
|`sim run`|`--scene --scenario`; optional `--root`; deterministic navigation/replay artifact|
|`sim list`|`--scene`; optional `--root`; list saved simulation runs|
|`auth init`|`--root` optional; provision private distinct local Builder/Reviewer credentials|
|`api serve`|`--root --port --demo` optional; loopback service, static built frontend if present|
|`research prepare`|`--out`; optional `--config`; freeze protocol and withhold candidate/test pixels|
|`research run`|`--study --phase acquire\|evaluate\|all`; verified sequential/recoverable research execution|
|`research analyze`|`--study --out`; use `uv run --frozen --extra research` for plots|
|`research register`|`--id --analysis`; optional `--root`; controlled read-only dashboard package|

Default registry root: `artifacts/studio`; default port 8000. Served assets use
registered keys and hashes, not arbitrary filesystem URLs. A new model/import
is not automatically a scene: build independent geometry, render frozen views,
then `scene create`. For supplied custom cameras use the bounded render HTTP API
in PIPELINE_API.md. These reference-free outputs are ineligible for held-out metrics.

## Canonical real-scene reproduction

After `make setup` and the separately documented GPU setup, use new output paths:

```bash
uv run --frozen python scripts/fetch_tum_data.py
uv run --frozen simready data import --source data/raw/rgbd_dataset_freiburg1_desk.tgz \
  --format tum_rgbd --max-frames 100 --out data/scenes/tum-fr1-desk
uv run --frozen simready recon train --scene data/scenes/tum-fr1-desk \
  --preset local_6gb --out artifacts/scenes/tum-fr1-desk/baseline-1
uv run --frozen simready recon render --artifact artifacts/scenes/tum-fr1-desk/baseline-1 \
  --scene data/scenes/tum-fr1-desk --split test --out artifacts/renders/tum-fr1-desk-test-1
OMP_NUM_THREADS=4 uv run --frozen --extra geometry simready geometry build \
  --scene data/scenes/tum-fr1-desk --out artifacts/geometry/tum-fr1-desk/tsdf-1
uv run --frozen simready eval run --scene data/scenes/tum-fr1-desk \
  --artifact artifacts/scenes/tum-fr1-desk/baseline-1 \
  --renders artifacts/renders/tum-fr1-desk-test-1 --out artifacts/evaluations/tum-fr1-desk-test-1
```

A training-view sample batch can be generated with `recon render --split train`
and a separate new `--out`; training views are not held-out quality evidence.
See WALKTHROUGH.md for the scene preparation/recording continuation. Avoid running
CLI/research GPU jobs concurrently with the API workers; the service's registry
lock does not serialize arbitrary external CLI invocations.

`quality_cloud`, pose recovery, general RGB-only video, physical simulator adapters,
base-scene removal and photorealistic edited-scene evaluation are unsupported.
No cloud GPU is configured; the verified fallback is `local_6gb` and saved CPU demo.
Changing a frozen split requires a new imported dataset/run, not a mutation command.

## Development and scripts

`make setup`, `lint`, `test`, `demo`, `studio`, `storage`, `setup-geometry`,
`fetch-example`, `import-example`, `test-official`, `test-real`, `gpu-setup`,
`test-gpu`, `browser-setup`, `test-browser`, `frontend`, `benchmark` are available.
GPU tests opt in via `SIMREADY_GPU_TESTS=1`; otherwise they skip explicitly.

Scripts supply bounded TUM/sample fetching, GPU setup, real navigation layouts,
review/export verification, benchmark measurements, walkthrough preparation,
multi-study output indexing and labeled companion analysis (the last via
`python -m simready.research.bench_analysis`). Each accepts `--help`.
The exact research protocol/configuration and outputs are in M5_RESULTS.md and
RECAPTURE_PROTOCOL.md. `make benchmark` requires the real assets above and writes
a new immutable measurement package; see BENCHMARK_PROTOCOL.md.
