"""Portable reviewed ZIP: separate visual/collision assets and immutable evidence."""

import hashlib
import json
import zipfile
from pathlib import Path

from pydantic import TypeAdapter

from simready.data.dataset import atomic_dataset, sha256_file
from simready.data.schema import Identifier
from simready.evaluation.runner import validate_evaluation
from simready.evaluation.store import EvaluationStore
from simready.review.auth import Principal
from simready.review.workflow import Workflow, scene_evidence_digest
from simready.scene.store import SceneStore, utc_now
from simready.simulation.store import SimulationStore


class ExportStore:
    def __init__(self, scenes: SceneStore):
        self.scenes = scenes
        with scenes.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS exports (
                scene_id TEXT NOT NULL, export_id TEXT NOT NULL, metadata_json TEXT NOT NULL,
                PRIMARY KEY(scene_id,export_id))""")

    def build(self, scene_id: str, version: int, actor: Principal) -> dict:
        # Both local roles may export; identity is still server-verified by the API.
        state = self.scenes.get(scene_id, version)
        workflow = Workflow(self.scenes)
        if state["status"] != "approved" or not state.get("review", {}).get("approval_event_id"):
            raise ValueError("only an approved immutable revision can be exported")
        review = state["review"]
        if scene_evidence_digest(state) != review["scene_payload_sha256"]:
            raise ValueError("approved scene content differs from captured evidence")
        audit = workflow.records(scene_id)
        approval = next((e for e in audit if e["event_id"] == review["approval_event_id"]), None)
        if (
            not approval
            or approval["action"] != "approve"
            or approval["after_version"] != version
            or approval["actor"]["user_id"] == review["submitted_by"]["user_id"]
        ):
            raise ValueError("approved badge lacks a matching independent audit decision")
        workflow.captured_readiness(scene_id, state)
        evaluations, simulations = EvaluationStore(self.scenes), SimulationStore(self.scenes)
        report_id, simulation_id = review["evaluation"]["run_id"], review["simulation"]["run_id"]
        metadata = validate_evaluation(evaluations.report_root(scene_id, report_id))
        if (
            evaluations.get(scene_id, report_id)["evaluation_sha256"]
            != review["evaluation"]["sha256"]
        ):
            raise ValueError("approved evaluation binding changed")
        simulation = simulations.get(scene_id, simulation_id)
        if simulation["simulation_sha256"] != review["simulation"]["sha256"]:
            raise ValueError("approved simulation binding changed")
        import uuid

        export_id = uuid.uuid4().hex
        output = self.scenes.package(scene_id) / "exports" / export_id
        hashes = {}

        def payload(value):
            return json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode()

        with atomic_dataset(output, 300_000_000) as stage:
            with zipfile.ZipFile(
                stage / "scene.zip", "w", compression=zipfile.ZIP_DEFLATED
            ) as archive:

                def write(name: str, data: bytes, expected: str | None = None):
                    digest = hashlib.sha256(data).hexdigest()
                    if expected is not None and digest != expected:
                        raise ValueError("export input changed while reading: " + name)
                    archive.writestr(name, data)
                    hashes[name] = digest

                portable = json.loads(json.dumps(state))
                for name, asset in portable["base"]["assets"].items():
                    prefix = asset["path"].split("/")[0]
                    target = (
                        {
                            "reconstruction": "render",
                            "geometry": "collision",
                            "views": "reference_views",
                        }[prefix]
                        + "/"
                        + Path(asset["path"]).name
                    )
                    write(target, self.scenes.asset(scene_id, name).read_bytes(), asset["sha256"])
                    asset["path"] = target
                write("scene.json", payload(portable))
                write(
                    "review/readiness.json",
                    (
                        self.scenes.package(scene_id)
                        / "reviews"
                        / review["review_id"]
                        / "readiness.json"
                    ).read_bytes(),
                    review["readiness_sha256"],
                )
                write("review/scope.json", payload(review))
                write(
                    "review/audit.json",
                    payload([e for e in audit if e["after_version"] <= version]),
                )
                for name in ("evaluation.json", *metadata["files_sha256"]):
                    write(
                        "evaluation/" + name,
                        evaluations.asset(scene_id, report_id, name).read_bytes(),
                    )
                manifest = json.loads(
                    simulations.asset(scene_id, simulation_id, "simulation.json").read_text()
                )
                for name in ("simulation.json", *manifest["files_sha256"]):
                    write(
                        "simulation/" + name,
                        simulations.asset(scene_id, simulation_id, name).read_bytes(),
                    )
                source = state["base"]["source"]
                license_text = (
                    "SimReady source: MIT. Analytic fixture: CC0.\n"
                    f"Dataset: {source['name']}\nLicense: {source['license']}\n"
                    f"Attribution: {source['attribution']}\nSource: {source['url']}\n"
                    "CC BY 4.0 terms: https://creativecommons.org/licenses/by/4.0/ "
                    "(where applicable).\n"
                    "No third-party model weights or full raw dataset are included; "
                    "aligned reference images appear in the report.\n"
                    "This package contains a scoped local review, not safety certification.\n"
                )
                write("LICENSES.txt", license_text.encode())
                write(
                    "manifest.json",
                    payload(
                        {
                            "schema_version": "1.0",
                            "scene_id": scene_id,
                            "approved_version": version,
                            "source_version": review["source_version"],
                            "approval_event_id": review["approval_event_id"],
                            "scope": review["scope"],
                            "units": "meters",
                            "world_frame": state["world_frame"],
                            "files_sha256": hashes.copy(),
                        }
                    ),
                )
            registration = {
                "export_id": export_id,
                "scene_id": scene_id,
                "approved_version": version,
                "source_version": review["source_version"],
                "created_at": utc_now(),
                "created_by": actor.model_dump(mode="json"),
                "approval_event_id": review["approval_event_id"],
                "sha256": sha256_file(stage / "scene.zip"),
                "bytes": (stage / "scene.zip").stat().st_size,
            }
        with self.scenes.connect() as db:
            db.execute(
                "INSERT INTO exports VALUES(?,?,?)", (scene_id, export_id, json.dumps(registration))
            )
        return registration

    def asset(self, scene_id: str, export_id: str) -> Path:
        TypeAdapter(Identifier).validate_python(export_id)
        self.scenes.get(scene_id)
        with self.scenes.connect() as db:
            row = db.execute(
                "SELECT metadata_json FROM exports WHERE scene_id=? AND export_id=?",
                (scene_id, export_id),
            ).fetchone()
        if row is None:
            raise KeyError("unknown reviewed export")
        metadata = json.loads(row[0])
        path = self.scenes.package(scene_id) / "exports" / export_id / "scene.zip"
        if sha256_file(path) != metadata["sha256"]:
            raise ValueError("reviewed export content hash mismatch")
        return path
