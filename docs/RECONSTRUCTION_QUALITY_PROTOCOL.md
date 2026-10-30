# Reconstruction-quality study

The preregistered specification is
[`EXPERIMENT_PLAN.md`](../refine-logs/reconstruction-quality-1/EXPERIMENT_PLAN.md).
It was committed before implementation or new training. Historical M1/M5/M6
outputs remain immutable. This study uses only the existing training observations
and complete frozen validation split. No test results select settings. Prior
exposure to the sequence and multiple comparisons limit interpretation.

## Reproduce

Use the existing validated CPU and isolated GPU environments (see GPU_SETUP.md).
Commit the implementation before freezing; no new dependencies are required.
From the repository root:

```bash
make storage
.venv-gpu/bin/python workers/test_quality_losses.py
SIMREADY_GPU_TESTS=1 UV_CACHE_DIR=$PWD/.cache/uv uv run --frozen pytest -q -m gpu
UV_CACHE_DIR=$PWD/.cache/uv uv run --frozen python -m simready.research.quality freeze \
  --study experiments/reconstruction-quality-NEW
UV_CACHE_DIR=$PWD/.cache/uv uv run --frozen python -m simready.research.quality run \
  --study experiments/reconstruction-quality-NEW
UV_CACHE_DIR=$PWD/.cache/uv uv run --frozen --extra research python -m simready.research.quality analyze \
  --study experiments/reconstruction-quality-NEW
make storage
```

A new study ID is mandatory. `freeze` records exact tracked source bytes, clean
Git commit, each configuration hash, dataset records, the specification hash,
evaluation configuration, and opaque historical artifact hashes. `run` rejects
changed sources/records or protocol tampering. Every completed stage is bound to
its inputs and revalidated before reuse. Interrupted/failed stages retain a
ledger entry and diagnostics; they are never silently retried under the same ID.
The single existing GPU-worker lock serializes training and evaluation. The
4.5 GB allocator cap leaves context/display headroom on the 6 GB GPU; reported
PyTorch allocator peaks do not measure all device allocations.

## Controls and artifact semantics

`QualityTrainingConfig` extends the legacy contract without changing legacy
serialization. It validates budgets, initial/final Gaussian caps, SH degree,
L1/MSE/L1+SSIM, SSIM mixing weight, depth off/L1/relative-L1, alpha-supported or
GT-valid depth masks, log intervals, and checkpoint steps. The frozen matrix
uses only the variants declared in the specification. SSIM training uses valid
uniform 7×7 population moments with constants 0.01² and 0.03²; RGB is clamped to
[0,1] for this term. Evaluation SSIM remains the existing scikit-image protocol.
Relative depth divides absolute axial-Z residual by max(reference, 0.05 m).
Depth-off retains RGB-D initialization, so it does not mean RGB-only training.

A checkpoint at N contains parameters after exactly N optimizer updates,
Graphdeco PLY, the prefix convergence log, the original trajectory job, timing
metadata and a standard reloadable hashed artifact. Its configuration describes
the full trajectory; `checkpoint_step` and worker `iterations` record its actual
age. It contains no optimizer state and cannot resume optimization. The final
snapshot tensors must equal the final trajectory tensors. Longer trajectories
retain the 100–900 densification interval and fixed learning rates.

Convergence logs contain completed update count, RGB L1, photometric/depth
objective components, valid depth fraction, total stochastic loss, Gaussian
count, allocator peaks, and cumulative optimization wall time. Checkpoint IO is
timed separately. Total worker/adapter and evaluation-stage times remain in raw
artifacts/ledger. CPU/GPU synchronization at snapshot boundaries makes their
cumulative timings observable. Timings are local measurements, not benchmarks
portable to other machines. Historical timings are not directly comparable.

## Acceptance and output interpretation

Before full training: CPU configuration/selection/stage-integrity tests, analytic
Torch CPU loss and gradient checks, actual CUDA loss/snapshot/reload/render
checks, existing GPU regressions, lint and full CPU regressions must pass.
Snapshots cannot be selected with test/candidate metrics, incomplete views,
changed split hashes, or nonfinite LPIPS/PSNR. Per seed, minimize validation LPIPS;
within 1e-6 of its minimum prefer PSNR, then fewer steps, then stable arm ID.

The automatic export includes the complete candidate/selection JSON, quality
versus runtime CSV/Markdown/HTML, measured Pareto points, seed-42 stochastic
convergence, and actual-image failure montages. Worst validation LPIPS and
largest paired degradation against that seed's control-1200 choose at most six
views deterministically. RGB/depth residuals and masks come from saved evaluated
observations, never illustrative fixtures. Paired seed deltas include negative
results; there is no population significance or test generalization claim.
