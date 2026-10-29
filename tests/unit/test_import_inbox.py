import pytest

from simready.pipeline.imports import ImportStore, fingerprint
from simready.scene.store import SceneStore


def test_inbox_digest_tracks_changes_and_rejects_links(tmp_path):
    store = ImportStore(SceneStore(tmp_path / "registry"))
    source = store.root / "inbox/source"
    source.mkdir()
    (source / "a").write_text("original")
    before = fingerprint(source)
    (source / "a").write_text("changed")
    assert fingerprint(source) != before
    outside = tmp_path / "outside"
    outside.mkdir()
    (source / "linked").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlinks"):
        fingerprint(source)
    (store.root / "inbox/escape").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="escapes"):
        store.source_path("escape")
