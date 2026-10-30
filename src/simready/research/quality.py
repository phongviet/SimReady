"""Validation-only ablations with immutable stages and explicit failures."""

import argparse
import csv
import fcntl
import hashlib
import json
import math
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from simready.data.dataset import sha256_file, write_json
from simready.evaluation.config import EvaluationConfig
from simready.evaluation.runner import evaluate, verify_evaluation_binding
from simready.reconstruction.contracts import QualityTrainingConfig, ReconstructionConfig
from simready.reconstruction.gsplat import GsplatBackend, load_records, validate_artifact
from simready.storage import PROJECT_ROOT, check_budget, project_bytes

ARMS = {
    "control": {},
    "cap20k": {"max_gaussians": 20000},
    "sh0": {"sh_degree": 0},
    "sh2": {"sh_degree": 2},
    "l1-ssim": {"photometric_loss": "l1_ssim"},
    "depth-off": {"depth_supervision": "none", "depth_loss_weight": 0.0},
    "relative-depth": {"depth_supervision": "relative_l1"},
}
SEEDS = (42, 43, 44)
BUDGETS = (1200, 2400, 3600)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def configurations():
    base = json.loads((PROJECT_ROOT / "configs/recon_local_6gb.json").read_text())
    for seed in SEEDS:
        yield f"baseline-s{seed}", QualityTrainingConfig(**(base | {"seed": seed}))
    for arm, changes in ARMS.items():
        for seed in SEEDS:
            yield (
                f"{arm}-s{seed}",
                QualityTrainingConfig(
                    **(
                        base
                        | {
                            "iterations": 3600,
                            "checkpoint_steps": list(BUDGETS),
                            "seed": seed,
                        }
                        | changes
                    )
                ),
            )


def select_validation(rows, split_hash, view_count):
    """Frozen lexicographic selection, LPIPS ties within 1e-6 of the minimum."""
    if not rows:
        raise ValueError("no eligible validation candidates")
    for row in rows:
        if (
            row["split"] != "validation"
            or row["split_sha256"] != split_hash
            or row["view_count"] != view_count
            or any(
                not isinstance(row[k], (int, float)) or not math.isfinite(row[k])
                for k in ("lpips", "psnr_db")
            )
        ):
            raise ValueError("selection requires complete finite frozen validation measurements")
    minimum = min(r["lpips"] for r in rows)
    tied = [r for r in rows if r["lpips"] <= minimum + 1e-6]
    return min(tied, key=lambda r: (-r["psnr_db"], r["step"], r["arm"]))


def source_pins():
    names = subprocess.check_output(["git", "ls-files"], cwd=PROJECT_ROOT, text=True).splitlines()
    return {
        name: sha256_file(PROJECT_ROOT / name)
        for name in names
        if name.startswith(("src/", "workers/", "configs/", "scripts/"))
        or name in ("uv.lock", "pyproject.toml")
    }


def historical_pins():
    """Opaque hashes only: never consume previous test metrics for study choices."""
    roots = [
        PROJECT_ROOT / "artifacts/scenes/tum-fr1-desk",
        PROJECT_ROOT / "experiments/tum-recapture-1",
        PROJECT_ROOT / "experiments/bench-companion-1",
        PROJECT_ROOT / "experiments/m6-benchmark-1",
    ]
    return {
        str(p.relative_to(PROJECT_ROOT)): sha256_file(p)
        for root in roots
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def freeze(root, scene, reference):
    if root.exists():
        raise ValueError("study ID already exists; use run to resume verified stages")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=PROJECT_ROOT):
        raise ValueError("commit implementation before freezing execution sources")
    check_budget(4_000_000_000)
    manifest, frames, splits = load_records(scene, ("train", "validation"))
    old = validate_artifact(reference)
    base = ReconstructionConfig.model_validate_json(
        (PROJECT_ROOT / "configs/recon_local_6gb.json").read_text()
    ).model_dump(mode="json")
    if old["config"] != base or old["worker"]["iterations"] != 1200:
        raise ValueError("historical reference differs from the declared 1200-step baseline")
    spec = PROJECT_ROOT / "refine-logs/reconstruction-quality-1/EXPERIMENT_PLAN.md"
    protocol = {
        "schema_version": "1.0",
        "study_id": root.name,
        "created_utc": datetime.now(UTC).isoformat(),
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True
        ).strip(),
        "source_sha256": source_pins(),
        "spec_sha256": sha256_file(spec),
        "scene": str(scene.resolve()),
        "reference": str(reference.resolve()),
        "dataset_sha256": {
            n: sha256_file(scene / n) for n in ("manifest.json", "frames.jsonl", "splits.json")
        },
        "split_sha256": manifest.split_sha256,
        "validation_count": len(splits.validation),
        "allowed_observations": {
            f.frame_id: {
                "rgb_path": f.rgb_path,
                "rgb_sha256": f.rgb_sha256,
                "depth_path": f.depth_path,
                "depth_sha256": f.depth_sha256,
            }
            for f in frames
            if f.frame_id in set(splits.train + splits.validation)
        },
        "reference_sha256": sha256_file(reference / "artifact.json"),
        "historical_sha256": historical_pins(),
        "evaluation": EvaluationConfig().model_dump(mode="json"),
        "runs": {
            name: {
                "config": c.model_dump(mode="json"),
                "config_sha256": digest(c.model_dump(mode="json")),
            }
            for name, c in configurations()
        },
        "selection": (
            "per seed; min validation LPIPS, ties <=1e-6: higher PSNR, fewer steps, arm ID"
        ),
        "scope": "Validation-only, one exposed sequence. No test or generalization claim.",
    }
    root.mkdir(parents=True)
    write_json(root / "protocol.json", protocol)
    write_json(root / "seal.json", {"protocol_sha256": sha256_file(root / "protocol.json")})


