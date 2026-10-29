import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./browser-tests",
  workers: 1,
  timeout: 60000,
  outputDir: "../.cache/playwright-results",
  use: {
    baseURL: "http://127.0.0.1:8001",
    viewport: { width: 1440, height: 1000 },
    launchOptions: {
      args: [
        "--enable-unsafe-swiftshader",
        "--use-angle=swiftshader",
        "--disable-dev-shm-usage",
      ],
    },
  },
  webServer: {
    command:
      "uv run --frozen simready api serve --root artifacts/browser-tests --demo --port 8001",
    cwd: "..",
    url: "http://127.0.0.1:8001/api/v1/health",
    reuseExistingServer: false,
    timeout: 60000,
  },
});
