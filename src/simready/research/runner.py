"""Sequential, resumable frozen-budget study with sealed observation acquisition."""

import fcntl
import json
import os
import subprocess
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from simready.data.dataset import local_file, sha256_file, write_json
from simready.evaluation.config import EvaluationConfig
from simready.evaluation.readiness import pose_diagnostics
from simready.evaluation.runner import evaluate, verify_evaluation_binding
from simready.reconstruction.contracts import ReconstructionConfig
from simready.reconstruction.gsplat import (
    GsplatBackend,
    camera_record,
    load_records,
    validate_artifact,
    validate_renders,
)
from simready.research.contracts import StudyConfig
from simready.research.data import append_access, create_dataset, curate, release_test
from simready.research.selection import (
    Acquisition,
    CandidateFeature,
    SelectionSeal,
    calibrate,
    json_digest,
    select_farthest,
    select_random,
    select_risk,
    validate_seal,
)
from simready.storage import PROJECT_ROOT, check_budget


def now() -> str:
    return datetime.now(UTC).isoformat()


def git_state() -> dict:
    return {
        "commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True
        ).strip(),
        "dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=PROJECT_ROOT, text=True)
        ),
    }


def source_hashes() -> dict:
    paths = [
        *(PROJECT_ROOT / "src/simready").rglob("*.py"),
        *(PROJECT_ROOT / "workers").glob("*.py"),
        PROJECT_ROOT / "uv.lock",
        PROJECT_ROOT / "configs/compute-gpu.json",
        PROJECT_ROOT / "configs/gpu-requirements-lock.txt",
        PROJECT_ROOT / "configs/perception-weights.json",
    ]
    return {p.relative_to(PROJECT_ROOT).as_posix(): sha256_file(p) for p in sorted(paths)}


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + ".pending")
    write_json(temporary, value)
    os.replace(temporary, path)


def prepare(config_path: Path, output: Path) -> Path:
    config = StudyConfig.model_validate_json(config_path.read_text())
    reconstruction = ReconstructionConfig.model_validate_json(
        (PROJECT_ROOT / config.reconstruction_config).read_text()
    )
    evaluation = EvaluationConfig.model_validate_json(
        (PROJECT_ROOT / config.evaluation_config).read_text()
    )
    if reconstruction.iterations != 1200 or reconstruction.width != 320:
        raise ValueError("frozen study requires 1200 iterations at 320px")
    source = git_state()
    if source["dirty"]:
        raise ValueError("commit study code/protocol before curation")
    check_budget(8_000_000_000)
    protocol = {
        "schema_version": "1.0",
        "created_at": now(),
        "study": config.model_dump(mode="json"),
        "reconstruction": reconstruction.model_dump(mode="json"),
        "evaluation": evaluation.model_dump(mode="json"),
        "curator_source": source,
        "source_files_sha256": source_hashes(),
        "plan_sha256": sha256_file(PROJECT_ROOT / "refine-logs/EXPERIMENT_PLAN.md"),
        "scope": "One correlated TUM capture; no novel-method or safety claim.",
    }
    return curate(
        PROJECT_ROOT / config.source_dataset,
        PROJECT_ROOT / config.source_archive,
        output,
        protocol,
    )


class StageCache:
    """Validate completed outputs on resume; never replace a successful artifact."""

    def __init__(self, study: Path):
        self.study = study
        self.path = study / "stages.json"
        self.state = (
            json.loads(self.path.read_text())
            if self.path.exists()
            else {"schema_version": "1.0", "stages": {}, "failures": []}
        )

    def run(self, key, output, manifest, inputs, action, validator):
        digest = json_digest(inputs)
        previous = self.state["stages"].get(key)
        if previous and previous["inputs_sha256"] != digest:
            raise ValueError(f"stage {key}: frozen inputs changed; use a new study")
        started = time.perf_counter()
        try:
            if previous and not output.is_dir():
                raise ValueError(f"stage {key}: completed output is missing")
            recovered = output.is_dir() and previous is None
            if not output.exists():
                check_budget(400_000_000)
                print(json.dumps({"stage": key, "status": "running", "at": now()}), flush=True)
                action()
            result = validator(output)
            actual = sha256_file(output / manifest)
            if previous:
                if previous["manifest_sha256"] != actual:
                    raise ValueError(f"stage {key}: completed manifest changed")
                return result
            entry = {
                "inputs_sha256": digest,
                "inputs": inputs,
                "output": output.relative_to(self.study).as_posix(),
                "manifest": manifest,
                "manifest_sha256": actual,
                "finished_at": now(),
                "wall_seconds": None if recovered else time.perf_counter() - started,
                "recovered_existing_output": recovered,
                "storage_bytes": check_budget(),
            }
            self.state["stages"][key] = entry
            atomic_json(self.path, self.state)
            print(json.dumps({"stage": key, "status": "verified", **entry}), flush=True)
            return result
        except Exception:
            self.state["failures"].append(
                {"stage": key, "at": now(), "traceback": traceback.format_exc()}
            )
            atomic_json(self.path, self.state)
            raise


