# SimReady improvement plan

Created 2026-10-31. This extends the implemented project; historical experiment
records, frozen splits and source pins remain immutable. Status: audit/design,
with no new independent-scene, densification or annotated-perception results yet.

## Current-state audit

React/Vite/Three.js/Spark provides scene selection, proxy editing, camera views,
validation, research summaries, navigation and scoped review. Python adapters
isolate CUDA training/rendering from API requests. The previous quality study
contains 24 actual training runs and 67 validation evaluations; its selected
configuration is L1+SSIM, 3,600 updates, SH1, depth L1 weight0.05, initial10k/cap40k,
refinement100–900/100, width320. This choice used exposed desk validation, not an
independent test. Existing data includes TUM fr1 desk, synthetic fixtures and an
authored annotated bench; the latter does not establish real-scene detection AP.

UI problems: green-tinted surfaces, competing header badges, a crowded workflow/
editing toolbar, wide three-column minimums and inconsistent contextual panels.
Some empty-state text incorrectly describes implemented simulation/review as
future milestones. Preserve existing account, edit, validation and review paths.

README problems: development narrative, milestone claims, long command lists,
personal resource policy and implementation details obscure the actual workflow.
Resource guards remain functional; developer records retain their historical
context. User-facing copy must describe measured compatibility rather than a
personal disk budget. Search results include README, architecture, CLI and old
acceptance records. Historical evidence will not be silently rewritten.

## Research specification and gates

1. Freeze the previous selected policy from its actual configuration/source hashes
   in a new study ID. Use two additional independent TUM sequences selected by
   metadata before viewing their held-out images. Prefer different capture paths
   and disclose shared rooms/sensors rather than calling them independent sites.
   Verify official URLs, bounded archive sizes, actual download SHA256, calibration,
   association and pose coverage before import. Freeze train/validation/test blocks
   before training. Do not reuse desk test results for choices.
2. Compare original1200 L1, matched-budget3600 L1, and frozen3600 L1+SSIM under
   identical frames, resolution, seed set42/43/44 and metric definitions. The middle
   control distinguishes budget from objective changes. No per-sequence tuning.
   Record all PSNR/SSIM/LPIPS/depth support/error, count, wall times and allocator
   peaks; include per-view images and failures. Evaluate frozen test only after
   training/configuration gates, never select using those measurements.
3. Desk validation-only densification: same3600 L1+SSIM policy, compare fixed
   windows100–900,100–1800,100–3000, every100; three seeds, same initialization,
   optimizer and cap. Existing reference outputs remain read-only; use fresh
   control runs. Report guard activation, realized counts, quality and cost, since
   nominal cap is not realized capacity. No cross-scene test-driven schedule tuning.
4. Detection accuracy requires trustworthy camera-aligned object annotations and
   explicit class/visibility/ignore conventions. Audit available sources/access
   before choosing one. A manually reviewed subset requires actual human review;
   model proposals cannot become ground truth by assertion. Implement AP50/recall
   with matching/duplicate/empty/ignore tests, record annotation provenance, and
   separate this benchmark from detector agreement. Data access/review is pending;
   do not publish AP claims from the authored fixture or unreviewed predictions.

Compute: reuse the validated isolated GTX1660Ti6GB environment, with fresh kernel
witness, serial GPU lock and the existing allocator guard. Initial matrix18
cross-sequence runs plus9 densification runs; estimate1–3 GPU/host hours including
full evaluation, not measured execution. Acquisition/output reserves must pass
existing storage checks before downloading or training. No environment rebuild
or automatic parameter reduction. Failed/negative arms remain in the ledger.

Acceptance: CPU contract/metric/leakage tests, actual CUDA smoke, clean execution
seal, immutable input/config/source hashes, complete planned arms, actual metric
replay and qualitative inspection. Each study gets a focused final protocol before
its first training dispatch. No study results are claimed by this planning file.

## Frontend design specification

