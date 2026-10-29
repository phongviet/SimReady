# Experiment integrity audit: authored bench companion

Date: 2026-10-29. Auditor: `/root/bench_integrity_audit`.
Requested reviewer route: GPT-6-Astra, ultra, fresh context (`fork_turns: none`). This route was confirmed by the executor from its invocation; the backend model identity is not independently exposed to the reviewer. Review independence: **same-family**. Acceptance status: **provisional**.

## Overall verdict: WARN

**No invalidating numerical, ground-truth, or split-leakage discrepancy was found in the saved companion.** The independent CPU replay reproduces the authored observations/labels and reported metrics. The experiment supports a narrow synthetic integration result. Its error endpoint is saturated, so it does not establish prediction of true task failures, shared-error failure cases, detector generalization, or superiority of task-aware validation. Reporting and provenance limitations below should accompany the result.

The audit did not modify code, datasets, model outputs, or experimental results; it did not rerun training, rendering, detector inference, or LPIPS inference. Files were written only below this audit directory. This is not acceptance of M5, M6, the whole project, or the prior TUM study.

## A. Ground-truth provenance: PASS

The object is authored from nine fixed box primitives in `src/simready/data/bench.py:12–22`. Camera rays and object/floor/wall intersections produce source RGB, axial depth, and the visible-object mask (`bench.py:50–76`); boxes are the half-open extent of nonzero mask pixels (`bench.py:79–83`). The generator writes masks and boxes before any reconstruction or detector invocation (`bench.py:97–137`). No model checkpoint, detector prediction, confidence, or learned representation is an input to these functions. `data/scenes/authored-bench/annotations.json:2–15` declares geometry-derived truth and binds it to geometry/mask hashes. The pre-measurement protocol explicitly states the authored, procedural scope (`refine-logs/SUPPLEMENTAL_GT_PLAN.md:7–19`).

I independently reimplemented geometry intersection using the six face planes of each box, rather than calling the repository's slab-intersection function. All **28** saved masks, half-open boxes, quantized depth images, and RGB images reproduced exactly. Source depth quantization error relative to the analytic surface was at most **0.0004999831 m**, consistent with nearest-millimeter encoding. All rotations were proper and orthonormal. The camera ray parameter is axial camera Z because the unnormalized camera-space ray has z=1; this agrees with the explicit OpenCV axes and meters/Y-up declaration (`manifest.json:29`, `manifest.json:42–48`, `manifest.json:64–67`).

The dataset's exact 14/4/4/6 partitions are disjoint and exhaustive (`data/scenes/authored-bench/splits.json:2–40`). Training opens only the training observations (`src/simready/reconstruction/gsplat.py:100–119`); the worker consumes the saved training buffer (`workers/gsplat_worker.py:128–133`). A supplementary deterministic reviewer independently rebuilt all seven arrays in `model/training.npz` from frames 00000–00013, including seed-42 initial point sampling: every array was bitwise identical. The model's declared training IDs agree (`model/artifact.json:47–62`). There is no observed held-out RGB-D initialization or training contamination.

The benchmark is authored here, not an official COCO evaluation dataset. Using custom class-gated accuracy and explicitly custom AP50 is appropriate; it must not be renamed official COCO mAP. The local pinned torchvision category metadata independently agrees that category 15 is `bench`.

## B. Score normalization and metric correctness: PASS

No reported metric is divided by a prediction-derived maximum or other model-output statistic. RGB scaling is the fixed 255 range (`src/simready/evaluation/metrics.py:13–20`); LPIPS uses fixed [-1,1] normalization (`workers/perception_worker.py:90–97`, `:123–132`); box-center error uses declared image dimensions (`metrics.py:105–107`). Depth error is reported in meters on an explicit positive-depth/alpha support, with the excluded-pixel fraction exposed by completeness (`metrics.py:24–39`). The LPIPS SVG scales bar height for display, with a labeled axis, while raw numeric LPIPS remains saved; this is not score renormalization (`src/simready/evaluation/report.py:79–96`).

Class precision/recall uses confidence >=0.5 and IoU >=0.5 with one-to-one matching (`src/simready/research/bench_analysis.py:21–33`; `metrics.py:58–94`). For this one-instance-per-view dataset, the reported counts independently reproduce: **6 TP, 0 FP, 0 FN, precision=recall=1.0 in each domain**. Precision is deliberately null when no positive predictions exist, and recall is defined from the truth count; these branches have explicit tests (`tests/unit/test_labeled_detection.py:10–22`). The generic matching implementation prioritizes cardinality and IoU rather than score; this does not affect this dataset, which has one retained prediction and one truth per view.

