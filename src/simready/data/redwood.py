"""Bounded acquisition and import of Open3D's official five-frame sample."""

import hashlib
import json
import shutil
import stat
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import numpy as np

from simready.data.camera import CV_TO_GL
from simready.data.dataset import (
    atomic_dataset,
    finalize_dataset,
    local_file,
    sha256_file,
)
from simready.data.schema import (
    DepthEncoding,
    Frame,
    Intrinsics,
    Source,
    relative_path,
    rigid_matrix,
)
from simready.storage import check_budget

SAMPLE_URL = (
    "https://github.com/isl-org/open3d_downloads/releases/download/"
    "20220301-data/SampleRedwoodRGBDImages.zip"
)
SAMPLE_SHA256 = "4f161ba04d81cbe628fc69dac20552749f1b255b0090fe51c766e5d02355937b"
MAX_ARCHIVE_BYTES = 20_000_000
MAX_EXTRACT_BYTES = 25_000_000


def safe_extract(archive: Path, destination: Path) -> None:
    """Check all entries before writing; refuse traversal, symlinks, duplicates, bombs."""
    with zipfile.ZipFile(archive) as bundle:
        entries = bundle.infolist()
        if sum(e.file_size for e in entries) > MAX_EXTRACT_BYTES or len(entries) > 100:
            raise ValueError("archive exceeds extraction limit")
        seen = set()
        for entry in entries:
            name = relative_path(entry.filename.rstrip("/"))
            if name in seen:
                raise ValueError("duplicate archive entry")
            seen.add(name)
            if stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError("archive symlinks are forbidden")
            target = (destination / name).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError("archive path escapes destination")
        check_budget(sum(e.file_size for e in entries))
        for entry in entries:
            target = destination / entry.filename
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(entry) as source, target.open("xb") as sink:
                    shutil.copyfileobj(source, sink)


def fetch_sample(destination: Path, archive: Path | None = None) -> Path:
    if destination.exists():
        raise ValueError(
            f"sample output already exists: {destination}; import it or use a new path"
        )
    check_budget(MAX_ARCHIVE_BYTES + MAX_EXTRACT_BYTES)
    archive = archive or destination.parent / "SampleRedwoodRGBDImages.zip"
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        temporary = tempfile.NamedTemporaryFile(
            prefix="sample-", suffix=".part", dir=archive.parent, delete=False
        )
        partial = Path(temporary.name)
        try:
            with (
                temporary as out,
                urllib.request.urlopen(SAMPLE_URL, timeout=30) as response,
            ):
                declared = int(response.headers.get("Content-Length", 0))
                if declared > MAX_ARCHIVE_BYTES:
                    raise ValueError("sample exceeds download limit")
                size = 0
                while chunk := response.read(64 * 1024):
                    size += len(chunk)
                    if size > MAX_ARCHIVE_BYTES:
                        raise ValueError("sample exceeds download limit")
                    out.write(chunk)
            if sha256_file(partial) != SAMPLE_SHA256:
                raise ValueError("official sample SHA-256 mismatch")
            partial.rename(archive)
        finally:
            partial.unlink(missing_ok=True)
    if archive.stat().st_size > MAX_ARCHIVE_BYTES or sha256_file(archive) != SAMPLE_SHA256:
        raise ValueError("official sample SHA-256 mismatch or archive exceeds limit")
    with atomic_dataset(destination, MAX_EXTRACT_BYTES) as stage:
        safe_extract(archive, stage)
    return destination


def read_log(path: Path) -> list[np.ndarray]:
    lines = path.read_text().splitlines()
    if not lines or len(lines) % 5:
        raise ValueError("pose log must have one ID row and four matrix rows per frame")
    poses = []
    for i in range(0, len(lines), 5):
        index = i // 5
        if [int(x) for x in lines[i].split()] != [index, index, index + 1]:
            raise ValueError("pose log frame IDs must be ordered and contiguous")
        poses.append(
            rigid_matrix(
                np.array([[float(x) for x in line.split()] for line in lines[i + 1 : i + 5]])
            )
        )
    return poses


