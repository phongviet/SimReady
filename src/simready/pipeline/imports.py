"""Authenticated API ingress uses controlled inbox keys, never client filesystem paths."""

import hashlib
import json
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, TypeAdapter, model_validator

from simready.data.dataset import sha256_file
from simready.data.schema import Contract, Identifier
from simready.scene.store import SceneStore, utc_now


class ImportRequest(Contract):
    scene_id: Identifier
    format: Literal["synthetic", "tum_rgbd", "open3d_redwood_sample"]
    source_key: Identifier | None = None
    max_frames: int = Field(default=100, ge=8, le=256, strict=True)

    @model_validator(mode="after")
    def source(self) -> Self:
        if (self.format == "synthetic") != (self.source_key is None):
            raise ValueError("synthetic needs no source; other formats require an inbox key")
        return self


def fingerprint(path: Path) -> str:
    if path.is_symlink():
        raise ValueError("inbox symlinks are forbidden")
    files = (
        [path]
        if path.is_file()
        else sorted(p for p in path.rglob("*") if p.is_file() or p.is_symlink())
    )
    if not files or len(files) > 2000:
        raise ValueError("inbox source must contain1–2000files")
    if any(p.is_symlink() for p in path.rglob("*")) if path.is_dir() else False:
        raise ValueError("inbox symlinks are forbidden")
    if sum(p.stat().st_size for p in files) > 500_000_000:
        raise ValueError("inbox source exceeds500MB")
    digest = hashlib.sha256()
    for file in files:
        if file.is_symlink():
            raise ValueError("inbox symlinks are forbidden")
        name = file.name if path.is_file() else file.relative_to(path).as_posix()
        digest.update(json.dumps([name, sha256_file(file)]).encode())
    return digest.hexdigest()


class ImportStore:
    def __init__(self, scenes: SceneStore):
        self.scenes = scenes
        self.root = scenes.root
        (self.root / "inbox").mkdir(exist_ok=True)
        with scenes.connect() as db:
            db.executescript("""CREATE TABLE IF NOT EXISTS import_jobs(
                job_id TEXT PRIMARY KEY,scene_id TEXT UNIQUE NOT NULL,request_json TEXT NOT NULL,
                source_sha256 TEXT,status TEXT NOT NULL,created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,error TEXT,result_json TEXT);
            """)

    def source_path(self, key):
        TypeAdapter(Identifier).validate_python(key)
        inbox = (self.root / "inbox").resolve()
        path = inbox / key
        if not path.resolve().is_relative_to(inbox) or path.is_symlink():
            raise ValueError("inbox source escapes controlled root")
        if not path.exists():
            raise ValueError("inbox source key is missing")
        return path

    def enqueue(self, request: ImportRequest):
        source_hash = (
            None
            if request.source_key is None
            else fingerprint(self.source_path(request.source_key))
        )
        job_id = uuid.uuid4().hex
        now = utc_now()
        with self.scenes.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if (
                db.execute(
                    "SELECT 1 FROM scenes WHERE scene_id=?",
                    (request.scene_id,),
                ).fetchone()
                or db.execute(
                    "SELECT job_id FROM import_jobs WHERE scene_id=?", (request.scene_id,)
                ).fetchone()
            ):
                raise ValueError("scene ID already exists; use a new ID")
            db.execute(
                "INSERT INTO import_jobs VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    job_id,
                    request.scene_id,
                    request.model_dump_json(),
                    source_hash,
                    "queued",
                    now,
                    now,
                    None,
                    None,
                ),
            )
        directory = self.root / "import-jobs" / job_id
        directory.mkdir(parents=True)
        try:
            with (directory / "launcher.log").open("w") as log:
                subprocess.Popen(
                    [sys.executable, "-m", "simready.pipeline.imports", str(self.root)],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
        except OSError as exc:
            with self.scenes.connect() as db:
                db.execute(
                    "UPDATE import_jobs SET status='failed',error=?,updated_at=? WHERE job_id=?",
                    (str(exc), utc_now(), job_id),
                )
        return self.job(job_id)

    def job(self, job_id):
        TypeAdapter(Identifier).validate_python(job_id)
        with self.scenes.connect() as db:
            row = db.execute("SELECT * FROM import_jobs WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            raise KeyError("unknown import job")
        result = dict(row)
        result.pop("request_json")
        payload = result.pop("result_json")
        result["result"] = json.loads(payload) if payload else None
        log = self.root / "import-jobs" / job_id / "job.log"
        result["log_tail"] = log.read_text()[-8000:] if log.exists() else ""
        result["kind"] = "import"
        return result


def work(root):
    import contextlib
    import fcntl
    import traceback

    from simready.data.dataset import validate_scene
    from simready.data.redwood import import_redwood
    from simready.data.synthetic import make_synthetic
    from simready.data.tum import import_tum

    store = ImportStore(SceneStore(root))
    with (root / "import-worker.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with store.scenes.connect() as db:
            db.execute(
                "UPDATE import_jobs SET status='failed',error='Import worker interrupted; "
                "use a new scene ID',updated_at=? WHERE status='running'",
                (utc_now(),),
            )
        while True:
            with store.scenes.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute(
                    "SELECT * FROM import_jobs WHERE status='queued' "
                    "ORDER BY created_at,job_id LIMIT 1"
                ).fetchone()
                if row is None:
                    return
                job = dict(row)
                db.execute(
                    "UPDATE import_jobs SET status='running',updated_at=? WHERE job_id=?",
                    (utc_now(), job["job_id"]),
                )
            directory = root / "import-jobs" / job["job_id"]
            directory.mkdir(parents=True, exist_ok=True)
            with (
                (directory / "job.log").open("a") as log,
                contextlib.redirect_stdout(log),
                contextlib.redirect_stderr(log),
            ):
                result = None
                error = None
                status = "failed"
                try:
                    request = ImportRequest.model_validate_json(job["request_json"])
                    output = directory / "dataset"
                    source = (
                        None
                        if request.source_key is None
                        else store.source_path(request.source_key)
                    )
                    if source is not None and fingerprint(source) != job["source_sha256"]:
                        raise ValueError("inbox source changed after enqueue")
                    if request.format == "synthetic":
                        make_synthetic(output)
                    elif request.format == "tum_rgbd":
                        import_tum(source, output, request.max_frames)
                    else:
                        import_redwood(source, output)
                    if source is not None and fingerprint(source) != job["source_sha256"]:
                        raise ValueError("inbox source changed during import")
                    result = validate_scene(output)
                    status = "succeeded"
                    print("Imported and validated canonical dataset", flush=True)
                except Exception as exc:
                    error = str(exc)[-2000:]
                    traceback.print_exc()
                with store.scenes.connect() as db:
                    db.execute(
                        "UPDATE import_jobs SET status=?,error=?,result_json=?,updated_at=? "
                        "WHERE job_id=?",
                        (
                            status,
                            error,
                            json.dumps(result) if result else None,
                            utc_now(),
                            job["job_id"],
                        ),
                    )


if __name__ == "__main__":
    work(Path(sys.argv[1]).resolve())
