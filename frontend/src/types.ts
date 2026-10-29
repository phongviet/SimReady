import type { ReviewRecord } from "./review";
import type { Scenario } from "./simulation";
export type Vec3 = [number, number, number];
export type Quaternion = [number, number, number, number];
export interface ProxyObject {
  object_id: string;
  name: string;
  kind: "box" | "barrier";
  position: Vec3;
  quaternion_xyzw: Quaternion;
  scale: Vec3;
  visible: boolean;
  collidable: boolean;
  color: string;
}
export interface CameraRecord {
  frame_id: string;
  width: number;
  height: number;
  K: number[][];
  viewmat: number[][];
}
export interface SceneState {
  schema_version: "1.0";
  scene_id: string;
  name: string;
  version: number;
  status: string;
  review?: ReviewRecord;
  objects: ProxyObject[];
  scenarios?: Scenario[];
  updated_at: string;
  base: {
    dataset_kind: "real" | "synthetic";
    assets: Record<string, { path: string; sha256: string }>;
    cameras: CameraRecord[];
    bounds_min_m: Vec3;
    bounds_max_m: Vec3;
    geometry_quality: string;
    limitations: string[];
    source: { name: string; license: string; attribution: string };
  };
}
