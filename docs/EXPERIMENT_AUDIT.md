# M5 experiment integrity audit

Fresh GPT-6-Astra ultra; same-family, provisional semantic review.
Historical execution source: `6947fb837b726c54dd4f4b2b17482dd9447ba857`.
References below identify the audited snapshot; later analysis/documentation changes are separate.
The initial usage-limit error and full reviewer trace are preserved locally under `.aris/traces/experiment-audit/2026-10-29_run01/`.

**Overall verdict: WARN. Integrity status: warn. Raw experiment evidence: PASS.**

No experimental-invalidating issue was found in the completed M5 study. The warnings concern its limited scientific scope, locally recorded chronology, and future recovery hardening. Missing analysis, figures, and dashboard work are deliverable gaps—not evidence that the completed experiments are invalid.

Auditor: `/root/m5_integrity_audit`, fresh read-only reviewer on the requested GPT-6-Astra ultra route. Review independence is **same-family**; semantic acceptance remains **provisional**. Supplemental resume review: `/root/m5_integrity_audit/audit_resume_check`. No repository files or experiment outputs were modified.

**Reviewed evidence and deterministic verification**

I read every indexed source file and programmatically inspected every indexed run/result record. All **163 indexed files** matched their supplied SHA-256 pins, including a final recheck. The complete reviewed inventory is [paths.json](/home/phong/simready/.aris/traces/experiment-audit/2026-10-29_run01/paths.json); its content pins are [audited-input-hashes.json](/home/phong/simready/.aris/traces/experiment-audit/2026-10-29_run01/audited-input-hashes.json).

The independent checks verified:

- **200 RGB/depth files** in the curator vault byte-match the pinned TUM archive. All 100 study poses and timestamps reproduce the deterministic association/selection procedure.
- The **18 new test RGB hashes, depth hashes, and respective timestamps** are disjoint from all 100 original observations.
- **12 trained artifacts**, with distinct checkpoint hashes, valid tensors, complete sampled training logs ending at step 1199, and the declared configurations.
- **636 training image/depth tensor pairs** exactly match only their declared training observations.
- **18 render batches**, including 936 indexed rendered RGB/depth/alpha files, pass hash, shape, and numerical validity checks.
- **15 evaluations**, covering **264 paired view records**, pass validation of 2,013 indexed evaluation files. RGB/depth/detection metrics and summary aggregations reproduce from saved images, depth arrays, and predictions.
- All **12 test evaluations** use identical cameras, reference input hashes, and real-image detector predictions.
- All **nine acquisitions**, three validation calibrations, feature values, rankings, and selected IDs reproduce.
- All **45 stage records** match their input digests, output manifests, and logged verified entries. There are **zero recorded failures and zero recovered stages**.

LPIPS inference and training were **not rerun** during this read-only audit. I verified their saved outputs, code paths, logs, package/weight provenance, and downstream aggregation; this is not a fresh neural-inference reproduction.

**A. Ground truth/reference provenance — PASS**

RGB and depth references come from the real TUM capture, rather than reconstruction outputs. Curation checks the pinned archive, retains the original allowed partitions, and deterministically extracts new late-frame observations. See [research/data.py:52](/home/phong/simready/src/simready/research/data.py:52), [research/data.py:108](/home/phong/simready/src/simready/research/data.py:108), and [curation.json:2](/home/phong/simready/experiments/tum-recapture-1/curation.json:2).

Evaluation loads reference RGB/depth from the frozen dataset and separately loads reconstructed RGB/depth from render artifacts: [evaluation/runner.py:105](/home/phong/simready/src/simready/evaluation/runner.py:105), [evaluation/runner.py:175](/home/phong/simready/src/simready/evaluation/runner.py:175).

Detector “real” boxes are model predictions on real photographs. They are **not object annotations**. The code applies the same detector to both domains, and the reports explicitly deny accuracy/mAP claims: [perception_worker.py:118](/home/phong/simready/workers/perception_worker.py:118), [evaluation/runner.py:291](/home/phong/simready/src/simready/evaluation/runner.py:291), [risk-s42-test/summary.json:137](/home/phong/simready/experiments/tum-recapture-1/evaluations/risk-s42-test/summary.json:137).

