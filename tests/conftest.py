from pathlib import Path

import pytest

from simready.data.synthetic import make_synthetic


@pytest.fixture
def scene(tmp_path: Path) -> Path:
    output = tmp_path / "scene"
    make_synthetic(output)
    return output
