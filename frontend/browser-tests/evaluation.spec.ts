import { expect, test } from "@playwright/test";

test("measured explorer loads paired images, failure ranking and verified exports", async ({
  page,
  request,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Evaluation", exact: true }).click();
  const explorer = page.getByRole("region", { name: "Evaluation explorer" });
  await expect(
    explorer.getByText("2 frozen test views", { exact: false }),
  ).toBeVisible();
  await expect(
    explorer.getByText("Both predictions empty.", { exact: false }),
  ).toBeVisible();
  const real = explorer.getByRole("img", { name: /frame_.* Real RGB/ });
  await expect(real).toBeVisible();
  await expect
    .poll(() =>
      real.evaluate(
        (image: HTMLImageElement) =>
          image.complete && image.naturalWidth === 64,
      ),
    )
    .toBe(true);
  await expect(
    explorer.getByRole("img", { name: /frame_.* Rendered RGB/ }),
  ).toBeVisible();
  await expect(
    explorer.getByRole("img", { name: /frame_.* RGB residual/ }),
  ).toBeVisible();
  const overlaySource = await real.getAttribute("src");
  await explorer.getByLabel("Detector overlays").uncheck();
  await expect(real).not.toHaveAttribute("src", overlaySource || "");
  await explorer.getByLabel("Sort failure views").selectOption("depth_mae_m");
  await explorer.getByRole("button", { name: /frame_00006 LPIPS/ }).click();
  await expect(
    explorer.getByRole("heading", { name: "frame_00006 · aligned comparison" }),
  ).toBeVisible();
  const csv = await explorer
    .getByRole("link", { name: "Per-view CSV" })
    .getAttribute("href");
  const response = await request.get(csv!);
  expect(response.status()).toBe(200);
  expect((await response.text()).split("\n")[0]).toContain(
    "depth_completeness",
  );
  const html = await explorer
    .getByRole("link", { name: "HTML report" })
    .getAttribute("href");
  const reportResponse = await request.get(html!);
  expect(await reportResponse.text()).toContain(
    "Detector consistency is not detection accuracy",
  );
  const reportPage = await page.context().newPage();
  await reportPage.goto(html!);
  const reportImages = reportPage.locator("section img");
  await expect(reportImages).toHaveCount(8);
  await expect
    .poll(() =>
      reportImages
        .first()
        .evaluate(
          (image: HTMLImageElement) => image.complete && image.naturalWidth > 0,
        ),
    )
    .toBe(true);
  await reportPage.close();
  await explorer
    .getByText("Protocol, provenance and limits", { exact: true })
    .click();
  await expect(
    explorer.getByText("Split SHA-256:", { exact: false }),
  ).toBeVisible();
});
