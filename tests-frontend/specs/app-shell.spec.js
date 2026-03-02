const { test, expect } = require("@playwright/test");
const { clearUiStorage, expectChartRendered, expectNoError, gotoRoute } = require("../helpers/app");

test.beforeEach(async ({ page }) => {
  await clearUiStorage(page);
});

test("root redirects to index and defaults to positions", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/index\.html(?:#\/positions)?$/);
  await expect(page.locator("#view h2")).toHaveText("Positions");
});

for (const route of [
  { hash: "/positions", heading: "Positions", chart: true },
  { hash: "/concentration", heading: "Concentration", chart: true },
  { hash: "/decomposition", heading: "Decomposition", chart: true },
  { hash: "/allocations", heading: "Allocations", chart: true },
  { hash: "/precious-metals", heading: "Precious Metals", chart: false },
]) {
  test(`renders ${route.hash}`, async ({ page }) => {
    await gotoRoute(page, route.hash);
    await expect(page.locator("#view h2")).toHaveText(route.heading);
    await expect(page.locator(".page-subtitle")).toBeVisible();
    await expect(page.locator(".table-wrapper")).toBeVisible();
    if (route.chart) {
      await expectChartRendered(page.locator(".chart-container").first());
    }
    await expectNoError(page);
    await expect(page.locator(`.nav-link.active[href="#${route.hash}"]`)).toBeVisible();
  });
}
