# SimReady

Implementation in progress: **Milestone M0 only**. `PLAN.md` is the project
specification. Reconstruction, scene editing, perception evaluation, simulation,
and review workflows are planned in later milestones and are not implemented.

The M0 slice establishes a CPU-only RGB-D import/validation package, explicit
camera conventions, synthetic fixtures, immutable splits, and a frontend shell.
See `docs/PROGRESS.md` for acceptance evidence and current status.

## Setup

Python 3.12, uv, Node 20.19+ and npm are required.

```bash
make setup
make test
make demo
make storage
```

The environment is locked in `uv.lock` and `frontend/package-lock.json`.
Raw data and build outputs are ignored by Git. The full working project has a
30 GB decimal storage limit. Downloads are optional and bounded.

Git author and committer dates for the initial M0 commits are intentionally
assigned across June–October 2026 at the user's request. Development and
verification actually occurred on October 29, 2026; dates are not evidence of
months of work. See `docs/DECISIONS.md`.