AP50 ranks every saved post-score-floor bench prediction by descending confidence, greedily assigns each GT at most once, and averages the interpolated precision envelope over 101 recall values (`bench_analysis.py:36–72`). I separately replayed this using scalar IoU and a reverse cumulative precision envelope. The reference domain has **396** bench candidates and the reconstruction domain **132**. In both domains the first six ranked predictions are the six true positives; remaining lower-scoring candidates are false positives after full recall. Consequently **AP50=1.0 is mathematically correct** under this declared interpolation, even though 390/126 lower-scoring class candidates remain. Raw postprocessing predictions, including other classes, were retained: 300 detections for each of 12 domain/view inputs. This AP is not an all-confidence precision claim.

The six reference prediction-to-GT IoUs are 0.9474–0.9667; reconstructed-view IoUs are 0.6835–0.7983. All clear the declared 0.5 gate. Perfect AP50 therefore does not imply perfect localization or equal image quality. The figure visibly retains reconstruction holes/background artifacts.

All six saved PSNR, SSIM, MSE, depth MAE/RMSE/completeness and support masks replayed from source/render pixels. Their aggregate means match. LPIPS was traced exactly from raw inference outputs into rows and means; its network was not rerun. Both saved Spearman results are correctly null with reason `constant input; rank correlation undefined`: true-error changes and prediction disagreement are [0,0,0,0,0,0] (`analysis-1/summary.json:7–15`; `src/simready/research/selection.py:130–136`). Null is not evidence of zero population association.

## C. Result existence, binding, and execution provenance: WARN

All referenced result files exist. All **80** declared content hashes passed: model 4, renders 18, evaluation 53, companion analysis 5. Source hashes in evaluation and analysis manifests match current files. The dataset manifest, frames, split, geometry, masks, freeze record, committed pre-run protocol, checkpoint, render camera list, paired evaluation pixels, JSON/CSV rows, and aggregate analysis are mutually consistent. The production validators `validate_scene`, `validate_artifact`, `validate_renders`, and `verify_evaluation_binding` also passed without invoking neural inference. Exact pairing checks compare the requested observations, manifest, training/test IDs, checkpoint index, render index, protocol, and camera list (`src/simready/evaluation/runner.py:28–52`, `:82–115`).

Pinned local detector/SqueezeNet/LPIPS weight files hash to the three recorded digests (`evaluation/summary.json:120–124`) and pinned config. The inference worker uses the same fixed model and preprocessing for both domains (`workers/perception_worker.py:25–87`, `:116–137`), with post-floor/NMS/top-k output clearly declared. The saved log contains all six inferred frame IDs.

Saved reconstruction evidence is substantive: the finite learned checkpoint contains **5,669** Gaussians, its means differ from initialization, worker metadata matches the artifact and committed run evidence, and 121 training-log records cover steps 0,10,…,1190,1199. `worker.log` matches that log byte-for-byte. The optimizer, loss, and checkpoint-saving paths are real and reachable (`workers/gsplat_worker.py:175–218`). This supports the recorded learned reconstruction rather than a fixture represented as a reconstruction. No audit-time GPU execution was performed.

Two caveats warrant WARN rather than a provenance guarantee:

1. `frozen-inputs.json:1–6` contains content hashes but no timestamp or pre-training execution attestation, and the model artifact's hash map omits the freeze record and `training.npz` (`model/artifact.json:18–23`; `src/simready/reconstruction/gsplat.py:267–274`). Filesystem times are consistent with freezing first: freeze 15:44:44.494834 UTC; training buffer 15:44:44.881609; checkpoint 15:44:57.877609. The plan also matches the earlier committed copy. Current contents independently validate, but hashes and mutable timestamps alone cannot prove historical ordering or exclude out-of-band access. This is a hardening limitation, not evidence of this run being invalid.
2. `docs/evidence/m5-bench-run.json:11` and `docs/PROGRESS.md:412–413` still describe object-accuracy analysis as pending. They are earlier-stage records; the later analysis artifacts and clean source commit are present (`analysis-1/summary.json:2–5`). The generic experiment tracker concerns TUM, not this companion (`refine-logs/EXPERIMENT_TRACKER.md:13–15`). Update the current progress/tracker view when reporting this completed analysis, while retaining historical execution evidence. No nonexistent or mismatched numerical result was found.

## D. Dead code: PASS

