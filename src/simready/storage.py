"""Project budget includes hidden files and dependencies; no destructive cleanup."""

import os
from pathlib import Path

BUDGET_BYTES = 30_000_000_000
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def project_bytes(root: Path = PROJECT_ROOT) -> int:
    if not root.is_dir():
        raise ValueError(f"storage root is not a directory: {root}")
    total = 0
    for directory, _, names in os.walk(root, followlinks=False):
        total += Path(directory).lstat().st_blocks * 512
        for name in names:
            path = Path(directory) / name
            # Count hard-linked files per path conservatively; do not traverse symlinks.
            metadata = path.lstat()
            total += max(metadata.st_size, metadata.st_blocks * 512)
    return total


def check_budget(
    additional_bytes: int = 0, root: Path = PROJECT_ROOT, limit: int = BUDGET_BYTES
) -> int:
    if additional_bytes < 0:
        raise ValueError("additional bytes must be nonnegative")
    used = project_bytes(root)
    if used + additional_bytes >= limit:
        raise ValueError(f"storage budget exceeded: {used} + {additional_bytes} >= {limit} bytes")
    return used


if __name__ == "__main__":
    import json

    print(
        json.dumps(
            {"root": str(PROJECT_ROOT), "used_bytes": check_budget(), "limit_bytes": BUDGET_BYTES},
            indent=2,
        )
    )
