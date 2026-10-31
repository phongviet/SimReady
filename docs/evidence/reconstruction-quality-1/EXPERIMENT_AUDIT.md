# Reconstruction-quality experiment integrity audit

**Overall verdict: WARN. Review independence: same-family. Acceptance status: provisional.**

Primary measurements, provenance, complete matrix, checkpoint ages, numeric summaries and selection reproduce. No evidence of fabricated results, unlabeled reconstruction-derived GT, deceptive self-normalization, or candidate/test-driven code selection was found. The baseline-check reporting gap is resolved by a separate verified supplement; conditional-depth/count/runtime/selection limitations still require qualifiers.

The warnings concern interpretation and implementation/reporting completeness. They are not findings of fabricated results. Only the two requested review files were written.

## Direct verification

- Verified 143 frozen source hashes, the specification hash, all 132 allowed train/validation RGB-D hashes, 5,458 opaque historical hashes, 11,931 nested artifact hashes, and all 19 analysis-file hashes. Recorded source bytes equal Git commit `15d783b702003037a17fc638a1dd9c899e6f1684`.
- The specification commit `e1c56e3` is dated 2026-10-30 11:13:25 UTC; implementation commit 11:29:29 UTC, protocol seal 11:29:31 UTC, and first stage 11:29:46 UTC. These checks establish recorded chronology; they are not a cryptographic third-party timestamp service.
- All 24 new runs, 63 snapshots, 67 validation evaluations and 91 complete ledger records are present: 79,200 optimizer updates and 1,072 paired views. Snapshot step, worker iterations, prefix-log completed count, final tensor equality, finite parameters, allocator bounds and ledger bindings agree.
- Recomputed RGB, depth, support masks and detection agreement for every one of the 1,072 new-study view pairs. All saved values matched exactly. Recomputed all 67 means, all 24 aggregate groups, CSV fields, Markdown rows, three selections and six failure selections.
- Independently reran LPIPS Squeeze 0.1 on CPU for frames 00050 and 00058 of baseline-s42/1200, control-s42/1200 and selected L1+SSIM seeds 42/43/44 at 3600. Maximum difference from saved GPU values was 4.470348358154297e-8.
- Inspected the actual seed-42 worst-view montage; it contains real reference, visibly imperfect reconstructions, residuals and a nontrivial depth mask. No illustrative fixture substitutes for the observed imagery.

## A. Ground-truth provenance: PASS

RGB and axial-Z depth references are dataset sensor observations from the real TUM sequence, not reconstruction outputs. All 1,072 staged RGB references were compared to resized dataset pixels. Training uses only 50 train frames; study evaluation uses exactly the frozen 16 validation frames. Detector agreement uses learned detector outputs on both domains and is explicitly disclaimed as accuracy. No official TUM reconstruction leaderboard or official evaluation claim was found.

Evidence: `data/scenes/tum-fr1-desk/manifest.json:41`; `data/scenes/tum-fr1-desk/manifest.json:48`; `data/scenes/tum-fr1-desk/manifest.json:55`; `data/scenes/tum-fr1-desk/manifest.json:59`; `src/simready/reconstruction/gsplat.py:100`; `src/simready/reconstruction/gsplat.py:321`; `src/simready/evaluation/runner.py:141`; `src/simready/evaluation/runner.py:211`; `src/simready/evaluation/runner.py:327`.

## B. Score normalization: WARN

No deceptive self-max score rescaling found. RGB uses fixed 255/1 ranges; LPIPS uses fixed [-1,1] input scaling; relative-depth training divides by GT clamped at 0.05 m; detector center error uses camera width/height. Depth MAE/RMSE condition on positive finite predictions and alpha>=0.1, so their mean denominator is a prediction-dependent support count. This is disclosed, with raw support counts and GT-denominator completeness, but prevents interpreting lower depth error alone as all-pixel geometry improvement. The LPIPS SVG maximum only scales its labeled plotting axis and does not alter raw metrics.

Evidence: `src/simready/evaluation/metrics.py:13`; `src/simready/evaluation/metrics.py:24`; `src/simready/evaluation/metrics.py:105`; `workers/perception_worker.py:90`; `workers/perception_worker.py:124`; `workers/quality_losses.py:21`; `src/simready/evaluation/runner.py:342`; `src/simready/evaluation/report.py:80`.

