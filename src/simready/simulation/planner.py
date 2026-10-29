"""Deterministic four-neighbor A* and independently checked fixed-step replay."""

import heapq
import math

import numpy as np

from simready.simulation.grid import collides, point_cell
from simready.simulation.models import Scenario


def astar(blocked: np.ndarray, start: tuple[int, int], goal: tuple[int, int]):
    if any(not (0 <= x < blocked.shape[1] and 0 <= z < blocked.shape[0]) for x, z in (start, goal)):
        return None
    if blocked[start[1], start[0]] or blocked[goal[1], goal[0]]:
        return None
    queue = [(abs(start[0] - goal[0]) + abs(start[1] - goal[1]), 0, start)]
    costs, parent = {start: 0}, {}
    while queue:
        _, cost, current = heapq.heappop(queue)
        if cost != costs[current]:
            continue
        if current == goal:
            route = [current]
            while current in parent:
                current = parent[current]
                route.append(current)
            return route[::-1]
        for dx, dz in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            candidate = (current[0] + dx, current[1] + dz)
            x, z = candidate
            if not (0 <= x < blocked.shape[1] and 0 <= z < blocked.shape[0]) or blocked[z, x]:
                continue
            next_cost = cost + 1
            if next_cost < costs.get(candidate, math.inf):
                costs[candidate], parent[candidate] = next_cost, current
                heuristic = abs(x - goal[0]) + abs(z - goal[1])
                heapq.heappush(queue, (next_cost + heuristic, next_cost, candidate))
    return None


def plan_and_replay(blocked: np.ndarray, scenario: Scenario) -> dict:
    targets = [scenario.start_xz_m, *scenario.waypoints_xz_m, scenario.goal_xz_m]
    for point in targets:
        if collides(point, blocked, scenario):
            return {
                "route_success": False,
                "reason": "start/waypoint/goal blocked or unknown",
                "path_xz_m": [],
                "trajectory": [],
                "path_length_m": None,
                "travel_distance_m": 0.0,
                "collisions": 0,
                "elapsed_simulated_s": 0.0,
            }
    if all(np.linalg.norm(np.asarray(point) - targets[0]) < 1e-10 for point in targets):
        return {
            "route_success": True,
            "reason": "already at goal",
            "path_xz_m": [list(targets[0])],
            "trajectory": [{"time_s": 0.0, "position_xz_m": list(targets[0])}],
            "path_length_m": 0.0,
            "travel_distance_m": 0.0,
            "collisions": 0,
            "elapsed_simulated_s": 0.0,
        }
    points = []
    origin = np.array(scenario.bounds_xz_m[:2])
    for start, goal in zip(targets[:-1], targets[1:], strict=True):
        cells = astar(blocked, point_cell(start, scenario), point_cell(goal, scenario))
        if cells is None:
            return {
                "route_success": False,
                "reason": "no route through supported unblocked cells",
                "path_xz_m": [],
                "trajectory": [],
                "path_length_m": None,
                "travel_distance_m": 0.0,
                "collisions": 0,
                "elapsed_simulated_s": 0.0,
            }
        segment = [
            np.asarray(start),
            *[origin + (np.asarray(c) + 0.5) * scenario.resolution_m for c in cells],
            np.asarray(goal),
        ]
        if points:
            segment = segment[1:]
        points.extend(segment)
    path = [points[0]]
    for point in points[1:]:
        if np.linalg.norm(point - path[-1]) > 1e-10:
            path.append(point)
    lengths = np.linalg.norm(np.diff(np.asarray(path), axis=0), axis=1)
    cumulative = np.r_[0, np.cumsum(lengths)]
    total = float(cumulative[-1])
    duration = total / scenario.speed_m_s
    steps = math.ceil(duration / scenario.timestep_s)
    if steps > 100000:
        raise ValueError("replay exceeds bounded 100000 time steps")
    trajectory, collisions, traveled = [], 0, 0.0
    previous = path[0]
    replay_times = sorted(
        set(
            [min(index * scenario.timestep_s, duration) for index in range(steps + 1)]
            + (cumulative / scenario.speed_m_s).tolist()
        )
    )
    if len(replay_times) > 100000:
        raise ValueError("replay including corner events exceeds bounded 100000 samples")
    # Exact corner events keep replay on the planned polyline instead of cutting across corners.
    for elapsed in replay_times:
        distance = min(elapsed * scenario.speed_m_s, total)
        segment = min(int(np.searchsorted(cumulative, distance, side="right")) - 1, len(path) - 2)
        if total <= 1e-10:
            point = path[0]
        else:
            fraction = (distance - cumulative[segment]) / lengths[segment]
            point = path[segment] + fraction * (path[segment + 1] - path[segment])
        # Swept checks prevent tunneling even when timestep*speed exceeds one grid cell.
        checks = max(1, math.ceil(np.linalg.norm(point - previous) / (scenario.resolution_m / 4)))
        if any(
            collides(previous + (point - previous) * k / checks, blocked, scenario)
            for k in range(1, checks + 1)
        ):
            collisions += 1
            break
        traveled += float(np.linalg.norm(point - previous))
        trajectory.append({"time_s": elapsed, "position_xz_m": point.tolist()})
        previous = point
    success = collisions == 0 and np.linalg.norm(previous - path[-1]) < 1e-8
    return {
        "route_success": bool(success),
        "reason": "goal reached" if success else "collision during swept replay",
        "path_xz_m": [p.tolist() for p in path],
        "trajectory": trajectory,
        "path_length_m": total,
        "travel_distance_m": traveled,
        "collisions": collisions,
        "elapsed_simulated_s": trajectory[-1]["time_s"] if trajectory else 0.0,
    }
