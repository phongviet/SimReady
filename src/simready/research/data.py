"""Curator/learner separation: withhold observations until immutable selection seals."""

import fcntl
import json
import os
import shutil
import tarfile
import tempfile
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from simready.data.dataset import (
    atomic_dataset,
    finalize_dataset,
    local_file,
    sha256_file,
    write_json,
)
from simready.data.schema import DatasetManifest, Frame
from simready.data.tum import index_tum_archive
from simready.reconstruction.gsplat import load_records
from simready.research.selection import json_digest, validate_seal
from simready.storage import PROJECT_ROOT


def metadata_of(manifest: DatasetManifest, scene_id: str) -> dict:
    metadata = manifest.model_dump(
        mode="json",
        exclude={
            "schema_version",
            "world_units",
            "world_frame",
            "camera_axes",
            "frames_sha256",
            "split_sha256",
        },
    )
    metadata["scene_id"] = scene_id
    metadata["source"]["description"] = (
        "M5 derived TUM subset: original50train/16validation/16candidate plus18new "
        "late-frame test observations; "
        "candidate/test access gated. Not uniform sampling or an independent scene."
    )
    metadata["limitations"] += [
        "Study access is phase-scoped; metadata is public, candidate/test pixels "
        "are withheld until seals.",
        "New held-out frames are close in time/pose to inspected M3 frames; "
        "no scene-level blindness claim.",
    ]
    return metadata


def curate(source: Path, archive: Path, output: Path, protocol: dict) -> Path:
    manifest, frames, splits = load_records(source, ())
    pin = json.loads((PROJECT_ROOT / "configs/tum_fr1_desk.source.json").read_text())
    if manifest.kind != "real" or len(frames) != 100 or sha256_file(archive) != pin["sha256"]:
        raise ValueError("study curator requires the pinned real TUM100-frame source/archive")
    if [len(getattr(splits, name)) for name in ("train", "validation", "candidate", "test")] != [
        50,
        16,
        16,
        18,
    ]:
        raise ValueError("source partitions differ from the frozen protocol")
    _, _, root, associated = index_tum_archive(archive)
    original_times = {frame.timestamp for frame in frames}
    original_depths = {frame.depth_timestamp for frame in frames}
    lower = min(frame.timestamp for frame in frames if frame.frame_id in splits.test)
    eligible = [
        pair
        for pair in associated
        if float(pair[0][0]) >= lower
        and float(pair[0][0]) not in original_times
        and float(pair[1][0]) not in original_depths
    ]
    if len(eligible) < 18:
        raise ValueError("not enough previously unimported paired late frames")
    selected = [eligible[i] for i in np.linspace(0, len(eligible) - 1, 18, dtype=int)]
    old = [frame for frame in frames if frame.frame_id not in splits.test]
    with atomic_dataset(output, 600_000_000) as stage:
        write_json(stage / "protocol.json", protocol)
        vault = stage / "vault"
        for channel in ("rgb", "depth"):
            (vault / channel).mkdir(parents=True)
        study_frames, origins = [], []
        for frame in old:
            update = {}
            for channel in ("rgb", "depth"):
                name = f"{channel}/{frame.frame_id}.png"
                shutil.copyfile(local_file(source, getattr(frame, channel + "_path")), vault / name)
                if sha256_file(vault / name) != getattr(frame, channel + "_sha256"):
                    raise ValueError("curator source content changed")
                update[channel + "_path"] = name
            study_frames.append(frame.model_copy(update=update))
            origins.append(
                {
                    "frame_id": frame.frame_id,
                    "source_frame_id": frame.frame_id,
                    "source_timestamp": frame.timestamp,
                    "mode": "opaque curator copy; no selection feature",
                }
            )
        desired = {}
        for i, (rgb, depth, _) in enumerate(selected):
            name = f"blindtest_{i:05d}"
            desired[root + "/" + rgb[1]] = f"rgb/{name}.png"
            desired[root + "/" + depth[1]] = f"depth/{name}.png"
        copied = set()
        with tarfile.open(archive, "r|gz") as bundle:
            for member in bundle:
                if member.name in desired:
                    if not member.isfile() or member.size > 2_000_000:
                        raise ValueError("invalid blind-test source member")
                    with (
                        bundle.extractfile(member) as stream,
                        (vault / desired[member.name]).open("xb") as sink,
                    ):
                        shutil.copyfileobj(stream, sink)
                    copied.add(member.name)
        if copied != set(desired):
            raise ValueError("blind-test archive changed")
        old_hashes = {frame.rgb_sha256 for frame in frames}
        for i, (rgb, depth, pose) in enumerate(selected):
            name = f"blindtest_{i:05d}"
            record = Frame(
                frame_id=name,
                timestamp=float(rgb[0]),
                depth_timestamp=float(depth[0]),
                camera_id="camera0",
                sequence_id=root,
                rgb_path=f"rgb/{name}.png",
                depth_path=f"depth/{name}.png",
                rgb_sha256=sha256_file(vault / f"rgb/{name}.png"),
                depth_sha256=sha256_file(vault / f"depth/{name}.png"),
                T_world_camera=pose.tolist(),
            )
            if record.rgb_sha256 in old_hashes:
                raise ValueError("blind test duplicates an already exposed RGB observation")
            study_frames.append(record)
            origins.append(
                {
                    "frame_id": name,
                    "source_rgb_member": rgb[1],
                    "source_depth_member": depth[1],
                    "source_timestamp": record.timestamp,
                    "mode": "opaque curator extraction; not decoded before protocol freeze",
                }
            )
        metadata = metadata_of(manifest, "tum_m5_base")
        partitions = {
            "train": list(splits.train),
            "validation": list(splits.validation),
            "candidate": list(splits.candidate),
            "test": [f.frame_id for f in study_frames if f.frame_id.startswith("blindtest_")],
        }
        write_json(
            stage / "curation.json",
            {
                "schema_version": "1.0",
                "protocol_sha256": json_digest(protocol),
                "parent_manifest_sha256": sha256_file(source / "manifest.json"),
                "parent_frames_sha256": manifest.frames_sha256,
                "parent_split_sha256": manifest.split_sha256,
                "archive_sha256": pin["sha256"],
                "excluded_exposed_test_ids": list(splits.test),
                "origins": origins,
                "blindness_scope": (
                    "New pixel observations withheld; same scene and nearby "
                    "earlier test views were inspected in M3."
                ),
                "frames": [f.model_dump(mode="json") for f in study_frames],
                "metadata": metadata,
                "partitions": partitions,
            },
        )
        write_json(
            stage / "access-ledger.json",
            {
                "schema_version": "1.0",
                "events": [
                    {
                        "phase": "curator",
                        "ids": [f.frame_id for f in study_frames],
                        "access": "opaque copy/hash only; not learner/selector access",
                    }
                ],
            },
        )
        create_dataset(stage, stage / "base-dataset", [], "tum_m5_base")
        for p in vault.rglob("*.png"):
            p.chmod(0o444)
    return output


