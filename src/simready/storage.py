"""Project budget includes hidden files and dependencies; no destructive cleanup."""

import os
import stat
from pathlib import Path

BUDGET_BYTES = 30_000_000_000
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def project_bytes(root: Path = PROJECT_ROOT) -> int:
    if not root.is_dir():
        raise ValueError(f"storage root is not a directory: {root}")
    total = os.lstat(root).st_blocks * 512
    stack = [os.fspath(root)]
    while stack:
        with os.scandir(stack.pop()) as entries:
            for entry in entries:
                metadata = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(metadata.st_mode):
                    total += metadata.st_blocks * 512
                    stack.append(entry.path)
                else:
                    # Count every hardlink path and the metadata of directory symlinks too.
                    # Never traverse a symlink target or discount sparse logical bytes.
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
