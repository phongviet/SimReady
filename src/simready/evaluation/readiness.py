"""Measured evidence components and explicit uncertainty, never a safety certificate."""

import json

import numpy as np

from simready.data.dataset import local_file, sha256_file
from simready.data.schema import DatasetManifest, Frame
from simready.evaluation.runner import validate_evaluation
from simready.evaluation.store import EvaluationStore
from simready.scene.store import SceneStore
from simready.simulation.store import SimulationStore


def pose_diagnostics(training: np.ndarray, queried: np.ndarray) -> list[dict]:
    if not len(training):
        raise ValueError("coverage needs training camera poses")
    result = []
    for pose in queried:
        distances = np.linalg.norm(training[:, :3, 3] - pose[:3, 3], axis=1)
        relative = np.swapaxes(training[:, :3, :3], 1, 2) @ pose[:3, :3]
        angles = np.degrees(
            np.arccos(np.clip((np.trace(relative, axis1=1, axis2=2) - 1) / 2, -1, 1))
        )
        nearest = int(distances.argmin())
        inside = bool(
            np.all(pose[:3, 3] >= training[:, :3, 3].min(0) - 1e-8)
            and np.all(pose[:3, 3] <= training[:, :3, 3].max(0) + 1e-8)
        )
        exact = bool(np.any((distances < 1e-6) & (angles < 1e-4)))
        classification = (
            "observed_training_pose"
            if exact
            else (
                "interpolated_but_tested"
                if inside and distances[nearest] <= 0.5 and angles[nearest] <= 30
                else "tested_extrapolation"
            )
        )
        result.append(
            {
                "nearest_training_index": nearest,
                "distance_m": float(distances[nearest]),
                "rotation_deg": float(angles[nearest]),
                "minimum_rotation_deg": float(angles.min()),
                "center_inside_training_aabb": inside,
                "classification": classification,
            }
        )
    return result


def mesh_diagnostics(vertices: np.ndarray, triangles: np.ndarray) -> dict:
    edges = np.sort(
        np.concatenate([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]]), axis=1
    )
    _, counts = np.unique(edges, axis=0, return_counts=True)
    area = (
        np.linalg.norm(
            np.cross(
                vertices[triangles[:, 1]] - vertices[triangles[:, 0]],
                vertices[triangles[:, 2]] - vertices[triangles[:, 0]],
            ),
            axis=1,
        )
        / 2
    )
    return {
        "vertices": len(vertices),
        "triangles": len(triangles),
        "boundary_edges": int((counts == 1).sum()),
        "nonmanifold_edges": int((counts > 2).sum()),
        "degenerate_triangles": int((area < 1e-10).sum()),
        "surface_area_m2": float(area.sum()),
        "bounds_min_m": vertices.min(0).tolist(),
        "bounds_max_m": vertices.max(0).tolist(),
        "quality": "coarse_observed_surface_proxy",
        "aligned_ground_truth_evaluated": False,
        "chamfer_m": None,
        "f_score": None,
    }


