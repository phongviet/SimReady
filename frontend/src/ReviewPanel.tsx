import { useEffect, useState } from "react";
import { api } from "./api";
import type { Principal } from "./auth";
import type { SceneState } from "./types";
import type { EvaluationReport } from "./evaluation";
import { reportAsset, score } from "./evaluation";
import type { SimulationRun } from "./simulation";
import type { AuditEvent, Readiness, ReviewScope } from "./review";

export function ReviewPanel({
  scene,
  user,
  unsaved,
  onScene,
}: {
  scene: SceneState;
  user: Principal | null;
  unsaved: boolean;
  onScene: (scene: SceneState) => void;
}) {
  const [qa, setQa] = useState<Readiness | null>(null),
    [reports, setReports] = useState<EvaluationReport[]>([]),
    [runs, setRuns] = useState<SimulationRun[]>([]);
  const [events, setEvents] = useState<AuditEvent[]>([]),
    [history, setHistory] = useState<
      { version: number; status: string; updated_at: string }[]
    >([]);
  const [reportId, setReportId] = useState(""),
    [runId, setRunId] = useState("");
  const [taskName, setTaskName] = useState(
      "Deterministic occupancy route regression",
    ),
    [expected, setExpected] =
      useState<ReviewScope["expected_navigation"]>("goal_reached");
  const [cameras, setCameras] = useState<string[]>([]),
    [ack, setAck] = useState(false),
    [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [exportVersion, setExportVersion] = useState(0),
    [exported, setExported] = useState<{
      export_id: string;
      sha256: string;
      bytes: number;
      approved_version: number;
    } | null>(null);
  useEffect(() => {
    let active = true;
    setError("");
    setAck(false);
    setExported(null);
    Promise.all([
      api.readiness(scene.scene_id),
      api.reports(scene.scene_id),
      api.simulations(scene.scene_id),
      api.audit(scene.scene_id),
      api.history(scene.scene_id),
    ])
      .then(([ready, values, simulations, audit, versions]) => {
        if (!active) return;
        setQa(ready);
        setReports(values);
        setEvents(audit);
        setHistory(versions);
        setCameras(ready.coverage.views.map((value) => value.frame_id));
        setReportId(
          ready.evaluation?.run_id || values[values.length - 1]?.run_id || "",
        );
        const source = scene.review?.source_version || scene.version;
        const current = simulations.filter(
          (value) => value.scene_version === source,
        );
        setRuns(current);
        setRunId(
          ready.simulation?.run_id || current[current.length - 1]?.run_id || "",
        );
        const selected =
          current.find((value) => value.run_id === ready.simulation?.run_id) ||
          current[current.length - 1];
        if (selected)
          setExpected(
            selected.result_summary.route_success ? "goal_reached" : "no_route",
          );
        const approved = versions.filter(
          (value) => value.status === "approved",
        );
        setExportVersion(approved[approved.length - 1]?.version || 0);
      })
      .catch((value) => {
        if (active) setError(String(value));
      });
    return () => {
      active = false;
    };
  }, [scene.scene_id, scene.version]);
  const run = runs.find((value) => value.run_id === runId);
  const report = reports.find((value) => value.run_id === reportId);
  const perform = async (action: () => Promise<SceneState>) => {
    setBusy(true);
    setError("");
    try {
      onScene(await action());
      setReason("");
    } catch (value) {
      setError(String(value));
    } finally {
      setBusy(false);
    }
  };
  const submit = () => {
    if (!run) return;
    const scope: ReviewScope = {
      task: "occupancy_navigation_regression",
      name: taskName,
      camera_ids: cameras,
      bounds_xz_m: run.scenario.bounds_xz_m,
      expected_navigation: expected,
      limitations_acknowledged: true,
    };
    return perform(() =>
      api.submit(scene, {
        report_run_id: reportId,
        simulation_run_id: runId,
        scope,
      }),
    );
  };
  const buildExport = async () => {
    setBusy(true);
    setError("");
    try {
      setExported(await api.exportScene(scene.scene_id, exportVersion));
    } catch (value) {
      setError(String(value));
    } finally {
      setBusy(false);
    }
  };
  const canReview =
    user?.role === "reviewer" &&
    scene.status === "submitted" &&
    user.user_id !== scene.review?.submitted_by.user_id;
  return (
    <section className="review-panel" aria-label="Readiness and scoped review">
      <h2>Readiness evidence & scoped review</h2>
      <p>
        Approval applies to the named local experiment, measured camera IDs, map
        bounds and captured revision. It does not certify physical safety or
        detection accuracy.
      </p>
      {error && (
        <div className="message error" role="alert">
          {error}
        </div>
      )}
      {qa && (
        <>
          <div className="metric-grid">
            <div className="metric-card">
              <small>Evidence outcome</small>
              <strong>{qa.outcome.replaceAll("_", " ")}</strong>
            </div>
            <div className="metric-card">
              <small>Reference views tested</small>
              <strong>{qa.coverage.tested_reference_views}</strong>
            </div>
            <div className="metric-card">
              <small>Source revision</small>
              <strong>v{qa.source_version}</strong>
            </div>
          </div>
          <ul className="qa-flags">
            {qa.flags.map((value) => (
              <li key={value}>{value}</li>
            ))}
          </ul>
          <div className="qa-components">
            <p>
              Geometry: {qa.geometry.vertices.toLocaleString()} vertices ·{" "}
              {qa.geometry.triangles.toLocaleString()} triangles ·{" "}
              {qa.geometry.boundary_edges} boundary edges ·{" "}
              {qa.geometry.nonmanifold_edges} nonmanifold edges. Coarse observed
              surface; no mesh accuracy computed.
            </p>
            <p>
              Perception predictions: real {qa.perception?.real_count ?? "N/A"}{" "}
              / rendered {qa.perception?.rendered_count ?? "N/A"} / matched{" "}
              {qa.perception?.matched_count ?? "N/A"}. Agreement is not
              accuracy.
            </p>
            <p>
              Navigation: support {qa.simulation?.floor_support_cells ?? "N/A"}{" "}
              cells · unknown {qa.simulation?.unknown_cells ?? "N/A"} cells.
              Camera coverage does not establish free volume.
            </p>
          </div>
          <details>
            <summary>Measured camera coverage and unknowns</summary>
            <p>
              {qa.coverage.training_cameras} training cameras. Free views:{" "}
              {qa.coverage.unobserved_free_views}. Pose classifications use
              uncalibrated .5m / 30° heuristics.
            </p>
            <table>
              <thead>
                <tr>
                  <th>Reference</th>
                  <th>Nearest train m</th>
                  <th>Rotation °</th>
                  <th>Classification</th>
                  <th>Depth support</th>
                </tr>
              </thead>
              <tbody>
                {qa.coverage.views.map((value) => (
                  <tr key={value.frame_id}>
                    <td>{value.frame_id}</td>
                    <td>{score(value.distance_m)}</td>
                    <td>{score(value.rotation_deg, 1)}</td>
                    <td>{value.classification.replaceAll("_", " ")}</td>
                    <td>{score(value.depth_completeness)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
          <details>
            <summary>Limitations and full QA JSON</summary>
            <ul>
              {qa.limitations.map((value, index) => (
                <li key={index}>{value}</li>
              ))}
            </ul>
            <a
              href={`/api/v1/scenes/${encodeURIComponent(scene.scene_id)}/readiness`}
              target="_blank"
              rel="noreferrer"
            >
              Readiness JSON ↗
            </a>
          </details>
        </>
      )}
      <h3>Submit a captured draft</h3>
      <fieldset
        disabled={
          busy ||
          unsaved ||
          user?.role !== "builder" ||
          scene.status !== "draft"
        }
        className="review-fields"
      >
        <label>
          Named experiment
          <input
            aria-label="Named experiment"
            value={taskName}
            onChange={(event) => setTaskName(event.target.value)}
          />
        </label>
        <label>
          Base evaluation
          <select
            aria-label="Base evaluation"
            value={reportId}
            onChange={(event) => setReportId(event.target.value)}
          >
            {reports.map((value) => (
              <option key={value.run_id} value={value.run_id}>
                {value.run_id} · base report v{value.scene_version}
              </option>
            ))}
          </select>
        </label>
        <label>
          Exact revision navigation
          <select
            aria-label="Exact revision navigation"
            value={runId}
            onChange={(event) => {
              setRunId(event.target.value);
              const value = runs.find((v) => v.run_id === event.target.value);
              if (value)
                setExpected(
                  value.result_summary.route_success
                    ? "goal_reached"
                    : "no_route",
                );
            }}
          >
            {runs.map((value) => (
              <option key={value.run_id} value={value.run_id}>
                {value.scenario.name} · v{value.scene_version} ·{" "}
                {value.result_summary.reason}
              </option>
            ))}
          </select>
        </label>
        <label>
          Expected navigation
          <select
            aria-label="Expected navigation"
            value={expected}
            onChange={(event) =>
              setExpected(
                event.target.value as ReviewScope["expected_navigation"],
              )
            }
          >
            <option value="goal_reached">Goal reached</option>
            <option value="no_route">No route / obstruction rejection</option>
          </select>
        </label>
        <p>
          Scoped map bounds X/Z:{" "}
          {run?.scenario.bounds_xz_m.join(", ") ||
            "Run navigation for this revision first."}
        </p>
        <div className="camera-scope">
          Measured camera scope
          {qa?.coverage.views.map((value) => (
            <label key={value.frame_id}>
              <input
                type="checkbox"
                checked={cameras.includes(value.frame_id)}
                onChange={(event) =>
                  setCameras((ids) =>
                    event.target.checked
                      ? [...ids, value.frame_id]
                      : ids.filter((id) => id !== value.frame_id),
                  )
                }
              />
              {value.frame_id}
            </label>
          ))}
        </div>
        <label>
          <input
            aria-label="Acknowledge measured limits"
            type="checkbox"
            checked={ack}
            onChange={(event) => setAck(event.target.checked)}
          />{" "}
          I read the evidence limits; this is a scoped local regression, not a
          safety or accuracy certificate.
        </label>
        <button
          className="primary"
          onClick={() => void submit()}
          disabled={
            !ack || !run || !report || !cameras.length || taskName.length < 5
          }
        >
          Submit for independent review
        </button>
      </fieldset>
      {unsaved && <p>Save/discard object edits before submitting evidence.</p>}
      {report && (
        <a
          href={reportAsset(scene.scene_id, report.run_id, "report.html")}
          target="_blank"
          rel="noreferrer"
        >
          Inspect selected measured report ↗
        </a>
      )}
      {scene.review && (
        <div className="captured-review">
          <h3>Captured review · source v{scene.review.source_version}</h3>
          <p>
            <strong>{scene.review.scope.name}</strong> ·{" "}
            {scene.review.scope.task} · expects{" "}
            {scene.review.scope.expected_navigation.replaceAll("_", " ")}
          </p>
          <p>
            Builder: {scene.review.submitted_by.display_name}. Camera IDs:{" "}
            {scene.review.scope.camera_ids.join(", ")}. Bounds:{" "}
            {scene.review.scope.bounds_xz_m.join(", ")}.
          </p>
          {scene.review.reason && (
            <p>
              Decision: {scene.review.reason} ·{" "}
              {scene.review.decided_by?.display_name}
            </p>
          )}
          <a
            href={`#audit-${scene.review.approval_event_id || scene.review.submission_event_id}`}
          >
            Inspect recorded decision / submission ↓
          </a>
        </div>
      )}
      <fieldset disabled={busy || !canReview} className="review-fields">
        <label>
          Reviewer justification
          <textarea
            aria-label="Reviewer justification"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </label>
        <div className="report-downloads">
          <button
            className="primary"
            disabled={reason.trim().length < 10}
            onClick={() =>
              void perform(() => api.review(scene, "approve", reason))
            }
          >
            Approve scoped experiment
          </button>
          <button
            disabled={reason.trim().length < 10}
            onClick={() =>
              void perform(() => api.review(scene, "reject", reason))
            }
          >
            Reject submission
          </button>
        </div>
      </fieldset>
      <p>
        A separate server-assigned Reviewer account is required; a submitter
        cannot review their own submission after a role change.
      </p>
      <h3>Reviewed export</h3>
      <label>
        Approved revision
        <select
          aria-label="Approved revision"
          value={exportVersion}
          onChange={(event) => setExportVersion(Number(event.target.value))}
        >
          {!exportVersion && <option value={0}>No approved revision</option>}
          {history
            .filter((v) => v.status === "approved")
            .map((value) => (
              <option key={value.version} value={value.version}>
                v{value.version} · approved
              </option>
            ))}
        </select>
      </label>
      <button
        disabled={!user || !exportVersion || busy}
        onClick={() => void buildExport()}
      >
        Build reviewed export
      </button>
      {exported && (
        <p role="status">
          <a
            href={`/api/v1/scenes/${encodeURIComponent(scene.scene_id)}/exports/${exported.export_id}`}
          >
            Download reviewed ZIP · v{exported.approved_version}
          </a>{" "}
          · {(exported.bytes / 1e6).toFixed(2)} MB · SHA-256{" "}
          <code>{exported.sha256}</code>
        </p>
      )}
      <details>
        <summary>Immutable scene history</summary>
        <ul>
          {history.map((value) => (
            <li key={value.version}>
              <a
                href={`/api/v1/scenes/${encodeURIComponent(scene.scene_id)}/versions/${value.version}`}
                target="_blank"
                rel="noreferrer"
              >
                v{value.version} · {value.status}
              </a>{" "}
              · {value.updated_at}
            </li>
          ))}
        </ul>
      </details>
      <h3>Append-only review audit</h3>
      <div className="audit-list">
        {events.length ? (
          events.map((event) => (
            <article key={event.event_id} id={`audit-${event.event_id}`}>
              <strong>
                {event.action} · v{event.before_version} → v
                {event.after_version}
              </strong>
              <p>
                {event.actor.display_name} ({event.actor.role}) ·{" "}
                {event.timestamp}
              </p>
              {event.details.reason && <p>{event.details.reason}</p>}
              <small>
                Event {event.event_id} · SHA-256 {event.sha256}
              </small>
            </article>
          ))
        ) : (
          <p>No submission or decision recorded.</p>
        )}
      </div>
    </section>
  );
}
