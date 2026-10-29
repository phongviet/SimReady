# Current limitations

- Gaussian training/rendering is implemented with a verified local CUDA kernel;
  real TUM sequence acceptance is still in progress. No collision geometry, editor,
  API, perception metrics, simulation, approval workflow or recapture experiments.
- Frontend is a React/TypeScript scope shell only, with no backend connection.
- Analytic fixture generation, official Open3D Redwood and TUM fr1 desk formats
  are implemented. Other captures, general video and pose recovery are unsupported.
- Redwood is synthetic ICL-NUIM; the initial M0 real label was wrong and corrected.
  It uses supplied odometry, nominal Y-up and frame-index timestamps.
- TUM uses approximate ROS-default pinhole calibration as recommended for its
  registered depth, with pose interpolation and nominal source Z-up. No independent
  gravity, calibration, rolling-shutter or exposure correction is performed.
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
- CUDA/gsplat forward/backward and small trained-checkpoint reload have been
  tested on the local 6 GB GTX 1660 Ti. Other GPU/runtime combinations are untested.
- GPU peaks in run metadata measure PyTorch allocated/reserved memory only;
  driver/context overhead is excluded. Short-run timings are not FPS benchmarks.
- Git dates are user-assigned June–October metadata; actual work took place on
  October 29, 2026. No claims of months of activity or experimental findings.
