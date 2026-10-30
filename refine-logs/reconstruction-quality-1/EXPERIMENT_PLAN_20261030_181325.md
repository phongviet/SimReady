# Reconstruction-quality ablation specification

Frozen design date: 2026-10-30 (Asia/Bangkok). Study ID:
`reconstruction-quality-1`. No training under this specification has run yet.
This specification must be committed and implementation acceptance passed before
any study training. Existing M1/M3/M5 artifacts, protocols and outputs are immutable.

## Questions and hypotheses

H1: increasing optimization from 1,200 to 2,400/3,600 updates improves validation
fidelity, or reveals a plateau/overfitting. Minimum evidence: paired checkpoint
metrics/convergence and costs across seeds42/43/44; retain losses/negative deltas.
H2: representation/objective changes affect the quality/runtime tradeoff at a
matched budget. Minimum evidence: one-factor controls at matching steps/seeds,
actual Gaussian counts/memory, validation metrics and qualitative failures.
Neither improvement, research novelty nor generalization is assumed.

## Baseline establishment (B1)

Read-only historical reference: `artifacts/scenes/tum-fr1-desk/baseline-1`, genuine
17,828-Gaussian reconstruction. Verify its saved configuration equals the current
`configs/recon_local_6gb.json`:1,200 steps,320×240, seed42, training-only RGB-D
initialization (stride4,10,000 points), cap40,000, SH1, fixed Adam rates,
DefaultStrategy refinement100–900 every100, RGB L1 +0.05 depth L1 on positive GT
and alpha>0.01. Historical timing is context, not a new measurement.
Render/evaluate this model on the existing complete16-view VALIDATION split under
new output IDs. Do not read its existing test metrics to choose this matrix.
Run fresh independent1,200-step baselines for seeds42/43/44. Compare seed42 to the
historical reference descriptively; flag |LPIPS delta|>0.03 or |PSNR delta|>0.5dB
as a reproduction discrepancy, not a reason to retune or silently rerun.

## Frozen inputs and access boundary

Canonical dataset `data/scenes/tum-fr1-desk`: unchanged100 frames, train50,
validation16, candidate16, test18. Pin manifest/records/splits and allowed RGB-D
hashes before dispatch. Training reads only train pixels. Reference/render
preparation reads metadata only; validation evaluation reads only validation
pixels. Candidate/test pixels never enter this study's fit, selection or metrics.
All previously inspected test results, including M3/M5, are excluded from model
selection and hypothesis scoring. No final-test or independent-scene claim.
Validation has prior project exposure and multiple comparisons: report validation
selection optimism and same-capture temporal dependence explicitly.

## Ablation matrix (B2–B3)

Every trajectory uses50 training frames,320×240, same initialization/seed sequence,
fixed optimizer rates, refinement100–900/100 and identical render/evaluation
protocol. Budget trajectory3,600 updates; save parameter checkpoints at
1,200/2,400/3,600. These are reloadable model snapshots, not optimizer-resume files.
Full checkpoints share one trajectory; no claim that they are independent seeds.

| Arm | Only change from control |
|---|---|
|control|SH1, cap40k, L1, depth L1 weight0.05 and alpha-supported mask|
|cap20k|final Gaussian cap20k; keep10k initialization|
|sh0|SH degree0|
|sh2|SH degree2|
|l1-ssim|0.8 RGB L1 +0.2(1−SSIM), differentiable uniform7×7 SSIM in sRGB[0,1]|
|depth-off|depth-supervision weight0; RGB-D initialization remains unchanged|
|relative-depth|0.05 mean(|Zrender−Zgt|/max(Zgt,0.05m)) on the same support|

All7 arms ×3 seeds =21 trajectories. Plus3 independent1,200-step baseline runs.
Checkpoint1200 of control is compared with the independent1200 baseline; flag
large discrepancies with the same tolerance above. Refinement stops at900 for
all arms/budgets to isolate extra optimization; longer refinement schedules are
intentionally excluded. SH is active from initialization (no new ramp/scheduler).
Cap binding is measured, not assumed: conservative upstream growth gating can
stop growth below the configured cap. Report nonbinding/identical-count outcomes.

