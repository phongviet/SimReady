import type { Readiness, AuditEvent } from "./review";
import { accountToken, type Principal } from "./auth";
import type {
  Scenario,
  SimulationRun,
  SimulationResult,
  OccupancyMap,
} from "./simulation";
import { simulationAsset } from "./simulation";
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
  const headers = new Headers(init?.headers);
  const token = accountToken();
  if (token && !headers.has("Authorization"))
    headers.set("Authorization", "Bearer " + token);
  const response = await fetch(`/api/v1${path}`, { ...init, headers });
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
  me: () => request<Principal>("/auth/me"),
  signIn: (token: string) =>
    request<Principal>("/auth/me", {
      headers: { Authorization: "Bearer " + token },
    }),
  readiness: (id: string) =>
    request<Readiness>(`/scenes/${encodeURIComponent(id)}/readiness`),
  audit: (id: string) =>
    request<AuditEvent[]>(`/scenes/${encodeURIComponent(id)}/audit`),
  history: (id: string) =>
    request<{ version: number; status: string; updated_at: string }[]>(
      `/scenes/${encodeURIComponent(id)}/history`,
    ),
  submit: (scene: SceneState, value: object) =>
    request<SceneState>(
      `/scenes/${encodeURIComponent(scene.scene_id)}/submit`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expected_version: scene.version, ...value }),
      },
    ),
  review: (scene: SceneState, decision: "approve" | "reject", reason: string) =>
    request<SceneState>(
      `/scenes/${encodeURIComponent(scene.scene_id)}/review`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          expected_version: scene.version,
          decision,
          reason,
        }),
      },
    ),
  exportScene: (id: string, version: number) =>
    request<{
      export_id: string;
      sha256: string;
      bytes: number;
      approved_version: number;
    }>(`/scenes/${encodeURIComponent(id)}/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ version }),
    }),
  saveScenarios: (scene: SceneState, scenarios: Scenario[]) =>
    request<SceneState>(
      `/scenes/${encodeURIComponent(scene.scene_id)}/scenarios`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expected_version: scene.version, scenarios }),
      },
    ),
  simulations: (id: string) =>
    request<SimulationRun[]>(`/scenes/${encodeURIComponent(id)}/simulations`),
  runSimulation: (scene: SceneState, scenarioId: string) =>
    request<SimulationRun>(
      `/scenes/${encodeURIComponent(scene.scene_id)}/scenarios/run`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          expected_version: scene.version,
          scenario_id: scenarioId,
        }),
      },
    ),
  simulationData: async (sceneId: string, runId: string) => {
    const read = async <T>(name: string): Promise<T> => {
      const response = await fetch(simulationAsset(sceneId, runId, name));
      if (!response.ok)
        throw new ApiError("Simulation asset unavailable", response.status);
      return response.json();
    };
    const [result, map, scene] = await Promise.all([
      read<SimulationResult>("result.json"),
      read<OccupancyMap>("occupancy.json"),
      read<SceneState>("scene-input.json"),
    ]);
    return { result, map, scene };
  },
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
