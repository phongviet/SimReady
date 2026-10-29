# M0 dataset and coordinate protocol

**Provenance correction discovered during M1 (2026-10-29):** the Open3D Redwood
sample depicts the synthetic Redwood/ICL-NUIM scene, not a real Kinect capture.
The original importer incorrectly labeled it `real`. New imports use `synthetic`,
and validation rejects the old mislabeled imports/artifacts. Historical M0 evidence
containing `real` is superseded for classification, not evidence of real capture.
The original Redwood site was reached over HTTP and identifies its indoor scenes
as a synthetic augmented ICL-NUIM dataset: http://redwood-data.org/indoor/dataset.html .
The verified real-data path is TUM, described below.

`manifest.json`, `frames.jsonl`, `splits.json` form the version **1.0** contract.
Pydantic models are in `src/simready/data/schema.py`; unknown fields and versions
are rejected. Schema version and coordinate metadata must be present explicitly.

## Representation

- Scene-local paths only, without traversal, absolute paths or symlink escape.
- RGB images are decoded RGB with calibrated dimensions. Depth is registered,
  single-channel uint16 axial camera Z, with explicit meters per stored unit
  and invalid sentinel. Invalid/nonpositive/nonfinite samples map to NaN in math.
- Manifest records source, attribution/license status, privacy, capture conditions,
  real/synthetic kind, intrinsics, pose/timestamp provenance, world transform,
  frame/split hashes and limitations. Optional RGB-only frames omit all depth fields.
- Frames record unique ID, strictly increasing timestamp, sequence/camera IDs,
  image paths and SHA-256 digests, depth timestamp, and `T_world_camera` (c2w).
- Import validates every image and proper rigid pose, association tolerance,
  exact frame coverage, and content hashes before publishing the output directory.
- Only zero-skew pinhole calibration and registered RGB-D are supported in M0.
  Distortion correction, general TUM association, masks and pose estimation are future work.

## Coordinates

World: meters, right-handed, nominal Y-up. Camera: OpenCV X-right/Y-down/Z-forward.
Column-vector equation `p_world = T_world_camera @ p_camera`. Matrix serialization
is a list of rows, never an implicitly transposed flat array.

`world_to_camera`, `gsplat_viewmat`, `open3d_extrinsic` return the inverse c2w.
Three.js camera local Y-up/-Z-forward uses `c2w @ diag(1,-1,-1,1)`; the canonical
world stays unchanged. These are tested mathematical conversions, not implemented
renderer adapters. For Three.js `Matrix4.fromArray`, flatten in column-major order;
for `Matrix4.set`, pass row-major elements explicitly. No browser renderer exists yet.

Projection: `u = fx*x/z + cx`, `v = fy*y/z + cy`, requiring positive Z.
Unprojection uses axial Z, not Euclidean ray range. Float64 round trips use
absolute tolerance 1e-12 in the tests. Pose checks tolerate 1e-5 in orthogonality
and determinant for the supplied rounded odometry log, with no silent reorthogonalization.

Resize uses integer pixel centers and half-pixel resampling:
`fx'=sx*fx`, `fy'=sy*fy`, `cx'=(cx+0.5)*sx-0.5`, `cy'=(cy+0.5)*sy-0.5`.
No images are actually resized by the M0 importer.

## Frozen split protocol

Creation orders frames by the supplied sequence and partitions contiguous blocks.
Train gets `min(max(1, N//2), N-3)`; validation and candidate each get
`max(1, (N-N_train)//3)`; test gets the remainder. At least four frames are needed.
All groups are nonempty, disjoint and exhaustive. Exact duplicate RGB observations
and reused file paths are rejected. There is no near-duplicate detector.

The synthetic fixture has 4/1/1/2 frames; the real sample has 2/1/1/1. Both are
**integration protocols**, with no guaranteed spatial separation, independence
or statistical power. They are unsuitable for research conclusions. Validation
exists for eventual threshold tuning; candidate and test observations must not
be used for fitting/tuning. Dataset validation reads files solely for integrity.
No acquisition or training algorithm is implemented, so no observation-access
sandbox is claimed.

