# Project Rules

## Privacy

File contents from the `personal_data/` directory must never be written to project plans, implementation plans, or any other planning artifacts.

---

## Architecture Invariants

- `Position` fields: `institution_name`, `account_name`, `account_number`, `account_type`, `owner`, `ticker`, `value`
- Registry keys on `(institution_name, account_number)` — never on `account_name`. Use `registry.validate(INSTITUTION, account_number)` and `registry.get_owner(INSTITUTION, account_number)`.
- Deduplication key in pipeline: `(institution_name, account_number, ticker)` — shared accounts across owner dirs count once.
- `_PARSERS` in `pipeline.py` is the only place to register a new parser.
- Asset mapping discovery is automatic: `_discover_mapping_paths()` finds `*-asset-mapping.csv` under `personal_data/<institution-dir>/` — no code changes needed when adding a new mapping file.

---

## Skills (Claude Slash Commands)

| Command | Purpose |
|---|---|
| `/add-institution <Name>` | Full workflow: parser → tests → registry → asset mapping → metadata |
| `/update-accounts [glob]` | Register unrecognized accounts into `known-accounts.csv` |
| `/update-assets [institution: Name]` | Map unknown tickers to canonical tickers and asset metadata |
| `/update-readme` | Sync README to reflect all changes since the last README commit |
| `/update-claude-md` | Sync CLAUDE.md to reflect all changes since the last CLAUDE.md commit |

---

## Running

```bash
python -m uv run invest positions
python -m uv run invest concentration
python -m uv run invest decomposition
python -m uv run invest precious-metals
python -m uv run invest allocations
python -m uv run invest owners
python -m uv run invest serve
python -m uv run pytest tests/ -v
```

`uv` is not on PATH — always invoke as `python -m uv`.
