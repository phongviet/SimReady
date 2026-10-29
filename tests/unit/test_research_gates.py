"""Read-boundary tests use analytic fixtures; numbers here are not experiment results."""

import json
import shutil
from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from pydantic import ValidationError

from simready.data.dataset import sha256_file, validate_scene, write_json
from simready.reconstruction.contracts import ReconstructionConfig
from simready.reconstruction.gsplat import load_records, prepare_training
from simready.research import data as research_data
from simready.research.data import create_dataset, release_test
from simready.research.selection import (
    CandidateFeature,
    SelectionSeal,
    calibrate,
    correlation,
    features,
    json_digest,
    select_farthest,
    select_random,
    select_risk,
    validate_seal,
)


def test_training_never_opens_withheld_candidate_or_test_pixels(scene, tmp_path, monkeypatch):
    manifest, frames, splits = load_records(scene)
    for frame in frames:
        if frame.frame_id in splits.candidate + splits.test:
            (scene / frame.rgb_path).unlink()
            (scene / frame.depth_path).unlink()
    with pytest.raises(ValueError, match="missing file"):
        validate_scene(scene)  # Ordinary validation remains complete and strict.
    observed = []
    original = Image.open

    def track(path, *args, **kwargs):
        observed.append(Path(path).relative_to(scene).as_posix())
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Image, "open", track)
    out = tmp_path / "prepared"
    out.mkdir()
    config = ReconstructionConfig.model_validate_json(Path("configs/recon_smoke.json").read_text())
    record = prepare_training(scene, config, out)
    allowed = {
        getattr(frame, channel + "_path")
        for frame in frames
        if frame.frame_id in splits.train
        for channel in ("rgb", "depth")
    }
    assert set(observed) == allowed
    assert record["training_frame_ids"] == list(splits.train)
    observed.clear()
    load_records(scene, ())
    assert observed == []
    load_records(scene, ("validation",))
    with pytest.raises(ValueError, match="absent"):
        validate_scene(scene, observation_ids={"not-a-frame"})


def test_selector_contract_rejects_ground_truth_channels_and_handles_constant_scores():
    with pytest.raises(ValidationError):
        CandidateFeature(
            frame_id="a",
            distance_m=1,
            rotation_deg=30,
            alpha_hole_fraction=0.1,
            rgb_path="private.png",
        )
    values = [
        CandidateFeature(
            frame_id=f"f{i}", distance_m=0.01 * i, rotation_deg=i, alpha_hole_fraction=0.02 * i
        )
        for i in range(12)
    ]
    targets = (0.2 + features(values) @ np.array([0.4, 0.1, 0.2])).tolist()
    model = calibrate(values, targets, 8, 0.1)
    assert model["fit_ids"] == [f"f{i}" for i in range(8)]
    assert model["check_ids"] == [f"f{i}" for i in range(8, 12)]
    assert np.isfinite(model["coefficients"]).all() and min(model["coefficients"]) >= 0
    selected, ranked = select_risk(values, model, 4)
    assert len(set(selected)) == 4 and ranked[0]["score"] >= ranked[-1]["score"]
    assert correlation([1, 1, 1], [2, 3, 4])["rho"] is None
    assert select_random([v.frame_id for v in values], 4, 42) == select_random(
        [v.frame_id for v in values], 4, 42
    )
    assert select_farthest(
        np.array([[0.0, 0, 0]]), ["a", "b", "c"], np.array([[1.0, 0, 0], [3, 0, 0], [2, 0, 0]]), 2
    ) == ["b", "a"]


