"""SQLite authoritative scene revisions and controlled filesystem asset packages."""

import json
import shutil
import sqlite3
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from pydantic import TypeAdapter

from simready.data.dataset import atomic_dataset, local_file, sha256_file, write_json
from simready.data.schema import Identifier
from simready.geometry.tsdf import validate_geometry
from simready.reconstruction.gsplat import load_records, validate_artifact, validate_renders
from simready.scene.models import ObjectUpdate
from simready.simulation.models import ScenarioUpdate
from simready.storage import check_budget


class VersionConflict(ValueError):
    def __init__(self, actual: int):
        self.actual = actual
        super().__init__(f"scene changed; current version is {actual}. Reload before saving.")


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class SceneStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.database = self.root / "studio.sqlite3"
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS scenes (
                    scene_id TEXT PRIMARY KEY, current_version INTEGER NOT NULL,
                    base_json TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS revisions (
                    scene_id TEXT NOT NULL, version INTEGER NOT NULL,
                    state_json TEXT NOT NULL, PRIMARY KEY(scene_id, version),
                    FOREIGN KEY(scene_id) REFERENCES scenes(scene_id));
            """)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def package(self, scene_id: str) -> Path:
        TypeAdapter(Identifier).validate_python(scene_id)
        path = self.root / "packages" / scene_id
        if not path.resolve().is_relative_to(self.root):
            raise ValueError("scene package escapes registry")
        return path

    def list_scenes(self) -> list[dict]:
        with self.connect() as db:
            ids = [row[0] for row in db.execute("SELECT scene_id FROM scenes ORDER BY scene_id")]
        return [self.get(scene_id) for scene_id in ids]

    def get(self, scene_id: str, version: int | None = None) -> dict:
        self.package(scene_id)
        with self.connect() as db:
            row = db.execute("SELECT * FROM scenes WHERE scene_id=?", (scene_id,)).fetchone()
            if row is None:
                raise KeyError(f"unknown scene: {scene_id}")
            selected = version if version is not None else row["current_version"]
            revision = db.execute(
                "SELECT state_json FROM revisions WHERE scene_id=? AND version=?",
                (scene_id, selected),
            ).fetchone()
            if revision is None:
                raise KeyError(f"unknown scene revision: {selected}")
            state = json.loads(revision[0])
            base = json.loads(row["base_json"])
        state["base"] = {key: value for key, value in base.items() if not key.startswith("local_")}
        return state

    def history(self, scene_id: str) -> list[dict]:
        self.get(scene_id)
        with self.connect() as db:
            rows = db.execute(
                "SELECT state_json FROM revisions WHERE scene_id=? ORDER BY version", (scene_id,)
            ).fetchall()
        return [
            {
                "version": json.loads(row[0])["version"],
                "updated_at": json.loads(row[0])["updated_at"],
            }
            for row in rows
        ]

    def _snapshot(self, scene_id: str, state: dict) -> None:
        """Atomic portable snapshot; SQLite revisions remain authoritative on recovery."""
        package = self.package(scene_id)
        package.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", dir=package, suffix=".tmp", delete=False) as out:
            path = Path(out.name)
            json.dump(state, out, indent=2, allow_nan=False)
        try:
            path.replace(package / "scene.json")
        finally:
            path.unlink(missing_ok=True)

    def update_objects(self, scene_id: str, change: ObjectUpdate) -> dict:
        return self.update_content(
            scene_id,
            change.expected_version,
            {"objects": [o.model_dump(mode="json") for o in change.objects]},
        )

    def update_scenarios(self, scene_id: str, change: ScenarioUpdate) -> dict:
        return self.update_content(
            scene_id,
            change.expected_version,
            {"scenarios": [s.model_dump(mode="json") for s in change.scenarios]},
        )

    def commit_revision(self, db: sqlite3.Connection, scene_id: str, state: dict) -> None:
        """Caller holds BEGIN IMMEDIATE; immutable revision plus current pointer/snapshot."""
        db.execute(
            "INSERT INTO revisions VALUES(?,?,?)", (scene_id, state["version"], json.dumps(state))
        )
        db.execute(
            "UPDATE scenes SET current_version=? WHERE scene_id=?", (state["version"], scene_id)
        )
        self._snapshot(scene_id, state)

    def update_content(self, scene_id: str, expected_version: int, changes: dict) -> dict:
        check_budget(500_000)
        self.package(scene_id)
        if not set(changes).issubset({"objects", "scenarios"}):
            raise ValueError("content changes accept only objects and scenarios")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT current_version FROM scenes WHERE scene_id=?", (scene_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown scene: {scene_id}")
            actual = row[0]
            if expected_version != actual:
                raise VersionConflict(actual)
            old = db.execute(
                "SELECT state_json FROM revisions WHERE scene_id=? AND version=?",
                (scene_id, actual),
            ).fetchone()
            state = json.loads(old[0])
            state.update(changes)
            state.update(version=actual + 1, status="draft", updated_at=utc_now())
            state.pop("review", None)
            self.commit_revision(db, scene_id, state)
        return self.get(scene_id)

    def asset(self, scene_id: str, asset_id: str) -> Path:
        state = self.get(scene_id)
        asset = state["base"]["assets"].get(asset_id)
        if asset is None:
            raise KeyError("unknown registered scene asset")
        path = local_file(self.package(scene_id), asset["path"])
        if sha256_file(path) != asset["sha256"]:
            raise ValueError("registered asset was modified; content hash mismatch")
        return path

    def register(
        self,
        scene_id: str,
        name: str,
        reconstruction: Path,
        geometry: Path,
        renders: Path,
        dataset: Path | None = None,
    ) -> dict:
        self.package(scene_id)
        if not name.strip() or len(name) > 100:
            raise ValueError("scene name must have 1..100 characters")
        model = validate_artifact(reconstruction)
        mesh = validate_geometry(geometry)
        views = validate_renders(renders)
        provenance = model["provenance"]
        if (
            mesh["frames_sha256"] != provenance["frames_sha256"]
            or mesh["split_sha256"] != provenance["split_sha256"]
            or mesh["dataset_manifest_sha256"] != provenance["dataset_manifest_sha256"]
            or views["artifact_sha256"] != sha256_file(reconstruction / "artifact.json")
        ):
            raise ValueError("geometry/render provenance does not match the reconstruction dataset")
        if mesh["training_frame_ids"] != provenance["training_frame_ids"]:
            raise ValueError(
                "collision geometry must use exactly the frozen reconstruction training frames"
            )
        if dataset is not None:
            manifest, _, _ = load_records(dataset)
            if sha256_file(dataset / "manifest.json") != provenance["dataset_manifest_sha256"]:
                raise ValueError("dataset differs from reconstruction provenance")
        else:
            manifest = None
        package = self.package(scene_id)
        now = utc_now()
        state = {
            "schema_version": "1.0",
            "scene_id": scene_id,
            "name": name,
            "version": 1,
            "world_units": "meters",
            "world_frame": "canonical_right_handed_y_up",
            "status": "draft",
            "objects": [],
            "scenarios": [],
            "created_at": now,
            "updated_at": now,
        }
        with atomic_dataset(package, 100_000_000) as stage:
            assets = {}
            for src_root, files, prefix in (
                (
                    reconstruction,
                    (
                        "gaussian.ply",
                        "gaussians.npz",
                        "artifact.json",
                        "train-job.json",
                        "training-log.jsonl",
                    ),
                    "reconstruction",
                ),
                (
                    geometry,
                    (
                        "collision_mesh.json",
                        "collision_mesh.npz",
                        "collision_mesh.ply",
                        "geometry.json",
                    ),
                    "geometry",
                ),
                (renders, tuple(views["files_sha256"]), "views"),
            ):
                (stage / prefix).mkdir()
                for filename in files:
                    source = local_file(src_root, filename)
                    target = stage / prefix / filename
                    shutil.copyfile(source, target)
                    target.chmod(0o444)
                    assets[filename] = {
                        "path": f"{prefix}/{filename}",
                        "sha256": sha256_file(target),
                    }
            centers = np.array(
                [np.linalg.inv(np.array(c["viewmat"]))[:3, 3] for c in views["cameras"]]
            )
            base = {
                "dataset_kind": provenance["dataset_kind"],
                "assets": assets,
                "cameras": views["cameras"],
                "source": provenance["source"],
                "geometry_quality": "coarse_proxy",
                "frames_sha256": provenance["frames_sha256"],
                "split_sha256": provenance["split_sha256"],
                "bounds_min_m": mesh["bounds_min_m"],
                "bounds_max_m": mesh["bounds_max_m"],
                "camera_center_m": centers.mean(axis=0).tolist(),
                "preview_mode": "browser_overlay_only; not scientific evaluation rendering",
                "limitations": list(provenance["limitations"]) + mesh["limitations"],
                "local_dataset_path": str(dataset.resolve()) if dataset else None,
                "local_reconstruction_path": str(reconstruction.resolve()),
                "local_geometry_path": str(geometry.resolve()),
                "dataset_manifest": manifest.model_dump(mode="json") if manifest else None,
            }
            write_json(stage / "base.json", base)
            write_json(stage / "scene.json", state)
        try:
            with self.connect() as db:
                db.execute("INSERT INTO scenes VALUES(?,?,?)", (scene_id, 1, json.dumps(base)))
                db.execute("INSERT INTO revisions VALUES(?,?,?)", (scene_id, 1, json.dumps(state)))
        except sqlite3.IntegrityError as exc:
            raise ValueError("scene ID already registered") from exc
        return self.get(scene_id)
