# Frozen local recapture case study

The M5 hypothesis and controls are declared in
`refine-logs/EXPERIMENT_PLAN.md`; `configs/recapture.json` pins the supported
matrix. Neither superiority nor novelty is assumed. No labeled object truth
exists for the TUM capture, so detector agreement is not accuracy.

```bash
# Start from clean committed source; use a new output directory each study.
make storage
uv run --frozen simready research prepare --out experiments/tum-recapture-1
uv run --frozen simready research run --study experiments/tum-recapture-1 --phase acquire
uv run --frozen simready research run --study experiments/tum-recapture-1 --phase evaluate
make storage
```

After the raw matrix completes, analysis can use the current development tree:

```bash
uv sync --frozen --extra research
uv run --frozen --extra research simready research analyze \
  --study experiments/tum-recapture-1 --out experiments/tum-recapture-1/analysis-1
uv run --frozen python scripts/index_research_outputs.py --study experiments/tum-recapture-1
```

Analysis checks historical Git objects against the experiment's source pins,
replays saved RGB/depth/matching metrics and selections, and refuses overwrite.
It does not rerun neural inference or retrain successful models. For reproducing
the original raw study, check out its recorded6947fb8source and locked GPU setup;
post-run analysis additions do not silently replace that source on resume.
`research run` deliberately rejects source drift; a new implementation requires
a new study directory. Reports keep analysis source separate from training source.

Register a full analysis for the Research tab:

```bash
uv run --frozen simready research register --id tum-recapture-1 \
  --analysis experiments/tum-recapture-1/analysis-1
make studio
```

The CPU demo also seeds a small actual measured-summary snapshot. It visibly
omits raw prediction downloads/checkpoints; it is not a new CPU experiment or
the selected analytic editor scene. The original full study keeps all raw outputs.

The ready local GPU spec is3db6217d; reuse it per `GPU_SETUP.md`. No remote or
paid compute is configured. These commands run sequentially on the local GPU;
do not start other GPU jobs concurrently. `--phase all` runs both phases. A
study lock prevents two runners from executing the same study simultaneously.

Preparation verifies the official TUM archive digest and preserves the original
50 train /16 validation /16 candidate frames. It reserves18 additional raw late
pairs as new test views, excluding all original100timestamps and image hashes.
M3's test views were already inspected. The new observations are withheld, but
the same capture and nearby previously seen views remain a strong limitation.
This is not an independent scene or population-level blind benchmark.

The curator copies/hashes opaque bytes into `vault/`; learner directories contain
only allowed observations. Training reads training RGB-D; camera rendering reads
metadata only. Validation reads its16references; candidate features use public
poses and current-model alpha, with no candidate reference images. Risk uses
independently nearest translation and minimum full-SO(3) rotation across training
poses, clipped at0.5m/30degrees, plus fraction(alpha<0.1). Nonnegative ridge fits
the first8validation LPIPS values and reports checks on the remaining8. The
intercept is unpenalized; feature coefficients have ridge0.1. There is no tuning
after check/test exposure, including when calibration fails.

Three base models and all nine method/seed selections must finish before sealing.
The seal binds protocol, curation, base metadata and selection details. Only then
can each arm materialize its own four selected candidate RGB-D observations.
Only sealed studies can release test references; those references are excluded
from every training split. Risk/random/farthest models start fresh for1200steps
at320px and54train frames; base controls have50train frames. Same detector,
evaluation protocol and18test IDs/hashes apply to all12models.

`stages.json` records validated stage manifests, exact inputs, observed wall
durations and persistent failures. Resume checks hashes/configs and refuses to
overwrite successful outputs. A recovered output with missing stage metadata
has null timing; no duration is invented. `access-ledger.json` records curation,
sealing and releases. These are method-level audit records, not OS isolation or
an attestation against a malicious administrator. Keep the protocol, source hash
snapshot, datasets, trained artifacts, renders and predictions with the results.

Required remaining acceptance: actual runs, independent fairness/hash audit,
E1/E2/E4 analysis, figures, honest negative/failure discussion and dashboard.
No result is asserted by this protocol document.
