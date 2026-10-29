import json
import os
from pathlib import Path

import numpy as np
import pytest

from simready.data.dataset import validate_scene
from simready.data.redwood import SAMPLE_SHA256, import_redwood


@pytest.mark.official_data
def test_official_synthetic_rgbd_import_and_supplied_pose(tmp_path):
    source = Path(os.environ.get("SIMREADY_OFFICIAL_SAMPLE", "data/raw/redwood"))
    if not source.is_dir():
        if "SIMREADY_OFFICIAL_SAMPLE" in os.environ:
            pytest.fail(f"explicitly configured official sample is missing: {source}")
        pytest.skip("official sample absent: run make fetch-example or make test-real")
    output = tmp_path / "real-scene"
    import_redwood(source, output)
    result = validate_scene(output)
    assert result["kind"] == "synthetic" and result["frames"] == 5
    assert result["splits"] == {"train": 2, "validation": 1, "candidate": 1, "test": 1}
    assert result["valid_depth_pixels"] > 0
    manifest = json.loads((output / "manifest.json").read_text())
    if (source.parent / "SampleRedwoodRGBDImages.zip").exists():
        assert manifest["source"]["archive_sha256"] == SAMPLE_SHA256
    camera = manifest["cameras"]["camera0"]
    assert (camera["fx"], camera["fy"], camera["cx"], camera["cy"]) == (525, 525, 319.5, 239.5)
    first = json.loads((output / "frames.jsonl").read_text().splitlines()[0])
    # First supplied odometry pose has identity rotation and (2,2,-.3)m translation.
    # Independently expected canonical pose after X rotation by pi:
    expected = [[1, 0, 0, 2], [0, -1, 0, -2], [0, 0, -1, 0.3], [0, 0, 0, 1]]
    np.testing.assert_allclose(first["T_world_camera"], expected, atol=1e-12)
    assert "Frame index only" in manifest["timestamp_provenance"]
    assert "estimated poses" in manifest["pose_provenance"]
    assert (output / "calib/odometry.log").read_bytes() == (source / "odometry.log").read_bytes()
