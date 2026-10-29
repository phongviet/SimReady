import { expect, test } from "vitest";
import {
  rankViews,
  score,
  reportAsset,
  type EvaluationView,
} from "./evaluation";

test("failure ranking uses measured values and leaves input order intact", () => {
  const view = (frame_id: string, lpips: number, disappeared: number) =>
    ({
      frame_id,
      metrics: { lpips, depth_mae_m: null },
      assets: {},
      detection: {
        real_count: 0,
        rendered_count: 0,
        matched_count: 0,
        empty_both: true,
        mean_matched_iou: null,
        class_mismatch_candidates: [],
        disappeared_count: disappeared,
        appeared_count: 0,
      },
    }) satisfies EvaluationView;
  const views = [view("a", 0.1, 3), view("b", 0.8, 1)];
  expect(rankViews(views, "lpips").map((v) => v.frame_id)).toEqual(["b", "a"]);
  expect(rankViews(views, "detector").map((v) => v.frame_id)).toEqual([
    "a",
    "b",
  ]);
  expect(views[0].frame_id).toBe("a");
  expect(score(null)).toBe("N/A");
  expect(reportAsset("demo", "run1", "images/frame-real.png")).toBe(
    "/api/v1/scenes/demo/reports/run1/assets/images/frame-real.png",
  );
});
