# Current limitations

- Gaussian training/rendering, independent TSDF and persistent proxy editing are
  verified locally, along with frozen-view perception metrics on 18 real TUM
  test views. Navigation and scoped local review/export are implemented; M4 real-scene
  acceptance is verified with automated local-role fixtures. The completed local recapture study reports a negative result; see M5_RESULTS.md.
- The short real baseline is blurry and has zero rendered detector predictions
  at the fixed >=0.5 threshold, versus 48 summed per-view real predictions. This
  exposes a failure, not detection accuracy. No real TUM annotated GT boxes are available; the separate authored bench companion has analytic labels.
  Matching quality is N/A for these unmatched views; no mAP or readiness claim.
- The browser uses a separate Spark renderer and explicit overlay-only mesh pass;
  splat/mesh occlusion and edited-scene perception realism are unverified.
- TSDF is an incomplete observed surface proxy, not necessarily watertight or
  physically exact. Triangle/box contact does not certify solid occupancy.
- The API binds to loopback. Mutation endpoints require server-assigned local
  Builder/Reviewer roles; separate opaque tokens are bootstrap fixtures. The OS
  owner controls both accounts/database. This is not production IAM or independent
  organizational/human review; automated acceptance decisions are labeled as such.
- Analytic fixture generation, official Open3D Redwood and TUM fr1 desk formats
  are implemented. Other captures, general video and pose recovery are unsupported.
- Redwood is synthetic ICL-NUIM; the initial M0 real label was wrong and corrected.
  It uses supplied odometry, nominal Y-up and frame-index timestamps.
- TUM uses approximate ROS-default pinhole calibration as recommended for its
  registered depth, with pose interpolation and nominal source Z-up. No independent
  gravity, calibration, rolling-shutter or exposure correction is performed.
- Tiny contiguous splits do not establish independent held-out evaluation.
  No near-duplicate detector or dynamic masks. The M5 runner enforces staged candidate/test access; local files are not an OS security boundary.
- Intrinsics assume a registered zero-skew pinhole camera. No distortion correction.
- Immutable records are local read-only files with hashes, not cryptographic
  attestations or an OS security boundary. Future experiments must pin their hashes.
- Storage checks are conservative preflight/postflight accounting, not a filesystem
  quota. Concurrent external writes or manually installing large packages can bypass
  them. Symlink targets outside the project are not counted. Keep project assets
  inside this directory and run `make storage` before/after large operations.
- Original Redwood sample redistribution terms remain unverified. No third-party
  raw dataset or model weight is committed or bundled. Derived TUM screenshots
  and the failure contact sheet carry CC BY 4.0 source attribution. The bundled
  analytic fixture, measured report and images derive from our CC0 synthetic data.
- CUDA/gsplat forward/backward and small trained-checkpoint reload have been
  tested on the local 6 GB GTX 1660 Ti. Other GPU/runtime combinations are untested.
- GPU peaks in run metadata measure PyTorch allocated/reserved memory only;
  driver/context overhead is excluded. Short-run timings are not FPS benchmarks.
- Git dates are user-assigned June–October metadata; actual execution dates are recorded in the
  milestone documents (October 2026). No claims of months of activity or experimental findings.
