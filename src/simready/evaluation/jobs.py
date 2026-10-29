"""Local subprocess queue. flock serializes GPU use; SQLite retains terminal state."""

import contextlib
import fcntl
import os
import sys
import traceback
from pathlib import Path

from simready.evaluation.runner import evaluate
from simready.evaluation.store import EvaluationStore
from simready.reconstruction.gsplat import GsplatBackend
from simready.scene.store import SceneStore, utc_now
from simready.storage import check_budget


def work(root: Path):
    store = EvaluationStore(SceneStore(root))
    with (root / "evaluation-worker.lock").open("w") as lock:
        # One launcher per submission; waiting launchers recheck the queue after acquiring.
        fcntl.flock(lock, fcntl.LOCK_EX)
        with store.scenes.connect() as db:
            # Holding the exclusive worker lock means no previous job can still be executing.
            db.execute(
                "UPDATE jobs SET status='failed', error='Worker interrupted; "
                "submit a new job', updated_at=? WHERE status='running'",
                (utc_now(),),
            )
        while True:
            with store.scenes.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute(
                    "SELECT * FROM jobs WHERE status='queued' ORDER BY created_at,job_id LIMIT 1"
                ).fetchone()
                if row is None:
                    return
                job = dict(row)
                db.execute(
                    "UPDATE jobs SET status='running', updated_at=?,worker_pid=? WHERE job_id=?",
                    (utc_now(), os.getpid(), job["job_id"]),
                )
            directory = root / "jobs" / job["job_id"]
            directory.mkdir(parents=True, exist_ok=True)
            with (directory / "job.log").open("a", buffering=1) as log:
                with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                    try:
                        check_budget(600_000_000)
                        references = store.references(job["scene_id"])
                        dataset, artifact = (
                            references["local_dataset_path"],
                            references["local_reconstruction_path"],
                        )
                        print(
                            "Rendering verified frozen cameras for base reconstruction", flush=True
                        )
                        GsplatBackend().render(
                            artifact, dataset, job["split"], directory / "renders"
                        )
                        print("Evaluating image/depth metrics and fixed detector", flush=True)
                        evaluate(dataset, artifact, directory / "renders", directory / "evaluation")
                        store.register(
                            job["scene_id"],
                            job["job_id"],
                            directory / "evaluation",
                            job["scene_version"],
                        )
                        status, error = "succeeded", None
                        print("Report registered", flush=True)
                    except Exception as exc:
                        traceback.print_exc()
                        status, error = "failed", str(exc)[-2000:]
                    with store.scenes.connect() as db:
                        db.execute(
                            "UPDATE jobs SET status=?,error=?,updated_at=? WHERE job_id=?",
                            (status, error, utc_now(), job["job_id"]),
                        )


if __name__ == "__main__":
    work(Path(sys.argv[1]).resolve())
