"""Immutable report registration and persistent single-machine evaluation jobs."""

import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Literal

from pydantic import Field, TypeAdapter

from simready.data.dataset import atomic_dataset, local_file, sha256_file
from simready.data.schema import Contract, Identifier
from simready.evaluation.runner import validate_evaluation
from simready.scene.store import SceneStore, VersionConflict, utc_now


class EvaluationRequest(Contract):
    expected_version: int = Field(ge=1, strict=True)
    split: Literal["validation", "test"] = "test"


class EvaluationStore:
    def __init__(self, scenes: SceneStore):
        self.scenes = scenes
        with scenes.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS evaluations (
                    scene_id TEXT NOT NULL, run_id TEXT NOT NULL, scene_version INTEGER NOT NULL,
                    metadata_json TEXT NOT NULL, PRIMARY KEY(scene_id, run_id));
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY, scene_id TEXT NOT NULL, scene_version INTEGER NOT NULL,
                    split TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL, error TEXT, worker_pid INTEGER);
            """)

    def references(self, scene_id: str) -> dict:
        self.scenes.get(scene_id)
        with self.scenes.connect() as db:
            base = json.loads(
                db.execute("SELECT base_json FROM scenes WHERE scene_id=?", (scene_id,)).fetchone()[
                    0
                ]
            )
        if not base.get("local_dataset_path"):
            raise ValueError("evaluation requires a registered canonical source dataset")
        return {key: Path(base[key]) for key in ("local_dataset_path", "local_reconstruction_path")}

    def report_root(self, scene_id: str, run_id: str) -> Path:
        TypeAdapter(Identifier).validate_python(run_id)
        return self.scenes.package(scene_id) / "reports" / run_id

    def register(
        self, scene_id: str, run_id: str, source: Path, version: int | None = None
    ) -> dict:
        state = self.scenes.get(scene_id, version)
        root = self.report_root(scene_id, run_id)
        metadata = validate_evaluation(source)
        if (
            metadata["artifact_sha256"] != state["base"]["assets"]["artifact.json"]["sha256"]
            or metadata["split_sha256"] != state["base"]["split_sha256"]
        ):
            raise ValueError("evaluation belongs to a different scene reconstruction or split")
        summary = json.loads((source / "summary.json").read_text())
        with atomic_dataset(root, 300_000_000) as stage:
            for name in ("evaluation.json", *metadata["files_sha256"]):
                target = stage / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(local_file(source, name), target)
                target.chmod(0o444)
        registration = {
            "run_id": run_id,
            "scene_id": scene_id,
            "scene_version": state["version"],
            "created_at": metadata["created_at"],
            "evaluation_sha256": sha256_file(root / "evaluation.json"),
            "summary": summary,
        }
        with self.scenes.connect() as db:
            db.execute(
                "INSERT INTO evaluations VALUES(?,?,?,?)",
                (scene_id, run_id, state["version"], json.dumps(registration)),
            )
        return registration

    def reports(self, scene_id: str) -> list[dict]:
        self.scenes.get(scene_id)
        with self.scenes.connect() as db:
            rows = db.execute(
                "SELECT metadata_json FROM evaluations WHERE scene_id=? ORDER BY run_id",
                (scene_id,),
            ).fetchall()
        return sorted(
            [json.loads(row[0]) for row in rows], key=lambda r: (r["created_at"], r["run_id"])
        )

    def get(self, scene_id: str, run_id: str) -> dict:
        self.report_root(scene_id, run_id)
        self.scenes.get(scene_id)
        with self.scenes.connect() as db:
            row = db.execute(
                "SELECT metadata_json FROM evaluations WHERE scene_id=? AND run_id=?",
                (scene_id, run_id),
            ).fetchone()
        if row is None:
            raise KeyError("unknown evaluation report")
        registration = json.loads(row[0])
        root = self.report_root(scene_id, run_id)
        if sha256_file(local_file(root, "evaluation.json")) != registration["evaluation_sha256"]:
            raise ValueError("registered evaluation manifest changed")
        # Asset requests additionally validate their own content; summary was copied into SQLite.
        return registration

    def asset(self, scene_id: str, run_id: str, name: str) -> Path:
        self.get(scene_id, run_id)
        root = self.report_root(scene_id, run_id)
        metadata = json.loads((root / "evaluation.json").read_text())
        expected = metadata["files_sha256"].get(name)
        if name == "evaluation.json":
            return root / name
        if expected is None:
            raise KeyError("unknown evaluation asset")
        path = local_file(root, name)
        if sha256_file(path) != expected:
            raise ValueError("evaluation asset content hash mismatch")
        return path

    def job(self, job_id: str) -> dict:
        TypeAdapter(Identifier).validate_python(job_id)
        with self.scenes.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            raise KeyError("unknown job")
        value = dict(row)
        value.pop("worker_pid")
        path = self.scenes.root / "jobs" / job_id / "job.log"
        value["log_tail"] = path.read_text()[-8000:] if path.is_file() else ""
        value["run_id"] = job_id if value["status"] == "succeeded" else None
        return value

    def jobs(self, scene_id: str) -> list[dict]:
        self.scenes.get(scene_id)
        with self.scenes.connect() as db:
            ids = [
                row[0]
                for row in db.execute(
                    "SELECT job_id FROM jobs WHERE scene_id=? ORDER BY created_at", (scene_id,)
                )
            ]
        return [self.job(job_id) for job_id in ids]

    def enqueue(self, scene_id: str, request: EvaluationRequest) -> dict:
        self.references(scene_id)
        now, job_id = utc_now(), uuid.uuid4().hex
        with self.scenes.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            version = db.execute(
                "SELECT current_version FROM scenes WHERE scene_id=?", (scene_id,)
            ).fetchone()[0]
            if version != request.expected_version:
                raise VersionConflict(version)
            db.execute(
                "INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?)",
                (job_id, scene_id, version, request.split, "queued", now, now, None, None),
            )
        directory = self.scenes.root / "jobs" / job_id
        directory.mkdir(parents=True)
        try:
            with (directory / "launcher.log").open("w") as log:
                subprocess.Popen(
                    [sys.executable, "-m", "simready.evaluation.jobs", str(self.scenes.root)],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
        except OSError as exc:
            with self.scenes.connect() as db:
                db.execute(
                    "UPDATE jobs SET status='failed', error=?, updated_at=? WHERE job_id=?",
                    (str(exc), utc_now(), job_id),
                )
            raise ValueError("could not launch local evaluation worker") from exc
        return self.job(job_id)
