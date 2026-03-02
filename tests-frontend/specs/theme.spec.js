const { test, expect } = require("@playwright/test");
const { expectChartRendered, gotoRoute, toggleSidebarControl } = require("../helpers/app");

test("light mode is default when storage is clear", async ({ page }) => {
  await gotoRoute(page, "/positions");
  await expect(page.locator("html")).not.toHaveAttribute("data-theme", "dark");
});

test("dark mode persists across reload and rerenders charts", async ({ page }) => {
  await gotoRoute(page, "/concentration");
  await toggleSidebarControl(page, "Dark mode");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.locator("#theme-toggle")).toBeChecked();
  await expectChartRendered(page.locator(".chart-container").first());

  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.locator("#theme-toggle")).toBeChecked();
  await expectChartRendered(page.locator(".chart-container").first());
});
