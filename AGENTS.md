# Working agreement

- Read `PLAN.md` as the specification. The user has now authorized completing the
  full project. Advance through M1–M6 with verified milestone gates; M5 research
  and M7 integrations retain the priorities/conditions in PLAN.md.
- Implement incrementally; run CPU tests, lint, frontend checks, and CLI smoke tests
  before claiming acceptance. Update `docs/PROGRESS.md` and `docs/DECISIONS.md`.
- Never label fixtures as reconstructions or invent metrics/experimental results.
- Use meters, right-handed Y-up world coordinates, OpenCV camera axes, and explicit
  camera-to-world transforms. Preserve provenance and immutable split hashes.
- Keep raw data, generated scenes, caches, dependencies, and build outputs out of Git.
- Total project storage must stay below **30,000,000,000 bytes (30 GB)**, including
  `.git`, `.venv`, `node_modules`, caches, downloads, and generated assets. Run
  `make storage` before and after large operations; respect acquisition limits.
- Keep GPU packages in the isolated `.venv-gpu`, separate from the CPU `.venv`.
  Before installation, check storage and record the compute spec and ledger.
  Do not claim a GPU environment works until an actual kernel/render witness runs.
- Make focused commits. The initial M0 history uses user-requested June–October
  2026 author/committer dates; actual execution is recorded in the docs. Future
  commits should use actual dates unless explicitly requested otherwise.

## Local compute

- Local WSL2 GPU: GTX 1660 Ti, 6 GB. No remote GPU is configured.
- Worker environment: `.venv-gpu`; declarative spec `configs/compute-gpu.json`.
- Local environment ledger: `.aris/compute/local.md`; setup instructions in
  `docs/GPU_SETUP.md`. W&B and external notifications are not configured.
