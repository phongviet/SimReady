"""Run declared real-TUM coarse-map layouts; never overwrite an existing registry."""

import argparse
import json
from pathlib import Path

from simready.data.dataset import sha256_file, write_json
from simready.scene.models import ObjectUpdate
from simready.scene.store import SceneStore
from simready.simulation.models import Scenario, ScenarioUpdate
from simready.simulation.store import SimulationStore
from simready.storage import PROJECT_ROOT, check_budget


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="new output registry directory")
    args = parser.parse_args()
    if args.root.exists():
        raise ValueError("navigation acceptance root already exists; choose a new directory")
    check_budget(100_000_000)
    layout_path = PROJECT_ROOT / "configs/navigation_layouts.json"
    scenario_path = PROJECT_ROOT / "configs/scenario_tum_floor.json"
    layouts = json.loads(layout_path.read_text())
    scenario = Scenario.model_validate_json(scenario_path.read_text())
    store = SceneStore(args.root)
    scene_id = layouts["scene_id"]
    state = store.register(
        scene_id,
        "TUM floor navigation",
        PROJECT_ROOT / "artifacts/scenes/tum-fr1-desk/baseline-1",
        PROJECT_ROOT / "artifacts/geometry/tum-fr1-desk/tsdf-1",
        PROJECT_ROOT / "artifacts/renders/tum-fr1-desk-test-1",
        PROJECT_ROOT / "data/scenes/tum-fr1-desk",
    )
    state = store.update_scenarios(
        scene_id, ScenarioUpdate(expected_version=state["version"], scenarios=[scenario])
    )
    simulations, rows = SimulationStore(store), []
    for layout in layouts["layouts"]:
        state = store.update_objects(
            scene_id, ObjectUpdate(expected_version=state["version"], objects=layout["objects"])
        )
        run = simulations.run(scene_id, scenario.scenario_id, state["version"])
        result = json.loads(simulations.asset(scene_id, run["run_id"], "result.json").read_text())
        rows.append(
            {
                "layout": layout["name"],
                "run_id": run["run_id"],
                "scene_version": state["version"],
                "simulation_sha256": run["simulation_sha256"],
                "result": run["result_summary"],
                "wall_seconds": run["wall_seconds"],
                "path_xz_m": result["path_xz_m"],
                "floor_evidence": run["floor_evidence"],
                "floor_support_cells": run["floor_support_cells"],
                "unknown_cells": run["unknown_cells"],
                "free_robot_center_cells": run["free_robot_center_cells"],
            }
        )
        print(layout["name"], json.dumps(run["result_summary"]), flush=True)
    acceptance = {
        "schema_version": "1.0",
        "scene_id": scene_id,
        "scope": layouts["scope"],
        "layout_config_sha256": sha256_file(layout_path),
        "scenario_config_sha256": sha256_file(scenario_path),
        "script_sha256": sha256_file(Path(__file__).resolve()),
        "results": rows,
        "checks": {
            "baseline_reaches_goal": rows[0]["result"]["route_success"],
            "inserted_box_changes_route_or_blocks": rows[1]["path_xz_m"] != rows[0]["path_xz_m"],
            "barrier_prevents_route": not rows[2]["result"]["route_success"],
            "zero_replay_collisions": all(row["result"]["collisions"] == 0 for row in rows),
            "unknown_floor_preserved": all(row["unknown_cells"] > 0 for row in rows),
        },
    }
    write_json(args.root / "acceptance.json", acceptance)
    if not all(acceptance["checks"].values()):
        raise ValueError("one or more layout checks failed; inspect saved actual outputs")
    check_budget()


if __name__ == "__main__":
    main()
