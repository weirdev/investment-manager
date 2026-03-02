const { test, expect } = require("@playwright/test");
const { gotoRoute } = require("../helpers/app");

test("api failures surface as error banners", async ({ page }) => {
  await page.route("**/api/concentration**", async (route) => {
    await route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ detail: "boom" }),
    });
  });

  await gotoRoute(page, "/concentration");
  await expect(page.locator("#view .error")).toContainText("HTTP 500");
});
