import { test, expect } from "@playwright/test";

test.beforeEach(async ({ request }) => {
  const original = await (
    await request.get("/api/v1/scenes/analytic-demo")
  ).json();
  await request.put("/api/v1/scenes/analytic-demo/objects", {
    data: { expected_version: original.version, objects: [] },
  });
});

test("actual splat loading, inserted transform, save/reload and deletion", async ({
  page,
  request,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Analytic plane · CPU demo" }),
  ).toBeVisible();
  await expect(
    page.getByText("Gaussian scene loaded", { exact: true }),
  ).toBeVisible({ timeout: 45000 });
  await expect
    .poll(
      async () =>
        page.locator("canvas").evaluate((canvas) => {
          const gl = canvas.getContext("webgl2")!;
          const pixels = new Uint8Array(32 * 32 * 4);
          gl.readPixels(
            Math.floor(canvas.width / 2) - 16,
            Math.floor(canvas.height / 2) - 16,
            32,
            32,
            gl.RGBA,
            gl.UNSIGNED_BYTE,
            pixels,
          );
          return new Set(
            Array.from(
              { length: 1024 },
              (_, i) =>
                `${pixels[i * 4]},${pixels[i * 4 + 1]},${pixels[i * 4 + 2]}`,
            ),
          ).size;
        }),
      { timeout: 30000 },
    )
    .toBeGreaterThan(8);
  const canvas = page.locator("canvas");
  const beforeOrbit = await canvas.screenshot();
  const rect = await canvas.boundingBox();
  await page.mouse.move(
    rect!.x + rect!.width * 0.65,
    rect!.y + rect!.height * 0.4,
  );
  await page.mouse.down();
  await page.mouse.move(
    rect!.x + rect!.width * 0.75,
    rect!.y + rect!.height * 0.45,
    { steps: 12 },
  );
  await page.mouse.up();
  await expect
    .poll(async () => (await canvas.screenshot()).equals(beforeOrbit))
    .toBe(false);
  await page.getByRole("button", { name: "Saved camera", exact: true }).click();
  await page.getByRole("button", { name: "3D scene", exact: true }).click();
  await expect(
    page.getByText("Gaussian scene loaded", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "＋ Box", exact: true }).click();
  await page
    .getByLabel("Object name", { exact: true })
    .fill("Known metric box");
  await page.getByLabel("Position (m) X", { exact: true }).fill("0.25");
  await page.getByLabel("Position (m) Y", { exact: true }).fill("0.1");
  await page.getByLabel("Position (m) Z", { exact: true }).fill("-1.2");
  await page.getByLabel("Rotation (°) Y", { exact: true }).fill("30");
  await page.getByLabel("Size (m) X", { exact: true }).fill("0.4");
  await page.getByLabel("Collision proxy", { exact: true }).check();
  await page
    .getByRole("button", { name: "Save revision", exact: true })
    .click();
  await expect(page.getByText(/Saved revision/)).toBeVisible();
  const saved = await (
    await request.get("/api/v1/scenes/analytic-demo")
  ).json();
  expect(saved.objects[0].position).toEqual([0.25, 0.1, -1.2]);
  expect(saved.objects[0].scale).toEqual([0.4, 0.3, 0.3]);
  expect(saved.objects[0].quaternion_xyzw[1]).toBeCloseTo(
    Math.sin(Math.PI / 12),
    6,
  );
  await page.reload();
  await page.getByRole("button", { name: /Known metric box/ }).click();
  await expect(page.getByLabel("Position (m) X", { exact: true })).toHaveValue(
    "0.25",
  );
  await expect(page.getByLabel("Rotation (°) Y", { exact: true })).toHaveValue(
    "30",
  );
  await page.getByLabel("Visible", { exact: true }).uncheck();
  await page
    .getByRole("button", { name: "Save revision", exact: true })
    .click();
  await expect(page.getByText(/Saved revision/)).toBeVisible();
  const hidden = await (
    await request.get("/api/v1/scenes/analytic-demo")
  ).json();
  expect(hidden.objects[0].visible).toBe(false);
  expect(hidden.objects[0].collidable).toBe(true);
  await page.getByLabel("Visible", { exact: true }).check();
  await page
    .getByRole("button", { name: "Save revision", exact: true })
    .click();
  await expect(page.getByText(/Saved revision/)).toBeVisible();
  await expect(
    page.getByText("Gaussian scene loaded", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Collision proxy", { exact: true }).check();
  await page.screenshot({
    path: "../docs/evidence/m2-analytic-editor.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Delete object", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Save revision", exact: true })
    .click();
  await expect(page.getByText(/Saved revision/)).toBeVisible();
  expect(
    (await (await request.get("/api/v1/scenes/analytic-demo")).json()).objects,
  ).toEqual([]);
  expect(errors).toEqual([]);
});

test("stale browser preserves local edits and shows version conflict", async ({
  page,
  request,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "＋ Barrier", exact: true }).click();
  const current = await (
    await request.get("/api/v1/scenes/analytic-demo")
  ).json();
  await request.put("/api/v1/scenes/analytic-demo/objects", {
    data: { expected_version: current.version, objects: [] },
  });
  await page
    .getByRole("button", { name: "Save revision", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("Version conflict");
  await expect(page.getByRole("alert")).toContainText(
    "local edits are preserved",
  );
  await expect(page.getByLabel("Object name", { exact: true })).toHaveValue(
    "Barrier 1",
  );
  await page
    .getByRole("button", { name: "Reload / discard", exact: true })
    .click();
  await expect(
    page.getByText("Loaded the latest saved revision."),
  ).toBeVisible();
  await expect(page.getByLabel("Object name", { exact: true })).toHaveCount(0);
});

test("saved-camera fallback supports persistent numeric editing", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Saved camera", exact: true }).click();
  await expect(
    page.getByRole("img", { name: /Saved Gaussian render/ }),
  ).toBeVisible();
  await page.getByRole("button", { name: "＋ Box", exact: true }).click();
  await expect(
    page.getByLabel("Projected inserted object wireframes").locator("line"),
  ).toHaveCount(12);
  await expect(
    page.getByText("Inserted meshes are not depth-composited with splats.", {
      exact: false,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Save revision", exact: true })
    .click();
  await expect(page.getByText(/Saved revision/)).toBeVisible();
});
