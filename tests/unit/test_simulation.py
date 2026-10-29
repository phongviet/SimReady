import json

import numpy as np
import pytest
from pydantic import ValidationError

from simready.scene.models import ProxyObject
from simready.simulation.grid import build_grid, clip_height, collides, point_cell
from simready.simulation.models import Scenario
from simready.simulation.planner import astar, plan_and_replay


def config(**kwargs):
    return Scenario(
        **(
            {
                "scenario_id": "route1",
                "name": "Controlled floor route",
                "bounds_xz_m": (0, 0, 2, 2),
                "floor_y_m": 0,
                "floor_note": "Known analytic plane for unit verification only",
                "resolution_m": 0.1,
                "start_xz_m": (0.55, 0.55),
                "goal_xz_m": (1.55, 1.55),
            }
            | kwargs
        )
    )


def floor():
    return np.array([[0.0, 0, 0], [2, 0, 0], [2, 0, 2], [0, 0, 2]]), np.array(
        [[0, 1, 2], [0, 2, 3]]
    )


def box(**kwargs):
    return ProxyObject(
        **(
            {
                "object_id": "box1",
                "name": "Box",
                "position": (0.55, 0.25, 1.05),
                "scale": (0.3, 0.5, 0.3),
            }
            | kwargs
        )
    )


def test_observed_floor_unknown_cells_and_footprint_inflation():
    scenario = config()
    vertices, triangles = floor()
    grid = build_grid(vertices, triangles, [], scenario)
    assert grid["floor_support"].all()
    assert not collides((0.55, 0.55), grid["blocked"], scenario)
    assert collides((0.05, 0.05), grid["blocked"], scenario)
    unknown = build_grid(vertices, np.empty((0, 3), dtype=int), [], scenario)
    assert unknown["blocked"].all() and not unknown["floor_support"].any()
    declared = build_grid(
        vertices, np.empty((0, 3), dtype=int), [], config(floor_mode="declared_virtual_plane")
    )
    assert declared[
        "floor_support"
    ].all()  # Explicit assumption, not inferred/observed floor truth.
    zero = np.array([[0.0, 0, 0], [0, 0, 0], [0, 0, 0]])
    assert not build_grid(zero, np.array([[0, 1, 2]]), [], scenario)["floor_support"].any()


def test_proxy_volume_hidden_collision_independence_and_rotated_footprint():
    vertices, triangles = floor()
    scenario = config()
    hidden = box(visible=False)
    a = build_grid(vertices, triangles, [hidden], scenario)
    x, z = point_cell(hidden.position[::2], scenario)
    assert a["surface_occupied"][z, x]  # Solid box interior, not just surface perimeter.
    b = build_grid(vertices, triangles, [box(visible=False, collidable=False)], scenario)
    assert not b["surface_occupied"].any()
    high = build_grid(vertices, triangles, [box(position=(1, 2, 1))], scenario)
    assert not high["surface_occupied"].any()
    rotated = box(
        position=(1, 0.25, 1),
        scale=(0.8, 0.5, 0.1),
        quaternion_xyzw=(0, np.sin(np.pi / 8), 0, np.cos(np.pi / 8)),
    )
    c = build_grid(vertices, triangles, [rotated], scenario)
    assert c["surface_occupied"].sum() > 6
    assert c["surface_occupied"][10, 10]


def test_metric_route_replay_determinism_and_obstacle_variant():
    scenario = config()
    vertices, triangles = floor()
    baseline_grid = build_grid(vertices, triangles, [], scenario)
    baseline = plan_and_replay(baseline_grid["blocked"], scenario)
    assert baseline["route_success"] and baseline["collisions"] == 0
    assert baseline["path_length_m"] == pytest.approx(2.0)
    assert baseline["travel_distance_m"] == pytest.approx(baseline["path_length_m"])
    assert baseline["elapsed_simulated_s"] == pytest.approx(2 / scenario.speed_m_s)
    assert baseline == plan_and_replay(baseline_grid["blocked"], scenario)
    assert baseline["trajectory"][-1]["position_xz_m"] == pytest.approx(scenario.goal_xz_m)
    obstacle_grid = build_grid(vertices, triangles, [box()], scenario)
    changed = plan_and_replay(obstacle_grid["blocked"], scenario)
    assert changed["route_success"] and changed["collisions"] == 0
    assert changed["path_xz_m"] != baseline["path_xz_m"]
    assert changed["travel_distance_m"] == pytest.approx(changed["path_length_m"])
    json.dumps(changed, allow_nan=False)


def test_blocked_and_unreachable_are_explicit_failures_and_stationary_is_zero():
    blocked = np.zeros((20, 20), dtype=bool)
    blocked[:, 10] = True
    result = plan_and_replay(blocked, config())
    assert not result["route_success"] and result["path_length_m"] is None
    assert result["trajectory"] == []
    blocked[5, 5] = True
    assert "blocked" in plan_and_replay(blocked, config())["reason"]
    zero = plan_and_replay(np.zeros((20, 20), dtype=bool), config(goal_xz_m=(0.55, 0.55)))
    assert zero["route_success"] and zero["path_length_m"] == zero["travel_distance_m"] == 0
    assert astar(blocked, (-1, 0), (3, 3)) is None


def test_swept_replay_detects_tunneling_injected_bad_plan(monkeypatch):
    blocked = np.zeros((20, 20), dtype=bool)
    blocked[:, 10] = True
    scenario = config(goal_xz_m=(1.55, 0.55), speed_m_s=2, timestep_s=1)
    monkeypatch.setattr("simready.simulation.planner.astar", lambda *args: [(5, 5), (15, 5)])
    result = plan_and_replay(blocked, scenario)
    assert not result["route_success"] and result["collisions"] == 1


def test_height_clipping_and_bounded_scenario_contract():
    polygon = clip_height(np.array([[0.0, -1, 0], [1, 1, 0], [0, 1, 1]]), 0, 0.5)
    assert len(polygon) >= 3 and polygon[:, 1].min() >= 0 and polygon[:, 1].max() <= 0.5
    for change in (
        {"resolution_m": 0.001},
        {"goal_xz_m": (5, 5)},
        {"floor_note": ""},
        {"unknown_policy": "free"},
        {"bounds_xz_m": (0, 0, 100, 100)},
        {"floor_y_m": float("nan")},
    ):
        with pytest.raises(ValidationError):
            config(**change)
