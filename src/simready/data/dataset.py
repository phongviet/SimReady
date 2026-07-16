"""Canonical dataset IO, atomic import, frozen splits and on-disk validation."""

import hashlib
import json
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import numpy as np
from PIL import Image

from simready.data.camera import depth_to_meters
from simready.data.schema import DatasetManifest, Frame, Splits, relative_path
from simready.storage import check_budget


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def local_file(root: Path, name: str) -> Path:
    relative_path(name)
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"path escapes scene directory: {name}")
    if not path.is_file():
        raise ValueError(f"missing file: {name}")
    return path


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def block_splits(frames: list[Frame], frames_hash: str) -> Splits:
    if len(frames) < 4:
        raise ValueError("at least four frames needed for train/validation/candidate/test")
    ids = [frame.frame_id for frame in frames]
    # Reserve nonempty contiguous blocks; for five frames this is 2/1/1/1.
    n_train = max(1, len(ids) // 2)
    n_other = max(1, (len(ids) - n_train) // 3)
    return Splits(
        frames_sha256=frames_hash,
        train=tuple(ids[:n_train]),
        validation=tuple(ids[n_train : n_train + n_other]),
        candidate=tuple(ids[n_train + n_other : n_train + 2 * n_other]),
        test=tuple(ids[n_train + 2 * n_other :]),
    )


def finalize_dataset(root: Path, metadata: dict, frames: list[Frame]) -> DatasetManifest:
    frame_path = root / "frames.jsonl"
    frame_path.write_text(
        "".join(
            json.dumps(f.model_dump(mode="json"), sort_keys=True, allow_nan=False) + "\n"
            for f in frames
        )
    )
    frames_hash = sha256_file(frame_path)
    splits = block_splits(frames, frames_hash)
    write_json(root / "splits.json", splits.model_dump(mode="json"))
    manifest = DatasetManifest(
        **metadata, frames_sha256=frames_hash, split_sha256=sha256_file(root / "splits.json")
    )
    write_json(root / "manifest.json", manifest.model_dump(mode="json"))
    validate_scene(root)
    for name in ("manifest.json", "frames.jsonl", "splits.json"):
        (root / name).chmod(0o444)
    return manifest


@contextmanager
def atomic_dataset(output: Path, reserve_bytes: int) -> Iterator[Path]:
    """Never overwrite an import; failed staging and lock are cleaned up."""
    check_budget(reserve_bytes)
    output = output.absolute()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or output.is_symlink():
        raise ValueError(f"output already exists; use a new scene directory: {output}")
    lock = output.with_name(output.name + ".import-lock")
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise ValueError(f"import already in progress: {output}") from exc
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
    try:
        yield stage
        check_budget()
        if output.exists():
            raise ValueError(f"output already exists: {output}")
        stage.rename(output)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
        lock.rmdir()


def validate_scene(root: Path) -> dict:
    manifest = DatasetManifest.model_validate_json(local_file(root, "manifest.json").read_text())
    frame_path = local_file(root, "frames.jsonl")
    split_path = local_file(root, "splits.json")
    if sha256_file(frame_path) != manifest.frames_sha256:
        raise ValueError("frames hash mismatch: frozen frame records were modified")
    splits = Splits.model_validate_json(split_path.read_text())
    if sha256_file(split_path) != manifest.split_sha256:
        raise ValueError("split hash mismatch: frozen split was modified")
    if splits.frames_sha256 != manifest.frames_sha256:
        raise ValueError("splits refer to different frame records")
    frames = [Frame.model_validate_json(line) for line in frame_path.read_text().splitlines()]
    ids = [f.frame_id for f in frames]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate frame IDs")
    all_split_ids = splits.train + splits.validation + splits.candidate + splits.test
    if set(all_split_ids) != set(ids):
        raise ValueError("split IDs must cover exactly the frame records")
    if any(b.timestamp <= a.timestamp for a, b in zip(frames, frames[1:], strict=False)):
        raise ValueError("frame timestamps must be strictly increasing")
    paths: set[str] = set()
    observations: set[str] = set()
    valid_depth_pixels = 0
    for frame in frames:
        if frame.camera_id not in manifest.cameras:
            raise ValueError(f"unknown camera {frame.camera_id} in frame {frame.frame_id}")
        camera = manifest.cameras[frame.camera_id]
        if frame.rgb_sha256 in observations:
            raise ValueError(f"duplicate RGB observation in frame {frame.frame_id}")
        observations.add(frame.rgb_sha256)
        for name, digest, is_depth in (
            (frame.rgb_path, frame.rgb_sha256, False),
            (frame.depth_path, frame.depth_sha256, True),
        ):
            if name is None:
                continue
            if name in paths:
                raise ValueError(f"reused image path: {name}")
            paths.add(name)
            path = local_file(root, name)
            try:
                with Image.open(path) as image:
                    if image.size != (camera.width, camera.height):
                        raise ValueError(f"image dimensions disagree with calibration: {name}")
                    image.load()
                    if is_depth:
                        raw = np.asarray(image)
                        if image.mode not in {"I;16", "I;16B", "I"} or raw.ndim != 2:
                            raise ValueError(f"depth must be a uint16 single-channel image: {name}")
                        if raw.min() < 0 or raw.max() > 65535:
                            raise ValueError(f"depth outside uint16 range: {name}")
                        valid_depth_pixels += int(
                            np.isfinite(
                                depth_to_meters(
                                    raw,
                                    manifest.depth.meters_per_unit,
                                    manifest.depth.invalid_value,
                                )
                            ).sum()
                        )
                    elif image.mode != "RGB":
                        raise ValueError(f"color image must have RGB channels: {name}")
            except (OSError, Image.DecompressionBombError) as exc:
                raise ValueError(f"unreadable image {name}: {exc}") from exc
            if sha256_file(path) != digest:
                raise ValueError(f"image content hash mismatch: {name}")
        if frame.depth_timestamp is not None:
            if abs(frame.timestamp - frame.depth_timestamp) > manifest.association_tolerance:
                raise ValueError(f"RGB/depth timestamp mismatch: {frame.frame_id}")
    return {
        "scene_id": manifest.scene_id,
        "kind": manifest.kind,
        "frames": len(frames),
        "splits": {
            name: len(getattr(splits, name))
            for name in ("train", "validation", "candidate", "test")
        },
        "frames_sha256": manifest.frames_sha256,
        "split_sha256": manifest.split_sha256,
        "valid_depth_pixels": valid_depth_pixels,
        "limitations": list(manifest.limitations),
    }
