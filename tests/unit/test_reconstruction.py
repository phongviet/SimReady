import json
import sys
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from simready.data.dataset import sha256_file, write_json
from simready.reconstruction.contracts import ReconstructionConfig
from simready.reconstruction.gsplat import GsplatBackend, prepare_training, validate_artifact


@pytest.fixture
def config():
    return ReconstructionConfig.model_validate_json(Path("configs/recon_smoke.json").read_text())


def test_preparation_uses_only_frozen_training_observations(scene, config, tmp_path):
    output = tmp_path / "prepared"
    output.mkdir()
    record = prepare_training(scene, config, output)
    splits = json.loads((scene / "splits.json").read_text())
    assert record["training_frame_ids"] == splits["train"]
    forbidden = set(splits["test"] + splits["candidate"] + splits["validation"])
    assert not forbidden.intersection(record["training_frame_ids"])
    with np.load(output / "training.npz", allow_pickle=False) as arrays:
        assert len(arrays["images"]) == 4
        assert arrays["means"].shape[1] == 3
        # Known fixture plane stays exactly at -2m, without centering/rescaling.
        np.testing.assert_allclose(arrays["means"][:, 2], -2, atol=1e-6)
        assert arrays["means"].shape[0] <= config.max_initial_gaussians
        assert arrays["images"].dtype == np.float32


@pytest.mark.parametrize(
    "change",
    [
        {"width": 0},
        {"iterations": 0},
        {"sh_degree": 4},
        {"max_gaussians": 10},
        {"refine_stop": 41},
        {"seed": -1},
        {"schema_version": "2.0"},
    ],
)
def test_config_rejects_invalid_or_unsafe_settings(config, change):
    with pytest.raises(ValidationError):
        ReconstructionConfig(**(config.model_dump() | change))


def make_artifact(output):
    output.mkdir()
    count = 8
    np.savez_compressed(
        output / "gaussians.npz",
        means=np.zeros((count, 3), np.float32),
        scales=np.zeros((count, 3), np.float32),
        quats=np.tile(np.array([[1, 0, 0, 0]], np.float32), (count, 1)),
        opacities=np.zeros(count, np.float32),
        sh0=np.zeros((count, 1, 3), np.float32),
        shN=np.zeros((count, 0, 3), np.float32),
    )
    for name in ("gaussian.ply", "training-log.jsonl", "train-job.json"):
        (output / name).write_text("unit fixture metadata\n")
    write_json(
        output / "artifact.json",
        {
            "schema_version": "1.0",
            "backend": "gsplat",
            "config": {"sh_degree": 0},
            "worker": {"final_gaussians": count},
            "files_sha256": {
                name: sha256_file(output / name)
                for name in (
                    "gaussians.npz",
                    "gaussian.ply",
                    "training-log.jsonl",
                    "train-job.json",
                )
            },
        },
    )


def test_artifact_integrity_detects_checkpoint_edits(tmp_path):
    output = tmp_path / "artifact"
    make_artifact(output)
    assert validate_artifact(output)["worker"]["final_gaussians"] == 8
    with (output / "gaussians.npz").open("ab") as out:
        out.write(b"tampered")
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_artifact(output)


def test_missing_worker_fails_before_creating_output(scene, config, tmp_path):
    output = tmp_path / "artifact"
    with pytest.raises(ValueError, match="GPU worker is not installed"):
        GsplatBackend(tmp_path / "missing-python").train(scene, config, output)
    assert not output.exists()


def test_worker_failure_preserves_actionable_diagnostics_and_cleans_staging(
    scene, config, tmp_path
):
    backend = GsplatBackend(Path(sys.executable))
    failing = tmp_path / "worker.py"
    failing.write_text("raise RuntimeError('deliberate worker failure')\n")
    backend.worker = failing
    with pytest.raises(ValueError, match="deliberate worker failure"):
        backend.train(scene, config, tmp_path / "artifact")
    assert not (tmp_path / "artifact").exists()
    assert not list(tmp_path.glob(".artifact-*"))


def test_invalid_split_fails_before_gpu_dispatch(tmp_path):
    with pytest.raises(ValueError, match="unknown split"):
        GsplatBackend().render(tmp_path, tmp_path, "unknown", tmp_path / "out")
