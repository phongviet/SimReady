"""Fetch the official TUM fr1 desk archive, bounded and hashed; never extract blindly."""

import hashlib
import json
import urllib.request
from pathlib import Path

from simready.storage import check_budget

URL = "https://cvg.cit.tum.de/rgbd/dataset/freiburg1/rgbd_dataset_freiburg1_desk.tgz"
MAX_BYTES = 500_000_000


def main() -> None:
    check_budget(2_000_000_000)
    output = Path("data/raw/rgbd_dataset_freiburg1_desk.tgz")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise SystemExit("TUM archive already exists; verify its recorded hash before reuse")
    partial = output.with_suffix(".tgz.part")
    digest = hashlib.sha256()
    size = 0
    try:
        with urllib.request.urlopen(URL, timeout=60) as source, partial.open("xb") as sink:
            declared = int(source.headers.get("Content-Length", 0))
            if declared > MAX_BYTES:
                raise ValueError("TUM download exceeds 500 MB cap")
            while chunk := source.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError("TUM download exceeds 500 MB cap")
                sink.write(chunk)
                digest.update(chunk)
                if size % (32 * 1024 * 1024) == 0:
                    print(f"Downloaded {size} bytes", flush=True)
            if declared and size != declared:
                raise ValueError("incomplete TUM download")
            final_url = source.url
        partial.rename(output)
    finally:
        partial.unlink(missing_ok=True)
    record = {
        "source": URL,
        "resolved_url": final_url,
        "bytes": size,
        "sha256": digest.hexdigest(),
        "license": "CC-BY-4.0",
        "license_source": "https://cvg.cit.tum.de/data/datasets/rgbd-dataset#license",
    }
    output.with_suffix(".source.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2), flush=True)
    check_budget()


if __name__ == "__main__":
    main()