def _create_dataset(
    study: Path, output: Path, selected: list[str], scene_id: str, selection_key: str | None = None
) -> Path:
    curation = json.loads((study / "curation.json").read_text())
    frames = [Frame.model_validate(value) for value in curation["frames"]]
    partitions = {key: list(values) for key, values in curation["partitions"].items()}
    if len(selected) != len(set(selected)) or not set(selected).issubset(partitions["candidate"]):
        raise ValueError("acquisition must name unique candidate IDs only")
    if selected:
        seal = validate_seal(study)
        acquisition = next((row for row in seal.acquisitions if row.key == selection_key), None)
        if acquisition is None or list(acquisition.selected_ids) != selected:
            raise ValueError(
                "released observations must exactly match the named sealed acquisition"
            )
    selected_set = set(selected)
    partitions["train"] = [
        f.frame_id for f in frames if f.frame_id in set(partitions["train"]) | selected_set
    ]
    partitions["candidate"] = [name for name in partitions["candidate"] if name not in selected_set]
    allowed = set(partitions["train"] + partitions["validation"])
    with atomic_dataset(output, 400_000_000) as stage:
        for channel in ("rgb", "depth"):
            (stage / channel).mkdir()
        for frame in frames:
            if frame.frame_id in allowed:
                for channel in ("rgb", "depth"):
                    name = getattr(frame, channel + "_path")
                    os.link(local_file(study / "vault", name), stage / name)
        metadata = curation["metadata"] | {"scene_id": scene_id}
        finalize_dataset(stage, metadata, frames, partitions=partitions, observation_ids=allowed)
    return output


def append_access(study: Path, phase: str, ids: list[str], **details) -> None:
    with (study / "access-ledger.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ledger = json.loads((study / "access-ledger.json").read_text())
        ledger["events"].append(
            {"phase": phase, "ids": ids, "at": datetime.now(UTC).isoformat(), **details}
        )
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", dir=study, prefix=".ledger-", delete=False
            ) as stream:
                temporary = Path(stream.name)
                json.dump(ledger, stream, indent=2, sort_keys=True, allow_nan=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, study / "access-ledger.json")
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


