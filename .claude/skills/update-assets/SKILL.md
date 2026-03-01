---
name: update-assets
description: Update institution asset mappings and asset metadata for unmapped positions
---

Map every position that currently shows `asset_class = 'unknown'` to a canonical ticker and asset metadata entry.

If `$ARGUMENTS` is provided, treat it as an institution name filter (e.g. `institution: Fidelity`) and restrict work to that institution. Otherwise, resolve all unknowns across all institutions.

---

## 1. Find unmapped positions

```python
python -m uv run python -c "
import polars as pl, sys
from investment_manager import pipeline
df = pipeline.run()
missing = df.filter(pl.col('asset_class') == 'unknown') \
            .select(['institution_name','ticker','account_name','account_type']) \
            .unique().sort(['institution_name','ticker'])
sys.stdout.buffer.write((f'Missing: {missing.height}\n').encode('utf-8'))
for row in missing.iter_rows(named=True):
    sys.stdout.buffer.write((str(row) + '\n').encode('utf-8'))
" 2>/dev/null
```

The `ticker` column contains the **canonical ticker** after mapping, or the raw ticker if no mapping entry exists yet. If a position has no mapping entry, `ticker` will equal the raw value from the brokerage CSV.

---

## 2. Look up the raw ticker and description

For each unknown ticker, find it in the institution's raw CSV under `personal_data/raw_account_details/<owner>/<institution>/`. Read the file and locate the row — the columns to check depend on the institution:

| Institution | Ticker column | Description column |
|---|---|---|
| Fidelity | `Symbol` | `Description` |
| Schwab | varies by section | fund name in the section header |
| Interactive Brokers | `Symbol` | `Description` |
| Alight | `Fund Name` | `Fund Name` |

Strip any trailing `**` or whitespace from the raw ticker before comparing.

---

## 3. Determine the canonical ticker

- If the raw ticker is a real, publicly traded ticker (ETF, stock, mutual fund with a standard ticker), use it unchanged as the canonical ticker.
- If the raw ticker is a **CUSIP** (9-character alphanumeric like `02508L742`) or other non-standard identifier, create a slug from the fund description: lowercase the description abbreviation, replace spaces with hyphens (e.g. `AC RD 2060 TR III` → `AC-RD-2060-TR-III`). Match the style of existing slugs in `asset-metadata.csv` (e.g. `INVESCO-STBL-VAL-B1`, `SSGA-EXUS-IDX-II`).

---

## 4. Update the institution asset mapping

Read `personal_data/<institution>/<institution>-asset-mapping.csv` (e.g. `personal_data/fidelity/fidelity-asset-mapping.csv`).

Add a row for each unmapped ticker:

```csv
account_type,raw_ticker,raw_description,canonical_ticker
401k,02508L742,AC RD 2060 TR III,AC-RD-2060-TR-III
```

Keep rows **grouped by `account_type`** and **sorted alphabetically by `raw_ticker`** within each group. Note that digits sort before letters (e.g. `02508L742` before `DFIEX`).

If no mapping file exists yet for the institution, create one with the header row.

---

## 5. Update asset metadata

Read `personal_data/asset-metadata.csv`.

For each new canonical ticker, add a row:

```csv
canonical_ticker,asset_class,security_type,market_segment,region
```

Classify using these conventions:

**Asset class:**
- `equities` — stock ETFs, stock mutual funds, target-date funds
- `fixed_income` — bond ETFs, bond mutual funds, stable value funds
- `real_estate` — REIT ETFs
- `precious_metals` — gold/silver ETFs
- `cash` — money market funds, cash equivalents

**Security type:** `etf`, `stock`, `mutual_fund`, `money_market`, `stable_value`

**Market segment** (equities): `large_cap`, `mid_cap`, `small_cap`, `total_market`, `extended_market`, `dividend`, `target_date_<year>`, `sector_<name>`

**Market segment** (fixed_income): `total_market`, `international_bond`, `inflation_protected`; leave blank for `stable_value` and `money_market`.

**Region:** `us`, `ex_us`, `emerging`, `global`

Insert the new rows **alphabetically by `canonical_ticker`**. Keep the file sorted — digits and hyphens sort before letters (e.g. `AC-RD-2060-TR-III` before `BND`).

---

## 6. Verify

```python
python -m uv run python -c "
import polars as pl, sys
from investment_manager import pipeline
df = pipeline.run()
missing = df.filter(pl.col('asset_class') == 'unknown') \
            .select(['institution_name','ticker','account_type']).unique()
sys.stdout.buffer.write((f'Missing: {missing.height}\n').encode('utf-8'))
for row in missing.iter_rows(named=True):
    sys.stdout.buffer.write((str(row) + '\n').encode('utf-8'))
" 2>/dev/null
```

The output must be `Missing: 0` before finishing.
