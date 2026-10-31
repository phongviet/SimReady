# Independent-sequence and densification protocol

Preregistered 2026-10-31 before new captures are downloaded, decoded or trained.
No new results are available at registration. Prior selected policy is pinned in
`evidence/improvement-intake/frozen-policy.json`; existing outputs are immutable.

## Data and access

ScanNet v2 is preferred for annotated accuracy. The official ScanNet repository
requires a Terms of Use agreement and institutional-email access request. No
confirmed authorized download or complete public subset is available locally.
No access forms will be signed, messages sent, or restrictions bypassed by this
study. Source: https://github.com/ScanNet/ScanNet#scannet-data (checked2026-10-31).

Fallback captures: TUM freiburg1_room and freiburg2_desk, selected using publisher
metadata before image inspection. These are additional recordings, not necessarily
independent locations: freiburg1_room includes desks from the original office.
The publisher describes fr2 desk as containing monitors, keyboards, phones and
chairs. This suggests potential COCO vocabulary overlap, not verified annotation
coverage. Inspect only the designated candidate-pilot views for class coverage;
report insufficient coverage rather than replacing/dropping test frames.

Use256 uniformly temporally sampled posed RGB-D associations per sequence.
Reserve every16th sampled frame (16 frames total) as a candidate pilot. Among the
remaining240, freeze112 train,32 validation,32 additional candidate and64 test
frames in temporal blocks, before decoding images. Total candidate count48.
Pose and timestamp metadata may be inspected to validate coverage; test RGB/depth
must not tune policies. Dataset ingestion may validate file integrity/shape.
No repartition after inspecting pixels. Record archive SHA256 as actually observed,
original official URL/resolved URL, calibration, frame hashes and frozen splits.

TUM's publisher recommends ROS-default pinhole intrinsics for registered depth;
use525/525/319.5/239.5 and depth scale1/5000, without reapplying already corrected
scale factors. Record residual calibration/pose uncertainty. Reference:
https://cvg.cit.tum.de/data/datasets/rgbd-dataset/file_formats.
Archive bounds are explicitly sequence-specific: existing desk500MB/1.5GB
compressed/member-byte bounds remain unchanged; room900MB/3GB and fr2 desk2.2GB/6GB
are new acquisition/index bounds. Stream metadata and extract selected frames only.
No unrestricted tar extraction. Project resource guards remain enforced privately.

## Reconstruction confirmation

Fresh study IDs `generalization-room-1` and `generalization-fr2-desk-1`.
Three seeds42/43/44, three policies: original1200 RGB L1; matched3600 RGB L1;
previously selected3600 L1+SSIM (0.8/0.2). All use width320, stride4,10k initial,
cap40k,SH1, alpha-supported depth L1 weight0.05, unchanged learning rates and
refinement100–900/every100. RGB-D initialization for every policy. No target-scene
hyperparameter adaptation, early stopping or validation re-selection.18 new runs.
Evaluate all64 frozen test cameras under the same existing metric protocol.
Measure PSNR/SSIM/LPIPS, depth MAE/RMSE with support, realized Gaussian counts,
optimizer/worker/adapter/evaluation wall times and allocator allocated/reserved
peaks. No test-result-driven reruns. Failed/nonfinite/OOM arms remain visible;
do not silently reduce budgets. Source/config/input hashes precede dispatch.

## Densification experiment

Fresh ID `densification-desk-1`, original desk training/validation observations
only. Three windows100–900,100–1800,100–3000, every100, under the selected3600
L1+SSIM policy. Three seeds each, fresh control runs, same40k cap and10k initial
points;9 runs. Save1200/2400/3600 parameter snapshots. Evaluate complete16-view
validation only. Log whether the conservative growth guard binds; it permanently
stops growth when twice the current count would exceed the cap. Longer windows
therefore test this existing guarded policy, not unconstrained density growth.
Identical or negative outcomes remain results; they cannot establish that cutoff
never matters under another guard/cap. No schedule is selected using the new
sequences' test scores.

## Ground-truth perception gate

Target64 held-out frames per new capture (within requested50–100 where feasible).
Use original RGB dimensions and COCO-format boxes with explicit fixed categories,
class definitions, visibility/truncation/ignore policy and original-image hashes.
Candidate-pilot review checks vocabulary coverage first, without detector-derived
labels becoming GT. Human annotation/review can then inspect the fixed evaluation
frames; this does not authorize model tuning or changing their membership.

Provide a local annotation-review interface with draft COCO export, frame-level
review status, explicit reviewer identity and separate hash-bound approval record.
Model proposals remain drafts. No generated label is marked manually verified.
The evaluator must reject absent/incomplete/mismatched approvals. Until a human
actually reviews and approves, publish `pending_human_review`, not AP numbers.

With approved annotations, run the same fixed detector on reference and rendered
images at identical calibrated poses, using exactly the same reference boxes
scaled to the evaluation resolution. Pin categories/thresholds/max detections and
report101-point AP50, recall, per-class GT counts, TP/FP/FN, missed objects and
render-minus-real ΔAP50 alongside photometric/depth metrics. Explain any custom
COCO-subset semantics. Zero-GT classes have undefined AP and are excluded from the
macro average, with counts disclosed. Keep raw detector agreement separate.
No automatic “human approved” execution step is permitted.

## Acceptance and costs

Before training: safe sequence adapter/split tests, original import regressions,
CPU metrics/leakage/source-seal checks, kernel witness and CUDA smoke. Preserve
baseline calibration semantics. Freeze a clean source commit and actual
configuration/file hashes after these gates. Serialize workers on the existing
GPU lock and4.5GB training allocator cap. Record failures and costs, never retry
under a completed experiment ID. Estimate1–3 hours for27 training runs and full
evaluation; actual times will be recorded. Check resource availability before
each acquisition/stage. Stream archives and reserve output space before dispatch.

After execution: complete-run verification, numeric replay, fixed qualitative
selection (worst test LPIPS per policy/seed and largest matched-policy error),
all-seed paired deltas/SD, counts/runtime/support tradeoffs and limitations. No
statistical independence or unseen-site claim from these two correlated captures.


## Input-integrity amendment before successful fr2 import

The official fr2 desk GT index contains two different poses at the same timestamp
1311868229.5760. Initial data import correctly rejected its non-strict ordering;
that failure and the original protocol are retained in improvement-data-1.
For this sequence only, exclude every record belonging to a duplicated timestamp
rather than arbitrarily choosing or averaging poses. Preserve original GT text,
record discarded record count/timestamps and source text hash in calibration
provenance. Remaining timestamps must still be strictly increasing, finite and
within the original <=50ms interpolation support. Unexpected reversals/nonfinite
records remain errors. Use improvement-data-2 for the recovery import ledger;
reuse room's unchanged existing frozen dataset and its original pre-extraction
split plan explicitly. Model policies, seeds, sampled frame counts and test
membership rules do not change. No fr2 image has been decoded/inspected or used
for this correction. This is input-integrity handling, not test-driven tuning.