def pose_features(dataset: Path, renders: Path, split: str) -> list[CandidateFeature]:
    _, frames, partitions = load_records(dataset, ())
    images = validate_renders(renders)
    selected = [frame for frame in frames if frame.frame_id in getattr(partitions, split)]
    if images["split"] != split or [c["frame_id"] for c in images["cameras"]] != [
        f.frame_id for f in selected
    ]:
        raise ValueError("risk renders differ from the declared pose pool")
    training = np.array([f.T_world_camera for f in frames if f.frame_id in partitions.train])
    diagnostics = pose_diagnostics(training, np.array([f.T_world_camera for f in selected]))
    return [
        CandidateFeature(
            frame_id=frame.frame_id,
            distance_m=pose["distance_m"],
            rotation_deg=pose["minimum_rotation_deg"],
            alpha_hole_fraction=float(
                (
                    np.load(local_file(renders, f"{frame.frame_id}-alpha.npy"), allow_pickle=False)
                    < 0.1
                ).mean()
            ),
        )
        for frame, pose in zip(selected, diagnostics, strict=True)
    ]


def run(study: Path, phase: str = "all") -> dict:
    if phase not in ("acquire", "evaluate", "all"):
        raise ValueError("unknown study phase")
    study = study.resolve()
    protocol = json.loads((study / "protocol.json").read_text())
    config = StudyConfig.model_validate(protocol["study"])
    reconstruction = ReconstructionConfig.model_validate(protocol["reconstruction"])
    evaluation = EvaluationConfig.model_validate(protocol["evaluation"])
    curation = json.loads((study / "curation.json").read_text())
    if curation["protocol_sha256"] != json_digest(protocol):
        raise ValueError("curation protocol changed")
    current = git_state()
    if current["dirty"]:
        raise ValueError("study execution requires committed source")
    snapshot = {"source_files_sha256": source_hashes(), "git": current}
    run_source = study / "run-source.json"
    if run_source.exists():
        saved = json.loads(run_source.read_text())
        if saved["source_files_sha256"] != snapshot["source_files_sha256"]:
            raise ValueError("study implementation changed; use a versioned follow-up study")
    else:
        write_json(run_source, snapshot)
    for folder in ("models", "renders", "evaluations", "selection", "datasets"):
        (study / folder).mkdir(exist_ok=True)
    with (study / "study.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("study is already running; inspect the existing process") from exc
        cache, backend = StageCache(study), GsplatBackend()

        def train(key, dataset, seed):
            cfg = reconstruction.model_copy(update={"seed": seed})
            artifact = study / "models" / key
            inputs = {
                "dataset": sha256_file(dataset / "manifest.json"),
                "config": cfg.model_dump(mode="json"),
            }

            def validate(path):
                metadata = validate_artifact(path)
                if (
                    metadata["config"] != inputs["config"]
                    or metadata["provenance"]["dataset_manifest_sha256"] != inputs["dataset"]
                ):
                    raise ValueError("cached training differs from frozen inputs")
                return metadata

            cache.run(
                "train-" + key,
                artifact,
                "artifact.json",
                inputs,
                lambda: backend.train(dataset, cfg, artifact),
                validate,
            )
            return artifact

        def render(key, dataset, artifact, split):
            output = study / "renders" / (key + "-" + split)
            artifact_hash = sha256_file(artifact / "artifact.json")
            inputs = {
                "artifact_sha256": artifact_hash,
                "split": split,
                "dataset": sha256_file(dataset / "manifest.json"),
            }

            def validate(path):
                metadata = validate_renders(path)
                manifest, frames, partitions = load_records(dataset, ())
                expected = [
                    camera_record(f, manifest, reconstruction.width)
                    for f in frames
                    if f.frame_id in getattr(partitions, split)
                ]
                if (
                    metadata["artifact_sha256"] != artifact_hash
                    or metadata["cameras"] != expected
                    or metadata["split"] != split
                ):
                    raise ValueError("cached renders differ from frozen cameras/model")
                return metadata

            cache.run(
                "render-" + key + "-" + split,
                output,
                "renders.json",
                inputs,
                lambda: backend.render(artifact, dataset, split, output),
                validate,
            )
            return output

        def compare(key, dataset, artifact, images, split):
            output = study / "evaluations" / (key + "-" + split)
            inputs = {
                "artifact": sha256_file(artifact / "artifact.json"),
                "renders": sha256_file(images / "renders.json"),
                "config": evaluation.model_dump(mode="json"),
            }

            def validate(path):
                return verify_evaluation_binding(path, dataset, artifact, images, evaluation)

            cache.run(
                "eval-" + key + "-" + split,
                output,
                "evaluation.json",
                inputs,
                lambda: evaluate(dataset, artifact, images, output, evaluation),
                validate,
            )
            return output

        base = study / "base-dataset"
        if phase in ("all", "acquire"):
            if not (study / "selections-sealed.json").exists():
                _, frozen_frames, frozen_splits = load_records(base, ())
                for frame in frozen_frames:
                    if frame.frame_id in frozen_splits.candidate + frozen_splits.test:
                        if any(
                            (base / getattr(frame, c + "_path")).exists() for c in ("rgb", "depth")
                        ):
                            raise ValueError("withheld pixels were released before selection seals")
                rows = []
                for seed in config.seeds:
                    key = f"base-s{seed}"
                    artifact = train(key, base, seed)
                    validation = render(key, base, artifact, "validation")
                    report = compare(key, base, artifact, validation, "validation")
                    candidates = render(key, base, artifact, "candidate")
                    validation_features = pose_features(base, validation, "validation")
                    views = json.loads((report / "views.json").read_text())
                    calibration = calibrate(
                        validation_features,
                        [v["metrics"]["lpips"] for v in views],
                        config.validation_fit_frames,
                        config.ridge_penalty,
                    )
                    candidate_features = pose_features(base, candidates, "candidate")
                    risk, ranking = select_risk(
                        candidate_features, calibration, config.additional_observations
                    )
                    _, frames, partitions = load_records(base, ())
                    ids = list(partitions.candidate)
                    frame_map = {f.frame_id: f for f in frames}
                    choices = {
                        "risk": risk,
                        "random": select_random(ids, config.additional_observations, seed),
                        "farthest": select_farthest(
                            np.array([frame_map[n].T_world_camera for n in partitions.train])[
                                :, :3, 3
                            ],
                            ids,
                            np.array([frame_map[n].T_world_camera for n in ids])[:, :3, 3],
                            config.additional_observations,
                        ),
                    }
                    for method, chosen in choices.items():
                        selection_key = f"{method}-s{seed}"
                        details = {
                            "key": selection_key,
                            "method": method,
                            "seed": seed,
                            "selected_ids": chosen,
                            "base_artifact_sha256": sha256_file(artifact / "artifact.json"),
                            "calibration": calibration,
                            "risk_ranking": ranking,
                            "candidate_features": [
                                v.model_dump(mode="json") for v in candidate_features
                            ],
                            "validation_evaluation_sha256": sha256_file(report / "evaluation.json"),
                            "allowed_information": (
                                "public poses, current-model alpha, validation LPIPS"
                            ),
                        }
                        path = study / "selection" / (selection_key + ".json")
                        if path.exists() and json.loads(path.read_text()) != details:
                            raise ValueError(
                                "previous acquisition differs; never replace a decision"
                            )
                        write_json(path, details)
                        rows.append(
                            Acquisition.model_validate(
                                {
                                    k: details[k]
                                    for k in (
                                        "key",
                                        "method",
                                        "seed",
                                        "selected_ids",
                                        "base_artifact_sha256",
                                    )
                                }
                                | {"details_sha256": sha256_file(path)}
                            )
                        )
                seal = SelectionSeal(
                    schema_version="1.0",
                    curation_sha256=sha256_file(study / "curation.json"),
                    protocol_sha256=json_digest(protocol),
                    candidate_ids=curation["partitions"]["candidate"],
                    seeds=config.seeds,
                    k=config.additional_observations,
                    acquisitions=rows,
                )
                write_json(study / "selections-sealed.json", seal.model_dump(mode="json"))
                (study / "selections-sealed.sha256").write_text(
                    sha256_file(study / "selections-sealed.json") + "\n"
                )
                append_access(
                    study,
                    "all_selections_sealed",
                    [],
                    sha256=sha256_file(study / "selections-sealed.json"),
                )
            validate_seal(study)
        if phase in ("all", "evaluate"):
            seal = validate_seal(study)
            datasets = {f"base-s{seed}": base for seed in config.seeds}
            for row in seal.acquisitions:
                dataset = study / "datasets" / row.key
                if not dataset.exists():
                    create_dataset(
                        study,
                        dataset,
                        list(row.selected_ids),
                        "tum_m5_" + row.key.replace("-", "_"),
                        row.key,
                    )
                _, _, partitions = load_records(dataset, ("train", "validation"))
                if set(partitions.train) != set(curation["partitions"]["train"]) | set(
                    row.selected_ids
                ):
                    raise ValueError("recapture training set differs from sealed acquisition")
                datasets[row.key] = dataset
            # All candidate selections are fixed before any test reference release.
            for dataset in sorted(set(datasets.values())):
                release_test(study, dataset)
            for seed in config.seeds:
                for method in config.methods:
                    key = f"{method}-s{seed}"
                    dataset = datasets[key]
                    artifact = train(key, dataset, seed)
                    images = render(key, dataset, artifact, "test")
                    compare(key, dataset, artifact, images, "test")
        return {
            "study": str(study),
            "phase": phase,
            "verified_stages": len(cache.state["stages"]),
            "storage_bytes": check_budget(),
            "selection_seal_sha256": sha256_file(study / "selections-sealed.json"),
        }
