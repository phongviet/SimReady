# M0 re-verification

Executed on **2026-10-29, Asia/Bangkok**, against the existing repository at
`a231b9e` plus the unfinished working-tree changes present at inspection.
This request covers M0 only. M1–M4 already exist in history; unfinished M5 code
was neither completed nor accepted by this verification. No experiments ran.

## Acceptance criteria and results

| M0 requirement | Verified evidence |
|---|---|
| Environment inspection | Ubuntu 24.04.4 WSL2; Python 3.12.3, uv 0.12.2, Node 20.20.2, npm 10.8.2, Git 2.43.0; 11 GiB RAM; GTX 1660 Ti 6144 MiB, driver 616.92; 656 GiB filesystem available |
| Repository foundation | Package/CLI, README, AGENTS.md, decision/progress logs, frozen Python/npm locks and CPU CI configuration exist |
| Typed canonical data/scene contracts | Strict versioned Pydantic contracts; meters, right-handed Y-up, explicit camera-to-world transforms; malformed inputs rejected by tests |
| Synthetic fixture | Eight analytic RGB-D views, known poses and metric plane mesh; explicitly synthetic, not a reconstruction |
| Official sample import | Five-frame Open3D Redwood/ICL-NUIM sample imported and validated as synthetic, with supplied calibration/pose provenance |
| Real data | Existing official 100-frame TUM import fully validated; real integration test passed; mock TUM format tests are separate from real evidence |
| Frozen splits | Synthetic 4/1/1/2, official sample 2/1/1/1, TUM 50/16/16/18; exhaustive/disjoint IDs and serialized hashes validated |
| Mathematical sanity | Independent known point projects to (419.5, 199.5); projection/unprojection and world/camera round trips retain 1e-12 assertions |
| Automated checks | 101 targeted CPU tests passed; Ruff lint/format, lock consistency, five frontend unit tests and TypeScript/Vite production build passed |
| Resource limit | Live conservative accounting about 14.24 GB, below 30 GB decimal, including Git, environments, caches, dependencies and data |

## Reproduce the checks

Run from the repository root after the documented setup. Official integration
tests require the local sample/TUM data described in `DATASET_PROTOCOL.md`.
Explicit environment variables below make missing required inputs fail rather
than silently skip.

```bash
SIMREADY_OFFICIAL_SAMPLE=data/raw/redwood \
SIMREADY_TUM_SCENE=data/scenes/tum-fr1-desk \
UV_CACHE_DIR="$PWD/.cache/uv" uv run --frozen pytest \
  tests/unit/test_camera.py tests/unit/test_dataset.py \
  tests/unit/test_acquisition.py tests/unit/test_storage_accounting.py \
  tests/unit/test_tum.py tests/unit/test_tum_archive.py \
  tests/integration/test_cli.py \
  tests/integration/test_official_sample.py \
  tests/integration/test_tum_real.py -q

uv run --frozen ruff check .
uv run --frozen ruff format --check src tests scripts workers
uv lock --check
npm --prefix frontend test
npm --prefix frontend run build
uv run --frozen simready data validate --scene data/scenes/synthetic
uv run --frozen simready data validate --scene data/scenes/redwood-synthetic-v2
uv run --frozen simready data validate --scene data/scenes/tum-fr1-desk
make storage
git diff --check
```

The observed CPU test run passed **101 tests in 38.64 seconds** with the default
local input paths and no skips. Test duration is not a product performance
benchmark. All three manual CLI validations returned `validation_scope: complete`.
The existing Vite large-chunk warning remains; hosted CI was not executed.
Later UI functionality is preexisting and is not established by these M0 checks.

## Provenance and boundaries

The original Open3D sample was incorrectly labeled real in the historical M0
records. The corrected importer labels it synthetic and rejects legacy mislabeled
datasets. This verification uses the corrected sample and the separate real TUM
capture; it does not rewrite immutable input manifests or invent results.

The first commit has author and committer dates **2026-06-01**, and the latest
commit is in **October 2026**. The initial historical dates were assigned at the
user's request; actual execution occurred on October 29 and is disclosed in
`DECISIONS.md`. Existing history is preserved. This verification commits only
working agreements and documentation; unrelated unfinished changes remain local.

M0 is accepted locally. No GPU training, later-milestone acceptance, new research
result, hosted CI run or external publication is claimed by this verification.