## C. Results, provenance, completeness, and timing: PASS

All 24 planned new training runs and 67 complete 16-view evaluations exist; all 91 ledger records are complete. All checked source/spec/data/history/model/checkpoint/render/evaluation/analysis hashes match. Frozen source equals recorded commit; specification commit precedes source commit, seal, and execution. All 63 snapshot ages/prefix logs/final tensor equalities are consistent. All 1,072 CPU metric replays and all summary, table, aggregate, selection and failure-selection checks passed; ten independent LPIPS forwards matched within 4.470348358154297e-8. No missing arms or fabricated results found. The original immutable report emits standalone-vs-trajectory discrepancy checks only for seed 42, but the subsequently supplied verification/replay-result-v2.json records all three seeds and resolves the reporting-completeness gap. Its deltas, verifier hash, 91 ledger hashes, runtime sums/span and allocator maxima were independently verified; all three seeds pass the stated tolerances. Audit status in tracker remains pending at the audited snapshot, correctly describing unfinished assurance.

Evidence: `experiments/reconstruction-quality-1/protocol.json:400`; `experiments/reconstruction-quality-1/protocol.json:425`; `experiments/reconstruction-quality-1/protocol.json:5888`; `experiments/reconstruction-quality-1/seal.json:2`; `experiments/reconstruction-quality-1/ledger/train-control-s42.json:2`; `experiments/reconstruction-quality-1/control-s42/model/checkpoints/step_001200/artifact.json:4`; `experiments/reconstruction-quality-1/control-s42/model/checkpoints/step_001200/artifact.json:132`; `workers/gsplat_worker.py:185`; `workers/gsplat_worker.py:231`; `src/simready/research/quality.py:90`; `src/simready/research/quality.py:229`; `src/simready/research/quality.py:363`; `src/simready/research/quality_report.py:33`; `experiments/reconstruction-quality-1/analysis/baseline-checks.json:11`; `refine-logs/reconstruction-quality-1/EXPERIMENT_TRACKER.md:7`.

## D. Dead code and executed variants: PASS

Study loss branches and RGB/depth/LPIPS/detector metrics are actually invoked and appear in saved per-view outputs, predictions, and convergence logs. MSE and GT-valid-mask variants are supported/tested code, explicitly outside the frozen study; they are not represented as empirical ablation arms. Geometry Chamfer/F-score remain explicitly unavailable, not phantom measurements. CPU/GPU acceptance-test source was inspected; this audit did not rerun or independently substantiate the tracker historical test-count assertions.

Evidence: `workers/gsplat_worker.py:191`; `workers/quality_losses.py:21`; `workers/perception_worker.py:123`; `src/simready/evaluation/runner.py:206`; `src/simready/evaluation/runner.py:225`; `src/simready/evaluation/runner.py:229`; `src/simready/research/quality.py:21`; `refine-logs/reconstruction-quality-1/EXPERIMENT_PLAN.md:70`; `workers/test_quality_losses.py:13`; `tests/integration/test_gpu_reconstruction.py:54`.

## E. Scope and strength of claims: WARN

One previously exposed capture, three seeds, seven arms and three correlated checkpoints per trajectory support descriptive validation results only. Existing scope disclaimers are appropriate. Selection compares 21 checkpoints per seed on the same 16 views and is optimistic; no independent test generalization or significance claim is supported. Objective changes alter densification and realized counts, so matched-update comparisons are not equal-time or equal-count effects. Local serial timings are measurements, not a randomized portable speed benchmark. Aggregate secondary-metric tradeoffs need explicit narrative: LPIPS improvements are not universal SSIM/depth improvements. All largest-paired-degradation cases have negative signed deltas, so they are least-improved views rather than actual LPIPS regressions.

Evidence: `refine-logs/reconstruction-quality-1/EXPERIMENT_PLAN.md:34`; `refine-logs/reconstruction-quality-1/EXPERIMENT_PLAN.md:62`; `refine-logs/reconstruction-quality-1/EXPERIMENT_PLAN.md:84`; `experiments/reconstruction-quality-1/analysis/report.md:3`; `experiments/reconstruction-quality-1/analysis/report.md:80`; `experiments/reconstruction-quality-1/analysis/report.md:82`; `experiments/reconstruction-quality-1/analysis/report.md:92`; `experiments/reconstruction-quality-1/analysis/aggregates.json:300`; `experiments/reconstruction-quality-1/analysis/aggregates.json:399`; `workers/gsplat_worker.py:205`; `src/simready/research/quality_report.py:199`; `experiments/reconstruction-quality-1/analysis/failure-selection.json:12`.

