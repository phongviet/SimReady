"""Export a local COCO labeling/review package; no automatic approvals."""

import argparse
import json
import shutil
from pathlib import Path

from simready.data.dataset import atomic_dataset, local_file, sha256_file, write_json
from simready.reconstruction.gsplat import load_records
from simready.storage import PROJECT_ROOT

# Fixed subset chosen for office vocabulary; final coverage requires actual human review.
CATEGORIES = [
    (1, "person"),
    (44, "bottle"),
    (47, "cup"),
    (62, "chair"),
    (64, "potted plant"),
    (72, "tv"),
    (73, "laptop"),
    (74, "mouse"),
    (76, "keyboard"),
    (77, "cell phone"),
    (84, "book"),
    (85, "clock"),
    (88, "teddy bear"),
]


def export(scene: Path, output: Path, *, split="test", frame_ids=None):
    manifest, frames, splits = load_records(scene, ())
    allowed = list(getattr(splits, split))
    selected = allowed if frame_ids is None else list(frame_ids)
    if not selected or len(selected) != len(set(selected)) or not set(selected) <= set(allowed):
        raise ValueError("annotation frames must be unique members of the declared frozen split")
    by_id = {f.frame_id: f for f in frames}
    with atomic_dataset(output, len(selected) * 2_000_000 + 2_000_000) as stage:
        (stage / "images").mkdir()
        images = []
        for i, name in enumerate(selected):
            frame = by_id[name]
            camera = manifest.cameras[frame.camera_id]
            if sha256_file(local_file(scene, frame.rgb_path)) != frame.rgb_sha256:
                raise ValueError("reference image differs from frozen record")
            destination = f"images/{name}.png"
            shutil.copyfile(local_file(scene, frame.rgb_path), stage / destination)
            images.append(
                {
                    "id": i + 1,
                    "frame_id": name,
                    "file_name": destination,
                    "width": camera.width,
                    "height": camera.height,
                    "sha256": frame.rgb_sha256,
                }
            )
        coco = {
            "info": {"status": "draft_not_ground_truth", "dataset_scene_id": manifest.scene_id},
            "images": images,
            "categories": [{"id": i, "name": name} for i, name in CATEGORIES],
            "annotations": [],
        }
        shutil.copyfile(PROJECT_ROOT / "docs/ANNOTATION_PROTOCOL.md", stage / "annotation-rules.md")
        payload = {
            "scene_id": manifest.scene_id,
            "annotation_protocol_sha256": sha256_file(stage / "annotation-rules.md"),
            "split": split,
            "coco": coco,
            "dataset_manifest_sha256": sha256_file(scene / "manifest.json"),
            "split_sha256": manifest.split_sha256,
        }
        template = Path(__file__).with_name("review.html").read_text()
        embedded = json.dumps(payload, ensure_ascii=True).replace("<", "\\u003c")
        (stage / "index.html").write_text(template.replace("__PAYLOAD__", embedded))
        write_json(stage / "draft.coco.json", coco)
        write_json(
            stage / "package.json",
            {
                **{k: v for k, v in payload.items() if k != "coco"},
                "status": "pending_human_review",
                "frame_ids": selected,
                "scope": "No labels or approvals are generated; human review required.",
                "files_sha256": {
                    str(p.relative_to(stage)): sha256_file(p)
                    for p in stage.rglob("*")
                    if p.is_file()
                },
            },
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--split", choices=["test", "candidate"], default="test")
    parser.add_argument("--frame-ids", nargs="+")
    args = parser.parse_args()
    export(args.scene, args.out, split=args.split, frame_ids=args.frame_ids)
