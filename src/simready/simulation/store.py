"""Content-addressed simulator runs tied to immutable scene and scenario inputs."""

import importlib.metadata
import json
import platform
import subprocess
import time
import uuid
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from pydantic import TypeAdapter

from simready.data.dataset import atomic_dataset, local_file, sha256_file, write_json
from simready.data.schema import Identifier
from simready.scene.models import ProxyObject
from simready.scene.store import SceneStore, VersionConflict, utc_now
from simready.simulation.grid import build_grid
from simready.simulation.models import Scenario
from simready.simulation.planner import plan_and_replay
from simready.storage import PROJECT_ROOT


class SimulationStore:
    def __init__(self, scenes: SceneStore):
        self.scenes = scenes
        with scenes.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS simulations (
                scene_id TEXT NOT NULL, run_id TEXT NOT NULL, scene_version INTEGER NOT NULL,
                metadata_json TEXT NOT NULL, PRIMARY KEY(scene_id,run_id))""")

    def run_root(self, scene_id: str, run_id: str) -> Path:
        TypeAdapter(Identifier).validate_python(run_id)
        return self.scenes.package(scene_id) / "simulations" / run_id

    def runs(self, scene_id: str) -> list[dict]:
        self.scenes.get(scene_id)
        with self.scenes.connect() as db:
            rows = db.execute(
                "SELECT metadata_json FROM simulations WHERE scene_id=?", (scene_id,)
            ).fetchall()
        return sorted(
            [json.loads(row[0]) for row in rows], key=lambda r: (r["created_at"], r["run_id"])
        )

    def get(self, scene_id: str, run_id: str) -> dict:
        self.run_root(scene_id, run_id)
        self.scenes.get(scene_id)
        with self.scenes.connect() as db:
            row = db.execute(
                "SELECT metadata_json FROM simulations WHERE scene_id=? AND run_id=?",
                (scene_id, run_id),
            ).fetchone()
        if row is None:
            raise KeyError("unknown simulation run")
        registration = json.loads(row[0])
        root = self.run_root(scene_id, run_id)
        if sha256_file(local_file(root, "simulation.json")) != registration["simulation_sha256"]:
            raise ValueError("simulation manifest content changed")
        return registration

    def asset(self, scene_id: str, run_id: str, name: str) -> Path:
        self.get(scene_id, run_id)
        root = self.run_root(scene_id, run_id)
        metadata = json.loads((root / "simulation.json").read_text())
        if name == "simulation.json":
            return root / name
        expected = metadata["files_sha256"].get(name)
        if expected is None:
            raise KeyError("unknown simulation asset")
        path = local_file(root, name)
        if sha256_file(path) != expected:
            raise ValueError("simulation asset content hash mismatch")
        return path

    def run(self, scene_id: str, scenario_id: str, expected_version: int) -> dict:
        state = self.scenes.get(scene_id)
        if state["version"] != expected_version:
            raise VersionConflict(state["version"])
        scenario = next(
            (s for s in state.get("scenarios", []) if s["scenario_id"] == scenario_id), None
        )
        if scenario is None:
            raise KeyError("unknown saved scenario")
        config = Scenario.model_validate(scenario)
        objects = [ProxyObject.model_validate(o) for o in state["objects"]]
        # Registered hash-checked arrays preserve the scene package's metric frame.
        mesh_path = self.scenes.asset(scene_id, "collision_mesh.npz")
        started = time.perf_counter()
        with np.load(mesh_path, allow_pickle=False) as arrays:
            grid = build_grid(arrays["vertices"], arrays["triangles"], objects, config)
        result = plan_and_replay(grid["blocked"], config)
        runtime = time.perf_counter() - started
        run_id = uuid.uuid4().hex
        root = self.run_root(scene_id, run_id)
        with atomic_dataset(root, 100_000_000) as stage:
            np.savez_compressed(stage / "occupancy.npz", **grid)
            map_json = {
                "resolution_m": config.resolution_m,
                "bounds_xz_m": config.bounds_xz_m,
                "floor_y_m": config.floor_y_m,
                "width": grid["blocked"].shape[1],
                "height": grid["blocked"].shape[0],
                **{key: value.astype(np.uint8).tolist() for key, value in grid.items()},
            }
            write_json(stage / "occupancy.json", map_json)
            write_json(stage / "scenario.json", scenario)
            write_json(stage / "scene-input.json", state)
            write_json(stage / "result.json", result)
            rgb = np.full((*grid["blocked"].shape, 3), [30, 40, 34], dtype=np.uint8)
            rgb[grid["floor_support"]] = [76, 110, 78]
            rgb[grid["surface_occupied"]] = [216, 132, 78]
            rgb[grid["blocked"] & grid["floor_support"] & ~grid["surface_occupied"]] = [
                100,
                90,
                78,
            ]
            image = Image.fromarray(rgb).resize(
                (rgb.shape[1] * 4, rgb.shape[0] * 4), Image.Resampling.NEAREST
            )
            draw = ImageDraw.Draw(image)
            origin = np.array(config.bounds_xz_m[:2])
            route = [
                tuple(((np.asarray(p) - origin) / config.resolution_m * 4).tolist())
                for p in result["path_xz_m"]
            ]
            if len(route) > 1:
                draw.line(route, fill="#d9ed96", width=3)
            for point, color in ((config.start_xz_m, "#99eeff"), (config.goal_xz_m, "#ffccdd")):
                x, z = (np.asarray(point) - origin) / config.resolution_m * 4
                draw.ellipse((x - 3, z - 3, x + 3, z + 3), fill=color)
            image.save(stage / "route.png")
            metadata = {
                "schema_version": "1.0",
                "git_commit": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True
                ).strip(),
                "git_dirty": bool(
                    subprocess.check_output(
                        ["git", "status", "--porcelain"], cwd=PROJECT_ROOT, text=True
                    )
                ),
                "source_files_sha256": {
                    p.relative_to(PROJECT_ROOT).as_posix(): sha256_file(p)
                    for p in sorted(
                        [
                            *(PROJECT_ROOT / "src/simready/simulation").glob("*.py"),
                            PROJECT_ROOT / "src/simready/scene/models.py",
                        ]
                    )
                },
                "type": "occupancy_navigation",
                "world_units": state["world_units"],
                "world_frame": state["world_frame"],
                "planner": "deterministic four-neighbor A*; same-map swept occupancy replay",
                "environment": {
                    "python": platform.python_version(),
                    **{
                        name: importlib.metadata.version(name)
                        for name in ("numpy", "scipy", "pillow")
                    },
                },
                "run_id": run_id,
                "scene_id": scene_id,
                "scene_version": state["version"],
                "created_at": utc_now(),
                "scenario": scenario,
                "result_summary": {
                    key: value
                    for key, value in result.items()
                    if key not in ("trajectory", "path_xz_m")
                },
                "wall_seconds": runtime,
                "geometry_sha256": sha256_file(mesh_path),
                "floor_evidence": (
                    "observed_surface_support"
                    if config.floor_mode == "observed_tsdf"
                    else "declared_virtual_floor_assumption"
                ),
                "floor_support_cells": int(grid["floor_support"].sum()),
                "unknown_cells": int((~grid["floor_support"]).sum()),
                "free_robot_center_cells": int((~grid["blocked"]).sum()),
                "scope": (
                    "Deterministic simplified occupancy navigation only; "
                    "no real robot or perception validation."
                ),
                "limitations": [
                    "Metric frame is inherited from supplied poses and "
                    "coarse TSDF; floor height is an explicit "
                    "assumption.",
                    "Observed TSDF floor or declared virtual floor is "
                    "selected explicitly; unknown cells and exterior "
                    "are blocked.",
                    "Surfaces are projected through robot-height slab; "
                    "mesh holes and solid occupancy truth remain "
                    "unverified.",
                    "Robot is a circle; radius plus conservative cell "
                    "inflation. Replay has fixed clock samples and "
                    "exact corner events.",
                    "All collidable proxies participate even when "
                    "hidden; visual overlay realism is not evaluated.",
                    "Planning uses the same declared map as replay. "
                    "Route success is not an independent real-world "
                    "benchmark.",
                ],
                "files_sha256": {p.name: sha256_file(p) for p in stage.iterdir() if p.is_file()},
            }
            write_json(stage / "simulation.json", metadata)
        registration = {key: value for key, value in metadata.items() if key != "files_sha256"}
        registration["simulation_sha256"] = sha256_file(root / "simulation.json")
        with self.scenes.connect() as db:
            db.execute(
                "INSERT INTO simulations VALUES(?,?,?,?)",
                (scene_id, run_id, state["version"], json.dumps(registration)),
            )
        return registration
