# M3 acceptance

Current status: implementation verification in progress; real acceptance pending.

- [x] Pin an explicit metric/detector protocol before measuring test observations.
- [x] Execute actual CUDA detection/NMS/LPIPS and gsplat witnesses; fresh-agent docs pass.
- [x] Implement whole-image PSNR/SSIM/LPIPS, depth support/MAE/RMSE and safe empty cases.
- [x] Gated Hungarian correspondence, raw predictions, class/view counts, discrepancy traces.
- [x] Reject training/candidate evaluation, changed/subset cameras and frozen provenance mismatch.
- [x] Initial actual analytic GPU evaluation builds all report formats; no positive task-quality claim for empty detections.
- [ ] Verify full CPU suite, lint, frontend tests/production build and live browser interactions.
- [ ] Run one command from a clean committed implementation on all 18 frozen real TUM test views.
- [ ] Inspect 5–10 actual qualitative failure views; link images, scores and raw predictions.
- [ ] Verify persistent queue/API success/failure, report hashes, downloads and explorer controls.
- [ ] Record actual results, limits and total storage below 30 GB; commit acceptance evidence.

Acceptance does not require a fabricated quality target, object detection accuracy,
new annotated data, mesh ground truth, a recapture benefit, or simulation approval.
Those claims require their own evidence in later milestones.