No fabricated object labels or model-derived RGB/depth ground truth were found. Mesh metrics remain null because aligned mesh truth is unavailable. The archive digest is a reproducibility pin, explicitly **not a publisher-signed digest**: [tum_fr1_desk.source.json:7](/home/phong/simready/configs/tum_fr1_desk.source.json:7).

This is a custom reconstruction case study using TUM observations, not a claim of official TUM trajectory-benchmark performance.

**B. Score normalization — PASS**

No performance metric is inflated by dividing it by its own maximum or mean.

RGB conversion uses the fixed uint8 range 255; PSNR/SSIM use declared image-domain conventions: [metrics.py:13](/home/phong/simready/src/simready/evaluation/metrics.py:13). LPIPS receives the declared `[-1,1]` transformation: [perception_worker.py:96](/home/phong/simready/workers/perception_worker.py:96).

Depth MAE/RMSE use finite positive reference/predicted depth with alpha ≥ 0.1. Completeness separately divides evaluated pixels by valid **reference** pixels: [metrics.py:24](/home/phong/simready/src/simready/evaluation/metrics.py:24). Depth error therefore remains conditional on support and must continue to be reported alongside completeness.

Detector outputs retain raw counts, matches, confidence gaps, and per-class counts. Localization normalization uses image dimensions: [metrics.py:99](/home/phong/simready/src/simready/evaluation/metrics.py:99). Standard IoU normalization is not evidence of self-normalized performance.

Risk features use fixed physical scales and a fixed image-pixel denominator, not fitted score extrema: [selection.py:116](/home/phong/simready/src/simready/research/selection.py:116), [research/runner.py:173](/home/phong/simready/src/simready/research/runner.py:173).

All saved RGB/depth/detection metrics and their equal-view summary means reproduced.

**C. Result existence and agreement with claims — PASS**

The tracker’s completed-run claims are supported: three base runs, nine acquired-data runs, nine sealed selections, and 45 pipeline stages. Its analysis row remains TODO, and it does not assert superiority: [EXPERIMENT_TRACKER.md:7](/home/phong/simready/refine-logs/EXPERIMENT_TRACKER.md:7).

All models use seeds 42/43/44, 1200 fresh optimization steps, width 320, 10,000 initial Gaussians, and the same configured maximum/optimizer scheme. Base models use 50 frames; acquired arms use exactly 54. Training initializes from allowed RGB-D and does not load a base checkpoint: [gsplat.py:100](/home/phong/simready/src/simready/reconstruction/gsplat.py:100), [gsplat_worker.py:119](/home/phong/simready/workers/gsplat_worker.py:119).

Verified test LPIPS values are:

| Method | Seed 42 | Seed 43 | Seed 44 | Mean ± sample SD |
|---|---:|---:|---:|---:|
| Base | 0.410655 | 0.417889 | 0.397184 | 0.408576 ± 0.010508 |
| Risk | 0.427938 | 0.414602 | 0.406233 | 0.416258 ± 0.010947 |
| Random | 0.414044 | 0.403663 | 0.386890 | 0.401532 ± 0.013702 |
| Farthest | 0.426405 | 0.411706 | 0.394321 | 0.410811 ± 0.016061 |

Each value is stored at line 149 of its respective test summary, for example [risk-s42](/home/phong/simready/experiments/tum-recapture-1/evaluations/risk-s42-test/summary.json:149), [random-s42](/home/phong/simready/experiments/tum-recapture-1/evaluations/random-s42-test/summary.json:149), [base-s42](/home/phong/simready/experiments/tum-recapture-1/evaluations/base-s42-test/summary.json:149), and [farthest-s42](/home/phong/simready/experiments/tum-recapture-1/evaluations/farthest-s42-test/summary.json:149). The table aggregates verified outputs; it is not a claim already present in the tracker.

The 50-file historical source snapshot matches Git objects at clean commit `6947fb837b726c54dd4f4b2b17482dd9447ba857`: [run-source.json:2](/home/phong/simready/experiments/tum-recapture-1/run-source.json:2). Saved evaluation source hashes agree with this snapshot. All three actual pretrained weight files match [perception-weights.json](/home/phong/simready/configs/perception-weights.json).

Current post-run changes to `src/simready/cli.py` and `uv.lock`, plus new analysis files, are outside the historical execution. They do not retroactively invalidate it. Reproduction must use the recorded source/environment rather than silently substituting the current development tree.

