"""Scoped review transitions create immutable revisions and transactional audit events."""

import hashlib
import json
import sqlite3
import uuid
from typing import Literal, Self

import numpy as np
from pydantic import Field, model_validator

from simready.data.dataset import atomic_dataset, sha256_file, write_json
from simready.data.schema import Contract, Identifier
from simready.evaluation.readiness import readiness
from simready.evaluation.store import EvaluationStore
from simready.review.auth import AuthorizationError, AuthStore, Principal
from simready.scene.store import SceneStore, VersionConflict, utc_now
from simready.simulation.store import SimulationStore


def digest_json(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def scene_evidence_digest(state: dict) -> str:
    return digest_json(
        {
            "objects": state["objects"],
            "scenarios": state.get("scenarios", []),
            "artifact_sha256": state["base"]["assets"]["artifact.json"]["sha256"],
            "geometry_sha256": state["base"]["assets"]["collision_mesh.npz"]["sha256"],
        }
    )


class ReviewScope(Contract):
    task: Literal["occupancy_navigation_regression", "heldout_view_inspection"]
    name: str = Field(min_length=5, max_length=160)
    camera_ids: tuple[Identifier, ...] = Field(min_length=1, max_length=128)
    bounds_xz_m: tuple[float, float, float, float]
    expected_navigation: Literal["goal_reached", "no_route"]
    limitations_acknowledged: Literal[True]

    @model_validator(mode="after")
    def scope_bounds(self) -> Self:
        xmin, zmin, xmax, zmax = self.bounds_xz_m
        if not xmin < xmax or not zmin < zmax or max(abs(v) for v in self.bounds_xz_m) > 10000:
            raise ValueError("review scope must be a bounded positive metric XZ region")
        if len(self.camera_ids) != len(set(self.camera_ids)):
            raise ValueError("scope camera IDs must be unique")
        return self


class SubmitRequest(Contract):
    expected_version: int = Field(ge=1, strict=True)
    report_run_id: Identifier
    simulation_run_id: Identifier
    scope: ReviewScope


class ReviewRequest(Contract):
    expected_version: int = Field(ge=1, strict=True)
    decision: Literal["approve", "reject"]
    reason: str = Field(min_length=10, max_length=2000)


class Workflow:
    def __init__(self, scenes: SceneStore):
        self.scenes = scenes
        with scenes.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS review_audit (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, scene_id TEXT NOT NULL,
                    event_id TEXT NOT NULL UNIQUE, payload_json TEXT NOT NULL,
                    sha256 TEXT NOT NULL);
                CREATE TRIGGER IF NOT EXISTS review_audit_no_update BEFORE UPDATE ON review_audit
                    BEGIN SELECT RAISE(ABORT,'review audit is append-only'); END;
                CREATE TRIGGER IF NOT EXISTS review_audit_no_delete BEFORE DELETE ON review_audit
                    BEGIN SELECT RAISE(ABORT,'review audit is append-only'); END;
            """)

    def records(self, scene_id: str) -> list[dict]:
        self.scenes.get(scene_id)
        with self.scenes.connect() as db:
            rows = db.execute(
                "SELECT * FROM review_audit WHERE scene_id=? ORDER BY sequence", (scene_id,)
            ).fetchall()
        previous, records = None, []
        for row in rows:
            payload = json.loads(row["payload_json"])
            if (
                payload["previous_sha256"] != previous
                or digest_json(payload) != row["sha256"]
                or payload["scene_id"] != scene_id
                or payload["event_id"] != row["event_id"]
            ):
                raise ValueError("review audit chain integrity failure")
            records.append(payload | {"sha256": row["sha256"]})
            previous = row["sha256"]
        return records

    def append(
        self,
        db: sqlite3.Connection,
        scene_id: str,
        action: str,
        actor: Principal,
        before: int,
        after: int,
        details: dict,
    ) -> dict:
        previous = db.execute(
            "SELECT sha256 FROM review_audit WHERE scene_id=? ORDER BY sequence DESC LIMIT 1",
            (scene_id,),
        ).fetchone()
        payload = {
            "event_id": uuid.uuid4().hex,
            "scene_id": scene_id,
            "action": action,
            "actor": actor.model_dump(mode="json"),
            "before_version": before,
            "after_version": after,
            "timestamp": utc_now(),
            "details": details,
            "previous_sha256": previous[0] if previous else None,
        }
        digest = digest_json(payload)
        db.execute(
            "INSERT INTO review_audit(scene_id,event_id,payload_json,sha256) VALUES(?,?,?,?)",
            (scene_id, payload["event_id"], json.dumps(payload), digest),
        )
        return payload | {"sha256": digest}

    def captured_readiness(self, scene_id: str, state: dict) -> dict:
        review = state.get("review")
        if not review:
            raise ValueError("scene revision has no captured review evidence")
        path = self.scenes.package(scene_id) / "reviews" / review["review_id"] / "readiness.json"
        if sha256_file(path) != review["readiness_sha256"]:
            raise ValueError("captured readiness content changed")
        return json.loads(path.read_text())

    def submit(self, scene_id: str, request: SubmitRequest, actor: Principal) -> dict:
        AuthStore.require(actor, "builder")
        state = self.scenes.get(scene_id)
        if state["version"] != request.expected_version:
            raise VersionConflict(state["version"])
        if state["status"] != "draft":
            raise ValueError(
                "only a draft can be submitted; revise rejected content before resubmitting"
            )
        qa = readiness(
            self.scenes,
            scene_id,
            state["version"],
            request.report_run_id,
            request.simulation_run_id,
        )
        if qa["outcome"] == "insufficient_evidence":
            raise ValueError(
                "submission requires a base evaluation and navigation evidence for this revision"
            )
        tested = {view["frame_id"] for view in qa["coverage"]["views"]}
        if not set(request.scope.camera_ids).issubset(tested):
            raise ValueError("review camera scope must use measured held-out reference views")
        simulation = SimulationStore(self.scenes).get(scene_id, request.simulation_run_id)
        if not np.allclose(
            request.scope.bounds_xz_m, simulation["scenario"]["bounds_xz_m"], atol=1e-8, rtol=0
        ):
            raise ValueError("review region must match the evaluated navigation map bounds")
        simulation_input = json.loads(
            SimulationStore(self.scenes)
            .asset(scene_id, request.simulation_run_id, "scene-input.json")
            .read_text()
        )
        if scene_evidence_digest(simulation_input) != scene_evidence_digest(state):
            raise ValueError("navigation input content differs from the submitted scene")
        review_id = uuid.uuid4().hex
        capture = self.scenes.package(scene_id) / "reviews" / review_id
        with self.scenes.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            actual = db.execute(
                "SELECT current_version FROM scenes WHERE scene_id=?", (scene_id,)
            ).fetchone()[0]
            if actual != request.expected_version:
                raise VersionConflict(actual)
            with atomic_dataset(capture, 2_000_000) as stage:
                write_json(stage / "readiness.json", qa)
            review = {
                "review_id": review_id,
                "scene_payload_sha256": scene_evidence_digest(state),
                "source_version": state["version"],
                "scope": request.scope.model_dump(mode="json"),
                "submitted_by": actor.model_dump(mode="json"),
                "evaluation": qa["evaluation"],
                "simulation": qa["simulation"],
                "readiness_sha256": sha256_file(capture / "readiness.json"),
                "disclaimer": (
                    "Scoped local experiment only; not safety certification, "
                    "physical free-space truth or detection accuracy."
                ),
            }
            event = self.append(db, scene_id, "submitted", actor, actual, actual + 1, review)
            review["submission_event_id"] = event["event_id"]
            state.update(
                version=actual + 1, status="submitted", updated_at=utc_now(), review=review
            )
            self.scenes.commit_revision(
                db, scene_id, {k: v for k, v in state.items() if k != "base"}
            )
        return self.scenes.get(scene_id)

    def decide(self, scene_id: str, request: ReviewRequest, actor: Principal) -> dict:
        AuthStore.require(actor, "reviewer")
        state = self.scenes.get(scene_id)
        if state["version"] != request.expected_version:
            raise VersionConflict(state["version"])
        if state["status"] != "submitted":
            raise ValueError("only the current submitted revision can be reviewed")
        review = state["review"]
        if review["submitted_by"]["user_id"] == actor.user_id:
            raise AuthorizationError(
                "self-approval/review is forbidden even after an account role change"
            )
        self.records(scene_id)
        if request.decision == "approve":
            if scene_evidence_digest(state) != review["scene_payload_sha256"]:
                raise ValueError("submitted scene content changed")
            qa = self.captured_readiness(scene_id, state)
            from simready.evaluation.runner import validate_evaluation

            evaluation = EvaluationStore(self.scenes)
            validate_evaluation(evaluation.report_root(scene_id, review["evaluation"]["run_id"]))
            if (
                evaluation.get(scene_id, review["evaluation"]["run_id"])["evaluation_sha256"]
                != review["evaluation"]["sha256"]
            ):
                raise ValueError("review evaluation binding changed")
            simulations = SimulationStore(self.scenes)
            run = simulations.get(scene_id, review["simulation"]["run_id"])
            for name in (
                "simulation.json",
                "result.json",
                "occupancy.json",
                "scenario.json",
                "scene-input.json",
            ):
                simulations.asset(scene_id, run["run_id"], name)
            for name in state["base"]["assets"]:
                self.scenes.asset(scene_id, name)
            if run["simulation_sha256"] != review["simulation"]["sha256"]:
                raise ValueError("review simulation binding changed")
            expected = review["scope"]["expected_navigation"] == "goal_reached"
            if bool(qa["simulation"]["result"]["route_success"]) != expected:
                raise ValueError(
                    "navigation evidence contradicts the declared regression expectation"
                )
        with self.scenes.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            actual = db.execute(
                "SELECT current_version FROM scenes WHERE scene_id=?", (scene_id,)
            ).fetchone()[0]
            if actual != request.expected_version:
                raise VersionConflict(actual)
            event = self.append(
                db,
                scene_id,
                request.decision,
                actor,
                actual,
                actual + 1,
                {
                    "review_id": review["review_id"],
                    "source_version": review["source_version"],
                    "reason": request.reason,
                    "scope": review["scope"],
                    "readiness_sha256": review["readiness_sha256"],
                },
            )
            review.update(
                decided_by=actor.model_dump(mode="json"),
                reason=request.reason,
                decision_event_id=event["event_id"],
                decision_at=event["timestamp"],
            )
            if request.decision == "approve":
                review["approval_event_id"] = event["event_id"]
            state.update(
                version=actual + 1,
                status="approved" if request.decision == "approve" else "rejected",
                updated_at=utc_now(),
                review=review,
            )
            self.scenes.commit_revision(
                db, scene_id, {k: v for k, v in state.items() if k != "base"}
            )
        return self.scenes.get(scene_id)
