import { test, expect } from "@playwright/test";

test("scenario save, actual metric navigation, 3D replay and hidden collider failure", async ({
  page,
  request,
}) => {
  const base = "/api/v1/scenes/analytic-demo";
  let scene = await (await request.get(base)).json();
  scene = await (
    await request.put(base + "/objects", {
      data: { expected_version: scene.version, objects: [] },
    })
  ).json();
  await request.put(base + "/scenarios", {
    data: { expected_version: scene.version, scenarios: [] },
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Navigation", exact: true }).click();
  const panel = page.getByRole("region", { name: "Navigation simulator" });
  await expect(panel.getByLabel("Floor evidence")).toHaveValue(
    "declared_virtual_plane",
  );
  await panel
    .getByLabel("Scenario name", { exact: true })
    .fill("Browser virtual floor");
  await panel.getByRole("button", { name: "Save scenario revision" }).click();
  await expect(
    panel.getByRole("button", { name: "Run navigation" }),
  ).toBeEnabled();
  const responsePromise = page.waitForResponse(
    (response) =>
      response.url().endsWith("/scenarios/run") &&
      response.request().method() === "POST",
  );
  await panel.getByRole("button", { name: "Run navigation" }).click();
  expect((await responsePromise).status()).toBe(201);
  await expect(panel.getByText("Goal reached", { exact: true })).toBeVisible();
  const canvas = panel.locator("canvas");
  await expect
    .poll(() => canvas.getAttribute("data-simulation-run"))
    .toBeTruthy();
  await expect
    .poll(() => canvas.getAttribute("data-robot-position"))
    .toBeTruthy();
  const firstPosition = await canvas.getAttribute("data-robot-position");
  const before = await canvas.screenshot();
  const slider = panel.getByRole("slider", { name: "Replay position" });
  await slider.focus();
  await slider.press("End");
  await expect
    .poll(() => canvas.getAttribute("data-replay-index"))
    .toBe(await slider.getAttribute("max"));
  await expect(canvas).not.toHaveAttribute(
    "data-robot-position",
    firstPosition!,
  );
  await expect
    .poll(async () => (await canvas.screenshot()).equals(before))
    .toBe(false);
  const finalPosition = JSON.parse(
    (await canvas.getAttribute("data-robot-position"))!,
  );
  expect(finalPosition[0]).toBeCloseTo(0.6, 8);
  expect(finalPosition[1]).toBeCloseTo(-0.45, 8);
  expect(finalPosition[2]).toBeCloseTo(-0.6, 8);
  await panel
    .getByText("2D route map and run evidence", { exact: true })
    .click();
  const image = panel.getByRole("img", { name: "Saved occupancy route map" });
  await expect
    .poll(() =>
      image.evaluate(
        (value: HTMLImageElement) => value.complete && value.naturalWidth > 0,
      ),
    )
    .toBe(true);
  await page.reload();
  await page.getByRole("button", { name: "Navigation", exact: true }).click();
  await expect(panel.getByLabel("Scenario name", { exact: true })).toHaveValue(
    "Browser virtual floor",
  );
  scene = await (await request.get(base)).json();
  await request.put(base + "/objects", {
    data: {
      expected_version: scene.version,
      objects: [
        {
          object_id: "hidden-nav-blocker",
          name: "Hidden navigation blocker",
          position: [-0.6, -0.45, -1.4],
          quaternion_xyzw: [0, 0, 0, 1],
          scale: [0.2, 0.5, 0.2],
          visible: false,
          collidable: true,
        },
      ],
    },
  });
  await page.reload();
  await page.getByRole("button", { name: "Navigation", exact: true }).click();
  const blockedResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/scenarios/run") &&
      response.request().method() === "POST",
  );
  await panel.getByRole("button", { name: "Run navigation" }).click();
  expect((await blockedResponse).status()).toBe(201);
  await expect(
    panel.getByText("Failed / blocked", { exact: true }),
  ).toBeVisible();
  await expect(
    panel.getByRole("button", { name: "Play replay" }),
  ).toBeDisabled();
});
