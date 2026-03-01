---
name: update-claude-md
description: Update CLAUDE.md to reflect changes since the last CLAUDE.md commit
---

Update `CLAUDE.md` to reflect all changes made since the last commit that touched it.

## 1. Identify what changed

Find the last commit that modified CLAUDE.md, then diff from there to HEAD:

```bash
git log --oneline -- CLAUDE.md        # find the last CLAUDE.md commit
git diff <that-commit>..HEAD --stat   # summarize what changed since then
```

For files that show meaningful changes in `--stat`, read their full diffs:

```bash
git diff <that-commit>..HEAD -- src/investment_manager/models.py \
    src/investment_manager/pipeline.py \
    src/investment_manager/registry.py \
    src/investment_manager/cli.py \
    .claude/skills/
```

Read `CLAUDE.md` in full before making any edits.

---

## 2. Update each affected section

Work through the diff and update every CLAUDE.md section touched by the changes. Use the checklist below.

### Checklist by changed area

- **`models.py`** — if `Position` or `Account` fields changed:
  - Update the `Position` fields bullet in **Architecture Invariants**
- **`registry.py`** — if the lookup key or method signature changed:
  - Update the registry bullet in **Architecture Invariants**
- **`pipeline.py`** — if deduplication key or `_PARSERS` list changed:
  - Update the deduplication bullet in **Architecture Invariants**
  - Update the `_PARSERS` bullet if the registration pattern changed
- **`cli.py`** — if new commands were added or existing ones removed:
  - Update the **Running** command list
- **New skill added** (new `.claude/skills/<name>/SKILL.md`):
  - Add a row to the **Skills** table
- **Skill removed**:
  - Remove its row from the **Skills** table

### General areas to check

- **Privacy**: only change if the `personal_data/` rule itself changed (rare — leave alone otherwise)
- **Architecture Invariants**: add/remove/update bullets when core contracts change (field names, registry key, dedup key, auto-discovery behavior)
- **Skills table**: keep in sync with the actual skills in `.claude/skills/`
- **Running**: add new CLI commands; remove deprecated ones

Do not rewrite sections that are unaffected. Do not add implementation detail that belongs in `MEMORY.md` — CLAUDE.md is for rules, invariants, and quick references that constrain future work.

---

## 3. Commit

Stage only `CLAUDE.md` and commit:

```bash
git add CLAUDE.md
git commit -m "Update CLAUDE.md for <summary of changes>"
```
