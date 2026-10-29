"""Bounded scenario contracts with explicit floor assumptions."""

import math
from typing import Literal, Self

from pydantic import Field, model_validator

from simready.data.schema import Contract, Identifier


class Scenario(Contract):
    scenario_id: Identifier
    name: str = Field(min_length=1, max_length=100)
    bounds_xz_m: tuple[float, float, float, float]
    floor_y_m: float
    floor_mode: Literal["observed_tsdf", "declared_virtual_plane"] = "observed_tsdf"
    floor_note: str = Field(min_length=1, max_length=1000)
    floor_tolerance_m: float = Field(default=0.1, ge=0.01, le=0.25)
    ground_clearance_m: float = Field(default=0.12, ge=0.01, le=0.3)
    robot_radius_m: float = Field(default=0.08, ge=0.03, le=2)
    robot_height_m: float = Field(default=0.5, ge=0.15, le=2.5)
    resolution_m: float = Field(default=0.05, ge=0.01, le=0.25)
    start_xz_m: tuple[float, float]
    goal_xz_m: tuple[float, float]
    waypoints_xz_m: tuple[tuple[float, float], ...] = Field(default=(), max_length=16)
    speed_m_s: float = Field(default=0.15, ge=0.01, le=2)
    timestep_s: float = Field(default=0.1, ge=0.02, le=1)
    seed: int = Field(default=42, ge=0, le=2**31 - 1)
    unknown_policy: Literal["blocked"] = "blocked"

    @model_validator(mode="after")
    def bounded_grid(self) -> Self:
        xmin, zmin, xmax, zmax = self.bounds_xz_m
        if not xmin < xmax or not zmin < zmax:
            raise ValueError("map bounds must have positive X/Z extent")
        cells = [
            math.ceil((xmax - xmin) / self.resolution_m),
            math.ceil((zmax - zmin) / self.resolution_m),
        ]
        if max(cells) > 256 or cells[0] * cells[1] > 65536:
            raise ValueError("local simulator grid is bounded to 256x256 cells")
        if max(abs(value) for value in (*self.bounds_xz_m, self.floor_y_m)) > 10000:
            raise ValueError("scenario coordinates exceed metric bounds")
        if self.ground_clearance_m >= self.robot_height_m:
            raise ValueError("ground clearance must be below robot height")
        for x, z in (self.start_xz_m, *self.waypoints_xz_m, self.goal_xz_m):
            if not xmin <= x < xmax or not zmin <= z < zmax:
                raise ValueError("start/waypoints/goal must lie inside map bounds")
        return self


class ScenarioUpdate(Contract):
    expected_version: int = Field(ge=1, strict=True)
    scenarios: tuple[Scenario, ...] = Field(max_length=16)

    @model_validator(mode="after")
    def unique_ids(self) -> Self:
        ids = [scenario.scenario_id for scenario in self.scenarios]
        if len(ids) != len(set(ids)):
            raise ValueError("scenario IDs must be unique")
        return self


class SimulationRequest(Contract):
    expected_version: int = Field(ge=1, strict=True)
    scenario_id: Identifier
