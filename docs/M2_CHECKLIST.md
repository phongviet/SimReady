# M2 acceptance criteria

- [x] Fuse an independent coarse TSDF from training RGB-D only; record hashes,
      metric frame, voxel size/truncation, supplied-pose limitations and actual output counts.
- [x] Test a known metric surface/box against the geometry representation.
- [x] Persist scene.json and non-destructive inserted box/barrier transforms,
      immutable revisions, visibility/deletion, and optimistic version conflicts.
- [x] API serves controlled scene assets and saved camera views; no arbitrary file paths.
- [x] Working browser splat/orbit view, inserted object selection, translation,
      rotation, scale, hide/delete, collision toggle and save/reload.
- [x] Numerical backend/browser camera projection parity and transform tests.
- [x] Browser smoke verifies editing, persistence after reload and conflict/error states.
- [x] Real reconstructed TUM scene and an offline analytic demo can be opened.
- [x] Screenshot with an actually inserted box and matching collider transform.
- [x] Occlusion scope explicitly disclosed; no perception claims about browser overlays.
- [x] CPU/API/frontend tests and optional geometry integration pass; storage <30 GB.

M2 success is usable persistent editing in one coordinate frame. Physics accuracy,
perception evaluation, simulation and review permissions remain later gates.

Accepted locally on 2026-10-29. Python: 129 passed, 1 optional GPU skip; frontend: 3 tests; Playwright: 3 live browser tests. Lint, formatting and production build pass. See PROGRESS.md and docs/evidence/m2-* for actual metadata/screenshots. Hosted CI has not run.
