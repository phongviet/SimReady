import { expect, test } from "vitest";
import { defaultScenario, simulationAsset } from "./simulation";
import type { SceneState } from "./types";

test("analytic floor is an explicit assumption and TUM example keeps unknown blocked", () => {
  const analytic = defaultScenario({ scene_id: "analytic-demo" } as SceneState);
  expect(analytic.floor_mode).toBe("declared_virtual_plane");
  expect(analytic.floor_note).toContain("no observed floor truth");
  const real = defaultScenario({ scene_id: "tum-fr1-desk" } as SceneState);
  expect(real.floor_mode).toBe("observed_tsdf");
  expect(real.unknown_policy).toBe("blocked");
  expect(real.start_xz_m).toEqual([-1.125, -2.175]);
  expect(simulationAsset("scene1", "run1", "result.json")).toBe(
    "/api/v1/scenes/scene1/simulations/run1/assets/result.json",
  );
});
