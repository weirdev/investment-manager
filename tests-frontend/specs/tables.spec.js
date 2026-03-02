const { test, expect } = require("@playwright/test");
const { clearUiStorage, gotoRoute, setFilterOptions } = require("../helpers/app");

test.beforeEach(async ({ page }) => {
  await clearUiStorage(page);
});

test("sorting numeric columns toggles direction", async ({ page }) => {
  await gotoRoute(page, "/allocations");
  const header = page.locator("th.num", { hasText: "total value" });
  await header.click();
  await expect(header).toContainText("▼");
  const firstDesc = await page.locator("tbody tr").first().locator("td.num").first().innerText();

  await header.click();
  await expect(header).toContainText("▲");
  const firstAsc = await page.locator("tbody tr").first().locator("td.num").first().innerText();
  expect(firstAsc).not.toBe(firstDesc);
});

test("multi-select filters update rows, labels, and totals", async ({ page }) => {
  await gotoRoute(page, "/concentration");
  const initialRows = await page.locator("tbody tr").count();
  const initialFooter = await page.locator("tfoot td").first().innerText();
  await page.locator(".filter-row th").first().locator(".filter-btn").click();
  const assetClassOptions = await page.locator(".filter-row th").first().locator(".filter-option").allInnerTexts();
  await page.locator("body").click({ position: { x: 5, y: 5 } });
  const secondOption = assetClassOptions
    .map(text => text.trim())
    .find(text => text && text !== "equities");

  await setFilterOptions(page, "asset class", ["equities"]);
  await expect(page.locator(".filter-btn.has-filter").first()).toContainText("equities");
  const filteredRows = await page.locator("tbody tr").count();
  expect(filteredRows).toBeLessThan(initialRows);
  await expect(page.locator("tfoot td").first()).toHaveText("Filtered Total");
  expect(initialFooter).not.toBe("Filtered Total");

  if (secondOption) {
    await setFilterOptions(page, "asset class", ["equities", secondOption]);
    await expect(page.locator(".filter-btn.has-filter").first()).toContainText("2 selected");
  }

  await setFilterOptions(page, "asset class", []);
  await expect(page.locator(".filter-btn").first()).toHaveText("All");
  await expect(page.locator("tfoot td").first()).not.toHaveText("Filtered Total");
});

test("column picker hides a dimension column and table remains populated", async ({ page }) => {
  await gotoRoute(page, "/positions");
  await page.locator(".col-picker-item", { hasText: "institution name" }).click();
  await expect(page.locator("thead tr").first()).not.toContainText("institution name");
  expect(await page.locator("tbody tr").count()).toBeGreaterThan(0);
});
