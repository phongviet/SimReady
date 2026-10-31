"""Synthetic unit calculations only; never evidence of human-reviewed labels."""

import copy

import pytest

from simready.annotations.evaluate import coco_ap50, validate_review


def fixture():
    coco = {
        "images": [
            {"id": 1, "frame_id": "a", "width": 100, "height": 100},
            {"id": 2, "frame_id": "b", "width": 100, "height": 100},
        ],
        "categories": [{"id": 1, "name": "person"}, {"id": 2, "name": "bicycle"}],
        "annotations": [
            {"id": 1, "image_id": 1, "category_id": 1, "bbox": [10, 10, 20, 20], "iscrowd": 0}
        ],
    }
    approval = {
        "status": "approved",
        "reviewer_kind": "human",
        "reviewed_by": "UNIT FIXTURE ONLY — not real human review",
        "reviewed_at": "2026-10-31T00:00:00+00:00",
        "annotations_sha256": "coco",
        "dataset_manifest_sha256": "manifest",
        "split_sha256": "split",
        "reviewed_frame_ids": ["a", "b"],
    }
    return coco, approval


def check(coco, approval):
    return validate_review(
        coco,
        approval,
        coco_sha256="coco",
        manifest_sha256="manifest",
        split_sha256="split",
        frame_ids=["a", "b"],
    )


def test_review_requires_every_frame_and_matching_hashes():
    coco, approval = fixture()
    assert len(check(coco, approval)) == 2
    for change in [
        {"status": "draft"},
        {"reviewer_kind": "model"},
        {"reviewed_frame_ids": ["a"]},
        {"annotations_sha256": "changed"},
        {"split_sha256": "different"},
        {"reviewed_by": ""},
    ]:
        with pytest.raises(ValueError):
            check(coco, approval | change)


def test_bad_boxes_and_duplicate_ids_rejected():
    coco, approval = fixture()
    for box in [[-1, 0, 2, 2], [90, 90, 20, 20], [0, 0, 0, 10], [0, 0, float("nan"), 1]]:
        changed = copy.deepcopy(coco)
        changed["annotations"][0]["bbox"] = box
        with pytest.raises(ValueError):
            check(changed, approval)


def test_official_coco_perfect_empty_and_false_positive():
    pytest.importorskip("pycocotools")
    coco, _ = fixture()
    perfect = [{"image_id": 1, "category_id": 1, "bbox": [10, 10, 20, 20], "score": 0.9}]
    score = coco_ap50(coco, perfect)
    assert score["ap50"] == pytest.approx(1)
    assert score["threshold_0_5"] == {"tp": 1, "fp": 0, "fn": 0, "recall": 1}
    assert score["per_class"]["2"]["ap50"] is None
    empty = coco_ap50(coco, [])
    assert empty["ap50"] == 0 and empty["threshold_0_5"]["fn"] == 1
    bad = [{"image_id": 2, "category_id": 1, "bbox": [10, 10, 20, 20], "score": 0.99}] + perfect
    assert coco_ap50(coco, bad)["ap50"] == pytest.approx(0.5)


def test_duplicate_predictions_do_not_add_recall():
    pytest.importorskip("pycocotools")
    coco, _ = fixture()
    pred = [
        {"image_id": 1, "category_id": 1, "bbox": [10, 10, 20, 20], "score": s} for s in [0.9, 0.8]
    ]
    result = coco_ap50(coco, pred)
    assert result["threshold_0_5"] == {"tp": 1, "fp": 1, "fn": 0, "recall": 1}


def test_missing_human_approval_blocks_before_any_evaluation(tmp_path):
    from simready.annotations.evaluate import evaluate

    absent = tmp_path / "not-an-approval.json"
    with pytest.raises(ValueError, match="pending_human_review"):
        evaluate(tmp_path, tmp_path, tmp_path, tmp_path, tmp_path, absent, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_review_package_contains_only_drafts_and_hashes(scene, tmp_path):
    import json

    from simready.annotations.package import export

    output = tmp_path / "annotation-review"
    export(scene, output)
    metadata = json.loads((output / "package.json").read_text())
    coco = json.loads((output / "draft.coco.json").read_text())
    assert metadata["status"] == "pending_human_review"
    assert coco["annotations"] == []
    assert not (output / "approval.json").exists()
    assert "__PAYLOAD__" not in (output / "index.html").read_text()
    assert len(coco["images"]) == 2
    assert all(len(i["sha256"]) == 64 for i in coco["images"])
    with pytest.raises(ValueError, match="new"):
        export(scene, output)


def test_class_rule_version_is_bound_when_required():
    coco, approval = fixture()
    kwargs = dict(
        coco_sha256="coco",
        manifest_sha256="manifest",
        split_sha256="split",
        frame_ids=["a", "b"],
        rules_sha256="frozen-rules",
    )
    with pytest.raises(ValueError, match="mismatched human approval"):
        validate_review(coco, approval, **kwargs)
    assert (
        len(
            validate_review(
                coco, approval | {"annotation_protocol_sha256": "frozen-rules"}, **kwargs
            )
        )
        == 2
    )
