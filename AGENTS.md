# Working agreement

- Read `PLAN.md` as the specification. Current authorized scope is **M0 only**.
- Implement incrementally; run CPU tests, lint, frontend checks, and CLI smoke tests
  before claiming acceptance. Update `docs/PROGRESS.md` and `docs/DECISIONS.md`.
- Never label fixtures as reconstructions or invent metrics/experimental results.
- Use meters, right-handed Y-up world coordinates, OpenCV camera axes, and explicit
  camera-to-world transforms. Preserve provenance and immutable split hashes.
- Keep raw data, generated scenes, caches, dependencies, and build outputs out of Git.
- Total project storage must stay below **30,000,000,000 bytes (30 GB)**, including
  `.git`, `.venv`, `node_modules`, caches, downloads, and generated assets. Run
  `make storage` before and after large operations; respect acquisition limits.
- No GPU packages, model weights, simulator downloads, or M1+ features in M0.
- Make focused commits. The initial M0 history uses user-requested June–October
  2026 author/committer dates; actual execution is recorded in the docs. Future
  commits should use actual dates unless explicitly requested otherwise.
