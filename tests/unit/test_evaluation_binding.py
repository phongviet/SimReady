"""An internally valid cached report must still bind to the requested render batch."""

import json
import shutil
from pathlib import Path

import pytest

from simready.data.dataset import sha256_file, write_json
from simready.evaluation.config import EvaluationConfig
from simready.evaluation.runner import validate_evaluation, verify_evaluation_binding


def test_missing_stage_recovery_rejects_internally_valid_wrong_render_binding(scene, tmp_path):
    fixture = Path("src/simready/demo/analytic-plane")
    output = tmp_path / "recovered"
    shutil.copytree(fixture / "evaluation", output)
    args = (scene, fixture / "reconstruction", fixture / "renders", EvaluationConfig())
    verify_evaluation_binding(output, *args)
    inputs = json.loads((output / "inputs.json").read_text())
    inputs["renders_index_sha256"] = "a" * 64
    write_json(output / "inputs.json", inputs)
    metadata = json.loads((output / "evaluation.json").read_text())
    metadata["files_sha256"]["inputs.json"] = sha256_file(output / "inputs.json")
    write_json(output / "evaluation.json", metadata)
    validate_evaluation(output)  # Consistent internal hashes alone are insufficient.
    with pytest.raises(ValueError, match="requested references, renders"):
        verify_evaluation_binding(output, *args)