def verify_protocol(root):
    protocol = json.loads((root / "protocol.json").read_text())
    if (
        sha256_file(root / "protocol.json")
        != json.loads((root / "seal.json").read_text())["protocol_sha256"]
    ):
        raise ValueError("protocol changed after freeze")
    if source_pins() != protocol["source_sha256"]:
        raise ValueError("execution source changed after freeze; create a new study ID")
    spec = PROJECT_ROOT / "refine-logs/reconstruction-quality-1/EXPERIMENT_PLAN.md"
    if sha256_file(spec) != protocol["spec_sha256"]:
        raise ValueError("experiment specification changed after freeze")
    for item in protocol["runs"].values():
        if digest(item["config"]) != item["config_sha256"]:
            raise ValueError("configuration digest mismatch")
    scene = Path(protocol["scene"])
    for name, expected in protocol["dataset_sha256"].items():
        if sha256_file(scene / name) != expected:
            raise ValueError("frozen dataset records changed")
    if historical_pins() != protocol["historical_sha256"]:
        raise ValueError("historical artifacts changed")
    return protocol


def stage(root, name, binding, action, verify):
    """Success is reusable only after hash/binding checks; failed IDs are never retried."""
    ledger = root / "ledger"
    ledger.mkdir(exist_ok=True)
    path = ledger / f"{name}.json"
    if path.exists():
        record = json.loads(path.read_text())
        if record["status"] != "complete" or record["binding"] != binding:
            raise ValueError(
                f"stage {name} failed/interrupted or inputs changed; use a new study ID"
            )
        verify()
        return
    record = {
        "stage": name,
        "binding": binding,
        "status": "running",
        "started_utc": datetime.now(UTC).isoformat(),
    }
    write_json(path, record)
    started = time.perf_counter()
    try:
        check_budget(300_000_000)
        if project_bytes(root) + 300_000_000 >= 4_000_000_000:
            raise ValueError("study output reserve exceeds its frozen 4 GB cap")
        action()
        verify()
        if project_bytes(root) >= 4_000_000_000:
            raise ValueError("study output exceeds its frozen 4 GB cap")
    except Exception as exc:
        record.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    else:
        record["status"] = "complete"
    finally:
        record["seconds"] = time.perf_counter() - started
        write_json(path, record)


def verify_validation(report, scene, checkpoint, renders, config):
    # Fail before consuming metrics from any non-validation report.
    if json.loads((renders / "renders.json").read_text())["split"] != "validation":
        raise ValueError("quality study permits validation evaluation only")
    return verify_evaluation_binding(report, scene, checkpoint, renders, config)


def run(root):
    p = verify_protocol(root)
    scene = Path(p["scene"])
    backend = GsplatBackend()
    evaluation = EvaluationConfig.model_validate(p["evaluation"])
    lock = PROJECT_ROOT / "artifacts/studio/evaluation-worker.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        models = [("reference", Path(p["reference"]), None)] + [
            (name, root / name / "model", item) for name, item in p["runs"].items()
        ]
        for name, model, item in models:
            print(f"QUALITY {name}", flush=True)
            if item:
                config = QualityTrainingConfig.model_validate(item["config"])

                def check_model(model=model, config=config):
                    metadata = validate_artifact(model)
                    if metadata["config"] != config.model_dump(mode="json"):
                        raise ValueError("cached model configuration differs")
                    if metadata["git_commit"] != p["git_commit"] or metadata["git_dirty"]:
                        raise ValueError("model source differs from execution seal")

                stage(
                    root,
                    f"train-{name}",
                    item["config_sha256"],
                    lambda config=config, model=model: backend.train(scene, config, model),
                    check_model,
                )
            checkpoints = (
                [(1200, model)]
                if item is None or not item["config"]["checkpoint_steps"]
                else [
                    (n, model / "checkpoints" / f"step_{n:06d}")
                    for n in item["config"]["checkpoint_steps"]
                ]
            )
            for step, checkpoint in checkpoints:
                target = root / name / f"step-{step}"
                renders, report = target / "renders", target / "evaluation"
                binding = sha256_file(checkpoint / "artifact.json")

                # Evaluation stage includes rendering; interrupted stages stay failed.
                def action(checkpoint=checkpoint, renders=renders, report=report):
                    backend.render(checkpoint, scene, "validation", renders)
                    evaluate(scene, checkpoint, renders, report, evaluation)

                stage(
                    root,
                    f"evaluate-{name}-{step}",
                    binding,
                    action,
                    lambda checkpoint=checkpoint, renders=renders, report=report: verify_validation(
                        report, scene, checkpoint, renders, evaluation
                    ),
                )
    verify_protocol(root)


