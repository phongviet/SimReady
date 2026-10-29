# M1 acceptance criteria

Actual work: 2026-10-29, after the user expanded scope to the full project.

- [x] Isolated worker spec, pinned packages, local GPU ledger and setup instructions.
- [x] Seeded CUDA matrix + Gaussian RGB/expected-depth forward/backward witness.
- [x] Fresh agent executed documented witness verbatim and confirmed it passes.
- [x] `ReconstructionBackend` interface with CPU preparation and isolated gsplat adapter.
- [x] `smoke` and `local_6gb` configurations, explicit seed and Gaussian budgets.
- [x] Initialization and losses consume only frozen training observations.
- [x] Portable Graphdeco SH PLY and safe NumPy checkpoint, content-hashed artifacts.
- [x] Actual short synthetic Redwood training run (40 iterations), validation-pose render.
- [x] Actual `local_6gb` real run, checkpoint reload and frozen-test RGB/depth render.
- [x] Saved provenance: dataset/split, source revision, configuration, timing,
      package/GPU versions, allocator peak memory, final Gaussian count.
- [x] GPU integration test verifies checkpoint reload, PLY values and metric depth.
- [x] Small genuinely trained analytic fixture for CPU-only artifact/render smoke.
- [x] CPU suite, lint, frontend regression checks pass with GPU tests skipping by default.

Success means genuine learned Gaussians are saved/reloaded and rendered, not a
photorealism claim. The five-frame Redwood sample is synthetic and is used only
for integration. Real-capture completion requires the separate TUM sequence.
GPU allocator memory is reported separately from driver/context overhead; the
reported PyTorch peaks are not total process or total device memory measurements.

## Accepted real-scene evidence

TUM `freiburg1_desk`: 100 frames, frozen split 50/16/16/18. The committed
`local_6gb` preset ran 1,200 iterations at 320x240, initialized 10,000 Gaussians
from training-only depth, and saved 17,828 learned Gaussians. A separate process
reloaded NPZ and rendered all 18 test cameras to RGB, expected axial depth and
alpha. All saved outputs passed content-hash/dimension/finite/support checks.

Source revision `3fcc516b1f24ab1c67c74bfcbe2995b5a58b545d` was clean during the
run. Actual loop time was 9.8135 seconds on the local GTX 1660 Ti; this is a
short initialization-assisted training run, not a portable performance claim.
PyTorch peak allocated/reserved memory was 86,880,768 / 102,760,448 bytes,
excluding driver/context overhead. Raw timings and configuration are preserved
without rounding in `docs/evidence/m1-tum-artifact.json`.

The separately trained CC0 analytic fixture contains 421 Gaussians and two saved
views (115,176 bytes total). `simready recon smoke` passes in an isolated wheel
install without torch/CUDA. The GPU integration test independently retrains,
reloads and checks metric depth, PLY positions and normalized quaternions.

No held-out fidelity metrics or perception accuracy have been measured yet.

Final verification: `make test` passed (112 CPU tests, 1 optional GPU skip,
1 frontend test, lint/format and production build). `make test-gpu` passed
(1 actual GPU integration test, 112 deselected). Hosted CI remains unrun because
no remote is configured. Conservative project accounting: approximately 11.55 GB
including dependencies, caches, data and generated artifacts, below 30 GB.
