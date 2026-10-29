import type { SceneState } from "./types";
export interface Scenario {
  scenario_id: string;
  name: string;
  bounds_xz_m: [number, number, number, number];
  floor_y_m: number;
  floor_mode: "observed_tsdf" | "declared_virtual_plane";
  floor_note: string;
  floor_tolerance_m: number;
  ground_clearance_m: number;
  robot_radius_m: number;
  robot_height_m: number;
  resolution_m: number;
  start_xz_m: [number, number];
  goal_xz_m: [number, number];
  waypoints_xz_m: [number, number][];
  speed_m_s: number;
  timestep_s: number;
  seed: number;
  unknown_policy: "blocked";
}
export interface SimulationRun {
  run_id: string;
  scene_version: number;
  created_at: string;
  scenario: Scenario;
  simulation_sha256: string;
  floor_evidence: string;
  unknown_cells: number;
  result_summary: {
    route_success: boolean;
    reason: string;
    path_length_m: number | null;
    travel_distance_m: number;
    collisions: number;
    elapsed_simulated_s: number;
  };
  limitations: string[];
}
export interface SimulationResult {
  path_xz_m: [number, number][];
  trajectory: { time_s: number; position_xz_m: [number, number] }[];
}
export interface OccupancyMap {
  bounds_xz_m: [number, number, number, number];
  resolution_m: number;
  floor_y_m: number;
  width: number;
  height: number;
  floor_support: number[][];
  surface_occupied: number[][];
  blocked: number[][];
}
export interface ReplayData {
  run: SimulationRun;
  result: SimulationResult;
  map: OccupancyMap;
  scene: SceneState;
}
export function simulationAsset(sceneId: string, runId: string, name: string) {
  return `/api/v1/scenes/${encodeURIComponent(sceneId)}/simulations/${encodeURIComponent(runId)}/assets/${encodeURIComponent(name)}`;
}
export function defaultScenario(scene: SceneState): Scenario {
  const analytic = scene.scene_id === "analytic-demo";
  return {
    scenario_id: "route-example",
    name: analytic ? "Virtual floor demo" : "Observed TUM floor example",
    bounds_xz_m: analytic ? [-1, -1.8, 1, -0.2] : [-2.4, -2.8, 1.8, 0.9],
    floor_y_m: analytic ? -0.7 : 0,
    floor_mode: analytic ? "declared_virtual_plane" : "observed_tsdf",
    floor_note: analytic
      ? "Declared virtual plane for simplified replay; no observed floor truth."
      : "Nominal TUM floor near Y0; inspect coarse TSDF and unknowns. Not independently gravity-calibrated.",
    floor_tolerance_m: 0.1,
    ground_clearance_m: 0.12,
    robot_radius_m: 0.08,
    robot_height_m: 0.5,
    resolution_m: 0.05,
    start_xz_m: analytic ? [-0.6, -1.4] : [-1.125, -2.175],
    goal_xz_m: analytic ? [0.6, -0.6] : [-0.775, -1.475],
    waypoints_xz_m: [],
    speed_m_s: 0.15,
    timestep_s: 0.1,
    seed: 42,
    unknown_policy: "blocked",
  };
}
