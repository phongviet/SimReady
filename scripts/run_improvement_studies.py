"""Frozen policy confirmation and guarded densification; no target-test selection."""

import argparse
import fcntl
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from simready.data.dataset import sha256_file, write_json
from simready.evaluation.config import EvaluationConfig
from simready.evaluation.runner import evaluate, verify_evaluation_binding
from simready.reconstruction.contracts import QualityTrainingConfig
from simready.reconstruction.gsplat import GsplatBackend, load_records, validate_artifact
from simready.research.quality import digest, historical_pins, source_pins, stage
from simready.storage import PROJECT_ROOT, check_budget

ROOT = PROJECT_ROOT / "experiments/engineering-improvement-1"
SPEC = PROJECT_ROOT / "docs/INDEPENDENT_SCENE_PROTOCOL.md"


def history():
    previous = PROJECT_ROOT / "experiments/reconstruction-quality-1"
    return historical_pins() | {
        str(f.relative_to(PROJECT_ROOT)): sha256_file(f) for f in previous.rglob("*") if f.is_file()
    }


def configs(kind):
    frozen = json.loads(
        (PROJECT_ROOT / "docs/evidence/improvement-intake/frozen-policy.json").read_text()
    )
    base = frozen["selected_config"] | {"checkpoint_steps": []}
    for seed in [42, 43, 44]:
        if kind == "densification":
            for end in [900, 1800, 3000]:
                yield (
                    f"refine{end}-s{seed}",
                    QualityTrainingConfig(
                        **(
                            base
                            | {
                                "seed": seed,
                                "refine_stop": end,
                                "checkpoint_steps": [1200, 2400, 3600],
                            }
                        )
                    ),
                )
        else:
            for name, updates, photo in [
                ("original", 1200, "l1"),
                ("matched", 3600, "l1"),
                ("selected", 3600, "l1_ssim"),
            ]:
                yield (
                    f"{name}-s{seed}",
                    QualityTrainingConfig(
                        **(base | {"seed": seed, "iterations": updates, "photometric_loss": photo})
                    ),
                )


def freeze(root):
    if root.exists():
        raise ValueError("study root exists; never overwrite frozen protocols")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=PROJECT_ROOT):
        raise ValueError("commit implementation and acceptance checks before freezing")
    check_budget(5_500_000_000)
    source = source_pins()
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True
    ).strip()
    children = {}
    for name, scene, kind, split in [
        ("generalization-room-1", "tum-fr1-room", "generalization", "test"),
        ("generalization-fr2-desk-1", "tum-fr2-desk", "generalization", "test"),
        ("densification-desk-1", "tum-fr1-desk", "densification", "validation"),
    ]:
        path = PROJECT_ROOT / "data/scenes" / scene
        manifest, _, splits = load_records(path, ())
        children[name] = {
            "scene": str(path),
            "kind": kind,
            "evaluation_split": split,
            "dataset_sha256": {
                n: sha256_file(path / n) for n in ["manifest.json", "frames.jsonl", "splits.json"]
            },
            "split_sha256": manifest.split_sha256,
            "evaluation_frames": list(getattr(splits, split)),
            "runs": {
                run: {
                    "config": c.model_dump(mode="json"),
                    "config_sha256": digest(c.model_dump(mode="json")),
                }
                for run, c in configs(kind)
            },
        }
    protocol = {
        "study_id": root.name,
        "created_utc": datetime.now(UTC).isoformat(),
        "source_commit": commit,
        "frozen_policy_sha256": sha256_file(
            PROJECT_ROOT / "docs/evidence/improvement-intake/frozen-policy.json"
        ),
        "source_sha256": source,
        "spec_sha256": sha256_file(SPEC),
        "annotation_rules_sha256": sha256_file(PROJECT_ROOT / "docs/ANNOTATION_PROTOCOL.md"),
        "historical_sha256": history(),
        "studies": children,
        "study_order": list(children),
        "evaluation": EvaluationConfig().model_dump(mode="json"),
        "policy": "No target-scene selection; preserve fixed policy and complete evaluation split.",
        "dirty_scope": (
            "Initial seal requires clean Git; later frontend/docs edits allowed "
            "only with identical frozen experimental source bytes. "
            "Actual artifact dirty state/commit retained."
        ),
    }
    root.mkdir(parents=True)
    write_json(root / "protocol.json", protocol)
    write_json(root / "seal.json", {"protocol_sha256": sha256_file(root / "protocol.json")})


