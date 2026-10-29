# M3 acceptance

Current status: **complete locally, 2026-10-29**. Hosted CI has not run.

- [x] Pin an explicit metric/detector protocol before measuring test observations.
- [x] Execute actual CUDA detection/NMS/LPIPS and gsplat witnesses; fresh-agent docs pass.
- [x] Implement whole-image PSNR/SSIM/LPIPS, depth support/MAE/RMSE and safe empty cases.
- [x] Gated Hungarian correspondence, raw predictions, class/view counts, discrepancy traces.
- [x] Reject training/candidate evaluation, changed/subset cameras and frozen provenance mismatch.
- [x] Initial actual analytic GPU evaluation builds all report formats; no positive task-quality claim for empty detections.
- [x] Verify full CPU suite, lint, frontend tests/production build and live browser interactions.
- [x] Run one command from a clean committed implementation on all 18 frozen real TUM test views.
- [x] Inspect 5–10 actual qualitative failure views; link images, scores and raw predictions.
- [x] Verify persistent queue/API success/failure, report hashes, downloads and explorer controls.
- [x] Record actual results, limits and total storage below 30 GB; commit acceptance evidence.

Acceptance does not require a fabricated quality target, object detection accuracy,
new annotated data, mesh ground truth, a recapture benefit, or simulation approval.
Those claims require their own evidence in later milestones.

Verified evidence:

- Full CPU/optional-geometry suite: **140 passed, 2 opt-in GPU skips**; the new
  actual queued GPU evaluation test separately passed (**1 passed**).
- Frontend: **4 unit tests**, **4 Playwright browser tests**, TypeScript/Vite
  production build, lint/format and lock checks passed.
- Installed wheel in an isolated core-only environment seeded the actual report
  and loaded its two measured analytic views without Open3D/CUDA.
- Real complete test run: clean source `06114ba`, 18 views, mean PSNR16.73498dB,
  SSIM.517702, LPIPS Squeeze.403211, depth MAE.0300706m, RMSE.0734139m,
  completeness.943788. Detector real48 / rendered0 / matched0 at confidence.5.
- [Nine inspected actual failure views](M3_FAILURE_CASES.md),
  [summary](evidence/m3-tum-summary.json), [CSV](evidence/m3-tum-per_view.csv),
  [content manifest](evidence/m3-tum-evaluation.json), and
  [actual explorer screenshot](evidence/m3-tum-explorer.png).
- Local queue success: independent process rendered and evaluated the analytic
  checkpoint, registered the report at submitted revision1 even after an edit
  produced revision2. Failure injection retained explicit error/logs and survived
  application reopening. Interrupted jobs become failed on the next worker.
- Last storage check before final evidence commit: approximately **13.61 GB**;
  the final check below in PROGRESS.md includes wheel-test caches and Git.

The upstream LPIPS pretrained/torch.load warnings and Starlette TestClient/httpx
warning remain visible. The viewer bundle-size warning is retained. These do not
substitute for the successful runtime checks above. No rendered task quality,
accuracy, mesh accuracy or broad safety certification is claimed.

Final M3 storage after isolated-wheel verification: **14,086,309,730 bytes**,
below the 30 GB cap (conservative per-path accounting).
