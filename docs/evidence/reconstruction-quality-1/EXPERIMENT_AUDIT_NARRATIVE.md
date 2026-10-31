# Narrative audit addendum

**Verdict: WARN — one low-priority evidence-attribution clarification. Same-family, provisional.**

No result-number, scientific-scope, or H1/H2 interpretation correction was found. The summary table is numerically correct. The narrative now makes the substantive qualifiers required by the original audit.

## N1: distinguish reported pre-training checks from independently inspected evidence

`docs/RECONSTRUCTION_QUALITY_RESULTS.md:131`–`:133` states precise local CPU/CUDA/focused/frontend/lint/CLI checks as pre-training facts. The corresponding raw pre-training logs were not supplied to this fresh reviewer. The executor confirms that the output was returned only in the parent tool transcript. The tracker is a repeated assertion, not an independent execution witness.

Qualify these sentences as **executor-reported pre-training checks recorded in the parent execution transcript**, not independently verified by this audit. If fresh verification logs are added, label them post-run; those logs cannot establish pre-training chronology. This is an attribution issue, not evidence of false test counts or failed acceptance, and it does not weaken the independently verified experiment measurements.

## Passed checks

- Independently regenerated all 10 table data rows in each file from the 67 primary candidates. Every mean, sample SD, rounded number, Gaussian count and optimization time matched. Evidence: `docs/RECONSTRUCTION_QUALITY_RESULTS.md:37` and `docs/evidence/reconstruction-quality-1/summary-table.md:1`.
- Verified the narrative totals, historical metrics and baseline deltas, all six quoted arm/control LPIPS deltas, selection, runtime totals, memory peaks and SSIM regression. In particular SH0's precise delta is 0.003954749243954818, correctly rounded to 0.00395.
- Verified eight linked analysis CSV/JSON/plot copies byte-for-byte; `acceptance.json` equals the separately reviewed `replay-result-v2.json`. All provenance fields, source/config/data hashes and historical catalog digest match the frozen protocol.
- Depth support conditioning is clearly explained (`docs/RECONSTRUCTION_QUALITY_RESULTS.md:31`); policy/count/time mediation is explicit (`:56`); negative and mixed results remain visible (`:63`); runtime is described as ordered local measurements (`:84`); failure labels correctly explain negative deltas (`:106`); validation exposure, temporal dependence and selection optimism are stated (`:124`).
- H1 is a qualified observed validation-LPIPS finding. H2 is a qualified whole-policy comparison at matched updates. Neither is presented as fixed-capacity causal attribution, universal fidelity improvement, or independent-test generalization.

The hosted-CI sentence at `docs/RECONSTRUCTION_QUALITY_RESULTS.md:133`–`:135` is supported: the public run identifies the sealed implementation commit and succeeds. All four public job pages report success: [run](https://github.com/phongviet/SimReady/actions/runs/41049601408), [CPU](https://github.com/phongviet/SimReady/actions/runs/41049601408/job/124042086301), [official sample](https://github.com/phongviet/SimReady/actions/runs/41049601408/job/124042085921), [geometry](https://github.com/phongviet/SimReady/actions/runs/41049601408/job/124042086298), [frontend/browser](https://github.com/phongviet/SimReady/actions/runs/41049601408/job/124042086219). These hosted statuses do not independently verify the earlier local pre-training counts.

Only this addendum's two response files were written. No original audit, source, narrative, dataset or experimental output was modified. The machine-readable response pins the exact document versions reviewed.
