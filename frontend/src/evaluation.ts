export interface DetectionSummary {
  real_count: number;
  rendered_count: number;
  matched_count: number;
  disappeared_count: number;
  appeared_count: number;
  empty_both: boolean | number;
  mean_matched_iou: number | null;
  class_mismatch_candidates: unknown[];
}
export interface EvaluationView {
  frame_id: string;
  metrics: Record<string, number | boolean | null>;
  detection: DetectionSummary;
  assets: Record<string, string>;
}
export interface EvaluationReport {
  run_id: string;
  scene_version: number;
  evaluation_sha256: string;
  summary: {
    dataset_kind: string;
    split: string;
    split_sha256: string;
    view_count: number;
    means: Record<string, number | null>;
    scope: string;
    limitations: string[];
    source: { name: string; attribution: string; license: string };
    detection_totals: DetectionSummary;
    per_class: Record<
      string,
      { real: number; rendered: number; matched: number }
    >;
    environment: { categories: string[] };
  };
}
export interface EvaluationJob {
  job_id: string;
  scene_id: string;
  scene_version: number;
  status: "queued" | "running" | "succeeded" | "failed";
  error: string | null;
  log_tail: string;
  run_id: string | null;
}
export function reportAsset(sceneId: string, runId: string, name: string) {
  return `/api/v1/scenes/${encodeURIComponent(sceneId)}/reports/${encodeURIComponent(runId)}/assets/${name.split("/").map(encodeURIComponent).join("/")}`;
}
export function score(value: unknown, precision = 3): string {
  return typeof value === "number" ? value.toFixed(precision) : "N/A";
}
export function rankViews(views: EvaluationView[], sort: string) {
  return [...views].sort((a, b) => {
    const metric = (view: EvaluationView): number => {
      if (sort === "detector")
        return view.detection.disappeared_count + view.detection.appeared_count;
      const value = view.metrics[sort];
      return typeof value === "number" ? value : -Infinity;
    };
    return metric(b) - metric(a);
  });
}
