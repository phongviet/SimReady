import { useEffect, useState } from "react";
import { api } from "./api";

export type Statistic = {
  mean: number | null;
  sample_sd: number | null;
  n: number;
  values: number[];
};
export type ResearchStudy = {
  study_id: string;
  package: {
    summary_snapshot: boolean;
    scope: string;
    files_sha256: Record<string, string>;
  };
  summary: {
    scope: string;
    seeds: number[];
    run_count: number;
    methods: Record<string, Record<string, Statistic>>;
    paired_risk_minus_random: Record<string, Statistic>;
    calibration: {
      seed: number;
      coefficients: number[];
      check_mae: number;
      check_spearman: { rho: number | null };
    }[];
    runs: {
      run: string;
      train_frames: number;
      test_frames: number;
      means: Record<string, number | null>;
      detection_totals: Record<string, number>;
      artifact_sha256: string;
    }[];
    semantic_audit: {
      verdict?: string;
      review_independence?: string;
      acceptance_status?: string;
    };
    source: { commit: string };
    limitations: string[];
    selections: Record<string, string[]>;
  };
};

export function researchAsset(id: string, name: string) {
  return `/api/v1/research/studies/${encodeURIComponent(id)}/assets/${name.split("/").map(encodeURIComponent).join("/")}`;
}
const number = (value: number | null | undefined) =>
  value == null ? "N/A" : value.toFixed(5);

