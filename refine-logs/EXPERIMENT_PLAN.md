# Experiment plan — M5

Problem: image resemblance alone does not establish detector consistency; limited
new observations may reduce reconstruction discrepancy, but an acquisition rule
must be tested against equal-budget controls. This is an engineering case study,
not a proposed novel active-reconstruction algorithm. No frontier model is central.

## Claim map and minimum evidence

- H1 (hypothesis, not a result): validation-calibrated pose/render risk selects
  four observations that improve held-out LPIPS more than four random observations.
  Minimum evidence: identical frozen blind cameras, detector/protocol, training
  steps/resolution/init budget, paired seeds and raw predictions for every arm.
- H2 (diagnostic): photometric and detector-discrepancy rankings need not coincide.
  Evidence: paired per-view metrics, Spearman with undefined constant cases
  explicit, pose-block summaries and concrete counterexamples. No causal claim.
- Anti-claim: any gain is merely from more data or training. Equal K=4 and1200
  fresh optimization steps in risk/random/farthest arms; base-only is separate.
- No superiority, novelty, true detection accuracy, safety or generalization claim
  is assumed. No annotated object GT exists; precision/recall/mAP and relations to
  true labeled errors remain N/A, not replaced by detector pseudo-labels.

## Fixed data/protocol

M3 test frames82–99 were inspected. E1/E2 may analyze that exposed case separately,
but E4 must reserve **18 additional never-inspected source RGB-D pairs** before
any new test evaluation. Curate them deterministically from the late source-time
interval, excluding every original100sample. Preserve original first82frames:
50train,16validation,16candidate. Replace the exposed18test observations with
new IDs/poses and opaque content digests. Source remains one real TUM fr1 desk
capture; new views are temporally correlated and not independent scenes.

Camera/index/association metadata are public. Candidate and blind-test images
are physically omitted from learner datasets before release. A separate curator
vault holds observations. The selector receives only fixed train/candidate poses,
current-model alpha renders and calibration results. Image validation/training
must explicitly scope reads to allowed observations; ordinary full validation
stays strict. Seal all method/seed selections before release of any candidate
observations, then release only the selected four to each arm. Release test GT
only after all selections are sealed. Log access phases, IDs and hashes. Test
GT cannot affect calibration, selection or training. This is an auditable method
interface, not an OS sandbox against a malicious local administrator.

## B1 — E1/E2 diagnostic blocks (must run)

Compute per-view PSNR/SSIM/LPIPS, depth MAE/RMSE/completeness and Hungarian detector
disagreement, as defined in EVALUATION_PROTOCOL.md. Report normalized unmatched
fraction and raw counts separately. Correlation is null with a reason for zero
variance; do not invent a coefficient. Show rankings/counterexamples and three
chronological six-view blocks. Bin nearest-train translation at0/.1/.25/.5m and
rotation at0/10/30/60degrees. Empty bins are explicit. Scene/visibility confounding
cannot be removed in this one-sequence study. Analyze the two-view analytic
fixture separately as integration evidence, not a second real scene.

## B2 — E4 calibration and acquisition (must run)

For each seed42/43/44 train a base model from only50original train images at
1200steps,320px width, init<=10000/max40000Gaussians, SH1, fixed M1 configuration.
Render/evaluate all16validation views. Fit a nonnegative ridge linear predictor
of LPIPS using **first8validation views only**; check on the last8, without test
labels or rule changes. Features are clipped nearest-train distance/.5m, clipped
nearest-train SO(3) angle/30degrees, and current-render fraction(alpha<.1).
Ridge penalty .1 applies to feature coefficients, not intercept. No extra model.
Score all16candidate poses using the base model; select top4 with frame-ID ties.
A weak/failed validation correlation is a reported failure; do not silently
replace the method or tune on test. Selection controls: uniform without replacement
(random seed1000+optimization seed), and greedy farthest translation from current
train+selected centers. Farthest is a simpler coverage control, not an implementation
of ActiveSplat/ActiveGAMER. All decisions are sealed before candidate GT release.

## B3 — equal-budget post-acquisition runs (must run)

For each seed and risk/random/farthest, retrain **from scratch** on the50+4selected
observations for exactly1200steps using the same resolution/optimizer/init limits
and seed. Do not fine-tune the base for extra steps. Base-only has50frames and is
an explicit no-acquisition control. Shared base/calibration costs are recorded.
Run each model on exactly the same18blind test cameras, after seals/release.
Keep full run configs, package/weight/source/split/input hashes, training logs,
checkpoints, renders, predictions, per-view metrics and reports.

## Statistics, gates, outputs

Main table: each method/seed and mean±sample SD of seed-level view means; paired
risk-minus-random differences with direction explicit. Report min/max and raw
seed values. No independent-frame confidence interval or significance claim from
18correlated cameras. Three optimization seeds estimate limited within-capture
variability, not across-scene uncertainty. Primary LPIPS lower-is-better; secondary
RGB/depth/detection metrics stay separate. Negative outcomes are valid results.

Gates: CPU math/read-boundary tests → frozen curation/splits → base/calibration
→ all sealed selections → observation release → equal-budget arms → fixed test
→ hash/fairness audit → analysis and failure figures → research dashboard/report.
Never relaunch/overwrite a successful run to improve its score. Failed runs retain
errors; resume only verified terminal stages. No new experiments after looking at
test outputs without a clearly versioned follow-up protocol.

Compute:12smallGPU training runs plus validation/candidate/test rendering and
inference on the existing6GBGTX1660Ti runtime; estimated <1GPU-hour, measured cost
recorded. Sequential jobs, no paid compute. Reserve8GB and keep total <30GB;
cache/data/model/report sizes are checked before/after every large stage.

Relations: ActiveNeRF (Pan et al., ECCV2022) studies uncertainty-driven acquisition;
ActiveSplat (Li et al., RA-L2025) combines Gaussian maps and exploration planning;
ActiveGAMER (Chen et al.,2025) uses rendering information gain. Those broader online
systems are related work, not reproduced baselines here. YUBI-Real2Sim (Nishizawa
et al., arXiv2610.17521,2026) studies task/policy ranking and limitations of quality
indicators under fisheye robot observations. Our pinhole detector-consistency
case study does not reproduce its robot-policy result. No research novelty claim.

Primary references:
- https://arxiv.org/abs/2209.08546
- https://li-yuetao.github.io/ActiveSplat/
- https://arxiv.org/abs/2501.06897
- https://arxiv.org/abs/2610.17521
