const { defineConfig, devices } = require("@playwright/test");

const PORT = process.env.FRONTEND_TEST_PORT || "8001";
const BASE_URL = `http://127.0.0.1:${PORT}`;

module.exports = defineConfig({
  testDir: "./tests-frontend/specs",
  timeout: 30_000,
  expect: {
    timeout: 5_000,
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.01,
    },
  },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : 1,
  reporter: process.env.CI ? [["html", { open: "never" }], ["list"]] : "list",
  use: {
    baseURL: `${BASE_URL}/index.html`,
    viewport: { width: 1440, height: 1100 },
    screenshot: "only-on-failure",
    trace: "on-first-retry",
  },
  webServer: {
    command: "uv run python tests/frontend_server.py",
    url: `${BASE_URL}/index.html`,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
  projects: [
    {
      name: "chromium",
      use: {
        browserName: "chromium",
      },
    },
    {
      name: "mobile-chromium",
      testMatch: /.*visual\.spec\.js/,
      use: {
        ...devices["Pixel 7"],
      },
    },
  ],
});
