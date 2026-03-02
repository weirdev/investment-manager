const { test, expect } = require("@playwright/test");
const { clearUiStorage, expectChartRendered, gotoRoute, toggleSidebarControl } = require("../helpers/app");

test.beforeEach(async ({ page }) => {
  await clearUiStorage(page);
});

const desktopCases = [
  ["/positions", "positions-light.png", false],
  ["/concentration", "concentration-light.png", true],
  ["/decomposition", "decomposition-light.png", true],
  ["/allocations", "allocations-light.png", true],
  ["/precious-metals", "precious-metals-light.png", false],
];

for (const [route, snapshot, hasDonut] of desktopCases) {
  test(`desktop snapshot ${route}`, async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "chromium");
    await gotoRoute(page, route);
    await expect(page).toHaveScreenshot(snapshot, { fullPage: true });
    if (hasDonut) {
      await expectChartRendered(page.locator(".chart-container").first());
    }
  });
}

for (const route of ["/concentration", "/decomposition", "/allocations"]) {
  test(`dark mode snapshot ${route}`, async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "chromium");
    await gotoRoute(page, route);
    await toggleSidebarControl(page, "Dark mode");
    await expect(page).toHaveScreenshot(`${route.slice(1)}-dark.png`, { fullPage: true });
  });
}

for (const route of ["/positions", "/concentration"]) {
  test(`mobile snapshot ${route}`, async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "mobile-chromium");
    await gotoRoute(page, route);
    await expect(page).toHaveScreenshot(`${route.slice(1)}-mobile.png`, { fullPage: true });
  });
}

for (const route of ["/concentration", "/decomposition"]) {
  test(`chart title spacing snapshot ${route}`, async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "chromium");
    await gotoRoute(page, route);
    await expect(page.locator(".chart-container").first()).toHaveScreenshot(`${route.slice(1)}-chart.png`);
  });
}

test("sidebar controls light and dark snapshots", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "chromium");
  await gotoRoute(page, "/positions");
  const footer = page.locator(".sidebar-footer");
  await expect(footer).toHaveScreenshot("sidebar-footer-light.png");
  await toggleSidebarControl(page, "Dark mode");
  await expect(footer).toHaveScreenshot("sidebar-footer-dark.png");
});
