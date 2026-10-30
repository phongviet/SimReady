import { test, expect } from "./helpers";

test("library displays saved evidence and reference path uses calibrated world centers", async ({
  page,
  request,
}) => {
  const scene = await (
    await request.get("/api/v1/scenes/analytic-demo")
  ).json();
  const reports = await (
    await request.get("/api/v1/scenes/analytic-demo/reports")
  ).json();
  const latest = reports.at(-1);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  const card = page
    .locator(".scene-card")
    .filter({ hasText: "Analytic plane · CPU demo" });
  const thumbnail = card.getByRole("img", {
    name: /saved reconstruction thumbnail/,
  });
  await expect
    .poll(() =>
      thumbnail.evaluate(
        (img: HTMLImageElement) => img.complete && img.naturalWidth === 64,
      ),
    )
    .toBe(true);
  await expect(card).toContainText("Reconstruction ready · 2 reference views");
  await expect(card.getByLabel("Latest base evaluation")).toHaveText(
    `Base QA v${latest.scene_version} · 2 views · LPIPS ${latest.summary.means.lpips.toFixed(3)}`,
  );
  await expect(
    page.getByText("Gaussian scene loaded", { exact: true }),
  ).toBeVisible({ timeout: 45000 });
  await page.getByLabel("Reference camera path", { exact: true }).check();
  const canvas = page.locator("canvas");
  await expect
    .poll(() => canvas.getAttribute("data-reference-camera-centers"))
    .toBeTruthy();
  const centers: number[][] = JSON.parse(
    (await canvas.getAttribute("data-reference-camera-centers"))!,
  );
  expect(centers).toHaveLength(scene.base.cameras.length);
  // Independent rigid inverse: camera center = -R^T t, not the w2c translation.
  for (let i = 0; i < centers.length; i++) {
    const view = scene.base.cameras[i].viewmat;
    for (let axis = 0; axis < 3; axis++)
      expect(centers[i][axis]).toBeCloseTo(
        -[0, 1, 2].reduce(
          (sum, row) => sum + view[row][axis] * view[row][3],
          0,
        ),
        7,
      );
  }
  await page.screenshot({
    path: "../.cache/playwright-results/library-reference-path.png",
    fullPage: true,
  });
  await page.getByLabel("Reference camera path", { exact: true }).uncheck();
  await expect(canvas).toHaveAttribute("data-reference-camera-centers", "");
  await page.getByRole("button", { name: "Saved camera", exact: true }).click();
  await expect(
    page.getByLabel("Reference camera path", { exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("img", { name: /Saved Gaussian render/ }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
