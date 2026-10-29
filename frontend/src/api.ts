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
