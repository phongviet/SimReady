"""Bounded, posed TUM RGB-D import from an official .tgz archive.

Uses publisher-recommended ROS-default pinhole intrinsics for pre-registered
fr1 depth; does not silently apply the raw-camera distortion coefficients.
"""

import bisect
import shutil
import tarfile
from pathlib import Path

import numpy as np

from simready.data.dataset import atomic_dataset, finalize_dataset, sha256_file, write_json
from simready.data.schema import DepthEncoding, Frame, Intrinsics, Source, relative_path

TUM_WORLD_TO_CANONICAL = np.array(
    [[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], dtype=float
)
MAX_UNCOMPRESSED = 1_500_000_000
MAX_MEMBERS = 10000


def parse_rows(text: str, columns: int) -> list[list[str]]:
    rows = [
        line.split()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not rows or any(len(row) != columns for row in rows):
        raise ValueError(f"TUM index must have {columns} columns per data row")
    times = np.array([float(row[0]) for row in rows])
    if not np.isfinite(times).all() or np.any(np.diff(times) <= 0):
        raise ValueError("TUM timestamps must be finite and strictly ordered")
    return rows


def quaternion_matrix(q: np.ndarray) -> np.ndarray:
    q = np.asarray(q, dtype=float)
    norm = np.linalg.norm(q)
    if q.shape != (4,) or not np.isfinite(q).all() or not np.isclose(norm, 1, atol=0.01):
        raise ValueError("TUM quaternion must be finite and approximately unit length")
    x, y, z, w = q / norm
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ]
    )


def interpolate_pose(timestamp: float, groundtruth: np.ndarray) -> np.ndarray:
    """Interpolate optical-center c2w at RGB time; no extrapolation or long gaps."""
    index = int(np.searchsorted(groundtruth[:, 0], timestamp))
    if index == 0 or index == len(groundtruth):
        raise ValueError("RGB timestamp outside motion-capture pose support")
    left, right = groundtruth[index - 1], groundtruth[index]
    gap = right[0] - left[0]
    if gap > 0.05 or gap <= 0:
        raise ValueError("motion-capture gap exceeds 50ms")
    fraction = (timestamp - left[0]) / gap
    q0, q1 = left[4:].copy(), right[4:].copy()
    quaternion_matrix(q0)
    quaternion_matrix(q1)
    q0 /= np.linalg.norm(q0)
    q1 /= np.linalg.norm(q1)
    dot = float(q0 @ q1)
    if dot < 0:
        q1, dot = -q1, -dot
    if dot > 0.9995:
        q = (1 - fraction) * q0 + fraction * q1
        q /= np.linalg.norm(q)
    else:
        angle = np.arccos(np.clip(dot, -1, 1))
        q = (np.sin((1 - fraction) * angle) * q0 + np.sin(fraction * angle) * q1) / np.sin(angle)
    pose = np.eye(4)
    pose[:3, :3] = quaternion_matrix(q)
    pose[:3, 3] = (1 - fraction) * left[1:4] + fraction * right[1:4]
    return TUM_WORLD_TO_CANONICAL @ pose


def index_tum_archive(archive: Path):
    """Read only bounded indexes/poses and archive member metadata; never decode images."""
    if archive.stat().st_size > 500_000_000:
        raise ValueError("TUM archive exceeds 500 MB cap")
    metadata_text = {}
    members = set()
    uncompressed = 0
    with tarfile.open(archive, "r|gz") as bundle:
        for member in bundle:
            relative_path(member.name.rstrip("/"))
            if not (member.isdir() or member.isfile()):
                raise ValueError("TUM archive links/special files are forbidden")
            if member.name in members:
                raise ValueError("duplicate TUM archive member")
            members.add(member.name)
            uncompressed += member.size
            if len(members) > MAX_MEMBERS or uncompressed > MAX_UNCOMPRESSED:
                raise ValueError("TUM archive exceeds extraction limits")
            if Path(member.name).name in ("rgb.txt", "depth.txt", "groundtruth.txt"):
                if member.size > 2_000_000:
                    raise ValueError("oversized TUM metadata")
                with bundle.extractfile(member) as stream:
                    metadata_text[Path(member.name).name] = stream.read().decode("utf-8")
    if set(metadata_text) != {"rgb.txt", "depth.txt", "groundtruth.txt"}:
        raise ValueError("TUM archive lacks RGB/depth index or ground-truth poses")
    roots = {name.split("/")[0] for name in members}
    if len(roots) != 1:
        raise ValueError("TUM archive must contain one sequence root")
    root = roots.pop()
    if root != "rgbd_dataset_freiburg1_desk":
        raise ValueError("this calibration/provenance adapter supports freiburg1_desk only")
    rgb_rows = parse_rows(metadata_text["rgb.txt"], 2)
    depth_rows = parse_rows(metadata_text["depth.txt"], 2)
    truth = np.array(parse_rows(metadata_text["groundtruth.txt"], 8), dtype=float)
    if not np.isfinite(truth).all():
        raise ValueError("non-finite TUM ground truth")
    depth_times = [float(row[0]) for row in depth_rows]
    used_depth = set()
    associated = []
    for rgb in rgb_rows:
        timestamp = float(rgb[0])
        index = bisect.bisect_left(depth_times, timestamp)
        nearest = sorted(
            [i for i in (index - 1, index) if 0 <= i < len(depth_times)],
            key=lambda i: abs(depth_times[i] - timestamp),
        )
        nearest = [
            i for i in nearest if i not in used_depth and abs(depth_times[i] - timestamp) <= 0.02
        ]
        if not nearest:
            continue
        try:
            pose = interpolate_pose(timestamp, truth)
        except ValueError:
            continue
        chosen = nearest[0]
        used_depth.add(chosen)
        associated.append((rgb, depth_rows[chosen], pose))
    return metadata_text, members, root, associated


