import json

import pytest

from simready.research.data import append_access


def test_failed_atomic_ledger_replace_preserves_previous_bytes(tmp_path, monkeypatch):
    path = tmp_path / "access-ledger.json"
    original = '{"events": []}\n'
    path.write_text(original)

    def fail(*args):
        raise OSError("injected failed replacement")

    monkeypatch.setattr("simready.research.data.os.replace", fail)
    with pytest.raises(OSError, match="replacement"):
        append_access(tmp_path, "fixture", [])
    assert path.read_text() == original
    assert json.loads(path.read_text())["events"] == []
    assert list(tmp_path.glob(".ledger-*")) == []
