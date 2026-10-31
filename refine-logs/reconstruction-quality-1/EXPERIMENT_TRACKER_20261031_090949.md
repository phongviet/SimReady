# Reconstruction-quality study tracker

Study executed 2026-10-30; closure/re-verification 2026-10-31. Existing timestamped
snapshots preserve the status at their creation.

| Stage | Work | State |
|---|---|---|
| Specification | Hypotheses, controls, compute and acceptance frozen before training | DONE,  e1c56e3 |
| Implementation | Strict knobs, losses, snapshots, orchestration/reports | DONE, 15d783b; pre-training checks recorded in parent transcript |
| Baseline | Historical validation reference +three fresh 1200-step seeds | DONE, 4 evaluations; all-seed discrepancy supplement passes |
| Matrix | Seven arms × three seeds × three checkpoint budgets | DONE, 21 trajectories/63 evaluations; zero failed stages |
| Analysis | Full candidate table, validation-only selection, cost/quality plots, actual failure images | DONE, all 67 evaluations retained |
| Numeric replay | GT/reference pixels, RGB/depth/detector metrics, LPIPS aggregation, selection and provenance | DONE, 1,072 pairs;132 allowed observation files;5,458 historical files |
| Fresh audit | Primary evidence and narrative | WARN, same-family/provisional; all numeric checks pass, scope/support/count/runtime limits retained |
| Durable post-run checks | CPU/CUDA, lint/format, frontend and CLI logs | DONE, 189 CPU passes +4 actual CUDA passes; separate logs do not prove pre-training chronology |
| Storage/publication | Curated evidence and ignored raw output | DONE, about 20.7 GB including retained legacy temporary fixtures; curated records versioned; no new simulation/frontend features |

Results and qualifications: docs/RECONSTRUCTION_QUALITY_RESULTS.md.
Actual source/configuration hashes: docs/evidence/reconstruction-quality-1/provenance.json.
All91 stage records are complete. The immutable original automatic report and
signed failure selections remain unchanged; supplemental replay adds all-seed
baseline flags. No independent-test/generalization claim is made.
