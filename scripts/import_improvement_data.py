"""Freeze 256-frame splits before extraction; only 16 candidate pilots may be inspected."""

import json
from pathlib import Path

from simready.data.dataset import sha256_file, write_json
from simready.data.tum import import_tum
from simready.storage import check_budget


def partitions():
    ids = [f"frame_{i:05d}" for i in range(256)]
    pilot = ids[::16]
    remaining = [name for name in ids if name not in set(pilot)]
    return {
        "train": remaining[:112],
        "validation": remaining[112:144],
        "candidate": sorted(pilot + remaining[144:176]),
        "test": remaining[176:],
    }, pilot


def main():
    root = Path("experiments/improvement-data-2")
    root.mkdir(parents=True, exist_ok=True)
    splits, pilot = partitions()
    for source, name in [("freiburg1_room", "tum-fr1-room"), ("freiburg2_desk", "tum-fr2-desk")]:
        output = Path("data/scenes") / name
        archive = Path("data/raw/improvement-1") / f"rgbd_dataset_{source}.tgz"
        acquisition = json.loads(archive.with_suffix(".source.json").read_text())
        if sha256_file(archive) != acquisition["sha256"]:
            raise ValueError("archive differs from observed acquisition pin")
        plan = root / f"{name}-split-plan.json"
        record = {
            "sequence": source,
            "archive_sha256": acquisition["sha256"],
            "max_frames": 256,
            "partitions": splits,
            "candidate_pilot": pilot,
            "protocol_sha256": sha256_file(Path("docs/INDEPENDENT_SCENE_PROTOCOL.md")),
            "status": (
                "reuse_existing_frozen_dataset"
                if output.exists()
                else "frozen_before_pixel_extraction"
            ),
        }
        if name == "tum-fr1-room" and output.exists():
            original = Path("experiments/improvement-data-1") / f"{name}-split-plan.json"
            record["original_pre_extraction_plan_sha256"] = sha256_file(original)
        if plan.exists():
            record["status"] = json.loads(plan.read_text())["status"]
            if json.loads(plan.read_text()) != record:
                raise ValueError("split plan changed; use a new experiment ID")
        else:
            write_json(plan, record)
        if output.exists():
            actual = json.loads((output / "splits.json").read_text())
            if any(actual[k] != v for k, v in splits.items()):
                raise ValueError("existing dataset differs from frozen split plan")
        else:
            check_budget(1_100_000_000)
            import_tum(archive, output, 256, partitions=splits)
        record_path = root / f"{name}-records.json"
        hashes = {
            n: sha256_file(output / n) for n in ("manifest.json", "frames.jsonl", "splits.json")
        }
        if record_path.exists():
            if json.loads(record_path.read_text()) != hashes:
                raise ValueError("dataset hashes changed after import")
        else:
            write_json(record_path, hashes)
        print(name, {k: len(v) for k, v in splits.items()}, flush=True)


if __name__ == "__main__":
    main()
