# Readiness, local accounts and reviewed packages (M4)

## Local identities and permissions

`simready api serve --demo` initializes two distinct local accounts once. To
provision a non-demo registry explicitly:

```bash
uv run --frozen simready auth init --root artifacts/studio
```

The command prints the **path**, not the credentials. Read
`artifacts/studio/local-credentials.json` locally and paste the Builder or Reviewer
token into the studio account bar. This file is created with mode0600 and is not
served by HTTP, committed, logged or exported. The database stores SHA-256 token
digests. Tokens are random opaque256-bit credentials, not user-chosen passwords.
Server account records assign roles and active status on every request. No role
or actor supplied by the client authorizes an operation.

| Operation | Permission |
|---|---|
| Read registered scenes/assets/reports/QA/history/audit | Local read-only, no token required |
| Edit objects/scenarios; run evaluation/navigation; submit | Authenticated Builder |
| Approve/reject | Authenticated Reviewer, distinct from submitter identity |
| Build an approved-revision export | Authenticated Builder or Reviewer |
| Download an already registered reviewed package | Local read-only |

Missing/revoked tokens return401; wrong roles or self-review return403. Changing
an account's role does not let that identity review its own prior submission.
Body schemas reject extra role/status fields. Version conflicts return409 and
preserve client edits. API binds to loopback. These are local demo identities;
the OS owner can read both tokens and administer the database. This is not
production IAM or independent organizational review.

## Evidence components

`GET /api/v1/scenes/{id}/readiness` reports separate components:

- Camera novelty: nearest training-camera translation and full SO(3) rotation,
  minimum rotation, training-center AABB membership and actual reference view IDs.
  Labels distinguish observed training pose, interpolated-but-tested pose and
  tested extrapolation. Free-view regions with no real references are unverified.
  The0.5m/30° classification heuristics are not calibrated readiness thresholds.
  Camera-center coverage does not establish volumetric visibility/free space.
- Geometry: vertex/triangle counts, boundary/nonmanifold edges, degeneracy,
  represented surface area and metric bounds. It is an observed coarse proxy;
  no aligned mesh accuracy is computed by this diagnostic. No invented Chamfer/F-score.
- Perception: actual fixed-model real/render prediction counts and base-view
  image/depth metrics. Empty pairs and failed rendered predictions remain flags.
  Agreement is not detection accuracy.
- Navigation: result/reason, floor-support and unknown cells, explicit floor
  evidence, and exact source scene revision. Virtual support stays an assumption.

Without both a base evaluation and exact-revision navigation evidence, outcome
is`insufficient_evidence`. With them it is`needs_review`; diagnostics do not
silently approve a scene. `usable_for_declared_test` requires a recorded scoped
approval and still exposes limitations/failures. No broad safety claim is made.

The immutable base-model evaluation may be reused after proxy-only edits: the
same artifact/split hash must match, and the report explicitly excludes proxies.
Its original report revision is shown separately. Navigation must use the exact
submitted object/scenario content and source revision. Later reports cannot
silently replace evidence captured in an existing approval.

## Immutable workflow and audit

1. A Builder saves the scene/scenario and runs navigation. In Readiness / review,
   choose the actual base report, exact-revision navigation, named local task,
   measured camera subset and expected navigation outcome. Scope bounds match
   that run's map; adjusting them requires another saved scenario/run. Acknowledge
   the evidence limits before submitting.
2. Submission captures content-hashed QA, object/scenario/base-asset bindings and
   the Builder identity. It creates a **new submitted revision**. The review
   retains the source content revision: e.g.draft2→submitted3.
3. A separate Reviewer inspects the evidence and writes a reason. Approve/reject
   creates another immutable revision (e.g.approved4) and a server-side audit
   event in the **same SQLite transaction**. Approval checks evidence content and
   the declared expected route outcome. A barrier rejection test can explicitly
   expect`no_route`; zero collisions with no motion is never goal success.
4. Further edits create a new draft and clear current approval. Old approved
   revisions, scope and decisions remain readable/exportable. Rejected content
   must be revised into a draft before another submission.

Audit events chain SHA-256 over canonical payloads including actor/role, source
and resulting versions, scope/reason, timestamp and previous event digest.
SQLite triggers reject update/delete; reads verify the chain. This logs workflow
submissions/decisions. Content revision history is separate. It is not an OS
security boundary or externally anchored cryptographic attestation.

The Review queue refreshes submitted scenes. Every approved status opens the
recorded scope/decision, and the panel links to its audit event and immutable
history. The backend enforces all permissions even if UI controls are bypassed.

## Reviewed export

`POST /api/v1/scenes/{id}/export` accepts an approved immutable version. It checks
its independent audit decision, captured content and evidence hashes. Historical
approvals remain exportable after later edits. Drafts and unrecorded approved
badges cannot be exported.

The ZIP separates`render/`Gaussian assets,`collision/`coarse mesh assets,
`reference_views/`, measured`evaluation/`, exact`simulation/`, and`review/`scope,
QA and audit. Portable`scene.json`rewrites only asset references. `manifest.json`
hashes every payload except itself; the server separately hashes the entire ZIP.
Source license/attribution accompanies the package. Raw full datasets, model
weights, tokens, account tables and the registry database are excluded. Aligned
reference images in evaluation retain their source license.

The exported QA is the original pre-decision snapshot (`needs_review`), preserved
byte-for-byte; its separate approval record supplies the scoped decision.

A successful export is a scoped experiment package for further local analysis.
It is not validated Isaac Sim/OpenUSD integration, real robot performance or
certified perception/simulation fidelity.