## F. Evaluation type: PASS

Photometric and depth evaluation: real_gt (real dataset RGB and measured sensor depth; LPIPS is a learned comparison metric, not a generated reference). Detector consistency: synthetic_proxy in the checklist taxonomy, specifically a learned-detector agreement proxy with predictions on real images as reference; it is not annotated detection accuracy. Analytic synthetic smoke fixtures are implementation tests only and do not contribute to this study. No simulation_only or human_eval study outcome is claimed. No learned image/depth reference is substituted for sensor observations.

Evidence: `data/scenes/tum-fr1-desk/manifest.json:48`; `src/simready/evaluation/runner.py:141`; `src/simready/evaluation/runner.py:211`; `workers/perception_worker.py:123`; `src/simready/evaluation/runner.py:327`; `tests/integration/test_gpu_reconstruction.py:13`.

## Specific interpretation and reporting findings

1. **Supported-depth conditioning is real, disclosed, and material.** `depth_metrics` uses the prediction/alpha-dependent support count for MAE/RMSE. Completeness uses GT-valid count and ranges from 0.9773765901 to 0.9925711522 across evaluated checkpoints. This is not illicit division by a prediction maximum, but a changing evaluation population. Report MAE/RMSE with completeness and raw support; do not infer all-pixel geometry accuracy from the conditional error alone.

2. **The original missing baseline discrepancy flags are resolved by a separately saved verification supplement.** The implementation hardcodes baseline-s42 and control-s42 (`src/simready/research/quality_report.py:33`), while the plan requests the standalone/checkpoint comparison across the baseline experiment (`refine-logs/reconstruction-quality-1/EXPERIMENT_PLAN.md:62`). The added `experiments/reconstruction-quality-1/verification/replay-result-v2.json:3` supplies all three checks, matching the following independent paired control-1200 minus standalone-baseline deltas:

| Seed | Delta LPIPS | Delta PSNR dB | Exceeds 0.03 / 0.5 tolerance |
|---|---:|---:|---|
| 42 | -0.0009167827665805817 | -0.008855494057320001 | no |
| 43 | +0.0013421885669231415 | +0.029202732860200697 | no |
| 44 | -0.00006729178130626678 | -0.0027730856380827618 | no |

3. **Matched-update interventions change capacity and measured time.** At 3600, L1+SSIM averages 23,016.7 Gaussians and 30.9622 optimization seconds, versus control 17,945 and 25.2521 seconds. Its lower LPIPS is a total configuration effect, not an objective-only effect at fixed count or time. Cap20k yields 11,299–11,430 final splats; the conservative `2 * count > cap` growth gate changes training well below the nominal cap (`workers/gsplat_worker.py:205`). Calling the cap irrelevant because a control ended below 20k would be incorrect. Local serial timings do not establish a portable causal speed ranking.

4. **Secondary metrics disagree with a blanket quality-improvement claim.** L1+SSIM/3600 improves mean LPIPS versus control (0.2420118107 versus 0.2828733666) but supported mean depth MAE is slightly worse (0.0833812452 versus 0.0820584361 m), while completeness is higher. Depth-off mean depth MAE worsens by 0.0048891594 m from 1200 to 3600 despite lower LPIPS. L1+SSIM mean SSIM changes by -0.0007602196 over that interval. These are retained raw outcomes, not missing data; include them in the final claim narrative. Evidence: `experiments/reconstruction-quality-1/analysis/aggregates.json:300`, `:333`, `:399`; raw fields are in `analysis/quality-runtime.csv:1`.

5. **Failure selection is correct; the label needs explanation.** The largest signed winner-minus-control-1200 LPIPS deltas are -0.0558586121, -0.0496695340 and -0.0578519255. Thus all selected examples improved on this comparator. The label means the largest signed delta / least improvement, not actual degradation. The comparator also differs in both arm and update count; these panels do not isolate an objective effect. Evidence: `experiments/reconstruction-quality-1/analysis/failure-selection.json:12`, `:30`, `:48`; comparator is explicit at `src/simready/research/quality_report.py:203`.

