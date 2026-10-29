import type { Principal } from "./auth";
export interface ReviewScope {
  task: "occupancy_navigation_regression" | "heldout_view_inspection";
  name: string;
  camera_ids: string[];
  bounds_xz_m: [number, number, number, number];
  expected_navigation: "goal_reached" | "no_route";
  limitations_acknowledged: true;
}
export interface ReviewRecord {
  review_id: string;
  source_version: number;
  scope: ReviewScope;
  submitted_by: Principal;
  submission_event_id: string;
  approval_event_id?: string;
  decision_event_id?: string;
  reason?: string;
  decided_by?: Principal;
  decision_at?: string;
}
export interface AuditEvent {
  event_id: string;
  action: string;
  actor: Principal;
  before_version: number;
  after_version: number;
  timestamp: string;
  sha256: string;
  previous_sha256: string | null;
  details: { reason?: string; scope?: ReviewScope; source_version?: number };
}
export interface Readiness {
  outcome: string;
  source_version: number;
  geometry: {
    vertices: number;
    triangles: number;
    boundary_edges: number;
    nonmanifold_edges: number;
    surface_area_m2: number;
  };
  coverage: {
    training_cameras: number;
    tested_reference_views: number;
    unobserved_free_views: string;
    views: {
      frame_id: string;
      distance_m: number;
      rotation_deg: number;
      classification: string;
      depth_completeness: number | null;
    }[];
  };
  perception: {
    real_count: number;
    rendered_count: number;
    matched_count: number;
  } | null;
  evaluation: { run_id: string; scene_version: number; sha256: string } | null;
  simulation: {
    run_id: string;
    scene_version: number;
    unknown_cells: number;
    floor_support_cells: number;
  } | null;
  flags: string[];
  limitations: string[];
}
