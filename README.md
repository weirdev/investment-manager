# investment-manager

A personal finance tool that aggregates investment positions across multiple brokerage accounts, enriches them with asset metadata, and provides portfolio concentration and allocation analysis.

---

## Overview

Drop your brokerage CSV exports into `personal_data/raw_account_details/<owner>/<institution>/` and run a single command to see your full portfolio consolidated across all accounts — with positions classified by asset class, market segment, region, and account type.

**Supported institutions:** Fidelity, Schwab, Interactive Brokers, Alight (extensible via the `/add-institution` Claude command)

---

## Setup

**Requirements:** Python 3.11+, [`uv`](https://github.com/astral-sh/uv)

```bash
pip install uv
python -m uv sync
```

### Directory structure

```
personal_data/
├── raw_account_details/
│   └── <owner>/               ← one directory per owner (e.g. "wesley", "Family Trust")
│       ├── fidelity/          ← drop Fidelity CSV exports here
│       ├── schwab/            ← drop Schwab CSV exports here
│       ├── interactive-brokers/  ← drop IB Flex Query exports here
│       └── alight/            ← drop Alight 401(k) exports here
├── fidelity/
│   └── fidelity-asset-mapping.csv
├── schwab/
│   └── schwab-asset-mapping.csv
├── interactive-brokers/
│   └── interactive-brokers-asset-mapping.csv
├── alight/
│   └── alight-asset-mapping.csv
├── known-accounts.csv         ← maps account numbers → account types and owners
├── asset-metadata.csv         ← maps tickers → asset class, region, etc.
└── fund-compositions.csv      ← (optional) splits composite tickers into component asset classes
```

`personal_data/` is gitignored. The schema files at `personal_data/*.csv` define what metadata is expected.

Shared accounts (e.g. a joint trust held by multiple owners) can appear in multiple owner directories. The pipeline deduplicates on `(institution, account, ticker)` so they count once in the aggregate view.

---

## CLI Commands

All commands support `--data-dir <path>` to override the default data directory and `--anonymize` to normalize all amounts so the portfolio sums to ~$100,000 (preserving relative weights, useful for screenshots or demos).

### `invest positions`

Aggregates all positions grouped by ticker, showing total value and per-account breakdown.

```bash
python -m uv run invest positions
```

**Example output:**
```
shape: (12, 5)
┌────────┬─────────────┬──────────────────────────────────────┬──────────────┬───────────┐
│ ticker ┆ total_value ┆ account_name                         ┆ account_type ┆ value     │
│ ---    ┆ ---         ┆ ---                                  ┆ ---          ┆ ---       │
│ str    ┆ f64         ┆ str                                  ┆ str          ┆ f64       │
╞════════╪═════════════╪══════════════════════════════════════╪══════════════╪═══════════╡
│ VTI    ┆ 85432.10    ┆ Individual Brokerage                 ┆ brokerage    ┆ 42150.00  │
│ VTI    ┆ 85432.10    ┆ Roth Contributory IRA ...567         ┆ roth_ira     ┆ 43282.10  │
│ VXUS   ┆ 31200.00    ┆ Roth Contributory IRA ...567         ┆ roth_ira     ┆ 18700.00  │
│ VXUS   ┆ 31200.00    ┆ Roth IRA                             ┆ roth_ira     ┆ 12500.00  │
│ BND    ┆ 22800.00    ┆ Family Trust ...718                  ┆ trust        ┆ 22800.00  │
│ VNQ    ┆ 14500.00    ┆ Family Trust ...718                  ┆ trust        ┆ 8200.00   │
│ VNQ    ┆ 14500.00    ┆ Individual Brokerage                 ┆ brokerage    ┆ 6300.00   │
│ GLD    ┆ 11200.00    ┆ Family Trust ...718                  ┆ trust        ┆ 11200.00  │
│ SPAXX  ┆ 5100.00     ┆ Individual Brokerage                 ┆ brokerage    ┆ 5100.00   │
│ TSLA   ┆ 4300.00     ┆ Individual Brokerage                 ┆ brokerage    ┆ 4300.00   │
│ MSFT   ┆ 3800.00     ┆ Traditional IRA                      ┆ traditional… ┆ 3800.00   │
│ GOOGL  ┆ 2950.00     ┆ Individual Brokerage                 ┆ brokerage    ┆ 2950.00   │
└────────┴─────────────┴──────────────────────────────────────┴──────────────┴───────────┘
Total: $181,282.10
```

### `invest concentration`

Shows portfolio concentration broken down by asset class, market segment, region, and account type — with each row's percentage of total portfolio value.

```bash
python -m uv run invest concentration
```

**Example output:**
```
shape: (14, 6)
┌──────────────────┬──────────────────────┬───────────┬──────────────┬───────────┬────────────────────┐
│ asset_class      ┆ market_segment       ┆ region    ┆ account_type ┆ value     ┆ pct_of_portfolio   │
│ ---              ┆ ---                  ┆ ---       ┆ ---          ┆ ---       ┆ ---                │
│ str              ┆ str                  ┆ str       ┆ str          ┆ f64       ┆ f64                │
╞══════════════════╪══════════════════════╪═══════════╪══════════════╪═══════════╪════════════════════╡
│ cash             ┆                      ┆ us        ┆ brokerage    ┆ 5100.00   ┆ 2.83               │
│ equities         ┆ large_cap            ┆ us        ┆ brokerage    ┆ 11050.00  ┆ 6.14               │
│ equities         ┆ large_cap            ┆ us        ┆ traditional… ┆ 3800.00   ┆ 2.11               │
│ equities         ┆ total_market         ┆ ex_us     ┆ roth_ira     ┆ 31200.00  ┆ 17.33              │
│ equities         ┆ total_market         ┆ us        ┆ brokerage    ┆ 42150.00  ┆ 23.42              │
│ equities         ┆ total_market         ┆ us        ┆ roth_ira     ┆ 43282.10  ┆ 24.05              │
│ fixed_income     ┆ total_market         ┆ us        ┆ trust        ┆ 22800.00  ┆ 12.67              │
│ precious_metals  ┆ gold                 ┆ global    ┆ trust        ┆ 11200.00  ┆ 6.22               │
│ real_estate      ┆ reit                 ┆ us        ┆ brokerage    ┆ 6300.00   ┆ 3.50               │
│ real_estate      ┆ reit                 ┆ us        ┆ trust        ┆ 8200.00   ┆ 4.56               │
└──────────────────┴──────────────────────┴───────────┴──────────────┴───────────┴────────────────────┘
Total: $181,282.10
```

### `invest allocations`

Shows total value and portfolio percentage grouped by account type and institution.

```bash
python -m uv run invest allocations
```

**Example output:**
```
shape: (6, 4)
┌────────────────┬──────────────┬─────────────┬────────────────────┐
│ account_type   ┆ institution  ┆ total_value ┆ pct_of_portfolio   │
│ ---            ┆ ---          ┆ ---         ┆ ---                │
│ str            ┆ str          ┆ f64         ┆ f64                │
╞════════════════╪══════════════╪═════════════╪════════════════════╡
│ roth_ira       ┆ Schwab       ┆ 61982.10    ┆ 34.45              │
│ brokerage      ┆ Fidelity     ┆ 55900.00    ┆ 31.07              │
│ trust          ┆ Schwab       ┆ 42200.00    ┆ 23.46              │
│ brokerage      ┆ Schwab       ┆ 8100.00     ┆ 4.50               │
│ traditional_ira┆ Schwab       ┆ 7200.00     ┆ 4.00               │
│ roth_ira       ┆ Fidelity     ┆ 4900.00     ┆ 2.72               │
└────────────────┴──────────────┴─────────────┴────────────────────┘
Total: $181,282.10
```

### `invest owners`

Shows total value and portfolio percentage grouped by owner.

```bash
python -m uv run invest owners
```

**Example output:**
```
shape: (2, 3)
┌──────────────┬─────────────┬────────────────────┐
│ owner        ┆ total_value ┆ pct_of_portfolio   │
│ ---          ┆ ---         ┆ ---                │
│ str          ┆ f64         ┆ f64                │
╞══════════════╪═════════════╪════════════════════╡
│ wesley       ┆ 160982.10   ┆ 89.47              │
│ Family Trust ┆ 18200.00    ┆ 10.12              │
└──────────────┴─────────────┴────────────────────┘
Total: $181,282.10
```

### `invest decomposition`

Shows look-through concentration: composite fund positions are split into their component asset classes using `personal_data/fund-compositions.csv`. Positions with no composition entry are passed through unchanged. Output format is identical to `invest concentration`.

```bash
python -m uv run invest decomposition
python -m uv run invest decomposition --no-account-type   # collapse across account types
```

### `invest precious-metals`

Shows precious metals holdings grouped by institution, account, and ticker — with value and percentage of the full portfolio.

```bash
python -m uv run invest precious-metals
```

**Example output:**
```
shape: (1, 6)
┌──────────────────┬─────────────────────┬──────────────┬────────┬───────────┬────────────────────┐
│ institution_name ┆ account_name        ┆ account_type ┆ ticker ┆ value     ┆ pct_of_portfolio   │
│ ---              ┆ ---                 ┆ ---          ┆ ---    ┆ ---       ┆ ---                │
│ str              ┆ str                 ┆ str          ┆ str    ┆ f64       ┆ f64                │
╞══════════════════╪═════════════════════╪══════════════╪════════╪═══════════╪════════════════════╡
│ Schwab           ┆ W_Fam_Trust_1 ...718┆ trust        ┆ GLD    ┆ 11200.00  ┆ 6.22               │
└──────────────────┴─────────────────────┴──────────────┴────────┴───────────┴────────────────────┘
Precious metals total: $11,200.00
Total: $181,282.10
```

### `invest serve`

Starts a local web dashboard with sortable tables, column filters, column picker, interactive charts, and per-view sidebar navigation.

```bash
python -m uv run invest serve
python -m uv run invest serve --host 0.0.0.0 --port 9000
python -m uv run invest serve --anonymize   # lock all API responses to anonymized values
```

Open `http://127.0.0.1:8000` in your browser. Views: Positions, Concentration, Decomposition, Allocations, Precious Metals.

The sidebar includes an **Anonymize** toggle that normalizes all displayed amounts to ~$100,000 on the fly. Passing `--anonymize` to `serve` locks this toggle to the enabled state for all visitors, regardless of their individual toggle setting.

When column filters are active, the percentage column header changes to **"Pct of Filtered"** and row percentages are renormalized so they always sum to 100% across the visible rows. The footer percentage cell shows 100% to reflect this. Removing all filters reverts to the original portfolio-relative percentages.

---

## Data Files

### `personal_data/known-accounts.csv`

Maps each brokerage account to its account type and owner. The registry keys on `(institution_name, account_number)` — `account_number` must match exactly what the parser emits (verify by reading the raw CSV). For institutions whose exports have no separate account number field (e.g. Alight), the parser uses the account name as the account number.

```csv
institution_name,account_name,account_number,account_type,is_retirement,owner
Fidelity,Individual Brokerage,123456789,brokerage,false,Wesley
Fidelity,Roth IRA,987654321,roth_ira,true,Wesley
Schwab,Roth_Contributory_IRA ...567,567,roth_ira,true,Wesley
Schwab,W_Fam_Trust_1 ...718,718,trust,false,Weirather Family Trust
Alight,UBS 401(k) Plan,UBS 401(k) Plan,401k,true,Meijia
```

**Supported account types:** `brokerage`, `roth_ira`, `traditional_ira`, `trust`, `401k`, `529`, `hsa`

The `owner` column is optional — accounts without it default to `"unknown"`. Use any label that makes sense for your situation (a name, an entity, `"joint"`, etc.).

### `personal_data/<institution>/<institution>-asset-mapping.csv`

Maps raw tickers from each institution to canonical tickers. Use this to normalize institution-specific fund names or ticker variations.

```csv
account_type,raw_ticker,raw_description,canonical_ticker
roth_ira,VTI,,VTI
trust,INVESCO STBL VAL B1,,INVESCO-STBL-VAL-B1
```

If no remapping is needed, set `canonical_ticker = raw_ticker`. New mapping files are discovered automatically — no code changes required.

### `personal_data/asset-metadata.csv`

Classifies each canonical ticker by asset class, security type, market segment, and region. Positions not found here show `unknown` in analysis outputs.

```csv
canonical_ticker,asset_class,security_type,market_segment,region
VTI,equities,etf,total_market,us
VXUS,equities,etf,total_market,ex_us
BND,fixed_income,etf,total_market,us
GLD,precious_metals,etf,gold,global
SPAXX,cash,money_market,,us
```

**Asset classes:** `equities`, `fixed_income`, `real_estate`, `precious_metals`, `cash`
**Security types:** `etf`, `stock`, `mutual_fund`, `money_market`, `stable_value`
**Regions:** `us`, `ex_us`, `emerging`, `global`

---

## Adding a New Institution

Use the built-in Claude command to walk through the full setup process:

```
/add-institution Vanguard
```

This command guides you through:

1. **Understand the export format** — read the raw CSVs to learn the file structure, encoding, and key columns
2. **Create the parser** — subclass `InstitutionParser` with `can_parse()` and `parse()` methods
3. **Register the parser** — add it to `_PARSERS` in `pipeline.py`
4. **Create an anonymized test fixture** — a minimal CSV covering all structural quirks
5. **Write parser tests** — covering detection, position count, values, account names, and registry integration
6. **Add accounts to the registry** — entries in `personal_data/known-accounts.csv`
7. **Create the asset mapping** — `personal_data/<institution>/<institution>-asset-mapping.csv`
8. **Extend asset metadata** — add any new tickers to `personal_data/asset-metadata.csv`
9. **Final verification** — run tests, `invest positions`, and `invest concentration`

### Parser structure

```python
# src/investment_manager/parsers/mybroker.py
from pathlib import Path
from ..models import Position
from ..registry import AccountRegistry
from .base import InstitutionParser

INSTITUTION = "MyBroker"

class MyBrokerParser(InstitutionParser):
    def __init__(self, registry: AccountRegistry | None = None) -> None:
        self._registry = registry or AccountRegistry()

    @classmethod
    def can_parse(cls, file_path: Path) -> bool:
        try:
            with file_path.open(encoding="utf-8-sig") as f:
                headers = f.readline()
            return "MyBroker" in headers
        except Exception:
            return False

    def parse(self, file_path: Path) -> list[Position]:
        # Return list[Position] with institution_name, account_name, account_number,
        # account_type (from registry.validate(INSTITUTION, account_number)),
        # owner (from registry.get_owner(INSTITUTION, account_number)),
        # ticker, value
        ...
```

Then add `MyBrokerParser` to `_PARSERS` in `pipeline.py` — auto-discovery handles everything else.

---

## Running Tests

```bash
python -m uv run pytest tests/ -v
npm run test:frontend
```

Test fixtures live under `tests/fixture_data/` and include raw exports plus test-owned metadata, registry, and compositions files.

### Frontend Browser Tests

Frontend tests use Playwright against the real FastAPI app served from fixture data in `tests/fixture_data`.

Setup:

```bash
npm install
npx playwright install chromium
```

Run:

```bash
npm run test:frontend
npm run test:frontend:headed
npm run test:frontend:update
```

`test:frontend:update` refreshes screenshot baselines after an intentional UI change.

---

## Architecture

```
src/investment_manager/
├── models.py          # Position + Account dataclasses (includes owner field)
├── registry.py        # AccountRegistry: loads known-accounts.csv
├── paths.py           # Centralised default paths (data dir, compositions, metadata, etc.)
├── parsers/
│   ├── base.py                 # Abstract InstitutionParser
│   ├── utils.py                # Shared CSV parsing helpers
│   ├── fidelity.py             # Fidelity flat-CSV parser
│   ├── schwab.py               # Schwab multi-section parser
│   ├── interactive_brokers.py  # Interactive Brokers Flex Query parser
│   └── alight.py               # Alight 401(k) flat-CSV parser
├── pipeline.py        # Discovers CSVs, selects parsers, deduplicates, merges to DataFrame
├── enrichment.py      # Joins asset mapping + metadata onto positions
├── decomposition.py   # Fund look-through: expands composite tickers into component rows
├── analysis.py        # aggregate_positions(), concentration_breakdown(), precious_metals_by_account(), allocation_breakdown(), owner_breakdown()
├── server.py          # FastAPI web dashboard server and JSON API routes
├── web/               # SPA frontend (index.html, app.js, style.css)
└── cli.py             # Typer CLI: invest positions / concentration / decomposition / precious-metals / allocations / owners / serve
```

**Pipeline flow:**
1. `pipeline.run()` recursively finds all `*.csv` files under `raw_account_details/`
2. Each file is matched to a parser via `can_parse()`
3. Parsers emit `list[Position]` (each with an `owner` from the registry); all are merged
4. Positions are deduplicated on `(institution_name, account_number, ticker)` — shared accounts across owner directories count once
5. `_discover_mapping_paths()` traverses `<owner>/<institution>/` dirs, collecting `*-asset-mapping.csv` paths (each institution discovered once)
6. `enrich()` joins the mapping (raw → canonical ticker) then the metadata (ticker → asset class)
7. If `anonymize=True`, all `value` fields are scaled so the portfolio totals ~$100,000 (positions below $0.01 are floored to $0.01)