def test_observations_cannot_be_materialized_without_complete_matching_seal(
    scene, tmp_path, monkeypatch
):
    manifest, frames, splits = load_records(scene)
    study = tmp_path / "study"
    study.mkdir()
    shutil.copytree(scene, study / "vault")
    metadata = manifest.model_dump(
        mode="json",
        exclude={
            "schema_version",
            "world_units",
            "world_frame",
            "camera_axes",
            "frames_sha256",
            "split_sha256",
        },
    )
    ids = [frame.frame_id for frame in frames]
    partitions = {"train": ids[:3], "validation": ids[3:4], "candidate": ids[4:6], "test": ids[6:]}
    protocol = {"study": {"seeds": [42], "additional_observations": 1}}
    curation = {
        "metadata": metadata,
        "frames": [f.model_dump(mode="json") for f in frames],
        "partitions": partitions,
        "protocol_sha256": json_digest(protocol),
    }
    write_json(study / "curation.json", curation)
    write_json(study / "protocol.json", protocol)
    write_json(study / "access-ledger.json", {"events": []})
    selected = partitions["candidate"][:1]
    with pytest.raises(ValueError, match="sealed"):
        create_dataset(study, tmp_path / "blocked", selected, "variant", "risk-s42")
    with pytest.raises(ValueError, match="sealed"):
        release_test(study, scene)
    rows = []
    (study / "selection").mkdir()
    base = study / "models/base-s42"
    base.mkdir(parents=True)
    write_json(base / "artifact.json", {"fixture": True})
    for method in ("risk", "random", "farthest"):
        key = method + "-s42"
        details = {
            "key": key,
            "method": method,
            "seed": 42,
            "selected_ids": selected,
            "base_artifact_sha256": sha256_file(base / "artifact.json"),
        }
        write_json(study / "selection" / (key + ".json"), details)
        rows.append(
            details
            | {
                "details_sha256": sha256_file(study / "selection" / (key + ".json")),
            }
        )
    seal = {
        "schema_version": "1.0",
        "curation_sha256": sha256_file(study / "curation.json"),
        "protocol_sha256": json_digest(protocol),
        "candidate_ids": partitions["candidate"],
        "seeds": [42],
        "k": len(selected),
        "acquisitions": rows,
    }
    with pytest.raises(ValidationError):
        SelectionSeal.model_validate(seal | {"acquisitions": rows[:1]})
    write_json(study / "selections-sealed.json", seal)
    (study / "selections-sealed.sha256").write_text(sha256_file(study / "selections-sealed.json"))
    output = tmp_path / "allowed"
    append = research_data.append_access

    def crash_before_completion(study, phase, ids, **details):
        if phase == "candidate_release" and details.get("status") == "completed":
            raise SystemExit("injected process death after dataset creation")
        return append(study, phase, ids, **details)

    monkeypatch.setattr(research_data, "append_access", crash_before_completion)
    with pytest.raises(SystemExit):
        create_dataset(study, output, selected, "variant", "risk-s42")
    assert output.is_dir()
    monkeypatch.setattr(research_data, "append_access", append)
    create_dataset(study, output, selected, "variant", "risk-s42")
    events = json.loads((study / "access-ledger.json").read_text())["events"]
    assert [e["status"] for e in events] == ["started", "resumed", "completed"]
    assert len({e["operation_id"] for e in events}) == 1
    assert all(e["at"] for e in events)
    _, _, resulting = load_records(output, ("train", "validation"))
    assert set(resulting.train) == set(partitions["train"] + selected)
    for frame in frames:
        if frame.frame_id in resulting.test + resulting.candidate:
            assert not (output / frame.rgb_path).exists()
            assert not (output / frame.depth_path).exists()
    with pytest.raises(ValueError, match="missing file"):
        validate_scene(output)
    link = research_data.os.link
    attempts = 0

    def fail_during_link(source, target):
        nonlocal attempts
        attempts += 1
        if attempts == 2:
            raise OSError("injected interrupted file linking")
        return link(source, target)

    monkeypatch.setattr(research_data.os, "link", fail_during_link)
    with pytest.raises(OSError, match="interrupted"):
        release_test(study, output)
    monkeypatch.setattr(research_data.os, "link", link)
    events = json.loads((study / "access-ledger.json").read_text())["events"]
    assert events[-1]["status"] == "failed"
    release_test(study, output)
    assert (
        json.loads((study / "access-ledger.json").read_text())["events"][-1]["status"]
        == "completed"
    )
    load_records(output, ("test",))
    for frame in frames:
        if frame.frame_id in resulting.candidate:
            assert not (output / frame.rgb_path).exists()
    with pytest.raises(ValueError, match="named sealed"):
        create_dataset(study, tmp_path / "wrong", partitions["candidate"][1:], "wrong", "risk-s42")
    write_json(study / "selection/risk-s42.json", {"tampered": True})
    with pytest.raises(ValueError, match="details changed"):
        validate_seal(study)
    with pytest.raises(ValueError, match="details changed"):
        release_test(study, output)
