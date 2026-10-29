# M5 acceptance criteria

- [x] Freeze acquisition methods, budgets, seeds, validation fit/check and test protocol.
- [x] Freeze new held-out observations; disclose M3 test exposure and temporal overlap.
- [x] Verify train/validation/selector read boundaries and withheld-image release gates.
- [x] Run three base models; calibrate only on validation and record independent check block.
- [x] Seal all nine K=4 acquisitions before candidate-image release.
- [x] Run nine fresh equal-budget 54-frame models and twelve common-test evaluations.
- [x] Audit configs, counts, source/input/content hashes and raw predictions.
- [x] E1 discrepancy correlations/counterexamples, E2 bins/blocks, E4 paired variability.
- [x] Explicit undefined metrics, negative results, unknown regions and missing object GT.
- [x] Reproducible figures, primary research report and working research dashboard.
- [x] CPU/unit/browser checks and actual local GPU pipeline evidence.
- [x] Confirm total storage below 30,000,000,000 bytes.
- [x] Controlled labeled-object E1 companion: true errors and agreement-versus-accuracy.
- [x] Recovered evaluations bind exact reference records and render-index hashes.
- [x] Atomic timestamped release-ledger completion and partial-operation recovery.

Primary case study verified: all45actual stages completed from clean6947fb8;
analysis from clean772e055. Fresh audit WARN, raw evidence pass, same-family
semantic acceptance provisional. Risk LPIPS is worse than random for all3seeds.
170CPU/geometry tests passed with2opt-in GPU skips;5frontend unit tests,
7actual browser tests, production build, lint and format checks passed. The
companion review is now complete: WARN, same-family/provisional, no invalidation.
The synthetic endpoint is saturated; its true-error relationship is unidentifiable.
Storage about15.55GB. See M5_RESULTS.md and EXPERIMENT_AUDIT.md.
Frozen design: `refine-logs/EXPERIMENT_PLAN.md`, config `configs/recapture.json`.
Read boundaries use physically omitted candidate/test images in learner datasets.
The curator may copy/hash opaque bytes, which is not selection-algorithm access.
This is an auditable interface, not a sandbox against a malicious administrator.