def verify(root):
    p = json.loads((root / "protocol.json").read_text())
    if (
        sha256_file(root / "protocol.json")
        != json.loads((root / "seal.json").read_text())["protocol_sha256"]
    ):
        raise ValueError("sealed protocol modified")
    if source_pins() != p["source_sha256"] or sha256_file(SPEC) != p["spec_sha256"]:
        raise ValueError("frozen experimental source/spec changed")
    if sha256_file(PROJECT_ROOT / "docs/ANNOTATION_PROTOCOL.md") != p["annotation_rules_sha256"]:
        raise ValueError("frozen annotation rules changed")
    if (
        sha256_file(PROJECT_ROOT / "docs/evidence/improvement-intake/frozen-policy.json")
        != p["frozen_policy_sha256"]
    ):
        raise ValueError("previous selected policy record changed")
    if history() != p["historical_sha256"]:
        raise ValueError("historical outputs changed")
    for child in p["studies"].values():
        for name, sha in child["dataset_sha256"].items():
            if sha256_file(Path(child["scene"]) / name) != sha:
                raise ValueError("frozen dataset records changed")
    return p


def run(root):
    p = verify(root)
    backend = GsplatBackend()
    cfg = EvaluationConfig.model_validate(p["evaluation"])
    lock = PROJECT_ROOT / "artifacts/studio/evaluation-worker.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for name in p["study_order"]:
            child = p["studies"][name]
            folder = root / name
            folder.mkdir(exist_ok=True)
            scene = Path(child["scene"])
            for run_id, item in child["runs"].items():
                if source_pins() != p["source_sha256"]:
                    raise ValueError("experimental source drift before dispatch")
                config = QualityTrainingConfig.model_validate(item["config"])
                model = folder / run_id / "model"
                print(name, run_id, flush=True)

                def validate_model(model=model, config=config, child=child):
                    record = validate_artifact(model)
                    if (
                        record["config"] != config.model_dump(mode="json")
                        or record["worker"]["iterations"] != config.iterations
                    ):
                        raise ValueError("cached model differs from frozen config")
                    if (
                        record["provenance"]["dataset_manifest_sha256"]
                        != child["dataset_sha256"]["manifest.json"]
                    ):
                        raise ValueError("cached training dataset differs from protocol")
                    if source_pins() != p["source_sha256"]:
                        raise ValueError("experimental source changed during training")

                stage(
                    folder,
                    "train-" + run_id,
                    item["config_sha256"],
                    lambda model=model, config=config, scene=scene: backend.train(
                        scene, config, model
                    ),
                    validate_model,
                )
                steps = config.checkpoint_steps or [config.iterations]
                for n in steps:
                    snapshot = (
                        model / "checkpoints" / f"step_{n:06d}"
                        if config.checkpoint_steps
                        else model
                    )
                    target = folder / run_id / f"step-{n}"
                    renders, report = target / "renders", target / "evaluation"

                    def measure(
                        snapshot=snapshot, renders=renders, report=report, scene=scene, child=child
                    ):
                        backend.render(snapshot, scene, child["evaluation_split"], renders)
                        evaluate(scene, snapshot, renders, report, cfg)

                    def check(
                        snapshot=snapshot, renders=renders, report=report, scene=scene, child=child
                    ):
                        if (
                            json.loads((renders / "renders.json").read_text())["split"]
                            != child["evaluation_split"]
                        ):
                            raise ValueError("evaluation split differs from preregistration")
                        verify_evaluation_binding(report, scene, snapshot, renders, cfg)

                    stage(
                        folder,
                        f"evaluate-{run_id}-{n}",
                        sha256_file(snapshot / "artifact.json"),
                        measure,
                        check,
                    )
    verify(root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["freeze", "run", "verify"])
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    {"freeze": freeze, "run": run, "verify": verify}[args.action](args.root)