export function ResearchDashboard() {
  const [studies, setStudies] = useState<ResearchStudy[]>([]);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    api
      .studies()
      .then((values) => {
        if (!active) return;
        setStudies(values);
        setSelected(values[values.length - 1]?.study_id || "");
      })
      .catch((reason) => {
        if (active) setError(String(reason));
      });
    return () => {
      active = false;
    };
  }, []);
  const study = studies.find((value) => value.study_id === selected);
  const summary = study?.summary;
  const asset = (name: string) => researchAsset(selected, name);
  return (
    <section
      className="evaluation-explorer research-dashboard"
      aria-label="Research dashboard"
    >
      <p className="eyebrow">MEASURED RESEARCH · TUM DESK CASE STUDY</p>
      <h2>Fixed-budget recapture study</h2>
      <p>
        This study is independent of the selected editor scene. Detector
        agreement is not detection accuracy.
      </p>
      {error && <p role="alert">{error}</p>}
      {!studies.length && !error && (
        <p>
          No measured studies registered. Run the documented research workflow,
          then register its analysis.
        </p>
      )}
      {study && summary && (
        <>
          <label>
            Measured study{" "}
            <select
              aria-label="Measured study"
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
            >
              {studies.map((value) => (
                <option key={value.study_id}>{value.study_id}</option>
              ))}
            </select>
          </label>
          <p>
            {summary.scope} {summary.run_count} models · seeds{" "}
            {summary.seeds.join(", ")}.
          </p>
          <p className="preview-banner">
            {study.package.summary_snapshot
              ? "PRECOMPUTED MEASURED SNAPSHOT"
              : "MEASURED BENCHMARK PACKAGE"}{" "}
            · {study.package.scope}
          </p>
          <p>
            <strong>
              Risk minus random LPIPS:{" "}
              {number(summary.paired_risk_minus_random.lpips.mean)} ±{" "}
              {number(summary.paired_risk_minus_random.lpips.sample_sd)}
            </strong>{" "}
            (sample SD; lower is better).
          </p>
          <p>
            {(summary.paired_risk_minus_random.lpips.mean ?? 0) > 0
              ? "Risk acquisition did not improve on random in this capture."
              : "Observed differences apply only to this capture."}{" "}
            No population significance or general superiority claim.
          </p>
          <div className="research-table">
            <table>
              <caption>Three seed-level means; ± sample SD</caption>
              <thead>
                <tr>
                  <th>Method</th>
                  <th>LPIPS ↓</th>
                  <th>SSIM ↑</th>
                  <th>Depth MAE (m) ↓</th>
                  <th>Depth completeness ↑</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(summary.methods).map(([method, metrics]) => (
                  <tr key={method}>
                    <th>{method}</th>
                    {["lpips", "ssim", "depth_mae_m", "depth_completeness"].map(
                      (key) => (
                        <td key={key}>
                          {number(metrics[key].mean)} ±{" "}
                          {number(metrics[key].sample_sd)}
                        </td>
                      ),
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <img
            className="research-figure"
            src={asset("study-figures.svg")}
            alt="Measured recapture comparisons, discrepancy, pose bins and validation checks"
          />
          <details>
            <summary>Raw run values and source hashes</summary>
            <div className="research-table">
              <table>
                <thead>
                  <tr>
                    <th>Run</th>
                    <th>Train / test</th>
                    <th>LPIPS</th>
                    <th>Real / rendered / matched predictions</th>
                    <th>Model SHA-256</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.runs.map((run) => (
                    <tr key={run.run}>
                      <th>{run.run}</th>
                      <td>
                        {run.train_frames} / {run.test_frames}
                      </td>
                      <td>{number(run.means.lpips)}</td>
                      <td>
                        {run.detection_totals.real_count} /{" "}
                        {run.detection_totals.rendered_count} /{" "}
                        {run.detection_totals.matched_count}
                      </td>
                      <td>
                        <code>{run.artifact_sha256}</code>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
          <details>
            <summary>Validation calibration and sealed acquisitions</summary>
            {summary.calibration.map((row) => (
              <p key={row.seed}>
                Seed {row.seed}: check MAE {number(row.check_mae)}, Spearman{" "}
                {number(row.check_spearman.rho)}; coefficients (intercept,
                distance, rotation, alpha hole):{" "}
                {row.coefficients.map(number).join(", ")}.
              </p>
            ))}
            <p>
              Only the first eight validation views fit the rule. The remaining
              eight check it. No test data fits this rule.
            </p>
            {Object.entries(summary.selections).map(([key, ids]) => (
              <p key={key}>
                <strong>{key}</strong>: {ids.join(", ")}
              </p>
            ))}
          </details>
          <h3>Post-hoc failure comparisons</h3>
          <p>
            Three largest risk-minus-random LPIPS losses at seed 42. Selected
            after measurement for diagnosis; never used for training.
          </p>
          <img
            className="research-figure"
            src={asset("failure-comparisons.png")}
            alt="Real TUM reference and four methods on three diagnostic views"
          />
          <p>TUM RGB-D benchmark · Sturm et al., IROS 2012 · CC BY 4.0.</p>
          <p>
            Fresh audit: {summary.semantic_audit.verdict ?? "unavailable"} ·{" "}
            {summary.semantic_audit.review_independence ?? "unavailable"} ·{" "}
            {summary.semantic_audit.acceptance_status ?? "unavailable"}.
            Training source <code>{summary.source.commit}</code>.
          </p>
          <div className="research-downloads">
            {[
              "report.html",
              "report.md",
              "metrics_summary.json",
              "per_view.csv",
              "runs.csv",
              "experiment-audit.json",
              "config.yaml",
              "dataset_and_split_hash.json",
            ].map((name) => (
              <a key={name} href={asset(name)} target="_blank" rel="noreferrer">
                {name}
              </a>
            ))}
            {!study.package.summary_snapshot &&
              ["predictions_real.jsonl", "predictions_rendered.jsonl"].map(
                (name) => (
                  <a key={name} href={asset(name)}>
                    {name}
                  </a>
                ),
              )}
          </div>
          <details>
            <summary>Study limitations and unverified claims</summary>
            <ul>
              {summary.limitations.map((value) => (
                <li key={value}>{value}</li>
              ))}
            </ul>
          </details>
        </>
      )}
    </section>
  );
}
