"""Fetch the official TUM fr1 desk archive, bounded and hashed; never extract blindly."""

import hashlib
import json
import tempfile
import urllib.request
from pathlib import Path

from simready.storage import check_budget

URL = "https://cvg.cit.tum.de/rgbd/dataset/freiburg1/rgbd_dataset_freiburg1_desk.tgz"
MAX_BYTES = 500_000_000
EXPECTED_BYTES = 344_011_403
EXPECTED_SHA256 = "e983d6830916e66dc4a46a71368046b149b283de87769690e7aa4e0b9483530c"


def main() -> None:
    check_budget(2_000_000_000)
    output = Path("data/raw/rgbd_dataset_freiburg1_desk.tgz")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        with output.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if output.stat().st_size != EXPECTED_BYTES or digest != EXPECTED_SHA256:
            raise SystemExit("Existing TUM archive does not match the pinned official download")
        print("Existing TUM archive matches pinned bytes and SHA-256; reuse verified.")
        return
    lock = output.with_suffix(".download-lock")
    lock.mkdir()
    temporary = tempfile.NamedTemporaryFile(
        prefix="tum-", suffix=".part", dir=output.parent, delete=False
    )
    partial = Path(temporary.name)
    digest = hashlib.sha256()
    size = 0
    try:
        with temporary as sink, urllib.request.urlopen(URL, timeout=60) as source:
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
        if size != EXPECTED_BYTES or digest.hexdigest() != EXPECTED_SHA256:
            raise ValueError("Downloaded TUM archive differs from pinned bytes/SHA-256")
        partial.rename(output)
    finally:
        partial.unlink(missing_ok=True)
        lock.rmdir()
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
