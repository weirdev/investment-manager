# Project Rules

## Privacy

File contents from the `personal_data/` directory must never be written to project plans, implementation plans, or any other planning artifacts.

---

## Architecture Invariants

- `Position` fields: `institution_name`, `account_name`, `account_number`, `account_type`, `owner`, `ticker`, `value`
- Registry keys on `(institution_name, account_number)` — never on `account_name`. Use `registry.validate(INSTITUTION, account_number)` and `registry.get_owner(INSTITUTION, account_number)`.
- Deduplication key in pipeline: `(institution_name, account_number, ticker)` — shared accounts across owner dirs count once.
- `_PARSERS` in `pipeline.py` is the only place to register a new parser.
- Raw export CSVs must be named `<YYYY-MM-DD>_<original-filename>.csv`. `pipeline.run()` keeps only the newest-dated file per directory (ignoring superseded exports); a missing or duplicated leading datestamp raises `MissingExportDateError` / `AmbiguousExportDateError` rather than guessing.
- Asset mapping discovery is automatic: `_discover_mapping_paths()` finds `*-asset-mapping.csv` under `personal_data/<institution-dir>/` — no code changes needed when adding a new mapping file.
- Institutions change export formats without notice (header casing, summary-row labels, etc.) — parsers should tolerate known variants rather than assume a format is fixed. Example: Schwab renamed its per-account summary row from `"Account Total"` to `"Positions Total"`; `schwab.py`'s `_SKIP_SYMBOLS` recognizes both.
- Fidelity leaves the `Symbol` column blank for some proprietary 401(k) collective investment trust funds (no public ticker). `fidelity.py` falls back to the `Description` text as a pseudo-ticker rather than dropping the position — silently skipping blank-symbol rows previously understated real account values by 5-6 figures. Map the resulting description-based ticker via `/update-assets` like any other unknown ticker.
- Committed reference data (public, not user-specific) lives in `src/investment_manager/data/` and is resolved via package-relative constants in `paths.py` (`DEFAULT_MARKET_WEIGHTS_PATH`), never through `DataPaths` (which is entirely derived from the gitignored `personal_data/`). `global-market-cap-weights.csv` is the `invest rebalancing` benchmark — edit it in place to tune weights.
- `rebalancing.market_cap_comparison(df, market_weights)` expects an already look-through-decomposed frame (same as `analysis.concentration_breakdown` gets on the decomposition path); it filters to `equities` and renormalizes internally. Tiers are `large_cap` / `mid_cap` / `small_cap` / `emerging` (emerging markets is its own tier regardless of cap); value that doesn't resolve to a tier is redistributed by the benchmark's developed-market tier ratios.

---

## Skills (Claude Slash Commands)

| Command | Purpose |
|---|---|
| `/add-institution <Name>` | Full workflow: parser → tests → registry → asset mapping → metadata |
| `/update-accounts [glob]` | Register unrecognized accounts into `known-accounts.csv` |
| `/update-assets [institution: Name]` | Map unknown tickers to canonical tickers and asset metadata |
| `/update-readme` | Sync README to reflect all changes since the last README commit |
| `/update-claude-md` | Sync CLAUDE.md to reflect all changes since the last CLAUDE.md commit |
| `/frontend-design` | Create distinctive, production-grade frontend interfaces |

---

## Running

```bash
python -m uv run invest positions
python -m uv run invest concentration
python -m uv run invest decomposition
python -m uv run invest precious-metals
python -m uv run invest allocations
python -m uv run invest owners
python -m uv run invest rebalancing
python -m uv run invest serve
python -m uv run pytest tests/ -v
```

`uv` is not on PATH — always invoke as `python -m uv`.
