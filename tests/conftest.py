from pathlib import Path

import pytest

from simready.data.synthetic import make_synthetic


def pytest_configure(config):
    # Pytest owns/cleans basetemp, but does not create a missing parent directory.
    basetemp = config.getoption("basetemp")
    if basetemp:
        Path(basetemp).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


@pytest.fixture
def scene(tmp_path: Path) -> Path:
    output = tmp_path / "scene"
    make_synthetic(output)
    return output
