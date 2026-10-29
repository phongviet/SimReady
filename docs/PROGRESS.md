# Progress

Actual execution: **2026-10-29 (Asia/Bangkok)**. User-requested Git dates across
June–October are documented in `DECISIONS.md`; they are not experiment timestamps.

**Correction found during M1:** Open3D's Redwood sample is synthetic ICL-NUIM,
not real capture. The earlier `real` importer label and corresponding M0 wording
below were incorrect. They are retained as historical execution records, with
classification explicitly superseded. New imports use `synthetic`; validators
reject the old mislabeled datasets/artifacts. Real-capture acceptance uses TUM.

## Initial inspection

Only `PLAN.md` and a Windows download metadata sidecar existed. There was no Git
repository, source, environment, tests, frontend or sample data. Environment and
exact tested package versions are recorded in `ENVIRONMENT.md` and the lockfiles.

## Milestones

- [x] **M0 complete locally:** repo bootstrap, typed versioned data/scene contracts,
  camera math, analytic fixture, official real RGB-D import, frozen splits, tests,
  frontend shell, CI configuration and documented acceptance.
- [ ] M1: reconstruction (in progress after expanded authorization; see M1_CHECKLIST.md).
- [ ] M2: geometry and editing (not started).
- [ ] M3: perception validation (not started).
- [ ] M4: simulation and review (not started).
- [ ] M5: research experiments (not started).
- [ ] M6: shipping (not started).
- [ ] M7: optional integrations (not started).

Detailed acceptance criteria: [M0 checklist](M0_CHECKLIST.md).

## Verified commands and evidence

| Command/check | Actual outcome |
|---|---|
| `make setup` | Locked Python sync and clean `npm ci` passed |
| `make test` | 80 Python tests passed (including real input), 1 frontend test passed, TypeScript/Vite production build passed; Ruff lint and format checks passed |
| `make demo` | Eight-frame analytic fixture validates; 4/1/1/2 splits |
| `make test-real` | Official sample validated; real integration test passed, 79 deselected |
| Fresh `simready data import` into `data/scenes/redwood-m0-verified` | Five real RGB-D pairs imported, validated; supplied estimated poses and 2/1/1/1 frozen splits |
| CLI error and repeat-import checks | Automated tests confirm exit 2, actionable errors and no overwrite |
| Known point projection | Camera point (0.4,-0.2,2)m projects to pixel (419.5,199.5) for declared test calibration |
| Transform/pixel round trips | Float64 tests pass at 1e-12 absolute tolerance; proper rotation checks reject invalid poses |
| Live local Vite HTTP smoke | `/`, `/src/main.tsx`, `/src/App.tsx` returned HTTP 200 with expected content; server stopped afterward |
| `npm audit` after dependency updates | Zero vulnerabilities reported at verification time |
| `uv lock --check`, `git diff --check` | Passed |
| `make storage` | About 0.30 GB including .git/.venv/node_modules/caches/data; below 30 GB decimal |

The official ZIP is 3,772,513 bytes and matched the publisher MD5 plus pinned
SHA-256. Raw data and imported scenes remain local and gitignored. Small actual
validation outputs are saved in [evidence](evidence/m0-provenance.json), with
[real-sample validation](evidence/redwood-validation.json) and
[synthetic validation](evidence/synthetic-validation.json). These are integrity
counts/hashes, not reconstruction quality or experimental results.

Development proceeded through bootstrap, camera/contracts (54 passing tests),
real import/adversarial checks (79 passing tests), then a four-frame split boundary
regression (final 80 passing tests) and frontend/CI acceptance. The four-frame
allocation was fixed rather than weakening nonempty split checks. The final
source tree retains every test.

## Limits and next task

Hosted CI has not run: there is no configured remote and nothing was published.
The UI is only a scope shell; HTTP smoke is not a visual/browser interaction test.
Real sample timing uses indices, world-up is nominal, odometry is supplied/estimated,
data redistribution terms remain unverified, and adjacent tiny split blocks are
not statistically independent. See `DATASET_PROTOCOL.md` and `LIMITATIONS.md`.

No reconstruction, perception metrics, navigation, approval or recapture
experiments exist. No experimental results are reported.

## Full-project continuation

The user subsequently authorized completing the full project. M0 evidence above
is historical. M1 now has an isolated Python3.10 / torch2.4.1+cu124 /
gsplat1.5.3+pt24cu124 worker, with an actual CUDA render/backward witness and a
fresh-agent documentation pass. A 40-iteration synthetic Redwood RGB-D smoke run
produced 1,283 learned Gaussians from 935 training-only depth points, exported
PLY/NPZ, and reloaded to render a validation pose. This is an integration result,
not a reconstruction-quality finding. A separate 1,200-iteration synthetic run
produced 9,187 Gaussians and rendered a frozen test pose; its original metadata
was wrongly labeled real and is rejected by the corrected validator. It does
not satisfy real-capture acceptance. The CPU suite passed 93 tests before the
optional GPU integration test was added; later non-GPU checks passed 105 tests,
with real TUM integration explicitly skipped pending its live download. Full
M1 acceptance is still in progress.

Scope/status descriptions elsewhere referring to M0 only are historical and are
being updated incrementally. M2+ remain unimplemented. No perception metrics,
navigation, approval or recapture experiments have run.
