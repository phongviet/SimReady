"""Prepare a fresh real-TUM walkthrough registry without altering source evidence."""

import argparse
import json
from pathlib import Path

from simready.api.app import create_app
from simready.data.dataset import sha256_file, write_json
from simready.simulation.models import Scenario, ScenarioUpdate
from simready.storage import PROJECT_ROOT, check_budget


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    if args.root.exists():
        raise ValueError("walkthrough needs a new registry; preserve earlier reviews")
    check_budget(150_000_000)
    app = create_app(args.root)
    app.state.auth.bootstrap()
    state = app.state.store.register(
        "tum-walkthrough",
        "TUM fr1 desk · recorded real scene",
        PROJECT_ROOT / "artifacts/scenes/tum-fr1-desk/baseline-1",
        PROJECT_ROOT / "artifacts/geometry/tum-fr1-desk/tsdf-1",
        PROJECT_ROOT / "artifacts/renders/tum-fr1-desk-test-1",
        PROJECT_ROOT / "data/scenes/tum-fr1-desk",
    )
    app.state.evaluations.register(
        "tum-walkthrough",
        "baseline-test-1",
        PROJECT_ROOT / "artifacts/evaluations/tum-fr1-desk-test-1",
    )
    scenario_path = PROJECT_ROOT / "configs/scenario_tum_floor.json"
    state = app.state.store.update_scenarios(
        "tum-walkthrough",
        ScenarioUpdate(
            expected_version=state["version"],
            scenarios=[Scenario.model_validate_json(scenario_path.read_text())],
        ),
    )
    write_json(
        args.root / "walkthrough-inputs.json",
        {
            "scene_id": state["scene_id"],
            "scenario_sha256": sha256_file(scenario_path),
            "source_artifact_sha256": state["base"]["assets"]["artifact.json"]["sha256"],
            "scope": (
                "Saved genuine TUM reconstruction and measured report; no live retraining; "
                "automated distinct local roles, no human endorsement."
            ),
        },
    )
    print(json.dumps({"root": str(args.root), "scene_id": state["scene_id"]}))
    check_budget()


if __name__ == "__main__":
    main()
