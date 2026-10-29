"""Hand-calculated statistics and adversarial exports; fixture values are not results."""

import json
from pathlib import Path

import numpy as np
import pytest

from simready.data.dataset import sha256_file, write_json
from simready.research.analysis import aggregate, describe, unmatched_fraction, validate_analysis
from simready.research.contracts import StudyConfig


def test_prediction_disagreement_is_not_undefined_empty_pair_success():
    assert (
        unmatched_fraction(
            {"real_count": 0, "rendered_count": 0, "disappeared_count": 0, "appeared_count": 0}
        )
        is None
    )
    assert (
        unmatched_fraction(
            {"real_count": 2, "rendered_count": 2, "disappeared_count": 1, "appeared_count": 1}
        )
        == 0.5
    )
    assert describe([None, None])["mean"] is None
    assert describe([3])["sample_sd"] is None


def test_seed_statistics_are_paired_not_independent_frame_confidence():
    config = StudyConfig.model_validate_json(Path("configs/recapture.json").read_text())
    runs, rows = [], []
    values = {
        "base": [1.0, 2.0, 3.0],
        "risk": [2.0, 3.0, 4.0],
        "random": [4.0, 4.0, 4.0],
        "farthest": [2.0, 2.0, 2.0],
    }
    for method in config.methods:
        for seed, value in zip(config.seeds, values[method], strict=True):
            key = f"{method}-s{seed}"
            metrics = dict(
                lpips=value,
                psnr_db=10.0,
                ssim=0.5,
                depth_mae_m=0.1,
                depth_rmse_m=0.2,
                depth_completeness=0.8,
                unmatched_fraction=0.5,
                unmatched_count=2.0,
            )
            runs.append({"run": key, "method": method, "seed": seed, "means": metrics})
            for i in range(3):
                rows.append(
                    {
                        "run": key,
                        "method": method,
                        "seed": seed,
                        "frame_id": f"f{i}",
                        "pose_block": i + 1,
                        "distance_m": 0.05,
                        "rotation_deg": 5.0,
                        **metrics,
                    }
                )
    result = aggregate(rows, runs, config)
    assert result["methods"]["risk"]["lpips"]["mean"] == 3.0
    assert result["methods"]["risk"]["lpips"]["sample_sd"] == 1.0
    paired = result["paired_risk_minus_random"]["lpips"]
    assert paired["values"] == [-2.0, -1.0, 0.0] and paired["mean"] == -1.0
    assert paired["sample_sd"] == 1.0 and paired["n"] == 3
    assert result["relative_improvement_percent_vs_base"]["risk"]["lpips"] == -50.0
    assert result["ranking_counterexamples"] == []
    assert all(r["rho"] is None and r["reason"] for r in result["correlations"])
    empty = [b for b in result["novelty_bins"] if not b["views"]]
    assert empty and all(b["means"]["lpips"] is None for b in empty)
    np.testing.assert_allclose(describe([1.0, 2.0, 3.0])["sample_sd"], 1.0)


def test_analysis_exports_reject_missing_files_changed_bytes_and_path_escape(tmp_path):
    names = {
        "metrics_summary.json",
        "per_view.csv",
        "runs.csv",
        "predictions_real.jsonl",
        "predictions_rendered.jsonl",
        "report.md",
        "report.html",
        "checks.json",
        "config.yaml",
        "environment.json",
        "git_commit.txt",
        "dataset_and_split_hash.json",
    }
    for name in names:
        (tmp_path / name).write_text("fixture\n")
    metadata = {
        "schema_version": "1.0",
        "type": "recapture_case_study",
        "files_sha256": {name: sha256_file(tmp_path / name) for name in names},
    }
    write_json(tmp_path / "analysis.json", metadata)
    validate_analysis(tmp_path)
    (tmp_path / "per_view.csv").write_text("altered\n")
    with pytest.raises(ValueError, match="content changed"):
        validate_analysis(tmp_path)
    (tmp_path / "per_view.csv").write_text("fixture\n")
    metadata["files_sha256"]["../escape"] = "a" * 64
    write_json(tmp_path / "analysis.json", metadata)
    with pytest.raises(ValueError, match="traversal"):
        validate_analysis(tmp_path)
    metadata["files_sha256"] = {}
    (tmp_path / "analysis.json").write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="required benchmark"):
        validate_analysis(tmp_path)
