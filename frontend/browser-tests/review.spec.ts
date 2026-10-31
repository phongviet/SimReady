import { test, expect, credentials } from "./helpers";

test("independent local reviewer approves scoped evidence, exports and preserves old approval after edits", async ({
  page,
  request,
}) => {
  test.setTimeout(90000);
  const base = "/api/v1/scenes/analytic-demo";
  let scene = await (await request.get(base)).json();
  scene = await (
    await request.put(base + "/objects", {
      data: { expected_version: scene.version, objects: [] },
    })
  ).json();
  const scenario = {
    scenario_id: "review-route",
    name: "Review virtual floor",
    bounds_xz_m: [-1, -1.8, 1, -0.2],
    floor_y_m: -0.7,
    floor_mode: "declared_virtual_plane",
    floor_note:
      "Explicit virtual floor for local review acceptance, not observed truth.",
    start_xz_m: [-0.6, -1.4],
    goal_xz_m: [0.6, -0.6],
  };
  scene = await (
    await request.put(base + "/scenarios", {
      data: { expected_version: scene.version, scenarios: [scenario] },
    })
  ).json();
  const simulation = await request.post(base + "/scenarios/run", {
    data: { expected_version: scene.version, scenario_id: "review-route" },
  });
  expect(simulation.status()).toBe(201);
  await page.goto("/");
  await expect(page.locator(".account-bar")).toContainText("Local Builder");
  await page
    .getByRole("button", { name: "Readiness / review", exact: true })
    .click();
  const panel = page.getByRole("region", {
    name: "Readiness and scoped review",
  });
  await expect(panel.getByText("needs review", { exact: true })).toBeVisible();
  await panel
    .getByLabel("Named experiment")
    .fill("Browser scoped route regression");
  await expect(
    panel.getByRole("button", { name: "Approve scoped experiment" }),
  ).toBeDisabled();
  await panel.getByLabel("Acknowledge measured limits").check();
  const submitted = page.waitForResponse(
    (response) =>
      response.url().endsWith("/submit") &&
      response.request().method() === "POST",
  );
  await panel
    .getByRole("button", { name: "Submit for independent review" })
    .click();
  expect((await submitted).status()).toBe(200);
  await expect(page.locator(".draft-badge")).toContainText("submitted");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await page
    .getByLabel("Local account token")
    .fill(credentials().reviewer.token);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator(".account-bar")).toContainText("Local Reviewer");
  await page.getByRole("button", { name: "Review queue", exact: true }).click();
  await expect(page.locator(".scene-card")).toContainText("submitted");
  // Editing controls are contextual to Workspace; keep the permission assertion visible.
  await page.getByRole("button", { name: "3D scene", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "＋ Box", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Readiness / review", exact: true })
    .click();
  await panel
    .getByLabel("Reviewer justification")
    .fill(
      "Automated browser acceptance: approve only this virtual-floor route regression and measured reference cameras. No safety or accuracy endorsement.",
    );
  const reviewed = page.waitForResponse(
    (response) =>
      response.url().endsWith("/review") &&
      response.request().method() === "POST",
  );
  await panel
    .getByRole("button", { name: "Approve scoped experiment" })
    .click();
  expect((await reviewed).status()).toBe(200);
  await expect(
    panel.getByText("usable for declared test", { exact: true }),
  ).toBeVisible();
  await expect(panel.locator(".audit-list")).toContainText("Local Reviewer");
  const exported = page.waitForResponse(
    (response) =>
      response.url().endsWith("/export") &&
      response.request().method() === "POST",
  );
  await panel.getByRole("button", { name: "Build reviewed export" }).click();
  expect((await exported).status()).toBe(201);
  const link = panel.getByRole("link", { name: /Download reviewed ZIP/ });
  await expect(link).toBeVisible();
  const archive = await request.get((await link.getAttribute("href"))!);
  expect(archive.headers()["content-type"]).toContain("zip");
  expect((await archive.body()).subarray(0, 2).toString()).toBe("PK");
  const approvedVersion = (await (await request.get(base)).json()).version;
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await page
    .getByLabel("Local account token")
    .fill(credentials().builder.token);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator(".account-bar")).toContainText("Local Builder");
  await page.getByRole("button", { name: "Saved camera", exact: true }).click();
  await page.getByRole("button", { name: "＋ Box", exact: true }).click();
  await page
    .getByLabel("Object name", { exact: true })
    .fill("Post-approval edit");
  await page
    .getByRole("button", { name: "Save revision", exact: true })
    .click();
  await expect(page.locator(".draft-badge")).toContainText("draft");
  const old = await (
    await request.get(base + `/versions/${approvedVersion}`)
  ).json();
  expect(old.status).toBe("approved");
  await page
    .getByRole("button", { name: "Readiness / review", exact: true })
    .click();
  await expect(panel.getByLabel("Approved revision")).toHaveValue(
    String(approvedVersion),
  );
});
