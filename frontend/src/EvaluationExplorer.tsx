import { useEffect, useState } from "react";
import { api } from "./api";
import type { SceneState } from "./types";
import {
  rankViews,
  reportAsset,
  score,
  type EvaluationReport,
  type EvaluationView,
  type EvaluationJob,
} from "./evaluation";

export function EvaluationExplorer({ scene }: { scene: SceneState }) {
  const [reports, setReports] = useState<EvaluationReport[]>([]);
  const [run, setRun] = useState("");
  const [views, setViews] = useState<EvaluationView[]>([]);
  const [selected, setSelected] = useState("");
  const [sort, setSort] = useState("lpips");
  const [overlays, setOverlays] = useState(true);
  const [job, setJob] = useState<EvaluationJob | null>(null);
  const [error, setError] = useState("");
  const [launching, setLaunching] = useState(false);
  const sceneId = scene.scene_id;
  const load = () =>
    api.reports(sceneId).then((values) => {
      setReports(values);
      if (values.length) setRun(values[values.length - 1].run_id);
    });
  useEffect(() => {
    let active = true;
    api
      .jobs(sceneId)
      .then((values) => {
        if (active && values.length) setJob(values[values.length - 1]);
      })
      .catch((reason) => {
        if (active) setError(String(reason));
      });
    api
      .reports(sceneId)
      .then((values) => {
        if (!active) return;
        setReports(values);
        setRun(values.length ? values[values.length - 1].run_id : "");
      })
      .catch((reason) => {
        if (active) setError(String(reason));
      });
    return () => {
      active = false;
    };
  }, [sceneId]);
  useEffect(() => {
    let active = true;
    setViews([]);
    setSelected("");
    if (run)
      api
        .reportViews(sceneId, run)
        .then((values) => {
          if (!active) return;
          setViews(values);
          setSelected(rankViews(values, "lpips")[0]?.frame_id || "");
        })
        .catch((reason) => {
          if (active) setError(String(reason));
        });
    return () => {
      active = false;
    };
  }, [sceneId, run]);
  useEffect(() => {
    if (!job || job.status === "failed" || job.status === "succeeded") return;
    const timer = setTimeout(() => {
      api
        .job(job.job_id)
        .then((value) => {
          setJob(value);
          if (value.status === "succeeded")
            void load().catch((reason) => setError(String(reason)));
        })
        .catch((reason) => setError(String(reason)));
    }, 1500);
    return () => clearTimeout(timer);
  }, [job]);
  const report = reports.find((value) => value.run_id === run);
  const ordered = rankViews(views, sort);
  const view = views.find((value) => value.frame_id === selected);
  const asset = (name: string) => reportAsset(sceneId, run, name);
  const evaluate = async () => {
    setError("");
    setLaunching(true);
    try {
      setJob(await api.evaluate(scene));
    } catch (reason) {
      setError(String(reason));
    } finally {
      setLaunching(false);
    }
  };
  const totals = report?.summary.detection_totals;
  return (
    <section className="evaluation-explorer" aria-label="Evaluation explorer">
      <div className="evaluation-intro">
        <div>
          <h2>Frozen-view evaluation</h2>
          <p>
            Camera-aligned base reconstruction · inserted proxies are excluded.
          </p>
        </div>
        <button
          className="primary"
          onClick={() => void evaluate()}
          disabled={
            launching || job?.status === "queued" || job?.status === "running"
          }
        >
          {launching ? "Submitting…" : "Evaluate frozen test views"}
        </button>
      </div>
      <p className="field-note">
        The fixed detector measures prediction consistency. Object detection
        accuracy and simulation readiness require separate evidence.
      </p>
      {error && (
        <div role="alert" className="message error">
          {error}
        </div>
      )}
      {job && (
        <div className="evaluation-job" role="status">
          <strong>Evaluation {job.status}</strong> · revision{" "}
          {job.scene_version}
          {job.error && <p>{job.error}</p>}
          <details>
            <summary>Worker log</summary>
            <pre>{job.log_tail || "Waiting for worker…"}</pre>
          </details>
        </div>
      )}
      {!reports.length ? (
        <p className="empty-copy">
          No measured report registered for this scene. Evaluation needs the
          local GPU worker and canonical source observations.
        </p>
      ) : (
        <>
          <label>
            Evaluation run{" "}
            <select
              aria-label="Evaluation run"
              value={run}
              onChange={(event) => setRun(event.target.value)}
            >
              {reports.map((value) => (
                <option key={value.run_id} value={value.run_id}>
                  {value.run_id} · v{value.scene_version} ·{" "}
                  {value.summary.split}
                </option>
              ))}
            </select>
          </label>
          {report && (
            <>
              <div className="metric-grid">
                {[
                  ["PSNR", "psnr_db", "dB"],
                  ["SSIM", "ssim", ""],
                  ["LPIPS · Squeeze", "lpips", ""],
                  ["Depth MAE", "depth_mae_m", "m"],
                  ["Depth RMSE", "depth_rmse_m", "m"],
                  ["Depth support", "depth_completeness", "fraction"],
                ].map(([label, key, unit]) => (
                  <div className="metric-card" key={key}>
                    <small>{label} · view mean</small>
                    <strong>
                      {score(report.summary.means[key])} <em>{unit}</em>
                    </strong>
                  </div>
                ))}
              </div>
              <p>
                {report.summary.view_count} frozen {report.summary.split} views
                · {report.summary.dataset_kind} · attached to revision{" "}
                {report.scene_version}. {report.summary.scope}
              </p>
              <div className="report-downloads">
                {[
                  ["report.html", "HTML report"],
                  ["report.md", "Markdown"],
                  ["per_view.csv", "Per-view CSV"],
                  ["summary.json", "Summary JSON"],
                  ["predictions.json", "Raw predictions"],
                  ["inputs.json", "Input provenance"],
                ].map(([file, label]) => (
                  <a
                    href={asset(file)}
                    key={file}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {label} ↗
                  </a>
                ))}
              </div>
              <div className="detector-totals">
                <span>
                  Detections · real <b>{totals?.real_count}</b> / rendered{" "}
                  <b>{totals?.rendered_count}</b>
                </span>
                <span>
                  Matched <b>{totals?.matched_count}</b>
                </span>
                <span>
                  Disappeared <b>{totals?.disappeared_count}</b> · appeared{" "}
                  <b>{totals?.appeared_count}</b>
                </span>
              </div>
              <div className="failure-controls">
                <label>
                  Sort failure views{" "}
                  <select
                    aria-label="Sort failure views"
                    value={sort}
                    onChange={(event) => setSort(event.target.value)}
                  >
                    <option value="lpips">LPIPS · highest first</option>
                    <option value="detector">
                      Unmatched detections · highest first
                    </option>
                    <option value="depth_mae_m">
                      Depth MAE · highest first
                    </option>
                  </select>
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={overlays}
                    onChange={(event) => setOverlays(event.target.checked)}
                  />{" "}
                  Detector overlays
                </label>
              </div>
              <div className="failure-strip">
                {ordered.map((value) => (
                  <button
                    key={value.frame_id}
                    className={value.frame_id === selected ? "selected" : ""}
                    onClick={() => setSelected(value.frame_id)}
                  >
                    {value.frame_id}
                    <small>LPIPS {score(value.metrics.lpips)}</small>
                  </button>
                ))}
              </div>
              {view && (
                <div className="view-diagnostics">
                  <h3>{view.frame_id} · aligned comparison</h3>
                  <div className="comparison-images">
                    {[
                      [overlays ? "real_overlay" : "real", "Real RGB"],
                      [
                        overlays ? "rendered_overlay" : "rendered",
                        "Rendered RGB",
                      ],
                      ["residual", "RGB residual"],
                    ].map(([key, title]) => (
                      <figure key={title}>
                        <img
                          src={asset(view.assets[key])}
                          alt={`${view.frame_id} ${title}`}
                        />
                        <figcaption>
                          {title}
                          {key === "residual" ? " · blue 0 → yellow/red 1" : ""}
                        </figcaption>
                      </figure>
                    ))}
                  </div>
                  <div className="comparison-images depth-comparison">
                    <figure>
                      <img
                        src={asset(view.assets.depth_error)}
                        alt="Depth discrepancy"
                      />
                      <figcaption>
                        Depth error · blue 0 → yellow/red ≥1 m; black invalid
                      </figcaption>
                    </figure>
                    <figure>
                      <img
                        src={asset(view.assets.depth_mask)}
                        alt="Evaluated depth mask"
                      />
                      <figcaption>
                        White: evaluated GT + rendered depth support
                      </figcaption>
                    </figure>
                    <div>
                      <p>
                        PSNR {score(view.metrics.psnr_db)} dB · SSIM{" "}
                        {score(view.metrics.ssim)}
                      </p>
                      <p>
                        LPIPS {score(view.metrics.lpips)} · depth MAE{" "}
                        {score(view.metrics.depth_mae_m)} m
                      </p>
                      <p>
                        Matched {view.detection.matched_count} · disappeared{" "}
                        {view.detection.disappeared_count} · appeared{" "}
                        {view.detection.appeared_count}
                      </p>
                      <p>
                        Class mismatch candidates{" "}
                        {view.detection.class_mismatch_candidates.length} ·
                        matched IoU {score(view.detection.mean_matched_iou)}
                      </p>
                      {view.detection.empty_both && (
                        <p>
                          Both predictions empty. This provides no positive
                          evidence of task quality.
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}
              <details>
                <summary>Measured LPIPS distribution</summary>
                <img
                  className="distribution"
                  src={asset("lpips-distribution.svg")}
                  alt="LPIPS by frozen view"
                />
              </details>
              <details>
                <summary>Per-class prediction counts</summary>
                <table>
                  <thead>
                    <tr>
                      <th>COCO class</th>
                      <th>Real</th>
                      <th>Rendered</th>
                      <th>Matched</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(report.summary.per_class).map(
                      ([label, count]) => (
                        <tr key={label}>
                          <td>
                            {
                              report.summary.environment.categories[
                                Number(label)
                              ]
                            }
                          </td>
                          <td>{count.real}</td>
                          <td>{count.rendered}</td>
                          <td>{count.matched}</td>
                        </tr>
                      ),
                    )}
                  </tbody>
                </table>
              </details>
              <details>
                <summary>Protocol, provenance and limits</summary>
                <p>
                  Split SHA-256: <code>{report.summary.split_sha256}</code>
                </p>
                <p>
                  Report SHA-256: <code>{report.evaluation_sha256}</code>
                </p>
                <p>
                  {report.summary.source.name} · {report.summary.source.license}
                  . {report.summary.source.attribution}
                </p>
                <ul>
                  {report.summary.limitations.map((value) => (
                    <li key={value}>{value}</li>
                  ))}
                </ul>
              </details>
            </>
          )}
        </>
      )}
    </section>
  );
}
