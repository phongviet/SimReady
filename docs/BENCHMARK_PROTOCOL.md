# Local shipping benchmark protocol

Run `make benchmark` from a clean source checkout after preparing the real TUM
baseline model, its frozen test renders and the validated `.venv-gpu` environment.
Use a new output directory for repeats; outputs are immutable. To override paths:

```bash
uv run --frozen python scripts/run_benchmark.py \
  --scene data/scenes/tum-fr1-desk \
  --artifact artifacts/scenes/tum-fr1-desk/baseline-1 \
  --renders artifacts/renders/tum-fr1-desk-test-1 \
  --out experiments/m6-benchmark-2
```

The harness pins input manifests, environment specification, weight hashes and
benchmark source. It preserves raw per-frame and per-request durations, the fresh
evaluation report/predictions, Git state, environment and source-model training
metadata. It checks complete evaluation binding and verifies input pins afterward.
It uses the default registry GPU lock; do not run research workers or a differently
rooted API GPU worker concurrently. No packages or weights should be downloaded.

- Render:18 fixed TUM test cameras,10 warmup frames,180 measured RGB+expected-depth
  frames, cycling in their original order. Synchronize CUDA before/after every
  frame, use no-grad, retain all durations. FPS is frames divided by total elapsed
  render time. Includes Python dispatch and synchronization; excludes model loading,
  host transfers, encoding, file output, HTTP and browser rendering. Report exact
  resolution/count, finite output witness and PyTorch peak allocated/reserved bytes.
  These allocator figures exclude driver/context memory and are not total VRAM.
- Evaluation:one fresh run of all18 test view pairs with the pinned detector,
  LPIPS, image/depth metrics and report exporter. Time the complete `evaluate`
  call including worker startup/model loading, staging and report writes. Excludes
  model training and render generation. Count paired views, not36 separate images.
  A single run provides a local throughput observation, not a variance estimate.
- API:one live Uvicorn loopback TCP service with a newly seeded analytic demo
  registry; health, scene listing and scene detail reads. Per endpoint discard5
  warmups then retain100 sequential urllib requests, opening a connection each
  time and parsing JSON. Compute NumPy linear-interpolated p50/p95. No concurrent
  load, TLS, authentication/mutations or remote network; no production SLO claim.
- Reconstruction time/memory:retain the original real baseline's worker metadata,
  labeled historical, rather than implying this benchmark retrains it. The worker
  timer excludes process startup and CPU data preparation; report its exact scope.

GTX1660Ti6GB under WSL2 is the tested hardware. Host load, GPU clocks and WSL
scheduling can change results. These observations do not imply a speedup over
another backend, interactive-browser FPS or real robot performance.
