import { assetUrl } from "./api";
import { objectCorners, projectWorld } from "./camera";
import type { ProxyObject, SceneState } from "./types";

const edges = [
  [0, 1],
  [0, 2],
  [0, 4],
  [1, 3],
  [1, 5],
  [2, 3],
  [2, 6],
  [3, 7],
  [4, 5],
  [4, 6],
  [5, 7],
  [6, 7],
];
export function SavedView({
  scene,
  objects,
  index,
}: {
  scene: SceneState;
  objects: ProxyObject[];
  index: number;
}) {
  const camera = scene.base.cameras[index];
  return (
    <div
      className="saved-view"
      style={{ aspectRatio: `${camera.width}/${camera.height}` }}
    >
      <img
        src={assetUrl(scene, `${camera.frame_id}.png`)}
        alt={`Saved Gaussian render ${camera.frame_id}`}
      />
      <svg
        viewBox={`0 0 ${camera.width} ${camera.height}`}
        aria-label="Projected inserted object wireframes"
      >
        {objects
          .filter((object) => object.visible)
          .map((object) => {
            const points = objectCorners(object).map((point) =>
              projectWorld(point, camera),
            );
            return (
              <g
                key={object.object_id}
                stroke={object.color}
                strokeWidth="1.5"
                fill="none"
              >
                {edges.map(([a, b], i) => {
                  const p = points[a],
                    q = points[b];
                  return p && q ? (
                    <line key={i} x1={p[0]} y1={p[1]} x2={q[0]} y2={q[1]} />
                  ) : null;
                })}
              </g>
            );
          })}
      </svg>
    </div>
  );
}