The metric paths used for the reported claims are active: `image_metrics`, `depth_metrics`, and `detection_metrics` are called in `src/simready/evaluation/runner.py:206`, `:225–234`; detector and LPIPS are called at `workers/perception_worker.py:123–124`. Class accuracy and AP50 are called at `src/simready/research/bench_analysis.py:123` and `:158`; correlation is called at `:160–163`; matching calls IoU and gated assignment at `metrics.py:82–94`. Their outputs appear in saved per-view/summary artifacts and independently reproduce. Geometry Chamfer/F-score are explicitly null (`evaluation/summary.json:127–128`), with no accuracy claim based on an unexecuted function.

## E. Scope and claim ceiling: WARN

Actual scope is **one authored bench object, one synthetic scene, one reconstruction seed (42), one configuration, one fixed detector, six correlated held-out poses**. There are six observations of one object, not six independent objects. The report states this correctly (`analysis-1/report.md:3–5`, `:68`), and the protocol explicitly disclaims population significance and generalization (`refine-logs/SUPPLEMENTAL_GT_PLAN.md:34–39`). No broad scope claim in the supplied companion report was found.

The WARN concerns evidence coverage: all per-domain FP+FN counts are zero, and no shared-missed view occurs (`analysis-1/summary.json:17–33`, `:46`). Thus the planned true-error relationship has no variation to measure. The experiment demonstrates correct label/evaluation integration and successful detections under this particular synthetic condition. It cannot establish that detector disagreement predicts true failures, that image similarity misses task failure, that shared detector errors occurred, or that task-aware validation is superior. Reporting this outcome is valid; no retuning or redesign of the frozen case is needed to preserve its integrity.

## F. Evaluation classification: WARN; primary type `simulation_only`

The RGB/depth/object-accuracy comparison is **simulation_only**, with independently authored geometry-derived GT. It is not `real_gt` in the sense of real captured-object accuracy and is not a `synthetic_proxy` whose GT comes from model predictions. The source clearly declares synthetic (`data/scenes/authored-bench/manifest.json:48–62`; `analysis-1/summary.json:43–55`). The underlying detector real/render agreement remains a model-to-model proxy, separate from the labeled class accuracy.

There is a reporting inconsistency: the inherited generic evaluation report says “No ground-truth object annotations” (`src/simready/evaluation/runner.py:335–336`, saved `evaluation/summary.json:132`), although the companion now has independent authored annotations. The analysis report is accurately scoped, but a reader opening only the generic report receives a false scene-wide statement. Also, stored field/figure labels `real` mean the **analytic reference image**, not a real photograph. Carry an explicit companion explanation or report erratum beside the immutable original artifacts. This affects presentation/classification, not the reproduced numbers.

## Claim impact

| Claim | Audit judgment |
|---|---|
| Labels are independent of detector/reconstruction outputs | Supported by source paths and independent 28-view geometry replay |
| The saved learned model uses exactly 14 training RGB-D views | Supported by split/code checks, bitwise training-buffer replay, and saved execution evidence; historical external nonaccess is unproven |
| Bench-class precision/recall and custom AP50 are 1.0 in both domains on these six poses | Supported, with confidence/IoU/post-floor/synthetic scope stated |
| The image/depth metrics and object-error changes are reproducible from saved artifacts | Supported; LPIPS scalar traced, neural inference not rerun |
| There is a measured association between visual discrepancy and true error change | Unsupported: true error change is constant and correlations are undefined |
| Shared errors reveal disagreement failure in this companion | Unsupported as an observation: shared missed views=0 |
| General detector robustness, real-domain accuracy, sim-to-real validity, or task-aware superiority | Unsupported by this one-object/seed synthetic case |
| Full M5 or project acceptance follows from this audit | Outside scope and not established |

## Action items and limits

- Report the unchanged saturated outcome and null correlations explicitly; retain the one-object/six-pose caveat.
- Add a current companion completion entry and clarify that `real` is the analytic reference domain. Qualify the inherited no-annotation boilerplate via companion documentation/erratum without rewriting historical measurements.
- For future runs, bind the input buffer and label-freeze record into pre-training provenance. Do not retroactively imply a stronger historical attestation for this run.

The independent replay is saved as `replay_checks.py` with `deterministic-replay.json`. One initial run of this audit-only script hit a CSV boolean-parsing error after all numerical checks; treating booleans before numbers fixed the audit harness, and the full rerun passed. No experimental file changed. Supplementary training/provenance checks are recorded in `002-provenance.response.md` (167 checks, all passed). Input digests are in `reviewed-input-hashes.json`.

This audit can detect the reviewed implementation/data inconsistencies; it cannot prove historical execution against a malicious artifact author, establish that no omitted trial exists, certify real-world performance, or validate GPU inference beyond the saved execution evidence. Semantic assurance remains same-family/provisional. Deterministic replay results are directly reproducible.