def import_redwood(source: Path, output: Path) -> None:
    """The supported format is open3d_redwood_sample, not arbitrary RGB-D sequences."""
    calibration = json.loads(local_file(source, "camera_primesense.json").read_text())
    matrix = np.array(calibration["intrinsic_matrix"], dtype=float).reshape(3, 3, order="F")
    if not np.allclose(
        matrix, [[matrix[0, 0], 0, matrix[0, 2]], [0, matrix[1, 1], matrix[1, 2]], [0, 0, 1]]
    ):
        raise ValueError("calibration is not supported zero-skew pinhole")
    camera = Intrinsics(
        width=calibration["width"],
        height=calibration["height"],
        fx=matrix[0, 0],
        fy=matrix[1, 1],
        cx=matrix[0, 2],
        cy=matrix[1, 2],
    )
    poses = read_log(local_file(source, "odometry.log"))
    pairs = [line.split() for line in local_file(source, "rgbd.match").read_text().splitlines()]
    if len(poses) != 5 or len(pairs) != 5:
        raise ValueError("official sample requires exactly five associated RGB-D frames and poses")
    for i, pair in enumerate(pairs):
        if pair != [f"depth/{i:05d}.png", f"color/{i:05d}.jpg"]:
            raise ValueError("unexpected RGB/depth association in official sample")
    selected = [local_file(source, name) for pair in pairs for name in pair]
    archive = source.parent / "SampleRedwoodRGBDImages.zip"
    archive_hash = None
    if archive.is_file():
        if archive.stat().st_size > MAX_ARCHIVE_BYTES or sha256_file(archive) != SAMPLE_SHA256:
            raise ValueError("official source archive SHA-256 mismatch")
        with zipfile.ZipFile(archive) as bundle:
            for path in selected + [
                local_file(source, name)
                for name in ("camera_primesense.json", "odometry.log", "rgbd.match")
            ]:
                name = str(path.relative_to(source.resolve()))
                if hashlib.sha256(bundle.read(name)).hexdigest() != sha256_file(path):
                    raise ValueError(f"source differs from verified official archive: {name}")
        archive_hash = SAMPLE_SHA256
    with atomic_dataset(output, sum(p.stat().st_size for p in selected) + 1_000_000) as stage:
        (stage / "rgb").mkdir()
        (stage / "depth").mkdir()
        (stage / "calib").mkdir()
        for name in ("camera_primesense.json", "odometry.log", "rgbd.match"):
            shutil.copyfile(local_file(source, name), stage / "calib" / name)
        frames = []
        for i, (depth_name, color_name) in enumerate(pairs):
            rgb_path, depth_path = f"rgb/{i:05d}.jpg", f"depth/{i:05d}.png"
            shutil.copyfile(local_file(source, color_name), stage / rgb_path)
            shutil.copyfile(local_file(source, depth_name), stage / depth_path)
            frames.append(
                Frame(
                    frame_id=f"frame_{i:05d}",
                    timestamp=i,
                    depth_timestamp=i,
                    camera_id="camera0",
                    sequence_id="redwood_sample",
                    rgb_path=rgb_path,
                    rgb_sha256=sha256_file(stage / rgb_path),
                    depth_path=depth_path,
                    depth_sha256=sha256_file(stage / depth_path),
                    T_world_camera=(CV_TO_GL @ poses[i]).tolist(),
                )
            )
        metadata = dict(
            scene_id="redwood_sample",
            kind="synthetic",
            source=Source(
                name="Open3D SampleRedwoodRGBDImages",
                url=SAMPLE_URL,
                license="Dataset-specific redistribution terms unverified; local development only",
                attribution="Redwood indoor dataset / Open3D sample maintainers",
                description="Five RGB-D pairs from the synthetic Redwood/ICL-NUIM scene. "
                "Archive hash is recorded only when source files match the pinned archive.",
                archive_sha256=archive_hash,
            ),
            cameras={"camera0": camera},
            depth=DepthEncoding(meters_per_unit=0.001, invalid_value=0),
            pose_provenance="Supplied odometry.log camera-to-world matrices; estimated poses, "
            "not independently verified ground truth. Left-multiplied by diag(1,-1,-1,1).",
            timestamp_provenance="Frame index only; archive does not provide capture timestamps. "
            "Pairing comes from rgbd.match; zero tolerance is index equality.",
            association_tolerance=0,
            capture_conditions="Indoor sample; registered 640x480 RGB and millimeter depth.",
            privacy="Public indoor sample; redistribution not audited. Do not bundle in Git.",
            limitations=(
                "Synthetic Redwood/ICL-NUIM sample; not a real Kinect capture.",
                "Only five adjacent views; contiguous 2/1/1/1 split is integration-only.",
                "Near-duplicate views can span blocks; no meaningful held-out evaluation claims.",
                "Nominal Y-up from source camera frame, not gravity-calibrated.",
                "No verified distortion/exposure/dynamic masks or original capture timestamps.",
                "License terms not independently confirmed; no sample redistribution.",
            ),
            T_canonical_source_world=CV_TO_GL.tolist(),
        )
        finalize_dataset(stage, metadata, frames)
