import { AccountBar } from "./AccountBar";
import type { Principal } from "./auth";
import { ReviewPanel } from "./ReviewPanel";
import { lazy, Suspense, useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { api, ApiError } from "./api";
import { spawnPosition } from "./camera";
import { SimulationPanel } from "./SimulationPanel";
import { EvaluationExplorer } from "./EvaluationExplorer";
import { ResearchDashboard } from "./ResearchDashboard";
import { SavedView } from "./SavedView";
import type { ProxyObject, SceneState, Vec3 } from "./types";

const Viewer = lazy(() =>
  import("./Viewer").then((module) => ({ default: module.Viewer })),
);

export function App() {
  const [user, setUser] = useState<Principal | null>(null);
  const canEdit = user?.role === "builder";
  const [libraryFilter, setLibraryFilter] = useState<"all" | "submitted">(
    "all",
  );
  const [scenes, setScenes] = useState<SceneState[]>([]);
  const [scene, setScene] = useState<SceneState | null>(null);
  const [objects, setObjects] = useState<ProxyObject[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false),
    [busy, setBusy] = useState(false);
  const [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [view, setView] = useState<
    "3d" | "saved" | "evaluation" | "simulation" | "review" | "research"
  >("3d");
  const [cameraIndex, setCameraIndex] = useState(0),
    [collision, setCollision] = useState(false);
  const [mode, setMode] = useState<"translate" | "rotate" | "scale">(
    "translate",
  );
  const placement = useRef<Vec3 | null>(null);
  const accept = (value: SceneState) => {
    setScene(value);
    setObjects(value.objects);
    setDirty(false);
    setError("");
    setSelected(null);
    setCameraIndex(0);
    placement.current = null;
  };
  useEffect(() => {
    api
      .list()
      .then((values) => {
        setScenes(values);
        if (values[0]) accept(values[0]);
      })
      .catch((reason) =>
        setError(
          `Studio API unavailable: ${String(reason)}. Start the local API with the demo enabled.`,
        ),
      );
  }, []);
  const choose = async (id: string) => {
    if (dirty) {
      setError("Save edits or use Reload / discard before switching scenes.");
      return;
    }
    try {
      accept(await api.scene(id));
      setNotice("");
      setView(libraryFilter === "submitted" ? "review" : "3d");
    } catch (reason) {
      setError(String(reason));
    }
  };
  const change = (object: ProxyObject) => {
    setObjects((values) =>
      values.map((value) =>
        value.object_id === object.object_id ? object : value,
      ),
    );
    setDirty(true);
    setNotice("");
  };
  const add = (kind: "box" | "barrier") => {
    if (!scene) return;
    const object: ProxyObject = {
      object_id: crypto.randomUUID(),
      name: `${kind === "box" ? "Box" : "Barrier"} ${objects.length + 1}`,
      kind,
      position:
        view === "3d" && placement.current
          ? [...placement.current]
          : spawnPosition(scene.base.cameras[cameraIndex]),
      quaternion_xyzw: [0, 0, 0, 1],
      scale: kind === "box" ? [0.3, 0.3, 0.3] : [0.8, 0.5, 0.08],
      visible: true,
      collidable: true,
      color: "#d3ed8b",
    };
    setObjects((values) => [...values, object]);
    setSelected(object.object_id);
    setDirty(true);
    setNotice("");
  };
  const save = async () => {
    if (!scene) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const saved = await api.save(scene, objects);
      setScene(saved);
      setObjects(saved.objects);
      setDirty(false);
      setScenes((values) =>
        values.map((value) =>
          value.scene_id === saved.scene_id ? saved : value,
        ),
      );
      setNotice(
        `Saved revision ${saved.version}. Base reconstruction unchanged.`,
      );
    } catch (reason) {
      const prefix =
        reason instanceof ApiError && reason.status === 409
          ? "Version conflict. Your local edits are preserved. "
          : "";
      setError(prefix + String(reason));
    } finally {
      setBusy(false);
    }
  };
  const reload = async () => {
    if (!scene) return;
    try {
      accept(await api.scene(scene.scene_id));
      setNotice("Loaded the latest saved revision.");
    } catch (reason) {
      setError(String(reason));
    }
  };
  const object = objects.find((value) => value.object_id === selected);
  const euler = object
    ? new THREE.Euler().setFromQuaternion(
        new THREE.Quaternion(...object.quaternion_xyzw),
        "XYZ",
      )
    : new THREE.Euler();
  const editVector = (
    field: "position" | "scale" | "rotation",
    index: number,
    raw: string,
  ) => {
    if (!object || raw === "" || !Number.isFinite(Number(raw))) return;
    const value = Number(raw);
    if (field === "rotation") {
      const angles: Vec3 = [euler.x, euler.y, euler.z];
      angles[index] = THREE.MathUtils.degToRad(value);
      const quaternion = new THREE.Quaternion()
        .setFromEuler(new THREE.Euler(...angles, "XYZ"))
        .normalize();
      change({ ...object, quaternion_xyzw: quaternion.toArray() });
    } else {
      const vector = [...object[field]] as Vec3;
      vector[index] =
        field === "scale" ? Math.min(100, Math.max(0.01, value)) : value;
      change({ ...object, [field]: vector });
    }
  };
  const vectorFields = (
    title: string,
    field: "position" | "scale" | "rotation",
    values: number[],
  ) => (
    <div className="transform-section">
      <h3>{title}</h3>
      <div className="vector-inputs">
        {values.map((value, index) => (
          <label key={index}>
            <span>{["X", "Y", "Z"][index]}</span>
            <input
              aria-label={`${title} ${["X", "Y", "Z"][index]}`}
              type="number"
              step={field === "rotation" ? 1 : 0.01}
              value={Number(value.toFixed(3))}
              onChange={(event) => editVector(field, index, event.target.value)}
            />
          </label>
        ))}
      </div>
    </div>
  );
  return (
    <div className="studio">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">S</span>
          <strong>SimReady</strong>
          <span className="local-badge">LOCAL STUDIO</span>
        </div>
        <span className="top-caption">Reconstruct. Inspect. Edit.</span>
        <span className="milestone-badge">
          Measured scenes · Scoped experiments
        </span>
      </header>
      <AccountBar user={user} onUser={setUser} />
      <aside className="library">
        <div className="section-label">
          SCENE LIBRARY <span>{scenes.length}</span>
        </div>
        <div className="library-filter">
          <button onClick={() => setLibraryFilter("all")}>All scenes</button>
          <button
            onClick={() => {
              if (dirty) {
                setError("Save/discard edits before opening the review queue.");
                return;
              }
              void api
                .list()
                .then((values) => {
                  setScenes(values);
                  setLibraryFilter("submitted");
                  const next = values.find((s) => s.status === "submitted");
                  if (next) {
                    accept(next);
                    setView("review");
                  } else setNotice("No scenes are submitted for review.");
                })
                .catch((reason) => setError(String(reason)));
            }}
          >
            Review queue
          </button>
        </div>
        {scenes
          .filter(
            (value) => libraryFilter === "all" || value.status === "submitted",
          )
          .map((value) => (
            <button
              className={`scene-card ${scene?.scene_id === value.scene_id ? "active" : ""}`}
              key={value.scene_id}
              onClick={() => void choose(value.scene_id)}
            >
              <span className="scene-symbol">▧</span>
              <strong>{value.name}</strong>
              <small>
                {value.base.dataset_kind === "real"
                  ? "REAL CAPTURE"
                  : "SYNTHETIC"}{" "}
                · v{value.version} · {value.status}
              </small>
            </button>
          ))}
        {!scenes.length && (
          <p className="empty-copy">
            Connect to the local API to load a registered scene. The offline
            analytic demo is available with <code>--demo</code>.
          </p>
        )}
        <div className="library-note">
          <span className="dot" /> METRIC COORDINATES
          <p>
            Right-handed · Y up
            <br />
            All dimensions in meters.
          </p>
        </div>
      </aside>
      <main className="workspace">
        <div className="workspace-heading">
          <div>
            <p className="eyebrow">SCENE WORKSPACE</p>
            <h1>{scene?.name || "Connect your local studio"}</h1>
          </div>
          {scene && (
            <button className="draft-badge" onClick={() => setView("review")}>
              {scene.status} · v{scene.version} · review ↗
            </button>
          )}
        </div>
        {error && (
          <div className="message error" role="alert">
            {error}
          </div>
        )}
        {notice && (
          <div className="message success" role="status">
            {notice}
          </div>
        )}
        {!scene ? (
          <div className="connection-panel">
            <h2>Start with a working scene.</h2>
            <p>
              Launch the API with the bundled, genuinely trained synthetic demo.
              No GPU is needed to inspect it or edit proxy boxes.
            </p>
            <pre>simready api serve --demo</pre>
            <p>
              Load a registered report to inspect frozen-view validation.
              Simulation and review are later milestones.
            </p>
          </div>
        ) : (
          <>
            <div className="toolbar">
              <div className="segmented">
                <button
                  className={view === "3d" ? "selected" : ""}
                  onClick={() => setView("3d")}
                >
                  3D scene
                </button>
                <button
                  className={view === "saved" ? "selected" : ""}
                  onClick={() => setView("saved")}
                >
                  Saved camera
                </button>
              </div>
              <button
                className={view === "evaluation" ? "selected" : ""}
                onClick={() => setView("evaluation")}
              >
                Evaluation
              </button>
              <button
                className={view === "simulation" ? "selected" : ""}
                onClick={() => setView("simulation")}
              >
                Navigation
              </button>
              <button
                className={view === "review" ? "selected" : ""}
                onClick={() => setView("review")}
              >
                Readiness / review
              </button>
              <button
                className={view === "research" ? "selected" : ""}
                onClick={() => setView("research")}
              >
                Research
              </button>
              <button
                onClick={() => add("box")}
                disabled={busy || !canEdit || objects.length >= 128}
              >
                ＋ Box
              </button>
              <button
                onClick={() => add("barrier")}
                disabled={busy || !canEdit || objects.length >= 128}
              >
                ＋ Barrier
              </button>
              <label className="collision-toggle">
                <input
                  type="checkbox"
                  checked={collision}
                  disabled={view !== "3d"}
                  onChange={(event) => setCollision(event.target.checked)}
                />{" "}
                Collision proxy
              </label>
            </div>
            {view === "research" ? (
              <ResearchDashboard />
            ) : view === "review" ? (
              <ReviewPanel
                scene={scene}
                user={user}
                unsaved={dirty}
                onScene={(value) => {
                  accept(value);
                  setScenes((values) =>
                    values.map((s) =>
                      s.scene_id === value.scene_id ? value : s,
                    ),
                  );
                }}
              />
            ) : view === "simulation" ? (
              <SimulationPanel
                key={scene.scene_id}
                scene={scene}
                unsaved={dirty}
                editable={canEdit}
                onScene={(value) => {
                  accept(value);
                  setScenes((values) =>
                    values.map((s) =>
                      s.scene_id === value.scene_id ? value : s,
                    ),
                  );
                }}
              />
            ) : view === "evaluation" ? (
              <EvaluationExplorer
                key={scene.scene_id}
                scene={scene}
                canEvaluate={canEdit}
              />
            ) : (
              <>
                <div className="preview-banner">
                  OVERLAY PREVIEW{" "}
                  <span>
                    Inserted meshes are not depth-composited with splats.
                    Unobserved space is unverified.
                  </span>
                </div>
                <div className="viewport-container">
                  {view === "3d" ? (
                    <Suspense
                      fallback={<span role="status">Loading viewer…</span>}
                    >
                      <Viewer
                        scene={scene}
                        objects={objects}
                        selected={selected}
                        showCollision={collision}
                        mode={mode}
                        editable={!busy && canEdit}
                        cameraIndex={cameraIndex}
                        onSpawnPosition={(value) => {
                          placement.current = value;
                        }}
                        onSelect={setSelected}
                        onChange={change}
                        onUnavailable={(message) => {
                          setView("saved");
                          setNotice(message);
                        }}
                      />
                    </Suspense>
                  ) : (
                    <SavedView
                      scene={scene}
                      objects={objects}
                      index={cameraIndex}
                    />
                  )}
                  <div className="viewport-footer">
                    <span>
                      {view === "3d"
                        ? "Orbit · left drag / Pan · right drag / Zoom · scroll"
                        : `Frozen ${scene.base.cameras[cameraIndex].frame_id} · generated Gaussian view`}
                    </span>
                    <span>Y ↑ &nbsp; meters</span>
                  </div>
                </div>
                <div className="below-viewport">
                  <div>
                    <strong>Coarse collision geometry</strong>
                    <p>
                      Independent TSDF from training RGB-D. Holes and unknown
                      regions remain unverified.
                    </p>
                  </div>
                  <label>
                    Reference camera{" "}
                    <select
                      aria-label="Reference camera"
                      value={cameraIndex}
                      onChange={(event) => {
                        placement.current = null;
                        setCameraIndex(Number(event.target.value));
                      }}
                    >
                      {scene.base.cameras.map((camera, index) => (
                        <option key={camera.frame_id} value={index}>
                          {camera.frame_id}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                <details className="source-details">
                  <summary>Source and limitations</summary>
                  <p>
                    {scene.base.source.name} · {scene.base.source.license}
                  </p>
                  <p>{scene.base.source.attribution}</p>
                  <ul>
                    {[...new Set(scene.base.limitations)].map((text) => (
                      <li key={text}>{text}</li>
                    ))}
                  </ul>
                </details>
              </>
            )}
          </>
        )}
      </main>
      <aside className="inspector">
        <div className="section-label">
          INSERTED OBJECTS <span>{objects.length}</span>
        </div>
        <div className="object-list">
          {objects.map((value) => (
            <button
              key={value.object_id}
              className={selected === value.object_id ? "active" : ""}
              onClick={() => setSelected(value.object_id)}
            >
              <span>▣</span>
              {value.name}
              <small>{value.visible ? "Visible" : "Hidden"}</small>
            </button>
          ))}
        </div>
        {!object ? (
          <p className="empty-copy">
            Add a box or barrier, then select it to edit its metric transform.
            The base splats stay immutable.
          </p>
        ) : (
          <fieldset disabled={busy || !canEdit} className="object-fields">
            <label className="name-label">
              Object name
              <input
                aria-label="Object name"
                value={object.name}
                maxLength={80}
                onChange={(event) =>
                  change({ ...object, name: event.target.value })
                }
              />
            </label>
            <div className="segmented transform-modes">
              {(["translate", "rotate", "scale"] as const).map((value) => (
                <button
                  key={value}
                  className={mode === value ? "selected" : ""}
                  onClick={() => setMode(value)}
                >
                  {value}
                </button>
              ))}
            </div>
            {vectorFields("Position (m)", "position", object.position)}
            {vectorFields(
              "Rotation (°)",
              "rotation",
              [euler.x, euler.y, euler.z].map(THREE.MathUtils.radToDeg),
            )}
            {vectorFields("Size (m)", "scale", object.scale)}
            <label className="check-label">
              <input
                type="checkbox"
                checked={object.visible}
                onChange={(event) =>
                  change({ ...object, visible: event.target.checked })
                }
              />
              Visible
            </label>
            <label className="check-label">
              <input
                type="checkbox"
                checked={object.collidable}
                onChange={(event) =>
                  change({ ...object, collidable: event.target.checked })
                }
              />
              Collider enabled
            </label>
            <p className="field-note">
              The collider shares this exact transform. Hiding the mesh does not
              disable its collider.
            </p>
            <button
              className="delete-button"
              onClick={() => {
                setObjects((values) =>
                  values.filter(
                    (value) => value.object_id !== object.object_id,
                  ),
                );
                setSelected(null);
                setDirty(true);
                setNotice("");
              }}
            >
              Delete object
            </button>
          </fieldset>
        )}
        <div className="save-panel">
          <span className={dirty ? "unsaved" : "muted"}>
            {dirty ? "● Unsaved edits" : "Saved state"}
          </span>
          <button
            className="primary"
            disabled={!scene || !dirty || busy || !canEdit}
            onClick={() => void save()}
          >
            {busy ? "Saving…" : "Save revision"}
          </button>
          <button disabled={!scene || busy} onClick={() => void reload()}>
            Reload / discard
          </button>
        </div>
      </aside>
    </div>
  );
}
