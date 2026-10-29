# M4 acceptance — complete locally, 2026-10-29

- [x] Measured coverage, geometry and perception diagnostics with explicit unknowns.
- [x] Server-enforced separate Builder/Reviewer identities, scoped review and audit.
- [x] Draft/submit/approve/reject transitions; edits invalidate current approval;
  old approved revisions remain inspectable; self-approval and role spoofing fail.
- [x] Bounded occupancy map, robot footprint, waypoints, deterministic planner,
  swept collision checks, scenario editor and 3D route replay.
- [x] Actual baseline and inserted-obstacle layouts, with measured route/collision
  outputs tied to geometry, scene revision and scenario config.
- [x] Reviewed export separates visual splats and collision assets and includes
  immutable evidence, approval scope, source licenses, hashes and audit.
- [x] CPU, API, browser and export acceptance; exact evidence and storage <30GB.

Evidence and limits:

- Full current CPU/geometry suite: **158 passed, 2 opt-in GPU skips**. The actual
  authenticated GPU queue/render/perception regression separately passed1test.
- Frontend: **5 unit tests, 6 Playwright tests**, production build and format.
  Browser checks exercise separate sign-ins, queue, scoped approval, reviewed
  download, role restrictions, and subsequent edit invalidation.
- Real navigation: source1afbb60,1.05m baseline,1.15m box detour, barrier rejects
  route;5269unknown cells stay blocked. See SIMULATION_PROTOCOL.md.
- Real scoped workflow: clean source3d584ed, source5→submitted6→approved7,
  actual TUM data,18reference cameras, local distinct-role fixture identities.
  Builder role spoof403, anonymous decision401; all ZIP payload hashes verified.
- Approval is explicitly an **automated local acceptance fixture**, for the
  named known-map obstruction regression. No human endorsement, safety claim,
  detection accuracy, physical free-space truth or external simulator validation.
- Sourceb20a246 additionally blocks approved-readiness/export on post-approval
  evidence tampering. A new actual verification reads the existing recorded
  real approval and builds/checks its package; it creates no new review decision.
- The original QA preserves all real failure/uncertainty flags. No metric was
  modified to make a scene look usable. The approval is scoped to the declared test.

See REVIEW_PROTOCOL.md, evidence/m4-review-evidence.json,
evidence/m4-review-current-code.json and the actual UI screenshot. Hosted CI
has not run because no remote is configured. M5/M6 remain pending.

Final M4 storage: **14,239,961,486 bytes**, below30GB. Current-code verification
checks213payload hashes in the27.0MB real package. Temporary API stopped cleanly.
