# M0 limitations

- No Gaussian reconstruction, learned rendering, collision geometry, editor, API,
  perception metrics, simulation, approval workflow, or recapture experiments.
- Frontend is a React/TypeScript scope shell only, with no backend connection.
- Only analytic fixture generation and the official five-pair Open3D Redwood
  sample format are supported. Generic TUM/video/pose recovery is not supported.
- Real sample uses supplied estimated odometry and nominal Y-up, with frame-index
  timestamps. No independently measured gravity, timing or pose accuracy.
- Tiny contiguous splits do not establish independent held-out evaluation.
  No near-duplicate detector, dynamic masks or candidate-access enforcement yet.
- Intrinsics assume a registered zero-skew pinhole camera. No distortion correction.
- Immutable records are local read-only files with hashes, not cryptographic
  attestations or an OS security boundary. Future experiments must pin their hashes.
- Storage checks are conservative preflight/postflight accounting, not a filesystem
  quota. Concurrent external writes or manually installing large packages can bypass
  them. Symlink targets outside the project are not counted. Keep project assets
  inside this directory and run `make storage` before/after large operations.
- Original sample redistribution terms remain unverified. No third-party data is
  committed, bundled in the frontend, or published. Synthetic fixture is CC0.
- No CUDA training compatibility has been tested. Driver-reported compatibility
  is not evidence of a working CUDA toolkit or reconstruction environment.
- Git dates are user-assigned June–October metadata; actual work took place on
  October 29, 2026. No claims of months of activity or experimental findings.
