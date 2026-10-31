# Reconstruction confirmation and annotation workflow

The preregistered design is [INDEPENDENT_SCENE_PROTOCOL.md](INDEPENDENT_SCENE_PROTOCOL.md).
The primary execution is `experiments/engineering-improvement-1`, frozen at source
`1c2782bcca3d08ef775077a2384114aaef83f44f`. It contains two additional TUM recordings,
three fixed policies and three seeds, plus three refinement schedules and three
seeds on the original desk validation split. This is27 training jobs and45
checkpoint evaluations. No configuration is selected on the new test splits.

## Reproduction

Use the CPU environment and the separately verified worker in [GPU_SETUP.md](GPU_SETUP.md).
All commands below run from the repository root. Acquisition and import scripts
reuse only hash-matching inputs; experimental output paths must be new.

```bash
uv run --frozen python scripts/fetch_improvement_data.py
uv run --frozen python scripts/import_improvement_data.py
uv run --frozen python scripts/run_improvement_studies.py freeze --root experiments/engineering-reproduction-1
uv run --frozen python scripts/run_improvement_studies.py run --root experiments/engineering-reproduction-1
uv run --frozen python scripts/analyze_improvement_studies.py --root experiments/engineering-reproduction-1 --out experiments/engineering-reproduction-1/analysis
```

Also prepare the original100-frame desk dataset using [CLI.md](CLI.md) before
freezing the study; it supplies the densification control. The import helper has
fixed canonical paths and an append-only acquisition ledger. The matrix and
analysis commands accept explicit paths/IDs. Reproducing the
original seal requires its exact experimental source, policy/specification bytes,
dataset records and recorded historical files. A fresh checkout can execute a
new study with its own observed source/history hashes; it does not recreate
missing historical artifacts merely by possessing the published summaries.
Use a clean source checkout to freeze a new protocol. The runner rejects altered
source, inputs or historical files; failed/interrupted stage IDs are retained
and require a new study ID. Do not modify a seal to force resumption.

The runner serializes GPU work on the existing evaluation-worker lock. Avoid
external GPU jobs during measurement. It checks resource limits before stages.
Allocator peaks are PyTorch observations, not total board utilization. Optimizer,
worker, adapter and evaluation time have different scopes. Runtime observations
are ordered on one local GPU, not randomized performance experiments.

Run the analysis command only after the full matrix completes. Its default root
is the original engineering-improvement-1 study; explicit paths above create a
separate reproduction. The analyzer checks model/evaluation bindings and every declared split frame,
exports per-run quality/runtime/memory tables, seed means/sample SD, paired
same-seed deltas and fixed worst-LPIPS diagnostics. It lists incomplete arms
rather than treating them as successful measurements. Never overwrite an
existing analysis directory. New diagnoses belong in a separately hashed export.

## Workstation presentation

The frontend presentation exporter only reads the frozen protocol and ledgers.
It never starts, cancels or configures training. From a built checkout:

```bash
npm --prefix frontend run research:publish -- --watch
```

This writes ignored snapshots under `frontend/public/research/` and
`frontend/dist/research/`. The Experiments → Reconstruction view refreshes that
snapshot and shows its actual export time. Stopping the exporter leaves a dated
snapshot, not a claim of live monitoring. Final metrics are withheld until all
planned jobs/evaluations finish and the analysis manifest hashes match. The
original Recapture view and its measured negative results remain accessible.
Frontend changes are outside the experiment's source hash scope; actual model
artifact commit/dirty metadata remain recorded. No measurement-source drift is
permitted by this presentation workflow.

## Human-reviewed detection accuracy

ScanNet access was not confirmed; no license restriction was bypassed. TUM
candidate pilots were checked for plausible vocabulary overlap. This is not a
human annotation-quality assessment. Read [ANNOTATION_PROTOCOL.md](ANNOTATION_PROTOCOL.md)
for the fixed class definitions and review rules.

The current draft packages each contain64 frozen evaluation frames:

- `artifacts/annotations/tum-fr1-room-v1/`
- `artifacts/annotations/tum-fr2-desk-v1/`

Serve them locally, then open the scene's review page:

```bash
python3 -m http.server 8090 --bind 127.0.0.1 --directory artifacts/annotations
```

A person must annotate/inspect every frame, correct every applicable box, mark
frames reviewed, download the current COCO bytes and explicitly attest approval.
Draft imports and edits invalidate review state. Empty boxes initially mean
**unannotated**, not verified negative frames. The separate approval file binds
reviewer attestation, exact COCO bytes, all frame IDs, dataset/split and rules.
This records an explicit human attestation; it is not cryptographic identity
verification. Neither a worker nor an agent issues that approval.

Install the optional CPU evaluator with `uv sync --frozen --extra annotations`.
`simready.annotations.evaluate.evaluate` compares complete, bound real
and rendered detector predictions using the same approved reference boxes at
matched poses. It exports official COCO AP50, recall, per-class counts and
misses, paired deltas and reconstruction metrics. Without valid human approval
it raises `pending_human_review` before computing accuracy. Detector-agreement
reports remain separate. Ground-truth results are pending until actual review;
small, temporally correlated samples will limit any eventual inference.
