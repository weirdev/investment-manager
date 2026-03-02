/* Investment Manager — SPA frontend */

const _cache = {};
let _anonymize = false;
let _byRetirement = false;
const THEME_STORAGE_KEY = "investment-manager-theme";
const ANONYMIZE_STORAGE_KEY = "investment-manager-anonymize";
const BY_RETIREMENT_STORAGE_KEY = "investment-manager-by-retirement";
const LIGHT_THEME = "light";
const DARK_THEME = "dark";

const CHART_COLORS = [
  "#c9a558", "#8b7cf8", "#40c8a0", "#f4798a",
  "#5b9cf6", "#e8874f", "#9ed464", "#f0c040",
  "#a78bfa", "#fb7185",
];

// ── Formatters ─────────────────────────────────────────────────────────────

function fmtDollar(v) {
  if (v == null || v === "") return "";
  return "$" + Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtPct(v) {
  if (v == null || v === "") return "";
  return Number(v).toFixed(2) + "%";
}

function fmtVal(v, col, valueFields, pctFields) {
  if (valueFields.includes(col)) return fmtDollar(v);
  if (pctFields.includes(col)) return fmtPct(v);
  return v == null ? "" : String(v);
}

// ── Theme helpers ───────────────────────────────────────────────────────────

function getSavedTheme() {
  try {
    const theme = window.localStorage.getItem(THEME_STORAGE_KEY);
    return theme === DARK_THEME || theme === LIGHT_THEME ? theme : null;
  } catch (_) {
    return null;
  }
}

function saveTheme(theme) {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch (_) {}
}

function getSavedAnonymize() {
  try {
    const value = window.localStorage.getItem(ANONYMIZE_STORAGE_KEY);
    if (value === "true") return true;
    if (value === "false") return false;
  } catch (_) {}
  return null;
}

function saveAnonymize(enabled) {
  try {
    window.localStorage.setItem(ANONYMIZE_STORAGE_KEY, String(Boolean(enabled)));
  } catch (_) {}
}

function getSavedByRetirement() {
  try {
    const value = window.localStorage.getItem(BY_RETIREMENT_STORAGE_KEY);
    if (value === "true") return true;
    if (value === "false") return false;
  } catch (_) {}
  return null;
}

function saveByRetirement(enabled) {
  try {
    window.localStorage.setItem(BY_RETIREMENT_STORAGE_KEY, String(Boolean(enabled)));
  } catch (_) {}
}

function getInitialTheme() {
  return getSavedTheme() || LIGHT_THEME;
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const toggleEl = document.getElementById("theme-toggle");
  if (toggleEl) toggleEl.checked = theme === DARK_THEME;
}

function getThemeColors() {
  const styles = getComputedStyle(document.documentElement);
  return {
    chartTitle: styles.getPropertyValue("--chart-title").trim(),
    chartText: styles.getPropertyValue("--chart-text").trim(),
  };
}

// ── Fetch helper ────────────────────────────────────────────────────────────

function _buildUrl(path) {
  const params = new URLSearchParams();
  if (_anonymize) params.set("anonymize", "true");
  if (_byRetirement) params.set("by_retirement", "true");
  const qs = params.toString();
  return qs ? `${path}?${qs}` : path;
}

async function fetchData(path) {
  const url = _buildUrl(path);
  if (_cache[url]) return _cache[url];
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
  const data = await res.json();
  _cache[url] = data;
  return data;
}

// ── Table rendering ─────────────────────────────────────────────────────────

function renderTable(container, columns, rows, { totals = null, valueFields = [], pctFields = [], total = null } = {}) {
  let sortCol = null;
  let sortDir = 1; // 1 = asc, -1 = desc
  const filters = {};
  const visibleCols = new Set(columns);

  // Dimension columns are all non-measure columns (used for regrouping when hidden)
  const dimCols = columns.filter(c => !valueFields.includes(c) && !pctFields.includes(c));

  function computeRows() {
    // Apply filters against original rows
    const filtered = rows.filter(row => {
      for (const col of Object.keys(filters)) {
        if (String(row[col] ?? "") !== filters[col]) return false;
      }
      return true;
    });

    const visibleDims = dimCols.filter(c => visibleCols.has(c));
    if (visibleDims.length === dimCols.length) return filtered; // no hidden dims — no regrouping needed

    // Regroup by visible dimension columns, summing valueFields
    const groups = new Map();
    for (const row of filtered) {
      const key = visibleDims.map(c => String(row[c] ?? "")).join("\u0000");
      if (!groups.has(key)) {
        const g = {};
        for (const c of visibleDims) g[c] = row[c];
        for (const c of valueFields) g[c] = 0;
        groups.set(key, g);
      }
      const g = groups.get(key);
      for (const c of valueFields) g[c] = (g[c] || 0) + (row[c] || 0);
    }

    const result = [...groups.values()];

    // Recalculate pct fields relative to portfolio total
    if (total && total > 0 && pctFields.length > 0 && valueFields.length > 0) {
      for (const g of result) {
        for (const pctCol of pctFields) {
          g[pctCol] = (g[valueFields[0]] / total) * 100;
        }
      }
    }

    return result;
  }

  function render() {
    const visCols = columns.filter(c => visibleCols.has(c));
    const baseRows = computeRows();
    const sorted = sortCol && visibleCols.has(sortCol)
      ? [...baseRows].sort((a, b) => {
          const av = a[sortCol], bv = b[sortCol];
          if (av == null && bv == null) return 0;
          if (av == null) return sortDir;
          if (bv == null) return -sortDir;
          return typeof av === "number"
            ? (av - bv) * sortDir
            : String(av).localeCompare(String(bv)) * sortDir;
        })
      : [...baseRows];

    container.innerHTML = "";

    // Column picker
    const picker = document.createElement("div");
    picker.className = "col-picker";
    const pickerLabel = document.createElement("span");
    pickerLabel.className = "col-picker-label";
    pickerLabel.textContent = "Columns:";
    picker.appendChild(pickerLabel);
    for (const col of columns) {
      const label = document.createElement("label");
      label.className = "col-picker-item";
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.checked = visibleCols.has(col);
      cb.addEventListener("change", () => {
        if (cb.checked) {
          visibleCols.add(col);
        } else {
          visibleCols.delete(col);
          delete filters[col];
          if (sortCol === col) sortCol = null;
        }
        render();
      });
      label.appendChild(cb);
      label.append(" " + col.replace(/_/g, " "));
      picker.appendChild(label);
    }

    // Table
    const table = document.createElement("table");

    // thead — sort row
    const thead = document.createElement("thead");
    const hrow = document.createElement("tr");
    for (const col of visCols) {
      const th = document.createElement("th");
      const isNum = valueFields.includes(col) || pctFields.includes(col);
      if (isNum) th.classList.add("num");
      th.innerHTML = col.replace(/_/g, " ");
      if (sortCol === col) {
        th.innerHTML += `<span class="sort-arrow">${sortDir === 1 ? "▲" : "▼"}</span>`;
      }
      th.addEventListener("click", () => {
        if (sortCol === col) sortDir = -sortDir;
        else { sortCol = col; sortDir = -1; }
        render();
      });
      hrow.appendChild(th);
    }
    thead.appendChild(hrow);

    // thead — filter row
    const filterRow = document.createElement("tr");
    filterRow.className = "filter-row";
    for (const col of visCols) {
      const th = document.createElement("th");
      const isNum = valueFields.includes(col) || pctFields.includes(col);
      if (isNum) th.classList.add("num");

      const uniqueVals = [...new Set(rows.map(r => r[col] ?? ""))].sort((a, b) => {
        if (typeof a === "number" && typeof b === "number") return a - b;
        return String(a).localeCompare(String(b));
      });

      const sel = document.createElement("select");
      sel.className = "col-filter";
      const allOpt = document.createElement("option");
      allOpt.value = "";
      allOpt.textContent = "All";
      sel.appendChild(allOpt);
      for (const v of uniqueVals) {
        const opt = document.createElement("option");
        const strV = String(v);
        opt.value = strV;
        opt.textContent = fmtVal(v, col, valueFields, pctFields);
        if (filters[col] === strV) opt.selected = true;
        sel.appendChild(opt);
      }
      sel.addEventListener("change", () => {
        if (sel.value) filters[col] = sel.value;
        else delete filters[col];
        render();
      });
      th.appendChild(sel);
      filterRow.appendChild(th);
    }
    thead.appendChild(filterRow);
    table.appendChild(thead);

    // tbody
    const tbody = document.createElement("tbody");
    for (const row of sorted) {
      const tr = document.createElement("tr");
      for (const col of visCols) {
        const td = document.createElement("td");
        const isNum = valueFields.includes(col) || pctFields.includes(col);
        if (isNum) td.classList.add("num");
        td.textContent = fmtVal(row[col], col, valueFields, pctFields);
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    table.appendChild(tbody);

    // tfoot
    if (totals) {
      const tfoot = document.createElement("tfoot");
      const frow = document.createElement("tr");
      for (const col of visCols) {
        const td = document.createElement("td");
        const isNum = valueFields.includes(col) || pctFields.includes(col);
        if (isNum) td.classList.add("num");
        if (col in totals) {
          td.textContent = fmtVal(totals[col], col, valueFields, pctFields);
        }
        frow.appendChild(td);
      }
      tfoot.appendChild(frow);
      table.appendChild(tfoot);
    }

    const wrapper = document.createElement("div");
    wrapper.className = "table-wrapper";
    wrapper.appendChild(picker);
    wrapper.appendChild(table);
    container.appendChild(wrapper);
  }

  render();
}

// ── Chart rendering ─────────────────────────────────────────────────────────

function renderDonut(container, labels, values, title) {
  const themeColors = getThemeColors();
  const el = document.createElement("div");
  el.className = "chart-container";
  container.appendChild(el);
  Plotly.newPlot(el, [{
    type: "pie",
    hole: 0.45,
    labels,
    values,
    textinfo: "label+percent",
    insidetextorientation: "horizontal",
    hovertemplate: "<b>%{label}</b><br>$%{value:,.2f}<br>%{percent}<extra></extra>",
    marker: { colors: labels.map((_, i) => CHART_COLORS[i % CHART_COLORS.length]) },
  }], {
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    title: { text: title || "", font: { size: 15, color: themeColors.chartTitle, family: "Outfit, sans-serif" }, y: 0.99, yanchor: "top", yref: "container" },
    height: 440,
    margin: { t: 50, b: 80, l: 30, r: 30 },
    showlegend: false,
    font: { color: themeColors.chartText, family: "Outfit, sans-serif", size: 14 },
  }, { responsive: true, displayModeBar: false });
}

function renderTreemap(container, labels, values, title) {
  const themeColors = getThemeColors();
  const el = document.createElement("div");
  el.className = "chart-container";
  el.style.maxWidth = "720px";
  container.appendChild(el);
  Plotly.newPlot(el, [{
    type: "treemap",
    labels,
    values,
    parents: labels.map(() => ""),
    branchvalues: "total",
    hovertemplate: "<b>%{label}</b><br>$%{value:,.2f}<extra></extra>",
    texttemplate: "<b>%{label}</b><br>$%{value:,.2f}",
  }], {
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    title: { text: title || "", font: { size: 15, color: themeColors.chartTitle, family: "Outfit, sans-serif" } },
    height: 400,
    margin: { t: 30, b: 10, l: 10, r: 10 },
    font: { color: themeColors.chartText, family: "Outfit, sans-serif", size: 14 },
  }, { responsive: true, displayModeBar: false });
}

// ── Page renderers ──────────────────────────────────────────────────────────

function showPositions(view, data) {
  view.innerHTML = `<h2>Positions</h2><p class="page-subtitle">All holdings &middot; <span class="total-value">${fmtDollar(data.total)}</span> total</p>`;

  // Treemap: unique ticker → sum of total_value
  const tickerMap = {};
  for (const r of data.rows) {
    if (!(r.ticker in tickerMap)) tickerMap[r.ticker] = r.total_value;
  }
  const labels = Object.keys(tickerMap);
  const values = Object.values(tickerMap);
  renderTreemap(view, labels, values, "Portfolio by Ticker");

  const hasCols = data.rows.length > 0 ? Object.keys(data.rows[0]) : [];
  const acctCol = hasCols.includes("is_retirement") ? "is_retirement" : "account_type";
  const cols = ["ticker", "institution_name", "account_name", acctCol, "value"];
  const tableEl = document.createElement("div");
  view.appendChild(tableEl);
  renderTable(tableEl, cols, data.rows, {
    totals: { ticker: "TOTAL", value: data.total },
    valueFields: ["value"],
  });
}

function showConcentration(view, data) {
  view.innerHTML = `<h2>Concentration</h2><p class="page-subtitle">By asset class &middot; <span class="total-value">${fmtDollar(data.total)}</span> total</p>`;

  // Donut: asset_class → sum of value
  const classMap = {};
  for (const r of data.rows) {
    classMap[r.asset_class] = (classMap[r.asset_class] || 0) + r.value;
  }
  renderDonut(view, Object.keys(classMap), Object.values(classMap), "By Asset Class");

  const hasCols = data.rows.length > 0 ? Object.keys(data.rows[0]) : [];
  const acctCols = hasCols.includes("is_retirement") ? ["is_retirement"] : hasCols.includes("account_type") ? ["account_type"] : [];
  const cols = ["asset_class", "market_segment", "region", ...acctCols, "value", "pct_of_portfolio"];
  const tableEl = document.createElement("div");
  view.appendChild(tableEl);
  renderTable(tableEl, cols, data.rows, {
    totals: { asset_class: "TOTAL", value: data.total },
    valueFields: ["value"],
    pctFields: ["pct_of_portfolio"],
    total: data.total,
  });
}

function showDecomposition(view, data) {
  view.innerHTML = `<h2>Decomposition</h2><p class="page-subtitle">Look-through fund analysis &middot; <span class="total-value">${fmtDollar(data.total)}</span> total</p>`;

  const classMap = {};
  for (const r of data.rows) {
    classMap[r.asset_class] = (classMap[r.asset_class] || 0) + r.value;
  }
  renderDonut(view, Object.keys(classMap), Object.values(classMap), "By Asset Class (Look-through)");

  const hasCols = data.rows.length > 0 ? Object.keys(data.rows[0]) : [];
  const acctCols = hasCols.includes("is_retirement") ? ["is_retirement"] : hasCols.includes("account_type") ? ["account_type"] : [];
  const cols = ["asset_class", "market_segment", "region", ...acctCols, "value", "pct_of_portfolio"];
  const tableEl = document.createElement("div");
  view.appendChild(tableEl);
  renderTable(tableEl, cols, data.rows, {
    totals: { asset_class: "TOTAL", value: data.total },
    valueFields: ["value"],
    pctFields: ["pct_of_portfolio"],
    total: data.total,
  });
}

function showAllocations(view, data) {
  view.innerHTML = `<h2>Allocations</h2><p class="page-subtitle">By account type &middot; <span class="total-value">${fmtDollar(data.total)}</span> total</p>`;

  const hasCols = data.rows.length > 0 ? Object.keys(data.rows[0]) : [];
  const acctCol = hasCols.includes("is_retirement") ? "is_retirement" : "account_type";

  const labelFor = acctCol === "is_retirement"
    ? v => (v === true || v === "true") ? "Retirement" : "Non-Retirement"
    : v => String(v);

  const typeMap = {};
  for (const r of data.rows) {
    const key = labelFor(r[acctCol]);
    typeMap[key] = (typeMap[key] || 0) + r.total_value;
  }
  renderDonut(view, Object.keys(typeMap), Object.values(typeMap), "By Account Type");

  const cols = [acctCol, "institution_name", "total_value", "pct_of_portfolio"];
  const tableEl = document.createElement("div");
  view.appendChild(tableEl);
  renderTable(tableEl, cols, data.rows, {
    totals: { [acctCol]: "TOTAL", total_value: data.total },
    valueFields: ["total_value"],
    pctFields: ["pct_of_portfolio"],
    total: data.total,
  });
}

function showPreciousMetals(view, data) {
  view.innerHTML = `<h2>Precious Metals</h2><p class="page-subtitle">Physical &amp; ETF holdings &middot; <span class="total-value">${fmtDollar(data.metals_total)}</span> metals</p>`;

  const hasCols = data.rows.length > 0 ? Object.keys(data.rows[0]) : [];
  const acctCol = hasCols.includes("is_retirement") ? "is_retirement" : "account_type";
  const cols = ["institution_name", "account_name", acctCol, "ticker", "value", "pct_of_portfolio"];
  const totals = {
    institution_name: "Metals total",
    value: data.metals_total,
  };
  const footerRows = [totals];
  if (data.metals_total !== data.total) {
    footerRows.push({ institution_name: "Portfolio total", value: data.total });
  }

  // Custom two-row footer: render table without totals, then add footer manually
  renderTable(view, cols, data.rows, {
    totals: { institution_name: "Metals total", value: data.metals_total },
    valueFields: ["value"],
    pctFields: ["pct_of_portfolio"],
    total: data.total,
  });
}

// ── Router ──────────────────────────────────────────────────────────────────

const ROUTES = {
  "/positions": { api: "/api/positions", show: showPositions },
  "/concentration": { api: "/api/concentration", show: showConcentration },
  "/decomposition": { api: "/api/decomposition", show: showDecomposition },
  "/allocations": { api: "/api/allocations", show: showAllocations },
  "/precious-metals": { api: "/api/precious-metals", show: showPreciousMetals },
};

async function render() {
  const hash = window.location.hash.replace(/^#/, "") || "/positions";
  const route = ROUTES[hash];
  const view = document.getElementById("view");

  // Highlight active nav link
  for (const link of document.querySelectorAll(".nav-link")) {
    link.classList.toggle("active", link.getAttribute("href") === "#" + hash);
  }

  if (!route) {
    view.innerHTML = `<p class="error">Unknown route: ${hash}</p>`;
    return;
  }

  view.innerHTML = `<p class="loading">Loading…</p>`;

  try {
    const data = await fetchData(route.api);
    route.show(view, data);
  } catch (err) {
    view.innerHTML = `<p class="error">Error: ${err.message}</p>`;
  }
}

window.addEventListener("hashchange", render);
window.addEventListener("DOMContentLoaded", async () => {
  const themeToggleEl = document.getElementById("theme-toggle");
  const anonymizeToggleEl = document.getElementById("anonymize-toggle");
  const retirementToggleEl = document.getElementById("retirement-toggle");
  const savedAnonymize = getSavedAnonymize();
  const savedByRetirement = getSavedByRetirement();

  applyTheme(getInitialTheme());
  if (savedAnonymize !== null) anonymizeToggleEl.checked = savedAnonymize;
  _anonymize = anonymizeToggleEl.checked;
  if (savedByRetirement !== null) retirementToggleEl.checked = savedByRetirement;
  _byRetirement = retirementToggleEl.checked;

  try {
    const cfg = await fetch("/api/config").then(r => r.json());
    if (cfg.anonymize_locked) {
      _anonymize = true;
      anonymizeToggleEl.checked = true;
      anonymizeToggleEl.disabled = true;
      saveAnonymize(true);
    }
  } catch (_) {}

  themeToggleEl.addEventListener("change", e => {
    const theme = e.target.checked ? DARK_THEME : LIGHT_THEME;
    applyTheme(theme);
    saveTheme(theme);
    render();
  });

  anonymizeToggleEl.addEventListener("change", e => {
    _anonymize = e.target.checked;
    saveAnonymize(_anonymize);
    render();
  });

  retirementToggleEl.addEventListener("change", e => {
    _byRetirement = e.target.checked;
    saveByRetirement(_byRetirement);
    render();
  });

  render();
});
