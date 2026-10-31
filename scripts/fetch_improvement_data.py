"""Bounded official TUM fallback acquisition; observed hashes, no access bypass."""

import hashlib
import json
import os
import urllib.request
from pathlib import Path

from simready.data.dataset import sha256_file, write_json
from simready.storage import check_budget

SOURCES = {
    "freiburg1_room": ("freiburg1", 782_381_450, 900_000_000),
    "freiburg2_desk": ("freiburg2", 1_893_351_095, 2_200_000_000),
}


def main():
    # Reserve for both acquisitions, selected data, models and evaluations.
    root = Path("data/raw/improvement-1")
    missing_bytes = sum(
        size
        for seq, (_, size, _) in SOURCES.items()
        if not (root / f"rgbd_dataset_{seq}.tgz").exists()
    )
    check_budget(missing_bytes + 6_000_000_000)
    root.mkdir(parents=True, exist_ok=True)
    for sequence, (group, expected_bytes, cap) in SOURCES.items():
        output = root / f"rgbd_dataset_{sequence}.tgz"
        record = output.with_suffix(".source.json")
        if output.exists():
            if not record.exists():
                raise ValueError("existing archive lacks acquisition record")
            pinned = json.loads(record.read_text())
            if output.stat().st_size != expected_bytes or sha256_file(output) != pinned["sha256"]:
                raise ValueError("existing acquisition differs from observed pin")
            continue
        url = f"https://cvg.cit.tum.de/rgbd/dataset/{group}/{output.name}"
        partial = output.with_suffix(".part")
        lock = output.with_suffix(".lock")
        lock.mkdir()
        total = 0
        digest = hashlib.sha256()
        try:
            with partial.open("xb") as sink, urllib.request.urlopen(url, timeout=45) as source:
                declared = int(source.headers.get("Content-Length", 0))
                if declared != expected_bytes or declared > cap:
                    raise ValueError("publisher archive size changed; review before acquisition")
                resolved = source.url
                while chunk := source.read(1024 * 1024):
                    total += len(chunk)
                    if total > cap:
                        raise ValueError("download exceeds explicit sequence limit")
                    sink.write(chunk)
                    digest.update(chunk)
                    if total % (64 * 1024 * 1024) == 0:
                        print(sequence, total, flush=True)
                if total != expected_bytes:
                    raise ValueError("incomplete official archive")
                sink.flush()
                os.fsync(sink.fileno())
            partial.rename(output)
            write_json(
                record,
                {
                    "source": url,
                    "resolved_url": resolved,
                    "bytes": total,
                    "sha256": digest.hexdigest(),
                    "license": "CC-BY-4.0",
                    "hash_provenance": (
                        "Observed official HTTPS bytes; not a publisher-signed digest."
                    ),
                    "attribution": "Sturm et al., IROS 2012",
                    "license_source": "https://cvg.cit.tum.de/data/datasets/rgbd-dataset#license",
                },
            )
            print(sequence, "verified bytes", total, digest.hexdigest(), flush=True)
        finally:
            partial.unlink(missing_ok=True)
            lock.rmdir()
        check_budget()


if __name__ == "__main__":
    main()
