import json
import os
from pathlib import Path

import numpy as np
import pytest

from simready.reconstruction.contracts import ReconstructionConfig
from simready.reconstruction.gsplat import GsplatBackend, validate_artifact


@pytest.mark.gpu
def test_trained_checkpoint_reloads_and_renders_frozen_camera(scene, tmp_path):
    if os.environ.get("SIMREADY_GPU_TESTS") != "1":
        pytest.skip("run make test-gpu to exercise actual CUDA training and reload")
    config = ReconstructionConfig.model_validate_json(Path("configs/recon_smoke.json").read_text())
    backend = GsplatBackend()
    artifact = backend.train(scene, config, tmp_path / "artifact")
    metadata = validate_artifact(artifact)
    assert metadata["worker"]["iterations"] == 40
    assert metadata["worker"]["final_gaussians"] > 0
    with (artifact / "gaussian.ply").open("rb") as stream:
        header = []
        while (line := stream.readline()) != b"end_header\n":
            assert line, "PLY header is incomplete"
            header.append(line.decode("ascii"))
        count = metadata["worker"]["final_gaussians"]
        assert f"element vertex {count}\n" in header
        assert "format binary_little_endian 1.0\n" in header
        ply = np.frombuffer(stream.read(), dtype="<f4").reshape(count, -1)
    with np.load(artifact / "gaussians.npz", allow_pickle=False) as arrays:
        np.testing.assert_allclose(ply[:, :3], arrays["means"], atol=1e-6)
        np.testing.assert_allclose(np.linalg.norm(ply[:, -4:], axis=1), 1, atol=1e-5)
    output = backend.render(artifact, scene, "test", tmp_path / "renders")
    renders = json.loads((output / "renders.json").read_text())
    assert renders["split"] == "test"
    assert len(renders["cameras"]) == 2
    for camera in renders["cameras"]:
        depth = np.load(output / f"{camera['frame_id']}-depth.npy", allow_pickle=False)
        alpha = np.load(output / f"{camera['frame_id']}-alpha.npy", allow_pickle=False)
        assert (alpha > 0.1).any()
        assert np.isfinite(depth).all()
        assert np.median(depth[alpha > 0.1]) == pytest.approx(2.0, abs=0.3)
