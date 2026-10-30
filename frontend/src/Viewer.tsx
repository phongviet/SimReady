import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { TransformControls } from "three/addons/controls/TransformControls.js";
import { SparkRenderer, SplatMesh } from "@sparkjsdev/spark";
import { assetUrl } from "./api";
import { calibratedCamera, objectMatrix } from "./camera";
import type { ReplayData } from "./simulation";
import type { ProxyObject, SceneState, Vec3 } from "./types";

type Mode = "translate" | "rotate" | "scale";
interface Props {
  scene: SceneState;
  objects: ProxyObject[];
  selected: string | null;
  showCollision: boolean;
  mode: Mode;
  onSelect: (id: string) => void;
  onChange: (object: ProxyObject) => void;
  onUnavailable: (message: string) => void;
  cameraIndex: number;
  onSpawnPosition: (position: Vec3) => void;
  editable: boolean;
  replay?: ReplayData;
  replayIndex?: number;
}
export function Viewer(props: Props) {
  const host = useRef<HTMLDivElement>(null);
  const latest = useRef(props);
  latest.current = props;
  const sync = useRef<() => void>(() => {});
  const [status, setStatus] = useState("Loading Gaussian scene…");
  useEffect(() => {
    if (!host.current) return;
    const element = host.current;
    setStatus("Loading Gaussian scene…");
    let disposed = false;
    const abort = new AbortController();
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: false,
        preserveDrawingBuffer: true,
      });
    } catch {
      props.onUnavailable(
        "WebGL2 unavailable. Saved camera view is active; numeric editing still works.",
      );
      return;
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.autoClear = false;
    element.appendChild(renderer.domElement);
    renderer.domElement.setAttribute(
      "aria-label",
      "Interactive Gaussian scene",
    );
    const base = new THREE.Scene();
    base.background = new THREE.Color("#101713");
    const overlay = new THREE.Scene();
    let lastActivity = performance.now();
    let splatsLoaded = false;
    const reference = props.scene.base.cameras[props.cameraIndex];
    const camera = calibratedCamera(reference);
    const lookTarget = camera.position
      .clone()
      .add(camera.getWorldDirection(new THREE.Vector3()).multiplyScalar(1.2));
    const orbit = new OrbitControls(camera, renderer.domElement);
    orbit.target.copy(lookTarget);
    orbit.update();
    const placement = () => {
      lastActivity = performance.now();
      latest.current.onSpawnPosition(
        camera.position
          .clone()
          .add(
            camera.getWorldDirection(new THREE.Vector3()).multiplyScalar(0.9),
          )
          .toArray(),
      );
    };
    orbit.addEventListener("change", placement);
    placement();
    const spark = new SparkRenderer({ renderer });
    base.add(spark);
    const splats = new SplatMesh({
      url: assetUrl(props.scene, "gaussian.ply"),
      enableLod: false,
    });
    base.add(splats);
    splats.initialized
      .then(() => {
        if (!disposed) {
          splatsLoaded = true;
          lastActivity = performance.now();
          setStatus("Gaussian scene loaded");
        }
      })
      .catch((error) => {
        if (!disposed)
          latest.current.onUnavailable(
            `Splat viewer unavailable: ${String(error)}. Saved views remain available.`,
          );
      });
    const gizmo = new TransformControls(camera, renderer.domElement);
    overlay.add(gizmo.getHelper());
    gizmo.addEventListener("dragging-changed", (event) => {
      orbit.enabled = !event.value;
    });
    const meshes = new Map<string, THREE.Mesh>();
    const colliders = new Map<string, THREE.LineSegments>();
    const boxGeometry = new THREE.BoxGeometry(1, 1, 1);
    const edgeGeometry = new THREE.EdgesGeometry(boxGeometry);
    let surface: THREE.Mesh | null = null;
    fetch(assetUrl(props.scene, "collision_mesh.json"), {
      signal: abort.signal,
    })
      .then((response) => {
        if (!response.ok) throw new Error("collision geometry request failed");
        return response.json();
      })
      .then((data) => {
        if (disposed) return;
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute(
          "position",
          new THREE.Float32BufferAttribute(data.vertices.flat(), 3),
        );
        geometry.setIndex(data.triangles.flat());
        surface = new THREE.Mesh(
          geometry,
          new THREE.MeshBasicMaterial({
            color: "#5fd7ad",
            wireframe: true,
            transparent: true,
            opacity: 0.22,
          }),
        );
        surface.visible = latest.current.showCollision;
        overlay.add(surface);
      })
      .catch((error) => {
        if (!disposed)
          setStatus(`Collision view unavailable: ${String(error)}`);
      });
    const navigation = new THREE.Group();
    overlay.add(navigation);
    let navigationId = "";
    let robot: THREE.Mesh | null = null;
    const clearNavigation = () => {
      navigation.traverse((node) => {
        if (node instanceof THREE.Mesh || node instanceof THREE.Line) {
          node.geometry.dispose();
          if (node.material instanceof THREE.MeshBasicMaterial)
            node.material.map?.dispose();
          (node.material as THREE.Material).dispose();
        }
      });
      navigation.clear();
      robot = null;
    };
    const syncNavigation = () => {
      const replay = latest.current.replay;
      if ((replay?.run.run_id || "") !== navigationId) {
        clearNavigation();
        navigationId = replay?.run.run_id || "";
        if (replay) {
          const { map, result, run } = replay;
          const [xmin, zmin, xmax, zmax] = map.bounds_xz_m;
          const y = map.floor_y_m + 0.01;
          const geometry = new THREE.BufferGeometry();
          geometry.setAttribute(
            "position",
            new THREE.Float32BufferAttribute(
              [xmin, y, zmin, xmax, y, zmin, xmax, y, zmax, xmin, y, zmax],
              3,
            ),
          );
          geometry.setAttribute(
            "uv",
            new THREE.Float32BufferAttribute([0, 0, 1, 0, 1, 1, 0, 1], 2),
          );
          geometry.setIndex([0, 2, 1, 0, 3, 2]);
          const pixels = new Uint8Array(map.width * map.height * 4);
          for (let z = 0; z < map.height; z++)
            for (let x = 0; x < map.width; x++) {
              const color = map.surface_occupied[z][x]
                ? [216, 132, 78]
                : !map.floor_support[z][x]
                  ? [30, 40, 34]
                  : map.blocked[z][x]
                    ? [100, 90, 78]
                    : [76, 110, 78];
              pixels.set([...color, 180], (z * map.width + x) * 4);
            }
          const texture = new THREE.DataTexture(
            pixels,
            map.width,
            map.height,
            THREE.RGBAFormat,
          );
          texture.needsUpdate = true;
          // Diagnostic layers have explicit order: map, route, then robot.
          // They are overlays, so they must not write depth or mask one another.
          const mapSurface = new THREE.Mesh(
            geometry,
            new THREE.MeshBasicMaterial({
              map: texture,
              transparent: true,
              side: THREE.DoubleSide,
              depthTest: false,
              depthWrite: false,
            }),
          );
          mapSurface.renderOrder = 10;
          navigation.add(mapSurface);
          const points = result.path_xz_m.map(
            ([x, z]) => new THREE.Vector3(x, y + 0.04, z),
          );
          const line = new THREE.Line(
            new THREE.BufferGeometry().setFromPoints(points),
            new THREE.LineBasicMaterial({
              color: "#d9ed96",
              transparent: true,
              depthTest: false,
              depthWrite: false,
            }),
          );
          line.renderOrder = 11;
          navigation.add(line);
          robot = new THREE.Mesh(
            new THREE.CylinderGeometry(
              run.scenario.robot_radius_m,
              run.scenario.robot_radius_m,
              run.scenario.robot_height_m,
              24,
            ),
            new THREE.MeshBasicMaterial({
              color: "#83ddfa",
              transparent: true,
              opacity: 0.9,
              depthTest: false,
              depthWrite: false,
            }),
          );
          robot.renderOrder = 12;
          navigation.add(robot);
          const extent = Math.max(xmax - xmin, zmax - zmin);
          orbit.target.set((xmin + xmax) / 2, y, (zmin + zmax) / 2);
          camera.position
            .copy(orbit.target)
            .add(new THREE.Vector3(extent * 0.3, extent, extent * 0.8));
          orbit.update();
        }
      }
      if (robot && replay) {
        const step = replay.result.trajectory[latest.current.replayIndex || 0];
        robot.visible = Boolean(step);
        if (step)
          robot.position.set(
            step.position_xz_m[0],
            replay.map.floor_y_m + replay.run.scenario.robot_height_m / 2,
            step.position_xz_m[1],
          );
      }
      renderer.domElement.dataset.simulationRun = navigationId;
      renderer.domElement.dataset.robotPosition = robot?.visible
        ? JSON.stringify(robot.position.toArray())
        : "";
      renderer.domElement.dataset.replayIndex = String(
        latest.current.replayIndex || 0,
      );
    };
    const update = () => {
      lastActivity = performance.now();
      const current = latest.current;
      const ids = new Set(current.objects.map((object) => object.object_id));
      for (const [id, mesh] of meshes) {
        if (!ids.has(id)) {
          if (gizmo.object === mesh) gizmo.detach();
          overlay.remove(mesh);
          (mesh.material as THREE.Material).dispose();
          meshes.delete(id);
          const wire = colliders.get(id)!;
          overlay.remove(wire);
          (wire.material as THREE.Material).dispose();
          colliders.delete(id);
        }
      }
      for (const object of current.objects) {
        let mesh = meshes.get(object.object_id);
        if (!mesh) {
          mesh = new THREE.Mesh(
            boxGeometry,
            new THREE.MeshBasicMaterial({ color: object.color }),
          );
          mesh.userData.objectId = object.object_id;
          meshes.set(object.object_id, mesh);
          overlay.add(mesh);
          const wire = new THREE.LineSegments(
            edgeGeometry,
            new THREE.LineBasicMaterial({ color: "#65f0bd", depthTest: false }),
          );
          colliders.set(object.object_id, wire);
          overlay.add(wire);
        }
        objectMatrix(object).decompose(
          mesh.position,
          mesh.quaternion,
          mesh.scale,
        );
        mesh.visible = object.visible;
        (mesh.material as THREE.MeshBasicMaterial).color.set(object.color);
        const wire = colliders.get(object.object_id)!;
        wire.position.copy(mesh.position);
        wire.quaternion.copy(mesh.quaternion);
        wire.scale.copy(mesh.scale);
        wire.visible = current.showCollision && object.collidable;
      }
      const selected = current.selected
        ? meshes.get(current.selected)
        : undefined;
      if (selected?.visible) {
        if (gizmo.object !== selected) gizmo.attach(selected);
      } else gizmo.detach();
      gizmo.setMode(current.mode);
      gizmo.enabled = current.editable;
      if (surface) surface.visible = current.showCollision;
      syncNavigation();
    };
    sync.current = update;
    update();
    gizmo.addEventListener("objectChange", () => {
      const object = latest.current.objects.find(
        (value) => value.object_id === gizmo.object?.userData.objectId,
      );
      const mesh = gizmo.object;
      if (object && mesh)
        latest.current.onChange({
          ...object,
          position: mesh.position.toArray(),
          quaternion_xyzw: mesh.quaternion.clone().normalize().toArray(),
          scale: mesh.scale
            .toArray()
            .map((v) => Math.min(100, Math.max(0.01, v))) as [
            number,
            number,
            number,
          ],
        });
    });
    const select = (event: PointerEvent) => {
      if (gizmo.dragging || !orbit.enabled) return;
      const rect = renderer.domElement.getBoundingClientRect();
      const ray = new THREE.Raycaster();
      ray.setFromCamera(
        new THREE.Vector2(
          ((event.clientX - rect.left) / rect.width) * 2 - 1,
          (-(event.clientY - rect.top) / rect.height) * 2 + 1,
        ),
        camera,
      );
      const hit = ray.intersectObjects(
        [...meshes.values()].filter((mesh) => mesh.visible),
      )[0];
      if (hit) latest.current.onSelect(hit.object.userData.objectId);
    };
    renderer.domElement.addEventListener("pointerup", select);
    const resize = new ResizeObserver(() => {
      renderer.setSize(element.clientWidth, element.clientHeight);
      const original = calibratedCamera(reference);
      const originalAspect = reference.width / reference.height;
      camera.projectionMatrix.copy(original.projectionMatrix);
      camera.projectionMatrix.elements[0] *=
        originalAspect / (element.clientWidth / element.clientHeight);
      camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
    });
    resize.observe(element);
    let renderedFrames = 0;
    let lastRendered = -Infinity;
    renderer.domElement.dataset.frameCadence = "30fps active / 5fps idle cap";
    renderer.setAnimationLoop((now) => {
      if (disposed) return;
      const cadence =
        !splatsLoaded || now - lastActivity < 500 ? 1000 / 30 : 1000 / 5;
      if (now - lastRendered < cadence) return;
      lastRendered = now;
      orbit.update();
      renderer.clear();
      renderer.render(base, camera);
      const baseCalls = renderer.info.render.calls;
      // Intentional overlay mode: do not imply validated splat/mesh depth compositing.
      renderer.clearDepth();
      renderer.render(overlay, camera);
      renderer.domElement.dataset.renderedFrames = String(++renderedFrames);
      renderer.domElement.dataset.renderCalls = String(
        baseCalls + renderer.info.render.calls,
      );
    });
    return () => {
      disposed = true;
      abort.abort();
      resize.disconnect();
      renderer.setAnimationLoop(null);
      renderer.domElement.removeEventListener("pointerup", select);
      gizmo.dispose();
      orbit.dispose();
      splats.dispose();
      spark.dispose();
      boxGeometry.dispose();
      edgeGeometry.dispose();
      meshes.forEach((mesh) => (mesh.material as THREE.Material).dispose());
      colliders.forEach((wire) => (wire.material as THREE.Material).dispose());
      if (surface) {
        surface.geometry.dispose();
        (surface.material as THREE.Material).dispose();
      }
      clearNavigation();
      renderer.dispose();
      renderer.domElement.remove();
      sync.current = () => {};
    };
  }, [props.scene.scene_id, props.cameraIndex]);
  useEffect(() => {
    sync.current();
  }, [
    props.objects,
    props.selected,
    props.showCollision,
    props.mode,
    props.editable,
    props.replay,
    props.replayIndex,
  ]);
  return (
    <div className="viewer" ref={host}>
      <span className="viewer-status" role="status">
        {status}
      </span>
    </div>
  );
}
