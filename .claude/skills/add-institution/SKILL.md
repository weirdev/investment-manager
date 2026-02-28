---
name: add-institution
description: Add support for a new financial institution
---

Add support for a new financial institution: $ARGUMENTS

Work through the following steps in order. Read the existing Fidelity and Schwab implementations before writing anything — match their patterns exactly.

---

## 1. Understand the export format

Read the raw CSV files in `personal_data/raw_account_details/<institution>/` to understand:
- File structure (single flat CSV vs. multi-section)
- Encoding (UTF-8 BOM is common — use `encoding="utf-8-sig"`)
- Which columns contain the ticker symbol and current market value
- How account names appear and how to detect section boundaries if multi-section
- What rows to skip (cash, totals, linked external accounts, etc.)
- A reliable set of header columns or first-line pattern for `can_parse()` detection

---

## 2. Create the parser

Create `src/investment_manager/parsers/<institution_lowercase>.py` subclassing `InstitutionParser`.

- `can_parse(file_path)` — detect by header columns or first-line content; return False on any exception
- `parse(file_path)` — return `list[Position]` with institution_name, account_name, account_type (from registry), ticker, value
- Strip/clean tickers (trailing `**`, whitespace, etc.) and skip rows with no parseable value
- Use `self._registry.validate(INSTITUTION, account_name)` for account_type
- Match the code style in `parsers/fidelity.py` and `parsers/schwab.py`

---

## 3. Register the parser

In `src/investment_manager/pipeline.py`, import the new parser class and add it to `_PARSERS`.

---

## 4. Create an anonymized test fixture

Create `tests/fixtures/<institution>/` and add a minimal CSV fixture with:
- At least 2 accounts and 3–4 positions total
- Realistic but anonymized tickers and round-number values
- All structural quirks of the real format (section headers, trailing commas, etc.)
- Cash/total rows included so the parser's skip logic is exercised

---

## 5. Write parser tests

Create `tests/test_<institution>_parser.py` following the pattern in `tests/test_fidelity_parser.py` and `tests/test_schwab_parser.py`. Cover:

- `can_parse` detects the fixture; rejects a nonexistent file
- Correct position count (verifies cash/total rows are skipped)
- `institution_name` is set correctly
- A specific `value` is parsed correctly
- Account names are preserved
- `account_type == "unknown"` when registry is empty
- Registry lookup sets `account_type` correctly

Run `python -m uv run pytest tests/ -v` and fix any failures before continuing.

---

## 6. Add accounts to the registry

Add the institution's accounts to `personal_data/known-accounts.csv` with the correct `account_type` and `is_retirement` values. Account names must match exactly what the parser produces.

---

## 7. Create the asset mapping

Create `personal_data/<institution>/<institution>-asset-mapping.csv` with columns:
`account_type,raw_ticker,raw_description,canonical_ticker`

Include an entry for every ticker that appears in the real position data. If no ticker remapping is needed, set `canonical_ticker = raw_ticker`. The pipeline's `_discover_mapping_paths()` will pick this file up automatically — no code changes needed.

---

## 8. Extend asset metadata

For each new `canonical_ticker` not already in `personal_data/asset-metadata.csv`, add a row with:
`canonical_ticker,asset_class,security_type,market_segment,region`

Keep the file sorted alphabetically by `canonical_ticker`. Verify coverage:
```
python -m uv run python -c "
import polars as pl
from investment_manager import pipeline
df = pipeline.run()
inst = df.filter(pl.col('institution_name') == '<InstitutionName>')
missing = inst.filter(pl.col('asset_class') == 'unknown').select(['ticker','account_type'])
print(f'Missing metadata: {missing.height}')
if missing.height: print(missing)
"
```

---

## 9. Final verification

```
python -m uv run pytest tests/ -v        # all tests pass
python -m uv run invest positions        # no warnings about unknown parsers
python -m uv run invest concentration   # new institution appears in output
```
