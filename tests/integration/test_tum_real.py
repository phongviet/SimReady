import json
import os
from pathlib import Path

import pytest

from simready.data.dataset import validate_scene


@pytest.mark.real_data
def test_real_tum_capture_has_original_timing_and_frozen_splits():
    scene = Path(os.environ.get("SIMREADY_TUM_SCENE", "data/scenes/tum-fr1-desk"))
    if not scene.is_dir():
        if "SIMREADY_TUM_SCENE" in os.environ:
            pytest.fail(f"explicit real scene is missing: {scene}")
        pytest.skip("real TUM RGB-D sequence absent; follow docs/DATASET_PROTOCOL.md")
    result = validate_scene(scene)
    manifest = json.loads((scene / "manifest.json").read_text())
    assert result["kind"] == "real"
    assert result["frames"] >= 8
    assert manifest["source"]["license"] == "CC-BY-4.0"
    assert manifest["depth"]["meters_per_unit"] == 0.0002
    assert "motion" in manifest["pose_provenance"].lower()
    frames = [json.loads(line) for line in (scene / "frames.jsonl").read_text().splitlines()]
    assert all(frame["timestamp"] > 1_000_000_000 for frame in frames)
    assert all(abs(frame["timestamp"] - frame["depth_timestamp"]) <= 0.020001 for frame in frames)