**D. Dead evaluation code — PASS for the audited M5 pipeline**

The defined RGB, depth, detection, matching, calibration, and acquisition functions are called by the executed pipeline, and their outputs appear in saved artifacts:

- RGB/depth/detection execution: [evaluation/runner.py:170](/home/phong/simready/src/simready/evaluation/runner.py:170).
- LPIPS and detector inference: [perception_worker.py:112](/home/phong/simready/workers/perception_worker.py:112).
- Validation fitting and candidate selection: [research/runner.py:329](/home/phong/simready/src/simready/research/runner.py:329).
- Summary construction: [evaluation/runner.py:242](/home/phong/simready/src/simready/evaluation/runner.py:242).

All 15 inference logs contain the corresponding 16 or 18 inferred-view entries. The per-view metrics, calibration outputs, and summaries reproduce. Null Chamfer/F-score fields are explicit unavailable measurements, not phantom computations.

**E. Scope and supported conclusions — WARN**

The evidence covers **one real TUM capture**, three optimization seeds, one reconstruction budget, one fixed detector, 16 validation views, 16 candidate poses, and 18 correlated new test observations. It does not constitute independent-scene replication or evidence about real robot performance.

Existing scope language is appropriately limited: [protocol.json:43](/home/phong/simready/experiments/tum-recapture-1/protocol.json:43), [EXPERIMENT_PLAN.md:19](/home/phong/simready/refine-logs/EXPERIMENT_PLAN.md:19), [summary.json:135](/home/phong/simready/experiments/tum-recapture-1/evaluations/risk-s42-test/summary.json:135). **No existing inflated novelty or comprehensive-evaluation claim was found.** WARN records the limit on future conclusions.

The prespecified H1 is **not supported**: risk-minus-random LPIPS is positive for every seed:

`[0.0138943311, 0.0109391908, 0.0193429771]`

Mean difference: **+0.0147254997**, sample SD **0.0042631018**; lower LPIPS is better. This is a negative acquisition result, not an integrity failure.

All three fitted models set distance and rotation coefficients to zero; their ranking therefore reduces to the alpha-hole feature. See [risk-s42 selection:40](/home/phong/simready/experiments/tum-recapture-1/selection/risk-s42.json:40) and the corresponding seed-43/44 records. Validation-check Spearman values are approximately 0.5952, 0.5000, and 0.4762 across only eight views each. These do not establish calibrated uncertainty or acquisition benefit.

**F. Evaluation classification — PASS**

| Evaluation | Classification | Meaning |
|---|---|---|
| Held-out RGB, LPIPS, depth comparison | `real_gt` | References are dataset sensor observations; LPIPS is a learned discrepancy metric, and depth remains noisy sensor evidence. |
| Detector agreement | `synthetic_proxy` | The reference boxes are model-generated predictions on real images, explicitly not annotations or detection accuracy. |
| Candidate risk/coverage score | `self_supervised_proxy` | Heuristic features calibrated to validation reconstruction discrepancy; no independent “true risk” labels. |
| Analytic fixture code | `simulation_only` | Explicit integration fixture; not counted as a second real scene in this experiment matrix. |
| Human judgment | Not present | No human-evaluation result was verified or claimed. |

Evidence: [evaluation/runner.py:175](/home/phong/simready/src/simready/evaluation/runner.py:175), [perception_worker.py:123](/home/phong/simready/workers/perception_worker.py:123), [selection.py:139](/home/phong/simready/src/simready/research/selection.py:139), [synthetic.py:18](/home/phong/simready/src/simready/data/synthetic.py:18).

**Leakage boundary, chronology, and resume**

The completed study passes the **declared method-level** leakage boundary:

