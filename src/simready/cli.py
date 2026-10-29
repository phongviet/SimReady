"""Dataset tools and isolated reconstruction commands."""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from simready.data.dataset import validate_scene
from simready.data.redwood import fetch_sample, import_redwood
from simready.data.synthetic import make_synthetic
from simready.reconstruction.contracts import ReconstructionConfig
from simready.reconstruction.gsplat import GsplatBackend, validate_artifact
from simready.storage import BUDGET_BYTES, PROJECT_ROOT, check_budget


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SimReady: RGB-D dataset and reconstruction tools")
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
    recon = commands.add_parser("recon").add_subparsers(dest="action", required=True)
    item = recon.add_parser("train")
    item.add_argument("--scene", type=Path, required=True)
    item.add_argument("--preset", choices=["smoke", "local_6gb"], default="smoke")
    item.add_argument("--config", type=Path)
    item.add_argument("--out", type=Path, required=True)
    item.add_argument("--python", type=Path)
    item = recon.add_parser("render")
    item.add_argument("--artifact", type=Path, required=True)
    item.add_argument("--scene", type=Path, required=True)
    item.add_argument(
        "--split", choices=["train", "validation", "candidate", "test"], default="test"
    )
    item.add_argument("--out", type=Path, required=True)
    item.add_argument("--python", type=Path)
    item = recon.add_parser("validate")
    item.add_argument("--artifact", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "storage":
            result = {
                "root": str(args.root.resolve()),
                "used_bytes": check_budget(root=args.root),
                "limit_bytes": BUDGET_BYTES,
            }
        elif args.command == "recon":
            if args.action == "validate":
                result = validate_artifact(args.artifact)
            elif args.action == "train":
                config_path = args.config or PROJECT_ROOT / f"configs/recon_{args.preset}.json"
                config = ReconstructionConfig.model_validate_json(config_path.read_text())
                path = GsplatBackend(args.python).train(args.scene, config, args.out)
                result = {"artifact": str(path), "metadata": validate_artifact(path)}
            else:
                path = GsplatBackend(args.python).render(
                    args.artifact, args.scene, args.split, args.out
                )
                result = {"renders": str(path)}
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