Implement reusable strict knobs for iteration/init/final limits/SH, L1/MSE/L1-SSIM,
SSIM weight, depth none/L1/relative-L1 and alpha-supported/GT-valid masks. The
unlisted MSE and GT-valid-mask combinations are supported/tested but not part of
this frozen matrix. Do not add arms after viewing results.

## Selection, evaluation and comparisons (B4)

Primary selection: minimum mean validation LPIPS Squeeze across all16 views,
within each seed. Ties within1e-6 use higher PSNR, then fewer steps, then stable
arm ID. No quality thresholds from inspected test images. Reject test/candidate
reports, wrong split/hash/cameras, incomplete views or nonfinite primary metrics.
Store the complete scored candidate table, selected IDs, metric/protocol/input
hashes and decision rule. Never replace the source checkpoint or old scene.

Use unchanged pinned M3 evaluation: PSNR/SSIM/LPIPS, axial depth MAE/RMSE and
completeness, fixed SSDLite agreement. No detection accuracy/real object GT claim.
Relative depth loss is dimensionless whereas baseline loss is meters: equal
numeric weights do not mean equal effective gradient scale. Log both loss terms.

Tables: every checkpoint's actual steps/config hash/count, optimization time,
checkpoint IO, total worker/adapter wall time, memory allocated/reserved, metrics;
matched-seed/budget deltas, mean±sample SD, runtime/quality Pareto flags and chosen
checkpoint IDs. No frame-independence CI or significance claims with three seeds.
Costs of snapshots/validation are separate from training-only timing. PNG/NPY
encoding and evaluator startup are not labeled raster FPS.

Figures: convergence curves of stochastic training components/counts vs step;
validation checkpoint curves; quality/runtime scatter; paired reference/control/
variant/residual/depth-support montages. Failure montage selection is fixed to the
worst validation LPIPS and largest signed paired degradation, at most6 views;
include actual frame IDs and selection rule. No invented images/scores.

## Compute, safety, failures

Local validated spec3db6217d, GTX1660Ti6GB, isolated .venv-gpu. No new packages,
cloud GPU, notifications or W&B required. Serialize with the local GPU job lock.
Use a4.5GB PyTorch allocator cap plus observed peaks; this excludes driver/context
usage and does not guarantee every arbitrary configuration fits. Explicitly fail
OOM/nonfinite/shape/hash errors; retain failure diagnostics, no automatic budget
reduction or precision changes. Stop rather than silently drop failed arms.

79,200 planned updates;67 validation evaluations (1 historical reference +3 fresh
baselines +63 checkpoint evaluations),1,072 paired views. Estimated30–90 minutes
on this machine, not a promised result. Check storage before/after operations;
reserve4GB for the new study and enforce its output cap plus the30GB project
limit. Existing output paths must never be overwritten. Resume only verified
completed stages; interrupted/failed stages are visible and require a new run ID.

## Acceptance gates and run order

1. CPU: strict knobs/default backward compatibility; photometric/depth math and
   gradients; invalid masks/weights/checkpoint schedules; train-only initialization.
2. Study access/selection: frozen source/config/data pins; no candidate/test pixel
   reads; rejection of test/forged/incomplete metrics; deterministic ties; immutability.
3. Actual GPU synthetic smoke: old default L1 math, SSIM/depth variants, snapshot
   save/reload/render, finite channels, count/memory cap and convergence records.
4. Recheck current CPU suite/lint and existing GPU reconstruction/evaluation tests.
   Only then freeze clean execution source and run B1, then all fixed B2–B3 arms.
5. Automated analysis reproduces summaries/deltas/selection from immutable artifacts,
   verifies all historical input/output pins remain unchanged and reports every
   failure/negative result. Render and inspect actual montage outputs.

Execution sequence: specification →implementation/tests →clean source/config seal
→historical validation reference/fresh baselines →matrix →validated selection/
quality-runtime report. If a gate fails, fix code under a new source seal/output ID;
never edit finished historical outputs to manufacture acceptance. No simulation
or frontend work is authorized/needed for this study; reports/CLI suffice.
