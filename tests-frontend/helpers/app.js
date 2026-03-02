const { expect } = require("@playwright/test");

const UI_STORAGE_KEYS = [
  "investment-manager-theme",
  "investment-manager-anonymize",
  "investment-manager-by-retirement",
];

async function clearUiStorage(page) {
  await page.goto("/index.html");
  await page.evaluate((keys) => {
    for (const key of keys) {
      window.localStorage.removeItem(key);
    }
  }, UI_STORAGE_KEYS);
  await page.goto("about:blank");
}

async function setUiStorage(page, values) {
  await page.addInitScript((entries) => {
    for (const [key, value] of Object.entries(entries)) {
      if (value == null) {
        window.localStorage.removeItem(key);
      } else {
        window.localStorage.setItem(key, value);
      }
    }
  }, values);
}

async function gotoRoute(page, route = "/positions") {
  await page.goto(`/index.html#${route}`);
  await waitForAppReady(page);
}

async function waitForAppReady(page) {
  await page.locator("#view .loading").waitFor({ state: "detached" });
  await Promise.race([
    page.locator("#view h2").waitFor({ state: "visible" }),
    page.locator("#view .error").waitFor({ state: "visible" }),
  ]);
}

async function expectNoError(page) {
  await expect(page.locator("#view .error")).toHaveCount(0);
}

async function expectChartRendered(container) {
  await expect(container).toBeVisible();
  await expect.poll(async () => await container.locator(".plot-container,.main-svg,svg").count(), {
    timeout: 10_000,
  }).toBeGreaterThan(0);
}

async function toggleSidebarControl(page, labelText) {
  const label = page.locator(".sidebar-toggle", {
    has: page.locator(".sidebar-toggle-label", { hasText: labelText }),
  });
  await label.click();
}

async function openFilter(page, columnName) {
  const headerCells = page.locator("thead tr").first().locator("th");
  const count = await headerCells.count();
  let index = -1;
  for (let i = 0; i < count; i += 1) {
    const text = (await headerCells.nth(i).innerText()).trim().replace(/[▲▼]/g, "").trim().toLowerCase();
    if (text === columnName.toLowerCase()) {
      index = i;
      break;
    }
  }
  expect(index).toBeGreaterThanOrEqual(0);
  const button = page.locator(".filter-row th").nth(index).locator(".filter-btn");
  await button.click();
  await expect(page.locator(".filter-row th").nth(index).locator(".filter-dropdown")).toHaveClass(/open/);
  return button;
}

async function setFilterOptions(page, columnName, labels) {
  const button = await openFilter(page, columnName);
  const cell = button.locator("xpath=ancestor::th[1]");
  let dropdown = cell.locator(".filter-dropdown");
  let checkedOptions = dropdown.locator('.filter-option:has(input:checked)');
  let checkedCount = await checkedOptions.count();

  for (let i = 0; i < checkedCount; i += 1) {
    const option = checkedOptions.nth(0);
    const text = (await option.innerText()).trim();
    if (!labels.includes(text)) {
      await option.locator('input[type="checkbox"]').evaluate((el) => el.click());
      dropdown = cell.locator(".filter-dropdown");
      checkedOptions = dropdown.locator('.filter-option:has(input:checked)');
      checkedCount = await checkedOptions.count();
      i -= 1;
    }
  }

  for (const label of labels) {
    const option = dropdown.locator(".filter-option", { hasText: label }).first();
    const checkbox = option.locator('input[type="checkbox"]');
    if (!(await checkbox.isChecked())) {
      await checkbox.evaluate((el) => el.click());
      dropdown = cell.locator(".filter-dropdown");
    }
  }

  await page.locator("body").click({ position: { x: 5, y: 5 } });
  await expect(dropdown).not.toHaveClass(/open/);
}

module.exports = {
  clearUiStorage,
  expectChartRendered,
  expectNoError,
  gotoRoute,
  openFilter,
  setFilterOptions,
  setUiStorage,
  toggleSidebarControl,
  waitForAppReady,
};
