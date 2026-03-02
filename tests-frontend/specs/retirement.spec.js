const { test, expect } = require("@playwright/test");
const { clearUiStorage, gotoRoute, toggleSidebarControl } = require("../helpers/app");

test.beforeEach(async ({ page }) => {
  await clearUiStorage(page);
});

test("by retirement adds query parameter and persists on reload", async ({ page }) => {
  const requests = [];
  page.on("request", (request) => {
    const url = request.url();
    if (url.includes("/api/allocations")) requests.push(url);
  });

  await gotoRoute(page, "/allocations");
  expect(requests.some((url) => url.includes("by_retirement=true"))).toBeFalsy();

  await toggleSidebarControl(page, "By retirement");
  await expect(page.locator("#retirement-toggle")).toBeChecked();
  await expect.poll(() => requests.some((url) => url.includes("by_retirement=true"))).toBeTruthy();

  requests.length = 0;
  await page.reload();
  await expect(page.locator("#retirement-toggle")).toBeChecked();
  await expect.poll(() => requests.some((url) => url.includes("by_retirement=true"))).toBeTruthy();
});

test("allocations switches to retirement labels when enabled", async ({ page }) => {
  await gotoRoute(page, "/allocations");
  await toggleSidebarControl(page, "By retirement");
  await expect(page.locator(".chart-container")).toContainText(/Retirement|Non-Retirement/);
  await expect(page.locator("thead tr").first()).toContainText(/is retirement/i);
});
