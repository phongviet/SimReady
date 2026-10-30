import { useEffect, useState } from "react";
import { api, assetUrl } from "./api";
import { score, type EvaluationReport } from "./evaluation";
import type { SceneState } from "./types";

export function SceneCard({
  scene,
  active,
  onChoose,
}: {
  scene: SceneState;
  active: boolean;
  onChoose: () => void;
}) {
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [status, setStatus] = useState("Loading base QA…");
  useEffect(() => {
    let current = true;
    const refresh = () =>
      api
        .reports(scene.scene_id)
        .then((reports) => {
          if (!current) return;
          setReport(reports.at(-1) || null);
          setStatus(reports.length ? "" : "Not evaluated");
        })
        .catch(() => {
          if (current) {
            setReport(null);
            setStatus("Base QA unavailable");
          }
        });
    void refresh();
    const timer = setInterval(() => void refresh(), 10000);
    return () => {
      current = false;
      clearInterval(timer);
    };
  }, [scene.scene_id, scene.version]);
  const camera = scene.base.cameras[0];
  return (
    <button
      className={`scene-card ${active ? "active" : ""}`}
      onClick={onChoose}
    >
      {camera && (
        <img
          className="scene-thumbnail"
          src={assetUrl(scene, camera.frame_id + ".png")}
          alt={`${scene.name} saved reconstruction thumbnail`}
          loading="lazy"
        />
      )}
      <strong>{scene.name}</strong>
      <small>
        {scene.base.dataset_kind === "real" ? "REAL CAPTURE" : "SYNTHETIC"} · v
        {scene.version} · {scene.status}
      </small>
      <small>
        Reconstruction ready · {scene.base.cameras.length} reference views
      </small>
      <small aria-label="Latest base evaluation" title={report?.run_id}>
        {report
          ? `Base QA v${report.scene_version} · ${report.summary.view_count} views · LPIPS ${score(report.summary.means.lpips)}`
          : status}
      </small>
    </button>
  );
}
