---
name: update-accounts
description: Register unrecognized accounts from new position CSV files into known-accounts.csv
---

Add entries to `personal_data/known-accounts.csv` for any accounts that appear in new position files but are not yet registered.

If `$ARGUMENTS` is provided, treat it as a glob or path hint pointing to the relevant position files. Otherwise, scan all CSV files under `personal_data/raw_account_details/`.

---

## 1. Find unregistered accounts

Read `personal_data/known-accounts.csv` to see what is already registered.

Read each new position CSV and collect every distinct `Account Name` value. The Fidelity parser uses the `Account Name` column; other institutions may differ — read the raw file to confirm which column contains the account name.

Cross-reference against the registry. An account is **unregistered** if no row in `known-accounts.csv` matches both its `institution_name` and `account_name`.

---

## 2. Determine the correct field values

For each unregistered account, decide:

| Field | How to determine |
|---|---|
| `institution_name` | Derive from the institution subdirectory name (e.g. `fidelity/` → `Fidelity`, `interactive-brokers/` → `Interactive Brokers`). Match the casing used by the existing parser (`INSTITUTION` constant). |
| `account_name` | Copy exactly as it appears in the CSV — the registry lookup is case- and whitespace-sensitive. |
| `account_type` | Infer from the account name or context: `brokerage`, `roth_ira`, `traditional_ira`, `401k`, `529`, `hsa`, `trust`. |
| `is_retirement` | `true` for `roth_ira`, `traditional_ira`, `401k`, `hsa`; `false` for `brokerage`, `trust`, `529`. |
| `owner` | Derive from the owner subdirectory (e.g. `raw_account_details/meijia/fidelity/` → `Meijia`). Use `Weirather Family Trust` for trust accounts; use `Wesley+Meijia` for joint accounts. |

If any value is ambiguous, ask before writing.

---

## 3. Insert the rows

Append the new rows to `personal_data/known-accounts.csv`. Keep rows grouped by institution and sorted alphabetically by `account_name` within each group.

---

## 4. Flag naming collisions

After inserting, check whether any `(institution_name, account_name)` pair now appears more than once. If so, warn the user — the registry can only store one entry per pair, and duplicate names across owners will cause incorrect owner attribution and may trigger unwanted deduplication.
