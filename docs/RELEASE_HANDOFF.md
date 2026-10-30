# Local release candidate handoff

Archived candidate: **v0.0.1-rc.2**. Public source and hosted acceptance are now
verified in PUBLICATION.md. The final **v0.0.1** tag also includes the subsequent
cold-test setup fix. RC2 remains a reproducible historical handoff; it is not
rewritten or presented as the final fixed test runner. No hosted service is claimed.

Files are generated under `artifacts/releases/v0.0.1-rc.2/`:

- Git history bundle: `simready-v0.0.1-rc.2.bundle`.
- Source archive: `simready-v0.0.1-rc.2.tar.gz`.
- CPU wheel: `simready-0.0.1-py3-none-any.whl`.
- `manifest.json`: exact release/tested commits, code-tree digest, file sizes/hashes.

These build outputs remain ignored. They exclude raw datasets, downloaded weights,
environments, caches and local credentials. Small authored saved demo assets and
attributed derived media are included. Read LICENSE/THIRD_PARTY.md before reuse.
The source checkout is the supported complete UI/GPU setup path; the standalone
wheel's CPU smoke scope is described in FRESH_INSTALL.md.

Restore the history bundle explicitly onto `main`:

```bash
git clone --branch main artifacts/releases/v0.0.1-rc.2/simready-v0.0.1-rc.2.bundle \
  .cache/restored-simready
```

The bundle includes HEAD, main and the annotated candidate tag. Alternatively,
extract the source archive; use the bundle when exact Git experiment history is
needed. Run the normal README setup from the restored checkout, and run outer
project `make storage` before/after installs when nesting restored checkouts here.

## Byte-exact checkout

A restore of RC1 with `core.autocrlf=true` changed a hashed JSON input and correctly
failed checkpoint validation. RC1 is preserved as historical evidence. RC2 adds
explicit Git attributes: hashed demo/evidence trees and binary assets are preserved
byte-for-byte; other source uses LF. A real fresh clone under that same setting
then passed saved-model, geometry, evaluation and research-package content checks.
See [checkout witness](evidence/m6-byte-exact-checkout.json). This is not a claim
that native Windows CUDA is supported.

Application code is unchanged from tested `22afb45`; the additional checkout
policy is independently verified. [Final verification](FINAL_VERIFICATION.md)
records 179 CPU tests, three actual CUDA tests and a separate clean CPU checkout
with eight browser tests. Candidate manifests preserve package hashes separately
from the earlier wheel used during the initial verification stage.

## Publication next step

The destination is https://github.com/phongviet/SimReady. Publication/hosted
acceptance are verified in PUBLICATION.md. The native local service remains the
verified deployment; Docker/cloud/external simulator targets are unsupported.
