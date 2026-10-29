import { test as base, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
export function credentials(): {
  builder: { token: string };
  reviewer: { token: string };
} {
  return JSON.parse(
    readFileSync(
      fileURLToPath(
        new URL(
          "../../artifacts/browser-tests/local-credentials.json",
          import.meta.url,
        ),
      ),
      "utf8",
    ),
  );
}
export const test = base.extend<{ _account: void }>({
  request: async ({ playwright, baseURL }, use) => {
    const context = await playwright.request.newContext({
      baseURL,
      extraHTTPHeaders: {
        Authorization: "Bearer " + credentials().builder.token,
      },
    });
    await use(context);
    await context.dispose();
  },
  _account: [
    async ({ context }, use) => {
      await context.addInitScript((token) => {
        if (!sessionStorage.getItem("simready-token"))
          sessionStorage.setItem("simready-token", token);
      }, credentials().builder.token);
      await use();
    },
    { auto: true },
  ],
});
export { expect };
