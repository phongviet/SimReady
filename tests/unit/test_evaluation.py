import json
import shutil
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from simready.data.dataset import write_json
from simready.data.synthetic import make_synthetic
from simready.evaluation.config import EvaluationConfig
from simready.evaluation.metrics import (
    depth_metrics,
    detection_metrics,
    gated_pairs,
    image_metrics,
    iou_matrix,
)
from simready.evaluation.runner import verify_inputs

FIXTURE = Path(__file__).resolve().parents[2] / "src/simready/demo/analytic-plane"


def prediction(box=(0, 0, 10, 10), score=0.9, label=1):
    return {"box": list(box), "score": score, "label": label}


def test_rgb_exact_match_is_json_safe_and_finite_psnr_known():
    image = np.zeros((8, 8, 3), dtype=np.uint8)
    identical = image_metrics(image, image)
    assert identical["rgb_exact_match"] and identical["psnr_db"] is None
    assert identical["ssim"] == pytest.approx(1)
    different = image_metrics(image, image + 255)
    assert different["psnr_db"] == 0
    assert different["rgb_mse"] == 1
    assert 0 < different["ssim"] < 0.001
    json.dumps(identical, allow_nan=False)
    with pytest.raises(ValueError, match="uint8"):
        image_metrics(image.astype(float), image)
    with pytest.raises(ValueError, match="same"):
        image_metrics(image, image[:7])


def test_depth_invalids_alpha_and_completeness_are_separate():
    real = np.array([[1, 2, 0], [np.nan, 4, 5]])
    rendered = np.array([[2, 0, 1], [5, np.inf, 7]])
    alpha = np.array([[1, 1, 1], [1, 1, 0.1]])
    result, mask = depth_metrics(real, rendered, alpha, 0.1)
    assert result == {
        "depth_reference_pixels": 4,
        "depth_evaluated_pixels": 2,
        "depth_completeness": 0.5,
        "depth_mae_m": 1.5,
        "depth_rmse_m": np.sqrt(2.5),
    }
    np.testing.assert_array_equal(mask, [[True, False, False], [False, False, True]])
    unknown, _ = depth_metrics(np.zeros((2, 2)), np.ones((2, 2)), np.ones((2, 2)))
    assert unknown["depth_completeness"] is None and unknown["depth_mae_m"] is None
    unsupported, _ = depth_metrics(np.ones((2, 2)), np.ones((2, 2)), np.zeros((2, 2)))
    assert unsupported["depth_completeness"] == 0 and unsupported["depth_mae_m"] is None


def test_hungarian_gate_maximizes_valid_cardinality_before_iou():
    matrix = np.array([[0.9, 0.6], [0.6, 0.4]])
    assert gated_pairs(matrix, matrix >= 0.5) == [(0, 1), (1, 0)]
    assert gated_pairs(np.zeros((0, 2)), np.zeros((0, 2), dtype=bool)) == []


def test_matching_empty_duplicate_threshold_and_known_localization():
    empty = detection_metrics([], [], 100, 100)
    assert empty["empty_both"] and empty["mean_matched_iou"] is None
    one = prediction()
    result = detection_metrics([one, one], [one, prediction(score=0.49)], 100, 100)
    assert result["matched_count"] == 1 and result["disappeared_count"] == 1
    shifted = detection_metrics([one], [prediction((2, 0, 12, 10), 0.8)], 100, 100)
    assert shifted["mean_matched_iou"] == pytest.approx(2 / 3)
    assert shifted["mean_center_error_normalized"] == pytest.approx(0.02)
    assert shifted["mean_confidence_gap"] == pytest.approx(-0.1)
    assert detection_metrics([prediction(score=0.5)], [one], 100, 100)["matched_count"] == 1


def test_class_disagreement_is_not_a_valid_match_or_accuracy():
    result = detection_metrics([prediction(label=1)], [prediction(label=2)], 100, 100)
    assert result["matched_count"] == 0
    assert result["disappeared_count"] == result["appeared_count"] == 1
    assert len(result["class_mismatch_candidates"]) == 1
    assert result["per_class"] == {
        "1": {"real": 1, "rendered": 0, "matched": 0},
        "2": {"real": 0, "rendered": 1, "matched": 0},
    }
    assert iou_matrix([prediction()], [prediction((20, 20, 30, 30))])[0, 0] == 0
    with pytest.raises(ValueError, match="invalid"):
        detection_metrics([prediction(score=float("nan"))], [], 100, 100)


def test_protocol_pins_network_and_forbids_accuracy_flags():
    assert EvaluationConfig().lpips_network == "squeeze"
    for change in ({"lpips_network": "alex"}, {"confidence_threshold": 0}, {"map": True}):
        with pytest.raises(ValidationError):
            EvaluationConfig(**change)


def test_frozen_evaluation_rejects_train_candidate_subset_and_camera_changes(tmp_path):
    dataset = tmp_path / "dataset"
    make_synthetic(dataset)
    *_, selected, cameras, model, images = verify_inputs(
        dataset, FIXTURE / "reconstruction", FIXTURE / "renders"
    )
    assert [f.frame_id for f in selected] == ["frame_00006", "frame_00007"]
    assert set(model["provenance"]["training_frame_ids"]).isdisjoint(f.frame_id for f in selected)
    renders = tmp_path / "renders"
    shutil.copytree(FIXTURE / "renders", renders)
    for split in ("train", "candidate"):
        metadata = images | {"split": split}
        write_json(renders / "renders.json", metadata)
        with pytest.raises(ValueError, match="only frozen"):
            verify_inputs(dataset, FIXTURE / "reconstruction", renders)
    write_json(renders / "renders.json", images | {"cameras": cameras[:1]})
    with pytest.raises(ValueError, match="complete frozen"):
        verify_inputs(dataset, FIXTURE / "reconstruction", renders)
    changed = json.loads(json.dumps(images))
    changed["cameras"][0]["K"][0][0] += 1
    write_json(renders / "renders.json", changed)
    with pytest.raises(ValueError, match="cameras"):
        verify_inputs(dataset, FIXTURE / "reconstruction", renders)
