# Local shipping measurements

Measured 2026-10-30, clean source `df422ba`, GTX 1660 Ti6 GB under WSL2,
Intel i7-10750H (12 logical CPUs). Isolated Python 3.10.20, torch2.4.1+cu124,
gsplat1.5.3+pt24cu124; CPU runner Python 3.12.3. No competing project GPU job was
observed. These are local observations, not cross-system guarantees or speedups.

[Raw samples and source pins](evidence/m6-benchmark.json) are a byte-identical copy
of `experiments/m6-benchmark-1/summary.json`, SHA-256
`48710cb1a41871fd18a44c8d9cbc2a735d344d8266d49004d408804ee4e74206`.
Full generated predictions/reports/logs remain ignored locally. Reproduce with
[the protocol](BENCHMARK_PROTOCOL.md) and `make benchmark` (choose a fresh output
path if the default already exists).

| Measurement | Observed result | Scope |
|---|---:|---|
| GPU RGB+expected-depth render throughput |656.77 frames/s|17,828 Gaussians;320×240;18 cameras cycled;10 warmups then180 synchronized frames|
| Render latency p50 / p95 |1.459 /1.882 ms|Python dispatch and CUDA sync; excludes loading, transfers, PNG/NPY, HTTP, browser|
| Render peak allocated / reserved |18,117,632 /29,360,128 bytes|PyTorch allocator; excludes driver/context and total device usage|
| Fresh evaluation |18 pairs /12.768 s =1.410 pairs/s|Saved real TUM test renders; startup, pinned SSDLite/LPIPS, metrics, staging and report writes included|
| Historical reconstruction loop/run |9.813 s;1,200 iterations|Original real baseline worker timer, including its tensor setup/model serialization; excludes process startup and CPU training-data preparation|
| Historical reconstruction peak allocated / reserved |86,880,768 /102,760,448 bytes|Original worker record, not a new training run; PyTorch allocator only|

| Sequential loopback endpoint |p50 ms|p95 ms|
|---|---:|---:|
|GET `/api/v1/health`|1.709|2.198|
|GET `/api/v1/scenes`|2.835|3.813|
|GET `/api/v1/scenes/analytic-demo`|2.656|3.491|

API results use a fresh analytic registry and live Uvicorn TCP server. Each
endpoint has5 warmups and100 recorded sequential urllib requests with a fresh
connection and JSON parsing included. These are read-only unauthenticated paths,
not production load, mutation, TLS or remote-network measurements. The server
was terminated after measurement.

The harness verifies the original real model, frozen cameras/split and all input
pins. A separate post-run check reproduced p50/p95 and FPS from raw durations,
confirmed18 evaluation pairs, validated every evaluation content hash/binding,
and confirmed `git_dirty:false`. Render finite-output witness passed. No training,
selection or model configuration changed in response to these timing results.

One evaluation run supplies no timing uncertainty estimate. Warm render timing
is deliberately narrower than full service or browser rendering: do not present
656.77 FPS as the studio's interactive FPS. Historical model quality remains the
same limited real TUM baseline documented in [M3](M3_CHECKLIST.md); high throughput
does not establish reconstruction or perception quality.
