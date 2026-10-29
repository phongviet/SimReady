import type {
  EvaluationReport,
  EvaluationView,
  EvaluationJob,
} from "./evaluation";
import { reportAsset } from "./evaluation";
import type { ProxyObject, SceneState } from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public requestId?: string,
  ) {
    super(message);
  }
}
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(
      body.error?.message || `Request failed (${response.status})`,
      response.status,
      body.error?.request_id,
    );
  }
  return response.json();
}
export const api = {
  reports: (id: string) =>
    request<EvaluationReport[]>(`/scenes/${encodeURIComponent(id)}/reports`),
  reportViews: async (id: string, run: string): Promise<EvaluationView[]> => {
    const response = await fetch(reportAsset(id, run, "views.json"));
    if (!response.ok)
      throw new ApiError(
        "Could not load measured view diagnostics",
        response.status,
      );
    return response.json();
  },
  evaluate: (scene: SceneState) =>
    request<EvaluationJob>(
      `/scenes/${encodeURIComponent(scene.scene_id)}/evaluate`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          expected_version: scene.version,
          split: "test",
        }),
      },
    ),
  jobs: (id: string) =>
    request<EvaluationJob[]>(`/scenes/${encodeURIComponent(id)}/jobs`),
  job: (id: string) =>
    request<EvaluationJob>(`/jobs/${encodeURIComponent(id)}`),
  list: () => request<SceneState[]>("/scenes"),
  scene: (id: string) =>
    request<SceneState>(`/scenes/${encodeURIComponent(id)}`),
  save: (scene: SceneState, objects: ProxyObject[]) =>
    request<SceneState>(
      `/scenes/${encodeURIComponent(scene.scene_id)}/objects`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expected_version: scene.version, objects }),
      },
    ),
};
export const assetUrl = (scene: SceneState, name: string) =>
  `/api/v1/scenes/${encodeURIComponent(scene.scene_id)}/assets/${encodeURIComponent(name)}`;
