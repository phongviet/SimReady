"""Resolve immutable experiment source IDs after an attribution-only Git rewrite."""

import json
import re
import subprocess
from pathlib import Path

from simready.storage import PROJECT_ROOT


def source_at(revision: str, name: str, root: Path = PROJECT_ROOT) -> bytes:
    aliases = root / "configs/git-author-map.json"
    mapping = json.loads(aliases.read_text())["commits"] if aliases.exists() else {}
    resolved = mapping.get(revision, revision)
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", resolved):
        raise ValueError("invalid historical source revision")
    return subprocess.check_output(["git", "show", f"{resolved}:{name}"], cwd=root)
