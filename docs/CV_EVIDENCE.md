# Implemented and measured portfolio evidence

Verified locally through 2026-10-30. This ledger supports limited statements;
it does not assert public deployment, hosted CI, human approval or broad accuracy.
The initial June–October Git dates were assigned at the user's request and do not
prove months of work. Actual execution dates are in PROGRESS.md.

| Claim that the evidence supports | Traceable evidence | Scope / limits |
|---|---|---|
|Built a posed RGB-D→learned 3DGS pipeline with metric camera contracts and isolated CUDA worker|M0/M1 checklists; DATASET_PROTOCOL.md; GPU_SETUP.md; reconstruction/gsplat.py|One recorded real TUM indoor scene; GTX 1660 Ti6 GB; no pose recovery or dynamic reconstruction|
|Implemented versioned rigid proxy editing and independent collision geometry|M2 checklist; SCENE_PROTOCOL.md; fresh UI evidence|TSDF is coarse/incomplete; inserted meshes are overlay-only; base splats remain immutable|
|Implemented held-out image/depth metrics, pinned detector matching, failure explorer and reports|M3 checklist; EVALUATION_PROTOCOL.md; M3_FAILURE_CASES.md|18 aligned TUM test views; agreement is not detection accuracy|
|Implemented deterministic occupancy navigation, scoped review/audit and verified scene exports|M4 checklist; SIMULATION_PROTOCOL.md; REVIEW_PROTOCOL.md; walkthrough evidence|Simplified simulated task; local Builder/Reviewer fixtures; no human endorsement or physical safety claim|
|Ran a three-seed fixed-budget recapture study and reported a negative result|M5_RESULTS.md; RECAPTURE_PROTOCOL.md; EXPERIMENT_AUDIT.md|One capture, nearby poses; risk minus random mean LPIPS +0.01473, sample SD 0.00426; risk worse in all 3 seeds; no novelty or generalization claim|
|Evaluated true object errors on a separately authored labeled companion|BENCH_COMPANION_RESULTS.md; BENCH_COMPANION_AUDIT.md|Six views of one synthetic bench; both endpoints saturated; error correlation undefined|
|Verified a reviewer-runnable CPU demo|FRESH_INSTALL.md; evidence/m6-fresh-ui.json; evidence/m6-fresh-wheel.json|Fresh wheel and separate checkout; torch/Open3D absent; saved model/views, no live CPU gsplat inference|
|Measured local performance with source pins and raw timing samples|BENCHMARK_PROTOCOL.md; BENCHMARK_RESULTS.md; evidence/m6-benchmark.json|Warm GPU rasterization and sequential loopback reads; not browser FPS or production load|
|Recorded an actual real-scene edit→QA→simulation→review workflow|WALKTHROUGH.md; evidence/m6-walkthrough.json; media/tum-walkthrough.webm|50.8 s recording; saved real model/report; separate automated local roles|

Selected measured observations, not quality guarantees:

- Original TUM baseline: 17,828 Gaussians; 18 test views; mean PSNR 16.735 dB,
  SSIM 0.518, LPIPS 0.403; supported depth MAE 0.0301 m and completeness 0.944.
  At confidence ≥0.5: 48 summed reference predictions and zero rendered predictions.
  The failure is retained in the report; no real detection precision/recall is claimed.
- Warm synchronized RGB+ED rasterization: 656.77 frames/s at 320×240, 180 measured
  frames after 10 warmups; excludes loading/transfers/encoding/HTTP/browser.
- Fresh 18-pair evaluation: 12.768 s including startup, staging, inference, metrics
  and report writes. One observation; no variance estimate.
- Sequential loopback read API p95: health 2.198 ms, scene list 3.813 ms,
  analytic scene detail 3.491 ms; 100 samples each, no concurrent load/TLS/mutations.
- Recorded inserted-box navigation: 1.15 m, zero replay collisions in the declared
  coarse map. This is not real robot performance or independent task selection.

A defensible CV description:

> Built SimReady, a local RGB-D-to-3DGS studio with versioned rigid proxy editing,
> independent TSDF colliders, held-out perception reports, deterministic navigation,
> and scoped review/audit/export. Evaluated 18 held-out views from a real TUM scene
> and ran a reproducible three-seed targeted-recapture study, reporting its failure
> to outperform random acquisition on that case study.

Optional measured-performance sentence (keep the exclusions attached):

> Measured 656.8 FPS warm GPU RGB+depth rasterization at 320×240 for a 17.8k-Gaussian
> model on GTX 1660 Ti, excluding IO/startup/browser; the full 18-pair evaluation
> completed in 12.77 s including model loading and report generation.

Do not claim: state-of-the-art reconstruction, novel recapture algorithm,
real-world detector accuracy, safety certification, sim-to-real transfer,
production IAM, Isaac/CARLA integration, physically correct weather/removal,
interactive browser 656 FPS, independent-scene validation, or a public service.
Local M6 gates are verified in FINAL_VERIFICATION.md. Public publication and
hosted CI remain pending; do not describe those as completed.
