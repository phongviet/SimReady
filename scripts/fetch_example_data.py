"""Download only the checksum-pinned, size-bounded M0 sample via the common CLI."""

import sys

from simready.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["data", "fetch", *sys.argv[1:]]))
