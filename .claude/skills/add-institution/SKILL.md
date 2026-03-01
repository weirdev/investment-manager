---
name: add-institution
description: Add support for a new financial institution
---

Add support for a new financial institution: $ARGUMENTS

Work through the following steps in order. Read the existing parser implementations in `src/investment_manager/parsers/` before writing anything — match their patterns exactly.

---

## 1. Understand the export format

Read the raw CSV files in `personal_data/raw_account_details/<institution>/` to understand:
- File structure (single flat CSV vs. multi-section with interleaved headers)
- Encoding (UTF-8 BOM is common — use `encoding="utf-8-sig"`)
- Which columns contain the ticker symbol and current market value
- How account names appear and how to detect section boundaries if multi-section
- What rows to skip (cash, totals, linked external accounts, accounts with no positions, etc.)
- A reliable set of header columns or first-line pattern for `can_parse()` detection

---

## 2. Create the parser

**Filename**: use underscores for the Python module even if the institution dir uses hyphens
(e.g., `interactive_brokers.py` for `interactive-brokers/`).

Create `src/investment_manager/parsers/<institution_lowercase>.py` subclassing `InstitutionParser`.

- `can_parse(file_path)` — detect by header columns or first-line content; return False on any exception
- `parse(file_path)` — return `list[Position]` with institution_name, account_name, account_type (from `registry.validate()`), owner (from `registry.get_owner()`), ticker, value
- Strip/clean tickers (trailing `**`, whitespace, etc.) and skip rows with no parseable value
- Use `self._registry.validate(INSTITUTION, account_name)` for account_type
- Match the code style in existing parsers

---

## 3. Register the parser

In `src/investment_manager/pipeline.py`, import the new parser class and add it to `_PARSERS`.

---

## 4. Create an anonymized test fixture

Create `tests/fixtures/john/<institution>/` and add a minimal CSV fixture with:
- At least 2 accounts and 3–4 positions total
- Realistic but anonymized tickers and round-number values
- All structural quirks of the real format (interleaved headers, trailing commas, etc.)
- Cash/total rows included so the parser's skip logic is exercised
- If the real data has accounts with no positions (e.g., cash-only accounts), include one — the parser must not emit any positions for it

The "reject nonexistent file" test in step 5 doesn't need a real fixture file — a nonexistent path works because `can_parse` catches all exceptions.

---

## 5. Write parser tests

Create `tests/test_<institution_underscored>_parser.py` following the pattern in the existing test files. Cover:

- `can_parse` detects the fixture; rejects a nonexistent file path
- Correct position count (verifies cash/total/cash-only-account rows are skipped)
- `institution_name` is set correctly
- A specific `value` is parsed correctly
- Account names are preserved
- `account_type == "unknown"` when registry is empty
- Registry lookup sets `account_type` correctly

Run `python -m uv run pytest tests/ -v` and fix any failures before continuing.

---

## 6. Add accounts to the registry

Add the institution's accounts to `personal_data/known-accounts.csv` with the correct `account_type` and `is_retirement` values. Account names must match exactly what the parser produces (verify by reading the raw CSV).

---

## 7. Create the asset mapping

**Directory name**: must exactly match the institution subdir under `raw_account_details/`
(e.g., `personal_data/interactive-brokers/` for `raw_account_details/interactive-brokers/`).

Create `personal_data/<institution>/<institution>-asset-mapping.csv` with columns:
`account_type,raw_ticker,raw_description,canonical_ticker`

Include an entry for every ticker that appears in the real position data. If no ticker remapping is needed, set `canonical_ticker = raw_ticker`. The pipeline's `_discover_mapping_paths()` will pick this file up automatically — no code changes needed.

---

## 8. Extend asset metadata

Check `personal_data/asset-metadata.csv` first — many common tickers (VOO, VWO, VXUS, GLD, etc.) are likely already present. Only add rows for tickers not yet in the file.

For each new `canonical_ticker`, add a row with:
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
