const { test, expect } = require("@playwright/test");
const { clearUiStorage, gotoRoute, toggleSidebarControl } = require("../helpers/app");

test.beforeEach(async ({ page }) => {
  await clearUiStorage(page);
});

test("anonymize adds query parameter and persists on reload", async ({ page }) => {
  const requests = [];
  page.on("request", (request) => {
    const url = request.url();
    if (url.includes("/api/positions")) requests.push(url);
  });

  await gotoRoute(page, "/positions");
  expect(requests.some((url) => url.includes("anonymize=true"))).toBeFalsy();

  const firstValue = await page.locator("tbody tr").first().locator("td.num").first().innerText();
  await toggleSidebarControl(page, "Anonymize");
  await expect(page.locator("#anonymize-toggle")).toBeChecked();
  await expect.poll(() => requests.some((url) => url.includes("anonymize=true"))).toBeTruthy();
  const anonymizedValue = await page.locator("tbody tr").first().locator("td.num").first().innerText();
  expect(anonymizedValue).not.toBe(firstValue);

  requests.length = 0;
  await page.reload();
  await expect(page.locator("#anonymize-toggle")).toBeChecked();
  await expect.poll(() => requests.some((url) => url.includes("anonymize=true"))).toBeTruthy();
});

test("locked anonymize config disables the toggle", async ({ page }) => {
  await page.route("**/api/config", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ anonymize_locked: true }),
    });
  });
  await gotoRoute(page, "/positions");
  await expect(page.locator("#anonymize-toggle")).toBeChecked();
  await expect(page.locator("#anonymize-toggle")).toBeDisabled();
});