SHA-256 hashes bind frames bytes to manifest/splits, split bytes to manifest,
and image bytes to frames. Read-only metadata and no-overwrite imports discourage
accidental edits. `data split` verifies the existing split; it cannot resample it.
Use a new output directory for a new dataset version. Filesystem users can rewrite
hashes, so experiments must eventually pin hashes separately in run provenance.

## Official sample provenance

The small official synthetic importer format is `open3d_redwood_sample`.
The [official sample descriptor](https://github.com/isl-org/Open3D/blob/main/cpp/open3d/data/dataset/SampleRedwoodRGBDImages.cpp)
identifies the release and publisher MD5 `43971c5f690c9cfc52dda8c96a0140ee`.
The downloaded 3,772,513-byte ZIP additionally has SHA-256
`4f161ba04d81cbe628fc69dac20552749f1b255b0090fe51c766e5d02355937b`, pinned in code.
The downloader verifies SHA-256, caps download at 20 MB and extraction at 25 MB,
and rejects archive traversal, symlinks and duplicate entries. No Open3D install is required.

Calibration is the supplied PrimeSense 640x480 / fx=fy=525 / cx=319.5 / cy=239.5.
Open3D's [RGB-D documentation](https://www.open3d.org/docs/latest/tutorial/geometry/rgbd_image.html)
describes the registered depth representation; M0 converts millimeters with 0.001.
The supplied `odometry.log` is used as c2w, following the inverse used for integration
in [Open3D's example](https://github.com/isl-org/Open3D/blob/main/examples/python/pipelines/rgbd_integration_uniform.py).
The world conversion is a left multiplication by diag(1,-1,-1,1). Nominal Y-up
comes from the source camera orientation, not a measured gravity direction.
No pose estimation is performed; estimated supplied poses are not independent GT.

The ZIP has associations in `rgbd.match` but no original capture timestamps.
Timestamps are therefore explicitly frame indices; zero association tolerance
means index equality, not a synchronization accuracy claim. Calibration, pairing
and odometry source files are copied into `calib/`. If the sibling pinned archive
is available, the importer checks consumed source bytes against it and records its
hash. Otherwise the archive hash is null; local image hashes still bind the import.

The five adjacent views may overlap heavily across splits. Sample license terms
could not be independently confirmed from the original Redwood site during this
run; do not redistribute this data or describe Open3D's code license as a data
license. Data stays ignored in local storage, fetched from its official source.

## Real TUM RGB-D path (M1)

```bash
uv run --frozen python scripts/fetch_tum_data.py
uv run --frozen simready data import --source data/raw/rgbd_dataset_freiburg1_desk.tgz --format tum_rgbd --max-frames 100 --out data/scenes/tum-fr1-desk
make test-real
```

The [official TUM sequence page](https://cvg.cit.tum.de/data/datasets/rgbd-dataset/download)
identifies `freiburg1_desk` as a real Kinect office sweep. The [dataset license](https://cvg.cit.tum.de/data/datasets/rgbd-dataset#license)
is CC BY 4.0, with attribution to Sturm et al., IROS 2012.
The downloader caps the archive at 500 MB; import caps its uncompressed contents
at 1.5 GB and extracts only the chosen RGB-D pairs. Links, traversal, duplicates
and missing indexes/poses are rejected. SHA-256 and the resolved source URL are
recorded. No raw data is committed to Git.

At most 20ms separates each uniquely associated RGB/depth pair. Optical-center
c2w poses are interpolated from the original motion-capture trajectory: linear
translation and quaternion SLERP, no extrapolation or gaps above 50ms. Timestamps
remain original Unix seconds. Nominal source Z-up is rotated to canonical Y-up;
accelerometer-based gravity alignment is not performed.

The [publisher's calibration guidance](https://cvg.cit.tum.de/data/datasets/rgbd-dataset/file_formats)
recommends ROS-default fx=fy=525, cx=319.5, cy=239.5 without further undistortion
for the pre-registered depth. M0's pinhole contract therefore remains valid, with
the residual calibration approximation explicitly disclosed. Raw depth is divided
by 5000; the publisher's prior scale correction is **not applied twice**.

Frames are selected by uniform temporal indices before fitting; the standard
contiguous split is frozen at import. This avoids image-quality selection but
does not guarantee spatially independent blocks. All pose/source uncertainty and
calibration limitations are retained in the manifest and future reports.
