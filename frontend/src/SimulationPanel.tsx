import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { api } from "./api";
import {
  defaultScenario,
  simulationAsset,
  type ReplayData,
  type Scenario,
  type SimulationRun,
} from "./simulation";
import { score } from "./evaluation";
import type { SceneState } from "./types";
const Viewer = lazy(() =>
  import("./Viewer").then((module) => ({ default: module.Viewer })),
);

export function SimulationPanel({
  scene,
  onScene,
  unsaved,
  editable = true,
}: {
  scene: SceneState;
  onScene: (scene: SceneState) => void;
  unsaved: boolean;
  editable?: boolean;
}) {
  const [config, setConfig] = useState<Scenario>(
    scene.scenarios?.[0] || defaultScenario(scene),
  );
  const [changed, setChanged] = useState(!scene.scenarios?.length);
  const loadingGeneration = useRef(0);
  const [runs, setRuns] = useState<SimulationRun[]>([]);
  const [replay, setReplay] = useState<ReplayData | null>(null);
  const [index, setIndex] = useState(0),
    [playing, setPlaying] = useState(false);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [unavailable, setUnavailable] = useState("");
  const [waypoints, setWaypoints] = useState(
    config.waypoints_xz_m.map((point) => point.join(",")).join("; "),
  );
  const load = async (run: SimulationRun) => {
    const generation = ++loadingGeneration.current;
    const data = await api.simulationData(scene.scene_id, run.run_id);
    if (generation !== loadingGeneration.current) return;
    setReplay({ run, ...data });
    setIndex(0);
    setPlaying(false);
  };
  useEffect(() => {
    let active = true;
    const generation = ++loadingGeneration.current;
    api
      .simulations(scene.scene_id)
      .then(async (values) => {
        if (!active || generation !== loadingGeneration.current) return;
        setRuns(values);
        if (values.length) {
          const run = values[values.length - 1],
            data = await api.simulationData(scene.scene_id, run.run_id);
          if (active && generation === loadingGeneration.current)
            setReplay({ run, ...data });
        }
      })
      .catch((reason) => {
        if (active) setError(String(reason));
      });
    return () => {
      active = false;
    };
  }, [scene.scene_id]);
  useEffect(() => {
    if (!playing || !replay?.result.trajectory.length) return;
    const timer = setInterval(
      () =>
        setIndex((value) => {
          if (value >= replay.result.trajectory.length - 1) {
            setPlaying(false);
            return value;
          }
          return value + 1;
        }),
      100,
    );
    return () => clearInterval(timer);
  }, [playing, replay]);
  const change = (patch: Partial<Scenario>) => {
    setConfig((value) => ({ ...value, ...patch }));
    setChanged(true);
  };
  const numeric = (key: keyof Scenario, label: string, step = 0.01) => (
    <label>
      {label}
      <input
        aria-label={label}
        type="number"
        step={step}
        value={config[key] as number}
        onChange={(event) => {
          if (event.target.value !== "")
            change({ [key]: Number(event.target.value) });
        }}
      />
    </label>
  );
  const vector = (
    key: "bounds_xz_m" | "start_xz_m" | "goal_xz_m",
    labels: string[],
  ) => (
    <div className="scenario-vector">
      {labels.map((label, i) => (
        <label key={label}>
          {label}
          <input
            aria-label={label}
            type="number"
            step="0.05"
            value={config[key][i]}
            onChange={(event) => {
              const values = [...config[key]];
              values[i] = Number(event.target.value);
              change({ [key]: values });
            }}
          />
        </label>
      ))}
    </div>
  );
  const save = async () => {
    setBusy(true);
    setError("");
    try {
      const points = waypoints.trim()
        ? waypoints.split(";").map((pair) => {
            const values = pair.split(",").map(Number);
            if (values.length !== 2 || !values.every(Number.isFinite))
              throw new Error("Waypoints use x,z; x,z in meters");
            return values as [number, number];
          })
        : [];
      const value = { ...config, waypoints_xz_m: points };
      const scenarios = (scene.scenarios || []).filter(
        (s) => s.scenario_id !== value.scenario_id,
      );
      const saved = await api.saveScenarios(scene, [...scenarios, value]);
      onScene(saved);
      setConfig(value);
      setChanged(false);
    } catch (reason) {
      setError(String(reason));
    } finally {
      setBusy(false);
    }
  };
  const run = async () => {
    ++loadingGeneration.current;
    setBusy(true);
    setError("");
    try {
      const result = await api.runSimulation(scene, config.scenario_id);
      setRuns((values) => [...values, result]);
      await load(result);
    } catch (reason) {
      setError(String(reason));
    } finally {
      setBusy(false);
    }
  };
  const result = replay?.run.result_summary,
    step = replay?.result.trajectory[index];
  return (
    <section className="simulation-panel" aria-label="Navigation simulator">
      <h2>Deterministic occupancy navigation</h2>
      <p>
        Metric XZ map · circular robot · conservative cell inflation · unknown
        cells blocked.
      </p>
      <div className="preview-banner">
        SIMULATED REPLAY{" "}
        <span>
          Coarse map and declared floor assumptions. No real robot, safety or
          perception validation.
        </span>
      </div>
      {error && (
        <div className="message error" role="alert">
          {error}
        </div>
      )}
      {unsaved && (
        <p className="message error">
          Save or discard object edits before saving/running a scenario.
        </p>
      )}
      <details open>
        <summary>Scenario editor · all distances in meters</summary>
        <fieldset
          disabled={busy || unsaved || !editable}
          className="scenario-fields"
        >
          <label>
            Saved scenario
            <select
              aria-label="Saved scenario"
              value={config.scenario_id}
              onChange={(event) => {
                const value = scene.scenarios?.find(
                  (s) => s.scenario_id === event.target.value,
                );
                if (value) {
                  setConfig(value);
                  setWaypoints(
                    value.waypoints_xz_m.map((p) => p.join(",")).join("; "),
                  );
                  setChanged(false);
                }
              }}
            >
              <option value={config.scenario_id}>{config.name}</option>
              {(scene.scenarios || [])
                .filter((s) => s.scenario_id !== config.scenario_id)
                .map((s) => (
                  <option key={s.scenario_id} value={s.scenario_id}>
                    {s.name}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Scenario name
            <input
              aria-label="Scenario name"
              value={config.name}
              onChange={(event) => change({ name: event.target.value })}
            />
          </label>
          <label>
            Floor evidence
            <select
              aria-label="Floor evidence"
              value={config.floor_mode}
              onChange={(event) =>
                change({
                  floor_mode: event.target.value as Scenario["floor_mode"],
                })
              }
            >
              <option value="observed_tsdf">Observed TSDF floor support</option>
              <option value="declared_virtual_plane">
                Declared virtual plane · assumption
              </option>
            </select>
          </label>
          <label className="wide-field">
            Floor assumption note
            <textarea
              aria-label="Floor assumption note"
              value={config.floor_note}
              onChange={(event) => change({ floor_note: event.target.value })}
            />
          </label>
          <div className="wide-field">
            {vector("bounds_xz_m", [
              "Map X min",
              "Map Z min",
              "Map X max",
              "Map Z max",
            ])}
          </div>
          <div className="wide-field">
            {vector("start_xz_m", ["Start X", "Start Z"])}
            {vector("goal_xz_m", ["Goal X", "Goal Z"])}
          </div>
          {numeric("floor_y_m", "Floor Y")}
          {numeric("robot_radius_m", "Robot radius")}
          {numeric("robot_height_m", "Robot height")}
          {numeric("resolution_m", "Grid resolution")}
          {numeric("speed_m_s", "Robot speed m/s")}
          {numeric("timestep_s", "Timestep seconds")}
          <label className="wide-field">
            Optional waypoints x,z; x,z
            <input
              aria-label="Waypoints"
              value={waypoints}
              onChange={(event) => {
                setWaypoints(event.target.value);
                setChanged(true);
              }}
            />
          </label>
        </fieldset>
        <div className="report-downloads">
          <button
            onClick={() => void save()}
            disabled={busy || unsaved || !editable || !changed}
          >
            Save scenario revision
          </button>
          <button
            className="primary"
            onClick={() => void run()}
            disabled={busy || unsaved || !editable || changed}
          >
            {busy ? "Working…" : "Run navigation"}
          </button>
        </div>
      </details>
      {runs.length > 0 && (
        <label>
          Saved replay
          <select
            aria-label="Saved replay"
            value={replay?.run.run_id || ""}
            onChange={(event) => {
              const found = runs.find((r) => r.run_id === event.target.value);
              if (found)
                void load(found).catch((reason) => setError(String(reason)));
            }}
          >
            {runs.map((value) => (
              <option key={value.run_id} value={value.run_id}>
                {value.scenario.name} · v{value.scene_version} ·{" "}
                {value.result_summary.route_success
                  ? "goal reached"
                  : "no route"}
              </option>
            ))}
          </select>
        </label>
      )}
      {replay && result && (
        <>
          <div className="metric-grid">
            <div className="metric-card">
              <small>Route outcome</small>
              <strong>
                {result.route_success ? "Goal reached" : "Failed / blocked"}
              </strong>
            </div>
            <div className="metric-card">
              <small>Path length</small>
              <strong>{score(result.path_length_m)} m</strong>
            </div>
            <div className="metric-card">
              <small>Collisions during replay</small>
              <strong>{result.collisions}</strong>
            </div>
          </div>
          <p>
            {result.reason} · source revision {replay.run.scene_version} ·
            simulated time {score(result.elapsed_simulated_s)} s · travel{" "}
            {score(result.travel_distance_m)} m.
          </p>
          <p>
            {replay.run.floor_evidence === "declared_virtual_floor_assumption"
              ? "Declared virtual floor: free support is assumed for this simulator, not observed in the real scene."
              : "Only near-horizontal TSDF floor triangles support free space. Unknown floor cells are blocked."}{" "}
            Unknown map cells: {replay.run.unknown_cells}.
          </p>
          <div className="replay-controls">
            <button
              onClick={() => {
                if (index >= replay.result.trajectory.length - 1) setIndex(0);
                setPlaying((value) => !value);
              }}
              disabled={!replay.result.trajectory.length}
            >
              {playing ? "Pause replay" : "Play replay"}
            </button>
            <label>
              Replay position
              <input
                aria-label="Replay position"
                type="range"
                min="0"
                max={Math.max(0, replay.result.trajectory.length - 1)}
                value={index}
                onChange={(event) => {
                  setIndex(Number(event.target.value));
                  setPlaying(false);
                }}
              />
            </label>
            <span>{score(step?.time_s)} simulated s</span>
          </div>
          <div className="simulation-viewport">
            {unavailable ? (
              <p>{unavailable} The 2D route map below remains available.</p>
            ) : (
              <Suspense fallback={<span>Loading replay viewer…</span>}>
                <Viewer
                  scene={replay.scene}
                  objects={replay.scene.objects}
                  selected={null}
                  showCollision={false}
                  mode="translate"
                  onSelect={() => {}}
                  onChange={() => {}}
                  onUnavailable={setUnavailable}
                  cameraIndex={0}
                  onSpawnPosition={() => {}}
                  editable={false}
                  replay={replay}
                  replayIndex={index}
                />
              </Suspense>
            )}
          </div>
          <details>
            <summary>2D route map and run evidence</summary>
            <img
              className="route-map"
              src={simulationAsset(
                scene.scene_id,
                replay.run.run_id,
                "route.png",
              )}
              alt="Saved occupancy route map"
            />
            <p>
              Green: floor support; orange: surface/proxy obstacle; brown:
              inflated blocked cells; dark: unknown. Cyan start, pink goal, pale
              route. Floor evidence is declared above.
            </p>
            <div className="report-downloads">
              {[
                "simulation.json",
                "scenario.json",
                "result.json",
                "occupancy.json",
              ].map((name) => (
                <a
                  key={name}
                  href={simulationAsset(
                    scene.scene_id,
                    replay.run.run_id,
                    name,
                  )}
                  target="_blank"
                  rel="noreferrer"
                >
                  {name} ↗
                </a>
              ))}
            </div>
            <ul>
              {replay.run.limitations.map((value) => (
                <li key={value}>{value}</li>
              ))}
            </ul>
          </details>
        </>
      )}
    </section>
  );
}
