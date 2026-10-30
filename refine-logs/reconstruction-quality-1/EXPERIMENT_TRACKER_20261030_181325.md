# Reconstruction-quality study tracker

| Stage | Purpose | Planned work | State |
|---|---|---|---|
|spec|Freeze questions, controls, matrix and access rules|EXPERIMENT_PLAN.md|written before training|
|implementation|Strict training knobs, loss math, snapshots, study orchestration/report|CPU + GPU smoke/regression|not started|
|baseline|Original-model validation + three fresh1200 baselines|4 validation evaluations|not run|
|matrix|Seven arms ×three seeds ×three checkpoints|21 trajectories/63 evaluations|not run|
|analysis|Validation-only selection, cost tables, actual failure figures|Read-only artifact replay|not run|