def readiness(
    scenes: SceneStore,
    scene_id: str,
    version: int | None = None,
    report_run_id: str | None = None,
    simulation_run_id: str | None = None,
) -> dict:
    state = scenes.get(scene_id, version)
    source_version = state.get("review", {}).get("source_version", state["version"])
    if state.get("review"):
        report_run_id = report_run_id or state["review"]["evaluation"]["run_id"]
        simulation_run_id = simulation_run_id or state["review"]["simulation"]["run_id"]
    evaluations, simulations = EvaluationStore(scenes), SimulationStore(scenes)
    reports = evaluations.reports(scene_id)
    report = (
        evaluations.get(scene_id, report_run_id)
        if report_run_id
        else (reports[-1] if reports else None)
    )
    runs = [run for run in simulations.runs(scene_id) if run["scene_version"] == source_version]
    run = (
        simulations.get(scene_id, simulation_run_id)
        if simulation_run_id
        else (runs[-1] if runs else None)
    )
    if run and run["scene_version"] != source_version:
        raise ValueError("simulation does not match the captured scene revision")
    geometry_path = scenes.asset(scene_id, "collision_mesh.npz")
    with np.load(geometry_path, allow_pickle=False) as arrays:
        geometry = mesh_diagnostics(arrays["vertices"], arrays["triangles"])
    model = json.loads(scenes.asset(scene_id, "artifact.json").read_text())
    references = evaluations.references(scene_id)
    dataset = references["local_dataset_path"]
    if (
        sha256_file(local_file(dataset, "manifest.json"))
        != model["provenance"]["dataset_manifest_sha256"]
    ):
        raise ValueError("coverage dataset manifest differs from model provenance")
    manifest = DatasetManifest.model_validate_json((dataset / "manifest.json").read_text())
    if sha256_file(local_file(dataset, "frames.jsonl")) != manifest.frames_sha256:
        raise ValueError("coverage camera metadata changed")
    frames = [
        Frame.model_validate_json(line)
        for line in (dataset / "frames.jsonl").read_text().splitlines()
    ]
    frame_map = {frame.frame_id: frame for frame in frames}
    train_ids = model["provenance"]["training_frame_ids"]
    training = np.array([frame_map[name].T_world_camera for name in train_ids])
    coverage, perception, photometric = [], None, None
    flags = []
    if report:
        validate_evaluation(evaluations.report_root(scene_id, report["run_id"]))
        summary = report["summary"]
        if summary["artifact_sha256"] != state["base"]["assets"]["artifact.json"]["sha256"]:
            raise ValueError("evaluation does not match the immutable scene model")
        views = json.loads(evaluations.asset(scene_id, report["run_id"], "views.json").read_text())
        poses = np.array([np.linalg.inv(np.array(view["camera"]["viewmat"])) for view in views])
        for view, diagnostic in zip(views, pose_diagnostics(training, poses), strict=True):
            diagnostic.update(
                frame_id=view["frame_id"],
                reference_available=True,
                nearest_training_frame_id=train_ids[diagnostic["nearest_training_index"]],
                depth_completeness=view["metrics"]["depth_completeness"],
            )
            coverage.append(diagnostic)
        photometric = summary["means"]
        perception = summary["detection_totals"]
        if perception["real_count"] and not perception["rendered_count"]:
            flags.append(
                "No rendered predictions meet the fixed confidence "
                "threshold; real-image predictions exist."
            )
        if perception["empty_both"]:
            flags.append(
                "Some detector pairs are empty in both domains; these "
                "provide no positive task-quality evidence."
            )
    else:
        flags.append("No measured held-out image/depth/perception report is registered.")
    if not run:
        flags.append("No navigation run matches this source scene revision.")
    if geometry["boundary_edges"] or geometry["nonmanifold_edges"]:
        flags.append(
            "Collision mesh has open/nonmanifold surface boundaries; solid "
            "occupancy is not established."
        )
    if run:
        if run["floor_evidence"] == "declared_virtual_floor_assumption":
            flags.append(
                "Navigation floor support is a declared virtual assumption, "
                "not observed floor truth."
            )
        if not run["result_summary"]["route_success"]:
            flags.append(
                "Selected navigation run did not reach the goal; inspect its"
                " reason and declared regression expectation."
            )
    approved = state["status"] == "approved" and bool(
        state.get("review", {}).get("approval_event_id")
    )
    if approved:
        from simready.review.workflow import Workflow, scene_evidence_digest

        workflow = Workflow(scenes)
        workflow.captured_readiness(scene_id, state)
        if scene_evidence_digest(state) != state["review"]["scene_payload_sha256"]:
            raise ValueError("approved content differs from captured review")
        simulation_manifest = json.loads(
            simulations.asset(scene_id, run["run_id"], "simulation.json").read_text()
        )
        for name in simulation_manifest["files_sha256"]:
            simulations.asset(scene_id, run["run_id"], name)
        events = workflow.records(scene_id)
        if not any(
            e["event_id"] == state["review"]["approval_event_id"]
            and e["action"] == "approve"
            and e["after_version"] == state["version"]
            for e in events
        ):
            raise ValueError("approved state has no matching recorded decision")
    return {
        "schema_version": "1.0",
        "scene_id": scene_id,
        "scene_version": state["version"],
        "source_version": source_version,
        "world_units": "meters",
        "world_frame": state["world_frame"],
        "outcome": "usable_for_declared_test"
        if approved
        else ("needs_review" if report and run else "insufficient_evidence"),
        "review_scope": state.get("review", {}).get("scope") if approved else None,
        "geometry": geometry,
        "photometric": photometric,
        "perception": perception,
        "coverage": {
            "training_cameras": len(training),
            "tested_reference_views": len(coverage),
            "views": coverage,
            "unobserved_free_views": "unverified; no real reference metrics",
            "heuristics": {
                "distance_m": 0.5,
                "rotation_deg": 30.0,
                "calibrated_readiness_thresholds": False,
            },
        },
        "evaluation": None
        if not report
        else {
            "run_id": report["run_id"],
            "scene_version": report["scene_version"],
            "sha256": report["evaluation_sha256"],
            "scope": "immutable base model only; excludes proxy edits",
        },
        "simulation": None
        if not run
        else {
            "run_id": run["run_id"],
            "scene_version": run["scene_version"],
            "sha256": run["simulation_sha256"],
            "result": run["result_summary"],
            "floor_evidence": run["floor_evidence"],
            "floor_support_cells": run["floor_support_cells"],
            "unknown_cells": run["unknown_cells"],
        },
        "flags": flags,
        "limitations": [
            (
                "Coverage measures reference camera pose novelty, not volumetric"
                " visibility or physical free-space coverage."
            ),
            (
                "Pose classification thresholds are declared heuristics, not "
                "certified or validation-calibrated readiness gates."
            ),
            (
                "Base evaluation can be reused across proxy-only revisions of "
                "the same model; simulation is bound to the exact source "
                "revision."
            ),
            (
                "Geometry and navigation are coarse proxies. Detector agreement "
                "is not detection accuracy; no broad safety or sim-to-real "
                "claim."
            ),
            *state["base"]["limitations"],
        ],
    }
