/* Investment Manager — SPA frontend */

const _cache = {};

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

// ── Fetch helper ────────────────────────────────────────────────────────────

async function fetchData(path) {
  if (_cache[path]) return _cache[path];
  const res = await fetch(path);
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${path}`);
  const data = await res.json();
  _cache[path] = data;
  return data;
}

// ── Table rendering ─────────────────────────────────────────────────────────

function renderTable(container, columns, rows, { totals = null, valueFields = [], pctFields = [] } = {}) {
  let sortCol = null;
  let sortDir = 1; // 1 = asc, -1 = desc

  function buildTable() {
    const sorted = sortCol === null ? [...rows] : [...rows].sort((a, b) => {
      const av = a[sortCol], bv = b[sortCol];
      if (av == null && bv == null) return 0;
      if (av == null) return sortDir;
      if (bv == null) return -sortDir;
      return typeof av === "number"
        ? (av - bv) * sortDir
        : String(av).localeCompare(String(bv)) * sortDir;
    });

    const table = document.createElement("table");

    // thead
    const thead = document.createElement("thead");
    const hrow = document.createElement("tr");
    for (const col of columns) {
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
        container.innerHTML = "";
        container.appendChild(buildTable());
      });
      hrow.appendChild(th);
    }
    thead.appendChild(hrow);
    table.appendChild(thead);

    // tbody
    const tbody = document.createElement("tbody");
    for (const row of sorted) {
      const tr = document.createElement("tr");
      for (const col of columns) {
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
      for (const col of columns) {
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

    return table;
  }

  const wrapper = document.createElement("div");
  wrapper.className = "table-wrapper";
  wrapper.appendChild(buildTable());
  container.appendChild(wrapper);
}

// ── Chart rendering ─────────────────────────────────────────────────────────

function renderDonut(container, labels, values, title) {
  const el = document.createElement("div");
  el.className = "chart-container";
  container.appendChild(el);
  Plotly.newPlot(el, [{
    type: "pie",
    hole: 0.4,
    labels,
    values,
    textinfo: "label+percent",
    hovertemplate: "<b>%{label}</b><br>$%{value:,.2f}<br>%{percent}<extra></extra>",
  }], {
    title: { text: title || "", font: { size: 14 }, y: 0.98, yanchor: "top", yref: "container" },
    height: 500,
    margin: { t: 110, b: 110, l: 60, r: 60 },
    showlegend: false,
  }, { responsive: true });
}

function renderTreemap(container, labels, values, title) {
  const el = document.createElement("div");
  el.className = "chart-container";
  el.style.maxWidth = "700px";
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
    title: { text: title || "", font: { size: 14 } },
    height: 420,
    margin: { t: 40, b: 10, l: 10, r: 10 },
  }, { responsive: true });
}

// ── Page renderers ──────────────────────────────────────────────────────────

function showPositions(view, data) {
  view.innerHTML = "<h2>Positions</h2>";

  // Treemap: unique ticker → sum of total_value
  const tickerMap = {};
  for (const r of data.rows) {
    if (!(r.ticker in tickerMap)) tickerMap[r.ticker] = r.total_value;
  }
  const labels = Object.keys(tickerMap);
  const values = Object.values(tickerMap);
  renderTreemap(view, labels, values, "Portfolio by Ticker");

  const cols = ["ticker", "institution_name", "account_name", "account_type", "value"];
  renderTable(view, cols, data.rows, {
    totals: { ticker: "TOTAL", value: data.total },
    valueFields: ["value"],
  });
}

function showConcentration(view, data) {
  view.innerHTML = "<h2>Concentration</h2>";

  // Donut: asset_class → sum of value
  const classMap = {};
  for (const r of data.rows) {
    classMap[r.asset_class] = (classMap[r.asset_class] || 0) + r.value;
  }
  renderDonut(view, Object.keys(classMap), Object.values(classMap), "By Asset Class");

  const hasCols = data.rows.length > 0 ? Object.keys(data.rows[0]) : [];
  const cols = ["asset_class", "market_segment", "region", ...(hasCols.includes("account_type") ? ["account_type"] : []), "value", "pct_of_portfolio"];
  renderTable(view, cols, data.rows, {
    totals: { asset_class: "TOTAL", value: data.total },
    valueFields: ["value"],
    pctFields: ["pct_of_portfolio"],
  });
}

function showDecomposition(view, data) {
  view.innerHTML = "<h2>Decomposition</h2>";

  const classMap = {};
  for (const r of data.rows) {
    classMap[r.asset_class] = (classMap[r.asset_class] || 0) + r.value;
  }
  renderDonut(view, Object.keys(classMap), Object.values(classMap), "By Asset Class (Look-through)");

  const hasCols = data.rows.length > 0 ? Object.keys(data.rows[0]) : [];
  const cols = ["asset_class", "market_segment", "region", ...(hasCols.includes("account_type") ? ["account_type"] : []), "value", "pct_of_portfolio"];
  renderTable(view, cols, data.rows, {
    totals: { asset_class: "TOTAL", value: data.total },
    valueFields: ["value"],
    pctFields: ["pct_of_portfolio"],
  });
}

function showAllocations(view, data) {
  view.innerHTML = "<h2>Allocations</h2>";

  const typeMap = {};
  for (const r of data.rows) {
    typeMap[r.account_type] = (typeMap[r.account_type] || 0) + r.total_value;
  }
  renderDonut(view, Object.keys(typeMap), Object.values(typeMap), "By Account Type");

  const cols = ["account_type", "institution_name", "total_value", "pct_of_portfolio"];
  renderTable(view, cols, data.rows, {
    totals: { account_type: "TOTAL", total_value: data.total },
    valueFields: ["total_value"],
    pctFields: ["pct_of_portfolio"],
  });
}

function showPreciousMetals(view, data) {
  view.innerHTML = "<h2>Precious Metals</h2>";

  const cols = ["institution_name", "account_name", "account_type", "ticker", "value", "pct_of_portfolio"];
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
window.addEventListener("DOMContentLoaded", render);
