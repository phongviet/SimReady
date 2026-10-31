import * as Collapsible from "@radix-ui/react-collapsible";
import {
  WorkbenchNav,
  viewFromSearch,
  type WorkbenchView,
} from "./WorkbenchNav";
import { Button } from "./components/ui/button";
import { SceneCard } from "./SceneCard";
import { AccountBar } from "./AccountBar";
import type { Principal } from "./auth";
import { lazy, Suspense, useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { api, ApiError } from "./api";
import { spawnPosition } from "./camera";
import { SavedView } from "./SavedView";
import type { ProxyObject, SceneState, Vec3 } from "./types";

const ReviewPanel = lazy(() =>
  import("./ReviewPanel").then((module) => ({ default: module.ReviewPanel })),
);

const SimulationPanel = lazy(() =>
  import("./SimulationPanel").then((module) => ({
    default: module.SimulationPanel,
  })),
);

const EvaluationExplorer = lazy(() =>
  import("./EvaluationExplorer").then((module) => ({
    default: module.EvaluationExplorer,
  })),
);

const ResearchDashboard = lazy(() =>
  import("./ResearchDashboard").then((module) => ({
    default: module.ResearchDashboard,
  })),
);

const Viewer = lazy(() =>
  import("./Viewer").then((module) => ({ default: module.Viewer })),
);

export function App() {
  const [libraryOpen, setLibraryOpen] = useState(
    () =>
      typeof window === "undefined" ||
      window.matchMedia("(min-width: 801px)").matches,
  );
  const [user, setUser] = useState<Principal | null>(null);
  const canEdit = user?.role === "builder";
  const [libraryFilter, setLibraryFilter] = useState<"all" | "submitted">(
    "all",
  );
  const [scenes, setScenes] = useState<SceneState[]>([]);
  const [scene, setScene] = useState<SceneState | null>(null);
  const [objects, setObjects] = useState<ProxyObject[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [deletedObject, setDeletedObject] = useState<ProxyObject | null>(null);
  const [dirty, setDirty] = useState(false),
    [busy, setBusy] = useState(false);
  const [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [view, setView] = useState<WorkbenchView>(() =>
    typeof window === "undefined"
      ? "3d"
      : viewFromSearch(window.location.search),
  );
  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.set("view", view);
    window.history.replaceState(null, "", url);
  }, [view]);
  useEffect(() => {
    const restore = () => setView(viewFromSearch(window.location.search));
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, []);
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  const navigate = (next: WorkbenchView) => {
    const url = new URL(window.location.href);
    url.searchParams.set("view", next);
    if (url.href !== window.location.href)
      window.history.pushState(null, "", url);
    setView(next);
  };
  const contextual = ["evaluation", "research", "review"].includes(view);
  const [cameraIndex, setCameraIndex] = useState(0),
    [collision, setCollision] = useState(false);
  const [showCameras, setShowCameras] = useState(false);
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
    setDeletedObject(null);
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
              name={`${field}-${index}`}
              autoComplete="off"
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
    <div
      className={`studio ${libraryOpen ? "" : "library-collapsed"} ${contextual ? "inspector-hidden" : ""}`}
    >
      <a className="skip-link" href="#workspace">
        Skip to workspace
      </a>
      <header className="topbar">
        <Button
          variant="ghost"
          aria-label="Toggle scene library"
          aria-expanded={libraryOpen}
          aria-controls="scene-library-content"
          onClick={() => setLibraryOpen((v) => !v)}
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path d="M3 4h18v16H3V4Zm5 0v16" />
          </svg>
        </Button>
        <div className="brand">
          <span className="brand-mark">S</span>
          <strong>SimReady</strong>
          <span className="local-badge">Real2Sim workstation</span>
        </div>
      </header>
      <AccountBar user={user} onUser={setUser} />
      <Collapsible.Root
        asChild
        open={libraryOpen}
        onOpenChange={setLibraryOpen}
      >
        <aside className="library" aria-label="Scene library">
          <WorkbenchNav
            view={view}
            onView={navigate}
            collapsed={!libraryOpen}
            disabled={!scene}
          />
          <Collapsible.Content id="scene-library-content">
            <div className="section-label">
              SCENE LIBRARY <span>{scenes.length}</span>
            </div>
            <div className="library-filter">
              <button onClick={() => setLibraryFilter("all")}>
                All scenes
              </button>
              <button
                onClick={() => {
                  if (dirty) {
                    setError(
                      "Save/discard edits before opening the review queue.",
                    );
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
                (value) =>
                  libraryFilter === "all" || value.status === "submitted",
              )
              .map((value) => (
                <SceneCard
                  key={value.scene_id}
                  scene={value}
                  active={scene?.scene_id === value.scene_id}
                  onChoose={() => void choose(value.scene_id)}
                />
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
          </Collapsible.Content>
        </aside>
      </Collapsible.Root>
      <main className="workspace" id="workspace" tabIndex={-1}>
        <Suspense fallback={<p role="status">Loading workspace…</p>}>
          <div className="workspace-heading">
            <div>
              <p className="eyebrow">
                Workspace / {view === "3d" ? "Scene" : view}
              </p>
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
          {deletedObject && (
            <div className="message" role="status">
              Removed {deletedObject.name}.{" "}
              <Button
                variant="ghost"
                disabled={!canEdit || busy || objects.length >= 128}
                onClick={() => {
                  setObjects((values) => [...values, deletedObject]);
                  setSelected(deletedObject.object_id);
                  setDeletedObject(null);
                  setDirty(true);
                }}
              >
                Undo removal
              </Button>
            </div>
          )}
          {!scene ? (
            <div className="connection-panel">
              <h2>Start with a working scene.</h2>
              <p>
                Launch the API with the bundled, genuinely trained synthetic
                demo. No GPU is needed to inspect it or edit proxy boxes.
              </p>
              <pre>simready api serve --demo</pre>
              <p>
                Load a registered report to inspect frozen-view validation.
                Registered scenes support navigation and scoped review.
              </p>
            </div>
          ) : (
            <>
              <div className="toolbar" hidden={contextual}>
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
                <label
                  className="collision-toggle"
                  title="Frame tested reference camera centers. Connecting segments do not establish coverage."
                >
                  <input
                    type="checkbox"
                    checked={showCameras}
                    disabled={view !== "3d"}
                    onChange={(event) => setShowCameras(event.target.checked)}
                  />{" "}
                  Reference camera path
                </label>
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
                          showCameras={showCameras}
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
        </Suspense>
      </main>
      <aside className="inspector" hidden={contextual}>
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
                name="object-name"
                autoComplete="off"
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
                setDeletedObject(object);
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