## Claim impact

- **H1: needs_qualifier — supported for descriptive validation LPIPS; mixed for broader fidelity.** All 21 trajectories improve mean validation LPIPS at both 1200->2400 and 2400->3600. Control mean LPIPS is 0.3287577784309785, 0.29819653028001386, 0.2828733666489522; paired 3600-1200 delta -0.04588441178202629, with mean cumulative optimization time increasing by 16.087380805000674 s. This is not universal fidelity improvement: depth-off mean depth MAE worsens by 0.004889159410621027 m and L1+SSIM mean SSIM decreases slightly (-0.000760219648341757) from 1200 to 3600. No test/generalization/independent-checkpoint claim.

- **H2: needs_qualifier — supported for configuration-level tradeoffs at matched updates; not isolated equal-capacity/equal-time effects.** At 3600, L1+SSIM mean LPIPS 0.24201181065291166 versus control 0.2828733666489522 (paired delta -0.04086155599604056), mean counts 23016.666666666668 versus 17945, mean optimization time 30.962186675000947 versus 25.252110198998707 s, and supported depth MAE 0.08338124520816641 versus 0.08205843608414129 m. Cap20k produces roughly 11369 splats and worse LPIPS, despite control also ending below nominal 20k: growth gating at twice current count is the operative intervention. SH2 improves LPIPS; depth-off and relative-depth do not dominate control. Selected same-validation results are descriptive, not unbiased estimates.

## Actions

- A1 (medium, interpretation): In the claim narrative or a new immutable supplement, state that H1 is supported for validation LPIPS and that H2 is a matched-update configuration intervention with count/runtime mediation. Include secondary-metric regressions, depth support/completeness, prior validation exposure, temporal dependence, and multiple-comparison optimism. Preserve the frozen study.
- A2 (low, implementation_specification_gap): Resolved by experiments/reconstruction-quality-1/verification/replay-result-v2.json:3. All three baseline discrepancy checks are present and independently verified. Retain this supplement alongside the immutable original report; no training or original-output rewrite is required.
- A3 (low, presentation): Clarify that the largest signed paired-degradation selections have negative deltas and therefore show least improvement, while preserving the deterministic selection rule and frame IDs.
- A4 (low, assurance_bookkeeping): Update the tracker after consuming this review with WARN, same-family, provisional status; do not mark cross-family independence or unrestricted acceptance.
- A5 (future_only, scope): Any claim about isolated objective effects at fixed density, equal-time efficiency, portable speed, or unseen-scene generalization requires a new preregistered experiment; the current data do not establish these claims.

## Limits of this audit

- The audit verifies present artifacts and source paths; it cannot prove absence of every prior human/agent exposure or unlogged off-path computation. The study already discloses prior sequence exposure.
- No new training or rasterization run was performed. Historical acceptance-test counts were not rerun by this reviewer.
- LPIPS inference was independently replayed on ten named saved new-study pairs, not all 1072. All 1072 saved LPIPS predictions were checked against view metrics and aggregates.
- Public dataset source authenticity is assessed from local acquisition provenance and observed real imagery; no fresh download or upstream archive re-acquisition was performed.

No cross-family independence, unseen-scene generalization, simulator readiness, or detection accuracy is established by this review.

## Supplementary artifacts added during review

Read `docs/evidence/reconstruction-quality-1/replay.py` directly. Its saved output `experiments/reconstruction-quality-1/verification/replay-result-v2.json` accurately describes saved-value LPIPS aggregation rather than new inference (`:130`), reports all three baseline discrepancies (`:3`), and binds 91 ledger hashes. Independently verified its source/protocol/selection/ledger hashes and all-seed deltas, 1,960.389493-second stage span, 594.2588169440169-second optimization sum, 4.644190482980775-second checkpoint-IO sum, and 100,306,944 / 121,634,816-byte allocator peaks. The resume log lists all 25 model/reference stages; the log alone does not attest kernel execution or exit status. These additional files resolve the omitted baseline-check reporting item without changing frozen training or evaluation outputs. The auditor's separate ten-pair LPIPS forward replay remains distinct from the supplement's saved-value aggregation.