- Training reads only training observations; rendering reads metadata: [gsplat.py:102](/home/phong/simready/src/simready/reconstruction/gsplat.py:102), [gsplat.py:287](/home/phong/simready/src/simready/reconstruction/gsplat.py:287).
- Calibration fits `frame_00050`–`frame_00057`; checks use `frame_00058`–`frame_00065`. All three calibrations reproduce exactly: [selection.py:144](/home/phong/simready/src/simready/research/selection.py:144), [risk-s42 selection:5](/home/phong/simready/experiments/tum-recapture-1/selection/risk-s42.json:5).
- All nine choices are sealed before releases; releases validate the seal and named acquisition: [research/runner.py:395](/home/phong/simready/src/simready/research/runner.py:395), [research/data.py:202](/home/phong/simready/src/simready/research/data.py:202).
- The ledger records curator → seal → nine candidate releases → ten test releases: [access-ledger.json:111](/home/phong/simready/experiments/tum-recapture-1/access-ledger.json:111).
- Protocol creation was **11:24:08 UTC**, before first training at **11:24:36**. Final candidate rendering completed at **11:26:28**; the acquire log records the seal before the evaluate log begins test rendering at **11:27:31**: [protocol.json:2](/home/phong/simready/experiments/tum-recapture-1/protocol.json:2), [acquire.log:1](/home/phong/simready/experiments/tum-recapture-1/acquire.log:1), [acquire.log:24](/home/phong/simready/experiments/tum-recapture-1/acquire.log:24), [evaluate.log:1](/home/phong/simready/experiments/tum-recapture-1/evaluate.log:1).

Chronology remains locally recorded evidence. Release events lack timestamps and are not immutable external attestations. The audit cannot prove absence of out-of-interface access to the vault. This limitation is already disclosed in [RECAPTURE_PROTOCOL.md:51](/home/phong/simready/docs/RECAPTURE_PROTOCOL.md:51).

Normal resume checks input hashes, manifest hashes, source drift, and missing outputs: [research/runner.py:120](/home/phong/simready/src/simready/research/runner.py:120), [research/runner.py:200](/home/phong/simready/src/simready/research/runner.py:200). Every saved evaluation’s model/render input hashes match its actual current artifacts.

Two **future hardening** issues were found; neither affected this execution:

1. Missing-stage recovery validates an existing evaluation’s protocol/model/split but does not explicitly compare its saved render-index hash against the currently requested renders. Add that comparison at [research/runner.py:290](/home/phong/simready/src/simready/research/runner.py:290).
2. Release ledger writes are nonatomic; candidate events occur after materialization while test events occur before linking completes. Use atomic timestamped begin/completed events and recovery reconciliation: [research/data.py:225](/home/phong/simready/src/simready/research/data.py:225), [research/data.py:236](/home/phong/simready/src/simready/research/data.py:236), [research/data.py:257](/home/phong/simready/src/simready/research/data.py:257).

**Action items and claim impact**

- Preserve the raw study and historical source pins. Do not rerun successful arms to improve scores.
- Report H1 as unsupported in this capture; retain all paired seeds and the zero distance/rotation coefficients.
- Complete the planned E1/E2/E4 analysis, failure figures, and dashboard before claiming M5 complete.
- Keep detector agreement separate from accuracy and report depth errors with completeness.
- Apply recovery/ledger hardening to future execution code without rewriting this study’s historical records.

Structured verdict:

