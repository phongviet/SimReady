"""M0 CLI: acquisition, fixture generation, import, validation and storage."""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from simready.data.dataset import validate_scene
from simready.data.redwood import fetch_sample, import_redwood
from simready.data.synthetic import make_synthetic
from simready.storage import BUDGET_BYTES, PROJECT_ROOT, check_budget


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SimReady M0: CPU dataset tools")
    commands = parser.add_subparsers(dest="command", required=True)
    storage = commands.add_parser("storage", help="check the 30 GB project budget")
    storage.add_argument("--root", type=Path, default=PROJECT_ROOT)
    data = commands.add_parser("data").add_subparsers(dest="action", required=True)
    for name in ("validate", "split"):
        item = data.add_parser(name, help="validate frozen dataset/splits; never overwrite them")
        item.add_argument("--scene", type=Path, required=True)
    for name in ("synthetic", "fetch"):
        item = data.add_parser(name)
        item.add_argument("--out", type=Path, required=True)
    item = data.add_parser("import")
    item.add_argument("--source", type=Path, required=True)
    item.add_argument("--format", choices=["open3d_redwood_sample"], required=True)
    item.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "storage":
            result = {
                "root": str(args.root.resolve()),
                "used_bytes": check_budget(root=args.root),
                "limit_bytes": BUDGET_BYTES,
            }
        elif args.action in ("validate", "split"):
            result = validate_scene(args.scene)
        elif args.action == "fetch":
            result = {"sample_path": str(fetch_sample(args.out))}
        else:
            if args.action == "synthetic":
                make_synthetic(args.out)
            else:
                import_redwood(args.source, args.out)
            result = validate_scene(args.out)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, ValidationError, KeyError) as exc:
        print(f"simready: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