@contextmanager
def release_operation(study: Path, phase: str, ids: list[str], **details):
    """Resume interrupted releases; completion is written only after verification."""
    key = json_digest({"phase": phase, "ids": ids, **details})
    events = json.loads((study / "access-ledger.json").read_text())["events"]
    terminal = {e.get("operation_id") for e in events if e.get("status") in ("completed", "failed")}
    pending = [
        e for e in events if e.get("operation_key") == key and e.get("operation_id") not in terminal
    ]
    operation_id = pending[-1]["operation_id"] if pending else uuid.uuid4().hex
    context = details | {"operation_key": key, "operation_id": operation_id}
    append_access(study, phase, ids, status="resumed" if pending else "started", **context)
    receipt = {}
    try:
        yield receipt
    except Exception as exc:
        append_access(study, phase, ids, status="failed", error=str(exc), **context)
        raise
    else:
        append_access(study, phase, ids, status="completed", **(context | receipt))


def create_dataset(
    study: Path, output: Path, selected: list[str], scene_id: str, selection_key: str | None = None
) -> Path:
    if not selected:
        return _create_dataset(study, output, selected, scene_id, selection_key)
    seal = validate_seal(study)
    row = next((r for r in seal.acquisitions if r.key == selection_key), None)
    if row is None or list(row.selected_ids) != selected:
        raise ValueError("released observations must exactly match the named sealed acquisition")
    with release_operation(
        study,
        "candidate_release",
        selected,
        selection_key=selection_key,
        dataset=str(output.absolute()),
        selection_seal_sha256=sha256_file(study / "selections-sealed.json"),
    ) as receipt:
        if output.exists():
            manifest, frames, splits = load_records(output, ("train", "validation"))
            curation = json.loads((study / "curation.json").read_text())
            partitions = curation["partitions"]
            actual_metadata = manifest.model_dump(
                mode="json",
                exclude={
                    "schema_version",
                    "world_units",
                    "world_frame",
                    "camera_axes",
                    "frames_sha256",
                    "split_sha256",
                },
            )
            if (
                actual_metadata != curation["metadata"] | {"scene_id": scene_id}
                or [f.model_dump(mode="json") for f in frames] != curation["frames"]
                or set(splits.train) != set(partitions["train"]) | set(selected)
                or set(splits.validation) != set(partitions["validation"])
                or set(splits.test) != set(partitions["test"])
                or set(splits.candidate) != set(partitions["candidate"]) - set(selected)
            ):
                raise ValueError("existing acquisition dataset differs from sealed inputs")
            for frame in frames:
                if frame.frame_id in splits.candidate and any(
                    (output / getattr(frame, c + "_path")).exists() for c in ("rgb", "depth")
                ):
                    raise ValueError("existing acquisition exposes unselected candidate pixels")
        else:
            _create_dataset(study, output, selected, scene_id, selection_key)
        receipt["dataset_manifest_sha256"] = sha256_file(output / "manifest.json")
    return output


def release_test(study: Path, dataset: Path) -> None:
    seal = validate_seal(study)
    _, frames, splits = load_records(dataset, ())
    curation = json.loads((study / "curation.json").read_text())
    expected = curation["partitions"]
    selected = set(splits.train) - set(expected["train"])
    if (
        [f.model_dump(mode="json") for f in frames] != curation["frames"]
        or set(splits.validation) != set(expected["validation"])
        or set(splits.test) != set(expected["test"])
        or not set(expected["train"]).issubset(splits.train)
        or set(splits.candidate) != set(expected["candidate"]) - selected
        or (selected and not any(selected == set(row.selected_ids) for row in seal.acquisitions))
    ):
        raise ValueError("test release dataset differs from the frozen curation/acquisitions")
    with release_operation(
        study,
        "test_release",
        list(splits.test),
        dataset_manifest_sha256=sha256_file(dataset / "manifest.json"),
        selection_seal_sha256=sha256_file(study / "selections-sealed.json"),
    ):
        for frame in frames:
            if frame.frame_id in splits.test:
                for channel in ("rgb", "depth"):
                    name = getattr(frame, channel + "_path")
                    target = dataset / name
                    if not target.exists():
                        os.link(local_file(study / "vault", name), target)
                    if sha256_file(target) != getattr(frame, channel + "_sha256"):
                        raise ValueError("released test content differs from frozen digest")