def import_tum(archive: Path, output: Path, max_frames: int = 100) -> None:
    if not 8 <= max_frames <= 256:
        raise ValueError("TUM import requires 8 to 256 sampled frames")
    metadata_text, members, root, associated = index_tum_archive(archive)
    if len(associated) < max_frames:
        raise ValueError(f"only {len(associated)} posed pairs; need {max_frames}")
    selected = [associated[i] for i in np.linspace(0, len(associated) - 1, max_frames, dtype=int)]
    archive_hash = sha256_file(archive)
    with atomic_dataset(output, max_frames * 4_000_000 + 6_000_000) as stage:
        (stage / "rgb").mkdir()
        (stage / "depth").mkdir()
        (stage / "calib").mkdir()
        for name, text in metadata_text.items():
            (stage / "calib" / name).write_text(text)
        desired = {}
        for i, (rgb, depth, _) in enumerate(selected):
            for channel, row in (("rgb", rgb), ("depth", depth)):
                relative_path(row[1])
                original = root + "/" + row[1]
                if original not in members:
                    raise ValueError(f"indexed TUM image missing: {row[1]}")
                desired[original] = f"{channel}/{i:05d}.png"
        # Second streaming pass: extract only the frozen selected observations.
        copied = set()
        with tarfile.open(archive, "r|gz") as bundle:
            for member in bundle:
                if member.name in desired:
                    if member.size > 2_000_000:
                        raise ValueError("oversized TUM image")
                    with (
                        bundle.extractfile(member) as source,
                        (stage / desired[member.name]).open("xb") as sink,
                    ):
                        shutil.copyfileobj(source, sink)
                    copied.add(member.name)
        if copied != set(desired):
            raise ValueError("TUM archive changed while importing")
        frames = []
        for i, (rgb, depth, pose) in enumerate(selected):
            rgb_path, depth_path = f"rgb/{i:05d}.png", f"depth/{i:05d}.png"
            frames.append(
                Frame(
                    frame_id=f"frame_{i:05d}",
                    timestamp=float(rgb[0]),
                    depth_timestamp=float(depth[0]),
                    camera_id="camera0",
                    sequence_id=root,
                    rgb_path=rgb_path,
                    rgb_sha256=sha256_file(stage / rgb_path),
                    depth_path=depth_path,
                    depth_sha256=sha256_file(stage / depth_path),
                    T_world_camera=pose.tolist(),
                )
            )
        camera = Intrinsics(width=640, height=480, fx=525, fy=525, cx=319.5, cy=239.5)
        write_json(stage / "calib/intrinsics.json", camera.model_dump(mode="json"))
        metadata = dict(
            scene_id="tum_fr1_desk",
            kind="real",
            source=Source(
                name="TUM RGB-D freiburg1_desk",
                url="https://cvg.cit.tum.de/data/datasets/rgbd-dataset",
                license="CC-BY-4.0",
                attribution="Sturm et al., RGB-D SLAM Systems Benchmark, IROS 2012.",
                description=f"Real Kinect capture; {max_frames} uniform temporal samples. "
                "ROS-default intrinsics follow publisher advice for registered depth.",
                archive_sha256=archive_hash,
            ),
            cameras={"camera0": camera},
            depth=DepthEncoding(meters_per_unit=0.0002, invalid_value=0),
            pose_provenance="Motion-capture optical-center c2w; linear translation and "
            "quaternion-SLERP at RGB time. No extrapolation; pose gaps <=50ms. "
            "Source nominal Z-up rotated to canonical Y-up.",
            timestamp_provenance="Original Unix timestamps from RGB/depth indexes; "
            "unique nearest-depth association within 20ms.",
            association_tolerance=0.020001,
            capture_conditions="Real Kinect desk sweep; publisher-registered depth "
            "with already corrected depth scale.",
            privacy="Public benchmark; no additional identity/privacy auditing performed.",
            limitations=(
                "ROS pinhole approximation follows publisher advice; residual errors possible.",
                "Temporal splits may overlap spatially; not independent scenes.",
                "Nominal mocap Z-up assumed; no accelerometer gravity alignment.",
                "Uncertainty: interpolated poses, exposure, rolling shutter, holes and dynamics.",
            ),
            T_canonical_source_world=TUM_WORLD_TO_CANONICAL.tolist(),
        )
        finalize_dataset(stage, metadata, frames)
        write_json(
            stage / "association-report.json",
            {
                "schema_version": "1.0",
                "source_rgb_frames": len(parse_rows(metadata_text["rgb.txt"], 2)),
                "associated_posed_pairs": len(associated),
                "sampled_frames": len(selected),
                "selection": "uniform temporal indices before reconstruction; no quality selection",
                "max_rgb_depth_delta_seconds": max(
                    abs(float(a[0]) - float(b[0])) for a, b, _ in selected
                ),
                "archive_sha256": archive_hash,
            },
        )