```json
{
  "audit_skill": "experiment-audit",
  "verdict": "WARN",
  "overall_verdict": "warn",
  "integrity_status": "warn",
  "raw_evidence_verdict": "pass",
  "experimental_invalidating_findings": [],
  "reason_code": "limited_scope_local_chronology_and_future_recovery_hardening",
  "summary": "The completed M5 raw experiment is internally consistent and traceable. No leakage through the declared pipeline, fabricated ground truth, score inflation, phantom run, or metric mismatch was found. Scientific conclusions remain limited to one correlated capture; risk acquisition is worse than random on LPIPS for all three seeds.",
  "agent_id": "/root/m5_integrity_audit",
  "verdict_id": "/root/m5_integrity_audit:2026-10-29T14:08:45Z",
  "supplemental_reviewer": "/root/m5_integrity_audit/audit_resume_check",
  "reviewer_model": "gpt-6-astra",
  "reviewer_reasoning": "ultra",
  "reviewer_family": "openai",
  "review_independence": "same-family",
  "acceptance_status": "provisional",
  "generated_at": "2026-10-29T14:08:45Z",
  "date": "2026-10-29",
  "read_only": true,
  "trace_path": ".aris/traces/experiment-audit/2026-10-29_run01/",
  "reviewed_paths_ref": ".aris/traces/experiment-audit/2026-10-29_run01/paths.json",
  "complete_audited_input_hashes_ref": ".aris/traces/experiment-audit/2026-10-29_run01/audited-input-hashes.json",
  "audited_input_count": 163,
  "audited_input_hash_mismatches": [],
  "audited_input_hashes": {
    ".aris/traces/experiment-audit/2026-10-29_run01/paths.json": "sha256:9a87b1d28a47d11af74a84b700a3c21d059c4cece27291254c7b79984db36530",
    ".aris/traces/experiment-audit/2026-10-29_run01/audited-input-hashes.json": "sha256:c129110d12db9e04b27da92901e680fa008833d9e4111581976749901876b1d0",
    "experiments/tum-recapture-1/protocol.json": "sha256:20a86410c4efd96777e6300f86ec7d148d8fca5419bce4c1539bc3c601a56912",
    "experiments/tum-recapture-1/curation.json": "sha256:a236722d59f8466554509efdaf0cdae2658d3577c7b48fc0eff4b40c24e3f8ec",
    "experiments/tum-recapture-1/selections-sealed.json": "sha256:7cbf5f76d68ecb14a5ccb2c867aa7197c22aeee976bae2f86c79dcf2791e866c",
    "experiments/tum-recapture-1/run-source.json": "sha256:e9e4e5fb4008510cb6ffdb65c6337f8d6cee4d2d9bbcb8edbd80a58131c9cf00",
    "experiments/tum-recapture-1/stages.json": "sha256:7d08d479ae65dff37495e8be93b33f29574e1e62bd4d683c3c9b068dfeecbeff"
  },
  "historical_source": {
    "commit": "6947fb837b726c54dd4f4b2b17482dd9447ba857",
    "recorded_dirty": false,
    "verified_source_files": 50,
    "git_object_hash_verification": "pass",
    "current_post_run_drift_in_recorded_files": [
      "src/simready/cli.py",
      "uv.lock"
    ],
    "impact": "No retrospective invalidation; reproduce with recorded source."
  },
  "verified_counts": {
    "real_captures": 1,
    "optimization_seeds": 3,
    "methods": 4,
    "trained_models": 12,
    "distinct_checkpoint_hashes": 12,
    "render_batches": 18,
    "evaluations": 15,
    "paired_evaluation_views": 264,
    "unique_test_views": 18,
    "vault_images_compared_to_archive": 200,
    "training_rgbd_tensor_pairs_compared": 636,
    "render_file_hash_checks": 936,
    "evaluation_file_hash_checks": 2013,
    "completed_stages": 45,
    "recorded_failures": 0,
    "recovered_stages": 0
  },
  "checks": {
    "gt_provenance": {
      "status": "pass",
      "details": "Real RGB-D references byte-match the pinned TUM archive. Detector references are explicitly declared model predictions, not annotations.",
      "evidence": [
        "src/simready/research/data.py:52",
        "src/simready/evaluation/runner.py:105",
        "src/simready/evaluation/runner.py:175",
        "workers/perception_worker.py:123",
        "experiments/tum-recapture-1/evaluations/risk-s42-test/summary.json:137"
      ]
    },
    "score_normalization": {
      "status": "pass",
      "details": "No own-output maximum/mean normalization inflates performance. RGB range, geometric scales, masks, completeness denominators and view aggregation are explicit; saved values reproduce.",
      "evidence": [
        "src/simready/evaluation/metrics.py:13",
        "src/simready/evaluation/metrics.py:24",
        "src/simready/evaluation/metrics.py:99",
        "src/simready/evaluation/runner.py:242",
        "src/simready/research/selection.py:116"
      ]
    },
    "result_existence": {
      "status": "pass",
      "details": "All four methods and three seeds exist with fixed budgets and common test cameras. Tracker DONE claims match outputs; analysis remains explicitly TODO.",
      "evidence": [
        "refine-logs/EXPERIMENT_TRACKER.md:7",
        "experiments/tum-recapture-1/stages.json:2",
        "src/simready/reconstruction/gsplat.py:100",
        "workers/gsplat_worker.py:119",
        "src/simready/evaluation/runner.py:28"
      ]
    },
    "dead_code": {
      "status": "pass",
      "details": "Audited metric, inference, calibration and selection functions are called and have saved outputs. RGB/depth/detection calculations and calibration/selection replay succeeded. Neural inference was not rerun.",
      "evidence": [
        "src/simready/evaluation/runner.py:170",
        "workers/perception_worker.py:112",
        "src/simready/research/runner.py:329"
      ]
    },
    "scope": {
      "status": "warn",
      "details": "One temporally correlated capture and three optimization seeds support a qualified case study only. Existing text is appropriately limited. H1 is unsupported: risk has higher LPIPS than random for every seed.",
      "evidence": [
        "refine-logs/EXPERIMENT_PLAN.md:19",
        "experiments/tum-recapture-1/protocol.json:43",
        "experiments/tum-recapture-1/evaluations/risk-s42-test/summary.json:149",
        "experiments/tum-recapture-1/evaluations/risk-s43-test/summary.json:149",
        "experiments/tum-recapture-1/evaluations/risk-s44-test/summary.json:149"
      ]
    },
    "eval_type": {
      "status": "pass",
      "classification": {
        "rgb_lpips_depth": "real_gt",
        "detector_agreement": "synthetic_proxy",
        "candidate_risk": "self_supervised_proxy",
        "analytic_fixture": "simulation_only",
        "human_eval": "not_present"
      },
      "details": "Detector synthetic_proxy denotes model-generated box references on real images, not a synthetic source capture.",
      "evidence": [
        "src/simready/evaluation/runner.py:175",
        "workers/perception_worker.py:123",
        "src/simready/research/selection.py:139",
        "src/simready/data/synthetic.py:18"
      ]
    }
  },
  "leakage_and_resume": {
    "declared_method_boundary": "pass",
    "validation_fit_check_separation": "pass",
    "all_selection_seal_before_release": "pass_with_local_record_limit",
    "training_excludes_validation_and_test": "pass",
    "current_saved_input_bindings": "pass",
    "completed_run_resume_records": "pass",
    "future_missing_stage_recovery": "warn",
    "external_chronology_attestation": "not_available"
  },
  "primary_lpips": {
    "seed_order": [42, 43, 44],
    "base": [0.41065486603313023, 0.4178885602288776, 0.3971835258934233],
    "risk": [0.4279378702243169, 0.4146023955610063, 0.406232828895251],
    "random": [0.4140435391002231, 0.4036632047759162, 0.38688985175556606],
    "farthest": [0.426405131816864, 0.4117058912913005, 0.39432112872600555],
    "risk_minus_random": [0.013894331124093773, 0.010939190785090092, 0.019342977139684914],
    "risk_minus_random_mean": 0.014725499682956259,
    "risk_minus_random_sample_sd": 0.004263101823009824,
    "lower_is_better": true
  },
  "claims": [
    {
      "id": "completed_fixed_budget_run_matrix",
      "impact": "supported"
    },
    {
      "id": "H1_risk_improves_lpips_more_than_random",
      "impact": "unsupported",
      "details": "Risk is worse for all three paired seeds in this capture."
    },
    {
      "id": "detector_accuracy_or_generalization",
      "impact": "unsupported",
      "details": "No object annotations or independent-scene replication; not asserted in audited claims."
    },
    {
      "id": "H2_and_E1_E2_diagnostic_conclusions",
      "impact": "pending_analysis"
    },
    {
      "id": "M5_complete",
      "impact": "not_established",
      "details": "Analysis, failure figures and dashboard remain deliverable work, not raw-experiment invalidation."
    }
  ],
  "action_items": [
    "Preserve raw outputs and historical pins; do not rerun successful arms to improve scores.",
    "Report the negative H1 outcome, paired seed values, and zero fitted distance/rotation coefficients.",
    "Complete E1/E2/E4 analysis, failure figures and dashboard before M5 acceptance.",
    "For future missing-stage recovery, compare saved evaluation render-index hashes with requested render artifacts.",
    "For future releases, use atomic timestamped begin/completed events and reconcile partial operations."
  ],
  "limits": [
    "Same-family semantic review is provisional.",
    "Training and neural inference were not rerun.",
    "Local ledgers and timestamps do not prove absence of access outside the declared interface.",
    "Archive provenance is a recorded HTTPS-download pin, not publisher-signed attestation.",
    "One correlated scene does not establish population significance, detector accuracy, real-robot validity, or method novelty.",
    "Post-run analysis additions were outside this frozen audit."
  ]
}
```