Apply Anthropic frontend-design, Vercel web-design-guidelines and React best
practices using their actual upstream instructions. Local frontend-design exists
in the Claude plugin directory; upstream Vercel instructions were retrieved because
local copies were absent. Cached source URLs/hashes: .cache/improvement-skills/.
Writing-guidelines was not found; use the supplied precise technical-English rules.

Audience: a CV/robotics engineer diagnosing a reconstructed scene. The primary
surface is the actual viewport. Signature: camera/coordinate context stays attached
to the viewport while workflow navigation and property inspection remain peripheral.
Use sidebar-07's collapsible navigation/inset workspace structure, adapted to Vite;
no Next.js migration, template KPI rows or empty feature routes.

Tokens: canvas#15191f, panel#1c222b, raised#252d38, border#3b4654,
text#e6edf5, accent#83b8ef. Supporting muted text must meet contrast on its surface.
Inter for controls/body, system monospace only for numeric/code values;14px body,
12px metadata,18px scene title. Spacing4/8/12/16/24px; controls32–36px, touch44px;
radius3–6px, no decorative shadows/gradients. Main alignment is left, data numeric
columns right with tabular numerals. Focus rings remain prominent.

Desktop: compact application header, collapsible workflow rail/scene hierarchy,
large center viewport and contextual property inspector. Navigation maps actual
Scenes/Workspace/Validation/Experiments/Simulation functions; review remains
accessible. Keep scene persistence/unsaved-edit guards and camera tools. Mobile:
one main column, explicit panel toggles, usable camera fallback, no horizontal
page overflow or hidden critical actions. Avoid unmounting the expensive viewer
for unrelated inspector changes; retain lazy loading and add contextual Suspense
boundaries for other heavy views where appropriate.

Use compatible shadcn/Radix primitives and Tailwind utilities incrementally; retain
working rendering and data logic. First critique: a dashboard shell alone would
still be generic; remove decorative badges and let the viewport/camera evidence
establish hierarchy. Do not apply a palette-only redesign and call the UI complete.

Gates: baseline browser tests, shared token/component refactor, workflow views,
keyboard/focus/labels/status/empty/error checks, desktop+mobile screenshots,
actual screenshot critique/iteration, Vercel audit with file:line findings,
frontend tests/build and browser regressions. Screenshots must show executed UI.

## README and documentation

Rewrite README around introduction, genuine demo, concise implemented capabilities,
accurate architecture diagram, verified split-labeled results/negative findings,
CPU demo quick start, separate GPU guide, documentation and limitations. Keep
reconstruction models distinct from colliders and planar navigation from physics.
Use current application screenshots after visual verification; retain the genuine
recording with clear context meanwhile. Preserve detailed protocols in docs.

## Priorities and acceptance tracking

| Priority | Deliverable | Acceptance | Status |
|---|---|---|---|
| P0 | Audit/design and experiment boundaries | This plan precedes implementation | Written |
| P1 | Freeze research and verify data access | New IDs/pins/splits; annotation source resolved | Pending |
| P1 | Shared workstation design and navigation | Working features preserved; desktop/mobile screenshots | Pending |
| P1 | Independent-scene and densification studies | Complete actual measurements/replay/failures | Pending |
| P1 | Annotated perception | Trustworthy labels; AP50/recall tests and actual evaluation | Data/review pending |
| P2 | README/public-copy cleanup | Short verified setup, real visuals/results; guards unchanged | Pending |
| P2 | Final acceptance | CPU/GPU/frontend/browser checks, visual audit, progress/decisions | Pending |

Risks: annotation access/review; download provenance and calibration differences;
shared-site versus independent-site claims; runtime/count confounding; unknown
viewer compatibility with new UI dependencies; mobile WebGL resource limits;
historical scientific records versus public documentation cleanup. Report blockers
specifically and continue independent work without inventing evidence.

References: https://ui.shadcn.com/blocks (sidebar-07),
https://github.com/anthropics/skills/tree/main/skills/frontend-design,
https://github.com/vercel-labs/agent-skills,
https://cvg.cit.tum.de/data/datasets/rgbd-dataset/download.