def collect(root):
    p = verify_protocol(root)
    rows = []
    for name in ["reference", *p["runs"]]:
        item = p["runs"].get(name)
        steps = item["config"]["checkpoint_steps"] or [1200] if item else [1200]
        model = root / name / "model" if item else Path(p["reference"])
        for step in steps:
            report = root / name / f"step-{step}" / "evaluation"
            if not report.exists():
                continue
            checkpoint = (
                model / "checkpoints" / f"step_{step:06d}"
                if item and item["config"]["checkpoint_steps"]
                else model
            )
            verify_validation(
                report,
                Path(p["scene"]),
                checkpoint,
                report.parent / "renders",
                EvaluationConfig.model_validate(p["evaluation"]),
            )
            summary = json.loads((report / "summary.json").read_text())
            worker = validate_artifact(checkpoint)["worker"]
            trajectory = validate_artifact(model)
            timing = json.loads((root / "ledger" / f"evaluate-{name}-{step}.json").read_text())
            row = {
                "run": name,
                "arm": name.rsplit("-s", 1)[0],
                "seed": item["config"]["seed"] if item else 42,
                "step": step,
                "split": summary["split"],
                "split_sha256": summary["split_sha256"],
                "view_count": summary["view_count"],
                **summary["means"],
                "optimization_seconds": worker.get("optimization_seconds"),
                "worker_seconds": worker["training_seconds"],
                "trajectory_worker_seconds": trajectory["worker"]["training_seconds"],
                "trajectory_adapter_seconds": trajectory["total_seconds"],
                "trajectory_checkpoint_io_seconds": trajectory["worker"].get("checkpoint_seconds"),
                "evaluation_stage_seconds": timing["seconds"],
                "max_gaussians_seen": worker.get("max_gaussians_seen"),
                "config_sha256": item["config_sha256"] if item else digest(trajectory["config"]),
                "source_commit": trajectory["git_commit"],
                "gaussians": worker["final_gaussians"],
                "peak_vram_allocated_bytes": worker["peak_vram_allocated_bytes"],
                "peak_vram_reserved_bytes": worker["peak_vram_reserved_bytes"],
                "initial_gaussians": worker["initial_gaussians"],
                "gaussian_limit": trajectory["config"]["max_gaussians"],
                "sh_degree": trajectory["config"]["sh_degree"],
                "snapshot_io_seconds": (
                    json.loads((checkpoint / "checkpoint.json").read_text())["checkpoint_seconds"]
                    if (checkpoint / "checkpoint.json").exists()
                    else None
                ),
                "evaluation_sha256": sha256_file(report / "evaluation.json"),
                "report": str(report.relative_to(root)),
            }
            rows.append(row)
    return p, rows


def analyze(root):
    from simready.research.quality_report import report

    p, rows = collect(root)
    expected = {
        (name, step)
        for name, item in p["runs"].items()
        for step in (item["config"]["checkpoint_steps"] or [1200])
    } | {("reference", 1200)}
    if {(r["run"], r["step"]) for r in rows} != expected:
        raise ValueError(
            "study incomplete; retain failed/interrupted ledger, do not select a subset"
        )
    selected = {
        str(seed): select_validation(
            [r for r in rows if r["seed"] == seed and r["arm"] not in ("reference", "baseline")],
            p["split_sha256"],
            p["validation_count"],
        )
        for seed in SEEDS
    }
    output = root / "analysis"
    if output.exists():
        raise ValueError("analysis already exists; preserve it and use a new named export")
    output.mkdir()
    write_json(
        output / "selection.json",
        {
            "rule": p["selection"],
            "candidates_sha256": digest(rows),
            "selected": selected,
            "candidates": rows,
        },
    )
    with (output / "quality-runtime.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report(root, output, rows, selected)
    write_json(
        output / "files.json",
        {str(f.relative_to(output)): sha256_file(f) for f in output.rglob("*") if f.is_file()},
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("freeze", "run", "analyze", "verify"))
    parser.add_argument(
        "--study", type=Path, default=PROJECT_ROOT / "experiments/reconstruction-quality-1"
    )
    parser.add_argument("--scene", type=Path, default=PROJECT_ROOT / "data/scenes/tum-fr1-desk")
    parser.add_argument(
        "--reference", type=Path, default=PROJECT_ROOT / "artifacts/scenes/tum-fr1-desk/baseline-1"
    )
    args = parser.parse_args()
    if args.action == "freeze":
        freeze(args.study, args.scene, args.reference)
    else:
        {"run": run, "analyze": analyze, "verify": verify_protocol}[args.action](args.study)


if __name__ == "__main__":
    main()
