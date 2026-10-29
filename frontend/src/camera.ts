import * as THREE from "three";
import type { CameraRecord, ProxyObject, Vec3 } from "./types";

export function matrixFromRows(rows: number[][]) {
  return new THREE.Matrix4().fromArray(rows.flat()).transpose();
}
export function calibratedCamera(record: CameraRecord) {
  const camera = new THREE.PerspectiveCamera();
  const cvToGl = new THREE.Matrix4().makeScale(1, -1, -1);
  const world = matrixFromRows(record.viewmat).invert().multiply(cvToGl);
  world.decompose(camera.position, camera.quaternion, camera.scale);
  camera.updateMatrixWorld(true);
  const [w, h] = [record.width, record.height];
  const [[fx, , cx], [, fy, cy]] = record.K;
  const near = 0.01,
    far = 100;
  camera.projectionMatrix.set(
    (2 * fx) / w,
    0,
    1 - (2 * (cx + 0.5)) / w,
    0,
    0,
    (2 * fy) / h,
    (2 * (cy + 0.5)) / h - 1,
    0,
    0,
    0,
    -(far + near) / (far - near),
    (-2 * far * near) / (far - near),
    0,
    0,
    -1,
    0,
  );
  camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
  return camera;
}
export function projectWorld(
  point: Vec3,
  record: CameraRecord,
): [number, number] | null {
  const view = new THREE.Vector3(...point).applyMatrix4(
    matrixFromRows(record.viewmat),
  );
  if (view.z <= 0) return null;
  return [
    (record.K[0][0] * view.x) / view.z + record.K[0][2],
    (record.K[1][1] * view.y) / view.z + record.K[1][2],
  ];
}
export function objectMatrix(object: ProxyObject) {
  return new THREE.Matrix4().compose(
    new THREE.Vector3(...object.position),
    new THREE.Quaternion(...object.quaternion_xyzw),
    new THREE.Vector3(...object.scale),
  );
}
export function objectCorners(object: ProxyObject): Vec3[] {
  const transform = objectMatrix(object);
  return [-0.5, 0.5].flatMap((x) =>
    [-0.5, 0.5].flatMap((y) =>
      [-0.5, 0.5].map(
        (z) =>
          new THREE.Vector3(x, y, z).applyMatrix4(transform).toArray() as Vec3,
      ),
    ),
  );
}
export function spawnPosition(record: CameraRecord): Vec3 {
  return new THREE.Vector3(0, 0, 0.9)
    .applyMatrix4(matrixFromRows(record.viewmat).invert())
    .toArray() as Vec3;
}
