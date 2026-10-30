# Fresh CPU demo acceptance

On2026-10-30 a detached clean checkout of `a407ddd` was created under
`.cache/m6-fresh-checkout`. It had its own `.venv`, `node_modules`, frontend build,
SQLite registry and demo assets. Python imports resolved to that checkout;
`torch` and `open3d` were absent. It reused package/browser download caches but
did not reuse the original installed environments, registry or build outputs.
An offline attempt failed on missing cached Ruff/Three archives; the normal
locked online install succeeded. An empty-cache/offline installation is not claimed.

A reviewer can run the regular path from a fresh checkout:

```bash
make setup
make demo
make studio
# Open http://127.0.0.1:8000 and use the locally generated Builder token.
```

See README for private local credential handling. The demo bundles an actual
learned analytic Gaussian model, saved renders, independent geometry and measured
report, plus a measured TUM research snapshot. The analytic scene is explicitly
synthetic. CPU smoke verifies421 Gaussians and two saved views; it does not train
or render Gaussian views on the CPU. Browser Spark rendering uses WebGL (software
SwiftShader in this acceptance), independently of the absent torch/CUDA worker.

Fresh checkout commands actually executed:

```bash
UV_CACHE_DIR=/home/phong/simready/.cache/uv uv sync --frozen
npm ci --cache /home/phong/simready/frontend/.npm-cache --no-audit --no-fund
npm test
npm run build
# From frontend, using an already installed shared Chromium binary:
PLAYWRIGHT_BROWSERS_PATH=/home/phong/simready/.cache/playwright npx playwright test
```

Frontend:5 tests passed; TypeScript/Vite production build passed. Browser:7 tests
passed in19.1s against a newly launched API and demo registry. They exercised:

- Actual Gaussian loading and nonuniform rendered pixels, orbit, proxy transform
  persistence/reload/delete, version conflict and saved-camera editing fallback.
- Paired report images, failure ranking and verified CSV/HTML downloads.
- Metric navigation execution, replay movement and hidden-collider failure.
- Measured negative research dashboard, provenance and exports.
- Separate local Reviewer approval/export and approval invalidation after edits.

The screenshot was visually inspected: the known metric box, collision mesh,
transform controls and overlay-only warning are visible without clipped controls.
These are automated local-role fixtures, not independent human review.

An additional actual subprocess evaluation request in this CPU checkout reached
persistent `failed` with `GPU worker is not installed; follow docs/GPU_SETUP.md`.
The existing saved report remained unchanged and readable. This is the expected
fallback boundary: viewing/editing/simulation/review work, fresh GPU inference
requires the separately installed environment. No CPU inference is fabricated.

Evidence: [structured results](evidence/m6-fresh-ui.json),
[inspected editor screenshot](evidence/m6-fresh-editor.png).
The frontend retains its visible large viewer-chunk build warning; upstream
Starlette TestClient deprecation also remains. Playwright terminated its server
at completion. The generated checkout remains ignored locally for reproducibility;
its dependencies count toward the project storage budget.
