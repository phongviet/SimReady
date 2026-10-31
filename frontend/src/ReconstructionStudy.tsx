import { useEffect, useState } from "react";

type Statistic = { mean: number | null; sample_sd: number | null };
type Snapshot = {
  study_id: string;
  exported_utc: string;
  source_commit: string;
  protocol_sha256: string;
  policy: string;
  completed_training: number;
  planned_training: number;
  completed_evaluations: number;
  planned_evaluations: number;
  runs: {
    study: string;
    run: string;
    split: string;
    views: number;
    iterations: number;
    config_sha256: string;
    training: string;
    evaluations: { step: number; status: string }[];
  }[];
  results: null | {
    aggregates: {
      study: string;
      policy: string;
      step: number;
      seeds: number;
      statistics: Record<string, Statistic>;
    }[];
    ground_truth_detection: string;
  };
};
const value = (stat?: Statistic, divisor = 1) =>
  stat?.mean == null
    ? "Undefined"
    : `${(stat.mean / divisor).toFixed(3)}${stat.sample_sd == null ? "" : ` ± ${(stat.sample_sd / divisor).toFixed(3)}`}`;

export function ReconstructionStudy() {
  const [data, setData] = useState<Snapshot | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [scope, setScope] = useState("");
  const selectedStudy = scope || data?.runs[0]?.study;
  useEffect(() => {
    const controller = new AbortController();
    async function update() {
      try {
        const response = await fetch("/research/reconstruction.json", {
          cache: "no-store",
          signal: controller.signal,
        });
        if (
          !response.ok ||
          !response.headers.get("content-type")?.includes("json")
        )
          throw new Error(
            "No reconstruction snapshot published. Run the documented presentation exporter after creating a frozen study.",
          );
        const next = await response.json();
        if (!Array.isArray(next.runs) || !next.source_commit)
          throw new Error("Invalid study snapshot.");
        setData(next);
        setError("");
      } catch (reason) {
        if (!controller.signal.aborted)
          setError(String(reason instanceof Error ? reason.message : reason));
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void update();
    const timer = window.setInterval(() => {
      if (!document.hidden) void update();
    }, 5000);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, []);
  return (
    <section
      className="evaluation-explorer reconstruction-study"
      aria-label="Reconstruction study"
    >
      <p className="eyebrow">FROZEN RECONSTRUCTION STUDY</p>
      <h2>Cross-sequence quality & refinement</h2>
      <p>
        Two additional TUM recordings and a controlled densification comparison.
        Fr1 room shares the original office; this is not an unseen-site
        benchmark.
      </p>
      {loading && <p role="status">Loading experiment snapshot…</p>}
      {error && <p role="alert">{error}</p>}
      {data && (
        <>
          <div className="study-progress" aria-label="Measured job progress">
            <label>
              Trained{" "}
              <strong>
                {data.completed_training} / {data.planned_training}
              </strong>
              <progress
                value={data.completed_training}
                max={data.planned_training}
              />
            </label>
            <label>
              Evaluated{" "}
              <strong>
                {data.completed_evaluations} / {data.planned_evaluations}
              </strong>
              <progress
                value={data.completed_evaluations}
                max={data.planned_evaluations}
              />
            </label>
          </div>
          <p>
            Snapshot{" "}
            <time dateTime={data.exported_utc}>
              {new Date(data.exported_utc).toLocaleString()}
            </time>
            . Ledger status; this is not a live GPU monitor.
          </p>
          <label className="study-filter">
            Study{" "}
            <select
              name="reconstruction-study"
              aria-label="Reconstruction study filter"
              value={selectedStudy ?? ""}
              onChange={(event) => setScope(event.target.value)}
            >
              {Array.from(new Set(data.runs.map((row) => row.study))).map(
                (study) => (
                  <option key={study}>{study}</option>
                ),
              )}
            </select>
          </label>
          {!data.results && (
            <p className="preview-banner">
              Test scores withheld until all frozen arms and the verified
              analysis are complete. No target-scene model selection.
            </p>
          )}
          {data.results && (
            <>
              <h3>Quality / runtime / memory</h3>
              <p>
                Seed-level mean ± sample SD. Test: new recordings. Validation:
                original desk refinement. Ordered local timings; depth MAE is
                conditional on support.
              </p>
              <div className="research-table">
                <table>
                  <caption>
                    Measured reconstruction comparisons; LPIPS lower is better
                  </caption>
                  <thead>
                    <tr>
                      {[
                        "Study / policy",
                        "Updates",
                        "Seeds",
                        "LPIPS ↓",
                        "PSNR (dB) ↑",
                        "SSIM ↑",
                        "Depth MAE (m) ↓",
                        "Support ↑",
                        "Optimizer (s)",
                        "Gaussians",
                        "Peak allocated (MB)",
                      ].map((k) => (
                        <th key={k} scope="col">
                          {k}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.results.aggregates
                      .filter((row) => row.study === selectedStudy)
                      .map((row) => (
                        <tr key={`${row.study}/${row.policy}/${row.step}`}>
                          <th scope="row">
                            {row.study} / {row.policy}
                          </th>
                          <td>{row.step}</td>
                          <td>{row.seeds}</td>
                          {[
                            "lpips",
                            "psnr_db",
                            "ssim",
                            "depth_mae_m",
                            "depth_completeness",
                            "optimization_seconds",
                            "gaussians",
                            "peak_allocated_bytes",
                          ].map((k) => (
                            <td key={k}>
                              {value(
                                row.statistics[k],
                                k === "peak_allocated_bytes" ? 1e6 : 1,
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
              <div className="report-downloads">
                {[
                  "report.html",
                  "quality-runtime.csv",
                  "paired-deltas.json",
                  "failure-cases.json",
                  "measurements.json",
                ].map((name) => (
                  <a
                    key={name}
                    href={`/research/engineering-improvement-1/${name}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {name}
                  </a>
                ))}
              </div>
              <p>
                HTML report includes every run’s worst-LPIPS image montage.
                Cases are selected by a fixed error rule, not favorable
                appearance.
              </p>
            </>
          )}
          <details open>
            <summary>Run ledger · {data.study_id}</summary>
            <div className="research-table">
              <table>
                <caption>
                  Frozen jobs and complete evaluation split sizes
                </caption>
                <thead>
                  <tr>
                    {[
                      "Study / run",
                      "Split · views",
                      "Updates",
                      "Training",
                      "Evaluation checkpoints",
                      "Configuration SHA-256",
                    ].map((k) => (
                      <th key={k} scope="col">
                        {k}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.runs
                    .filter((row) => row.study === selectedStudy)
                    .map((row) => (
                      <tr key={`${row.study}/${row.run}`}>
                        <th scope="row">
                          {row.study}
                          <br />
                          {row.run}
                        </th>
                        <td>
                          {row.split} · {row.views}
                        </td>
                        <td>{row.iterations}</td>
                        <td>{row.training}</td>
                        <td>
                          {row.evaluations
                            .map((e) => `${e.step}: ${e.status}`)
                            .join("; ")}
                        </td>
                        <td>
                          <code title={row.config_sha256}>
                            {row.config_sha256.slice(0, 16)}
                          </code>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </details>
          <details>
            <summary>Reproducibility</summary>
            <p>{data.policy}</p>
            <p>
              Training source <code>{data.source_commit}</code>
            </p>
            <p>
              Protocol SHA-256 <code>{data.protocol_sha256}</code>
            </p>
            <a href="/research/reconstruction.json" download>
              Download snapshot with full configuration hashes
            </a>
          </details>
        </>
      )}
      <p className="preview-banner">
        Ground-truth AP50 and recall: pending actual human approval of
        annotations. Detector agreement is a separate proxy.
      </p>
    </section>
  );
}
