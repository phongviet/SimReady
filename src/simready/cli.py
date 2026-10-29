"""Dataset tools and isolated reconstruction commands."""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from simready.data.dataset import validate_scene
from simready.data.redwood import fetch_sample, import_redwood
from simready.data.synthetic import make_synthetic
from simready.data.tum import import_tum
from simready.evaluation.config import EvaluationConfig
from simready.evaluation.runner import evaluate, validate_evaluation
from simready.evaluation.store import EvaluationStore
from simready.geometry.tsdf import build_tsdf
from simready.reconstruction.contracts import ReconstructionConfig
from simready.reconstruction.gsplat import GsplatBackend, cpu_smoke, validate_artifact
from simready.review.auth import AuthStore
from simready.scene.demo import seed_demo
from simready.scene.store import SceneStore
from simready.simulation.models import Scenario, ScenarioUpdate
from simready.simulation.store import SimulationStore
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
    item.add_argument("--format", choices=["open3d_redwood_sample", "tum_rgbd"], required=True)
    item.add_argument("--out", type=Path, required=True)
    item.add_argument("--max-frames", type=int, default=100)
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
    recon.add_parser("smoke", help="CPU-only validation of trained synthetic demo and saved views")
    evaluation = commands.add_parser("eval").add_subparsers(dest="action", required=True)
    item = evaluation.add_parser("run")
    for name in ("scene", "artifact", "renders", "out"):
        item.add_argument(f"--{name}", type=Path, required=True)
    item.add_argument("--config", type=Path, default=PROJECT_ROOT / "configs/evaluation.json")
    item.add_argument("--python", type=Path)
    report = commands.add_parser("report").add_subparsers(dest="action", required=True)
    item = report.add_parser("build", help="verify and locate exported reports")
    item.add_argument("--run", type=Path, required=True)
    geometry = commands.add_parser("geometry").add_subparsers(dest="action", required=True)
    item = geometry.add_parser("build")
    item.add_argument("--scene", type=Path, required=True)
    item.add_argument("--out", type=Path, required=True)
    item.add_argument("--voxel-size", type=float, default=0.03)
    item.add_argument("--method", choices=["tsdf"], default="tsdf")
    scenes = commands.add_parser("scene").add_subparsers(dest="action", required=True)
    item = scenes.add_parser("create")
    item.add_argument("--id", required=True)
    item.add_argument("--name", required=True)
    for name in ("dataset", "artifact", "geometry", "renders"):
        item.add_argument(f"--{name}", type=Path, required=True)
    item.add_argument("--root", type=Path, default=PROJECT_ROOT / "artifacts/studio")
    item = scenes.add_parser("demo")
    item.add_argument("--root", type=Path, default=PROJECT_ROOT / "artifacts/studio")
    item = scenes.add_parser("attach-report")
    item.add_argument("--id", required=True)
    item.add_argument("--run-id", required=True)
    item.add_argument("--run", type=Path, required=True)
    item.add_argument("--root", type=Path, default=PROJECT_ROOT / "artifacts/studio")
    simulation = commands.add_parser("sim").add_subparsers(dest="action", required=True)
    for name in ("save", "run", "list"):
        item = simulation.add_parser(name)
        item.add_argument("--scene", required=True, help="registered scene ID")
        item.add_argument("--root", type=Path, default=PROJECT_ROOT / "artifacts/studio")
        if name == "save":
            item.add_argument("--config", type=Path, required=True)
        if name == "run":
            item.add_argument("--scenario", required=True)
    auth = commands.add_parser("auth").add_subparsers(dest="action", required=True)
    item = auth.add_parser("init")
    item.add_argument("--root", type=Path, default=PROJECT_ROOT / "artifacts/studio")
    api = commands.add_parser("api").add_subparsers(dest="action", required=True)
    item = api.add_parser("serve")
    item.add_argument("--root", type=Path, default=PROJECT_ROOT / "artifacts/studio")
    item.add_argument("--port", type=int, default=8000)
    item.add_argument("--demo", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "storage":
            result = {
                "root": str(args.root.resolve()),
                "used_bytes": check_budget(root=args.root),
                "limit_bytes": BUDGET_BYTES,
            }
        elif args.command == "auth":
            result = {
                "credentials_file": str(AuthStore(SceneStore(args.root)).bootstrap()),
                "scope": "local separate Builder/Reviewer tokens; keep this file private",
            }
        elif args.command == "api":
            import uvicorn

            from simready.api.app import create_app

            if args.demo:
                seed_demo(SceneStore(args.root))
                AuthStore(SceneStore(args.root)).bootstrap()
            uvicorn.run(create_app(args.root), host="127.0.0.1", port=args.port)
            return 0
        elif args.command == "sim":
            store = SceneStore(args.root)
            state = store.get(args.scene)
            if args.action == "save":
                config = Scenario.model_validate_json(args.config.read_text())
                scenarios = [
                    s for s in state.get("scenarios", []) if s["scenario_id"] != config.scenario_id
                ]
                scenarios.append(config.model_dump(mode="json"))
                result = store.update_scenarios(
                    args.scene,
                    ScenarioUpdate(expected_version=state["version"], scenarios=scenarios),
                )
            elif args.action == "list":
                result = SimulationStore(store).runs(args.scene)
            else:
                result = SimulationStore(store).run(args.scene, args.scenario, state["version"])
        elif args.command == "scene":
            store = SceneStore(args.root)
            if args.action == "attach-report":
                result = EvaluationStore(store).register(args.id, args.run_id, args.run)
                print(json.dumps(result, indent=2, allow_nan=False))
                return 0
            result = (
                seed_demo(store)
                if args.action == "demo"
                else store.register(
                    args.id, args.name, args.artifact, args.geometry, args.renders, args.dataset
                )
            )
        elif args.command == "eval":
            config = EvaluationConfig.model_validate_json(args.config.read_text())
            result = {
                "evaluation": str(
                    evaluate(args.scene, args.artifact, args.renders, args.out, config, args.python)
                )
            }
        elif args.command == "report":
            validate_evaluation(args.run)
            result = {
                "html": str(args.run / "report.html"),
                "markdown": str(args.run / "report.md"),
            }
        elif args.command == "geometry":
            result = {"geometry": str(build_tsdf(args.scene, args.out, args.voxel_size))}
        elif args.command == "recon":
            if args.action == "smoke":
                result = cpu_smoke()
            elif args.action == "validate":
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
                if args.format == "tum_rgbd":
                    import_tum(args.source, args.out, args.max_frames)
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
