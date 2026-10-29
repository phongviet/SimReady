import { describe, expect, it } from "vitest";
import * as THREE from "three";
import { calibratedCamera, objectCorners, projectWorld } from "./camera";
import type { CameraRecord, ProxyObject } from "./types";

describe("canonical projection parity", () => {
  const camera: CameraRecord = {
    frame_id: "known",
    width: 640,
    height: 480,
    K: [
      [500, 0, 319.5],
      [0, 400, 239.5],
      [0, 0, 1],
    ],
    viewmat: [
      [1, 0, 0, -2],
      [0, -1, 0, 3],
      [0, 0, -1, 4],
      [0, 0, 0, 1],
    ],
  };
  it("projects a known world marker to the same pixel as the Python calibration test", () => {
    const world: [number, number, number] = [2.4, 3.2, 2];
    expect(projectWorld(world, camera)![0]).toBeCloseTo(419.5, 9);
    expect(projectWorld(world, camera)![1]).toBeCloseTo(199.5, 9);
    const ndc = new THREE.Vector3(...world).project(calibratedCamera(camera));
    expect(((ndc.x + 1) / 2) * 640 - 0.5).toBeCloseTo(419.5, 9);
    expect(((1 - ndc.y) / 2) * 480 - 0.5).toBeCloseTo(199.5, 9);
  });
  it("preserves metric size and quaternion rotation shared with collision transforms", () => {
    const object: ProxyObject = {
      object_id: "known",
      name: "Known box",
      kind: "box",
      position: [0, 0, -2],
      quaternion_xyzw: [0, Math.sqrt(0.5), 0, Math.sqrt(0.5)],
      scale: [2, 1, 0.5],
      visible: true,
      collidable: true,
      color: "#aabbcc",
    };
    const bounds = new THREE.Box3().setFromPoints(
      objectCorners(object).map((p) => new THREE.Vector3(...p)),
    );
    const size = bounds.getSize(new THREE.Vector3());
    expect(size.x).toBeCloseTo(0.5, 9);
    expect(size.y).toBeCloseTo(1, 9);
    expect(size.z).toBeCloseTo(2, 9);
  });
});
