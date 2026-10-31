import { expect, test } from "./helpers";

test("measured research dashboard shows negative results, provenance and working exports", async ({
  page,
  request,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Research", exact: true }).click();
  await page.getByRole("button", { name: "Recapture", exact: true }).click();
  const panel = page.getByRole("region", { name: "Research dashboard" });
  await expect(
    panel.getByText("PRECOMPUTED MEASURED SNAPSHOT", { exact: false }),
  ).toBeVisible();
  await expect(
    panel.getByText("Risk acquisition did not improve on random", {
      exact: false,
    }),
  ).toBeVisible();
  await expect(
    panel.getByText("0.01473 ± 0.00426", { exact: false }),
  ).toBeVisible();
  await expect(panel.getByText("12 models", { exact: false })).toBeVisible();
  const figure = panel.getByRole("img", {
    name: /Measured recapture comparisons/,
  });
  await expect
    .poll(() =>
      figure.evaluate(
        (img: HTMLImageElement) => img.complete && img.naturalWidth > 0,
      ),
    )
    .toBe(true);
  await panel
    .getByText("Raw run values and source hashes", { exact: true })
    .click();
  await expect(
    panel.getByRole("rowheader", { name: "risk-s42", exact: true }),
  ).toBeVisible();
  const csv = await panel
    .getByRole("link", { name: "per_view.csv", exact: true })
    .getAttribute("href");
  const response = await request.get(csv!);
  expect(response.status()).toBe(200);
  expect((await response.text()).split("\n")[0]).toContain(
    "unmatched_fraction",
  );
  await expect(
    panel.getByRole("link", { name: "predictions_real.jsonl" }),
  ).toHaveCount(0);
  const report = await panel
    .getByRole("link", { name: "report.html", exact: true })
    .getAttribute("href");
  const reportPage = await page.context().newPage();
  await reportPage.goto(report!);
  await expect(reportPage.locator("table")).toHaveCount(2);
  await expect
    .poll(() =>
      reportPage
        .locator("img")
        .last()
        .evaluate(
          (img: HTMLImageElement) => img.complete && img.naturalWidth === 1600,
        ),
    )
    .toBe(true);
  await reportPage.close();
});
