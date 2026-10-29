# M5 acceptance criteria

- [x] Freeze acquisition methods, budgets, seeds, validation fit/check and test protocol.
- [ ] Freeze new held-out observations; disclose M3 test exposure and temporal overlap.
- [x] Verify train/validation/selector read boundaries and withheld-image release gates.
- [ ] Run three base models; calibrate only on validation and report independent checks.
- [ ] Seal all nine K=4 acquisitions before candidate-image release.
- [ ] Run nine fresh equal-budget 54-frame models and twelve common-test evaluations.
- [ ] Audit configs, counts, source/input/content hashes and raw predictions.
- [ ] E1 correlations/counterexamples, E2 novelty bins/pose blocks, E4 paired variability.
- [ ] Explicit undefined metrics, negative results, unknown regions and missing object GT.
- [ ] Reproducible figures, research report and working research dashboard.
- [ ] CPU/unit/browser checks and actual local GPU pipeline evidence.
- [ ] Confirm total storage below 30,000,000,000 bytes.

Status: implementation in progress; no M5 experiments or results yet.
Core regression after access guards:161 passed,2 opt-in GPU skips. The new runner
has separate targeted verification before its first real execution.
Frozen design: `refine-logs/EXPERIMENT_PLAN.md`, config `configs/recapture.json`.
Read boundaries use physically omitted candidate/test images in learner datasets.
The curator may copy/hash opaque bytes, which is not selection-algorithm access.
This is an auditable interface, not a sandbox against a malicious administrator.
