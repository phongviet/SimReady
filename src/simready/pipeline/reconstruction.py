"""Serialized reconstruction jobs bound to imported or registered dataset inputs."""

import contextlib
import fcntl
import json
import subprocess
import sys
import traceback
import uuid
from pathlib import Path
from typing import Literal

from pydantic import TypeAdapter

from simready.data.dataset import local_file, sha256_file
from simready.data.schema import Contract, Identifier
from simready.evaluation.store import EvaluationStore
from simready.reconstruction.contracts import ReconstructionConfig
from simready.reconstruction.gsplat import GsplatBackend, load_records, validate_artifact
from simready.scene.store import SceneStore, utc_now
from simready.storage import PROJECT_ROOT


class ReconstructionRequest(Contract):
    preset: Literal["smoke", "local_6gb"] = "smoke"


class ReconstructionStore:
    def __init__(self, scenes):
        self.scenes = scenes
        self.root = scenes.root
        with scenes.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS reconstruction_jobs(
                job_id TEXT PRIMARY KEY,scene_id TEXT NOT NULL,dataset_path TEXT NOT NULL,
                dataset_sha256 TEXT NOT NULL,config_json TEXT NOT NULL,status TEXT NOT NULL,
                created_at TEXT NOT NULL,updated_at TEXT NOT NULL,error TEXT,
                artifact_sha256 TEXT)""")

    def dataset(self, scene_id):
        TypeAdapter(Identifier).validate_python(scene_id)
        with self.scenes.connect() as db:
            row = db.execute(
                "SELECT job_id,result_json FROM import_jobs "
                "WHERE scene_id=? AND status='succeeded'",
                (scene_id,),
            ).fetchone()
        if row:
            dataset = self.root / "import-jobs" / row["job_id"] / "dataset"
            result = json.loads(row["result_json"])
            manifest, _, _ = load_records(dataset, ("train",))
            if (
                result["frames_sha256"] != manifest.frames_sha256
                or result["split_sha256"] != manifest.split_sha256
            ):
                raise ValueError("imported dataset changed")
            return dataset
        return EvaluationStore(self.scenes).references(scene_id)["local_dataset_path"]

    def enqueue(self, scene_id, request):
        dataset = self.dataset(scene_id)
        load_records(dataset, ("train",))
        config = ReconstructionConfig.model_validate_json(
            (PROJECT_ROOT / f"configs/recon_{request.preset}.json").read_text()
        )
        job_id = uuid.uuid4().hex
        now = utc_now()
        with self.scenes.connect() as db:
            db.execute(
                "INSERT INTO reconstruction_jobs VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    job_id,
                    scene_id,
                    str(dataset),
                    sha256_file(dataset / "manifest.json"),
                    config.model_dump_json(),
                    "queued",
                    now,
                    now,
                    None,
                    None,
                ),
            )
        directory = self.root / "reconstruction-jobs" / job_id
        directory.mkdir(parents=True)
        try:
            with (directory / "launcher.log").open("w") as log:
                subprocess.Popen(
                    [sys.executable, "-m", "simready.pipeline.reconstruction", str(self.root)],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
        except OSError as exc:
            with self.scenes.connect() as db:
                db.execute(
                    "UPDATE reconstruction_jobs SET status='failed',error=?,updated_at=? "
                    "WHERE job_id=?",
                    (str(exc), utc_now(), job_id),
                )
        return self.job(job_id)

    def job(self, job_id):
        TypeAdapter(Identifier).validate_python(job_id)
        with self.scenes.connect() as db:
            row = db.execute(
                "SELECT * FROM reconstruction_jobs WHERE job_id=?", (job_id,)
            ).fetchone()
        if row is None:
            raise KeyError("unknown reconstruction job")
        value = dict(row)
        value.pop("dataset_path")
        value["config"] = json.loads(value.pop("config_json"))
        path = self.root / "reconstruction-jobs" / job_id / "job.log"
        value["log_tail"] = path.read_text()[-8000:] if path.exists() else ""
        value["kind"] = "reconstruction"
        return value

    def asset(self, job_id, name):
        job = self.job(job_id)
        if job["status"] != "succeeded":
            raise ValueError("reconstruction job has no completed artifact")
        root = self.root / "reconstruction-jobs" / job_id / "model"
        if sha256_file(local_file(root, "artifact.json")) != job["artifact_sha256"]:
            raise ValueError("model manifest changed")
        metadata = validate_artifact(root)
        if name not in {"artifact.json", *metadata["files_sha256"]}:
            raise KeyError("unregistered model asset")
        return local_file(root, name)


def work(root):
    store = ReconstructionStore(SceneStore(root))
    with (root / "evaluation-worker.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with store.scenes.connect() as db:
            db.execute(
                "UPDATE reconstruction_jobs SET status='failed',error='Worker interrupted; "
                "submit a new job',updated_at=? WHERE status='running'",
                (utc_now(),),
            )
        while True:
            with store.scenes.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute(
                    "SELECT * FROM reconstruction_jobs WHERE status='queued' "
                    "ORDER BY created_at,job_id LIMIT 1"
                ).fetchone()
                if row is None:
                    return
                job = dict(row)
                db.execute(
                    "UPDATE reconstruction_jobs SET status='running',updated_at=? WHERE job_id=?",
                    (utc_now(), job["job_id"]),
                )
            directory = root / "reconstruction-jobs" / job["job_id"]
            directory.mkdir(parents=True, exist_ok=True)
            with (
                (directory / "job.log").open("a") as log,
                contextlib.redirect_stdout(log),
                contextlib.redirect_stderr(log),
            ):
                status, error, digest = "failed", None, None
                try:
                    dataset = Path(job["dataset_path"])
                    if sha256_file(dataset / "manifest.json") != job["dataset_sha256"]:
                        raise ValueError("queued source manifest changed")
                    GsplatBackend().train(
                        dataset,
                        ReconstructionConfig.model_validate_json(job["config_json"]),
                        directory / "model",
                    )
                    if sha256_file(dataset / "manifest.json") != job["dataset_sha256"]:
                        raise ValueError("source manifest changed during training")
                    digest = sha256_file(directory / "model/artifact.json")
                    status = "succeeded"
                    print("Learned artifact saved and verified", flush=True)
                except Exception as exc:
                    error = str(exc)[-2000:]
                    traceback.print_exc()
                with store.scenes.connect() as db:
                    db.execute(
                        "UPDATE reconstruction_jobs SET status=?,error=?,artifact_sha256=?,"
                        "updated_at=? WHERE job_id=?",
                        (status, error, digest, utc_now(), job["job_id"]),
                    )


if __name__ == "__main__":
    work(Path(sys.argv[1]).resolve())
