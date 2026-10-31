"""Engineering CUDA preflight on new training/validation inputs; not study results."""

import fcntl

from simready.data.dataset import sha256_file, write_json
from simready.evaluation.config import EvaluationConfig
from simready.evaluation.runner import evaluate, verify_evaluation_binding
from simready.reconstruction.contracts import QualityTrainingConfig
from simready.reconstruction.gsplat import GsplatBackend, validate_artifact
from simready.storage import PROJECT_ROOT, check_budget


def main():
    root = PROJECT_ROOT / "experiments/improvement-gpu-preflight-1"
    if root.exists():
        raise ValueError("preflight ID exists; preserve it and use a new ID")
    check_budget(400_000_000)
    root.mkdir(parents=True)
    config = QualityTrainingConfig.model_validate_json(
        (PROJECT_ROOT / "configs/recon_smoke.json").read_text()
    )
    source = {
        str(p.relative_to(PROJECT_ROOT)): sha256_file(p)
        for folder in ["src", "workers", "scripts"]
        for p in (PROJECT_ROOT / folder).rglob("*.py")
    }
    write_json(
        root / "protocol.json",
        {
            "scope": "Engineering preflight only, no scientific primary-study claim.",
            "source_sha256": source,
            "config": config.model_dump(mode="json"),
            "split": "validation",
        },
    )
    lock = PROJECT_ROOT / "artifacts/studio/evaluation-worker.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for name in ["tum-fr1-room", "tum-fr2-desk"]:
            scene = PROJECT_ROOT / "data/scenes" / name
            backend = GsplatBackend()
            model = root / name / "model"
            renders = root / name / "renders"
            report = root / name / "evaluation"
            backend.train(scene, config, model)
            metadata = validate_artifact(model)
            assert metadata["worker"]["iterations"] == 40
            assert metadata["worker"]["peak_vram_allocated_bytes"] < config.memory_limit_bytes
            backend.render(model, scene, "validation", renders)
            evaluate(scene, model, renders, report)
            verify_evaluation_binding(report, scene, model, renders, EvaluationConfig())
            print(name, "40-step real-data training/reload/32-view validation passed", flush=True)
    write_json(
        root / "acceptance.json",
        {
            "status": "passed",
            "datasets": 2,
            "training_steps_each": 40,
            "validation_views_each": 32,
            "scope": "Preflight; excluded from primary 27-run matrix.",
        },
    )


if __name__ == "__main__":
    main()
