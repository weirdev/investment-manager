---
name: update-readme
description: Update README.md to reflect changes since the last README commit
---

Update `README.md` to reflect all changes made since the last commit that touched it.

## 1. Identify what changed

Find the last commit that modified the README, then diff from there to HEAD:

```bash
git log --oneline -- README.md        # find the last README commit
git diff <that-commit>..HEAD --stat   # summarize what changed since then
```

Read `README.md` in full before making any edits.

---

## 2. Update each affected section

Work through the diff and update every README section touched by the changes. Common areas:

- **Overview**: supported institutions list, data directory path pattern
- **Directory structure**: add/remove directories, update comments
- **CLI Commands**: add new commands with example output; update existing command descriptions if behavior changed
- **Data Files**: update CSV schema examples (e.g. new columns in `known-accounts.csv`); update file paths
- **Adding a New Institution / Parser structure**: update code examples to match current `Position` constructor signature and registry method calls
- **Running Tests**: update fixture paths if they moved
- **Architecture**: add new parsers/modules to the file tree; update `analysis.py` and `cli.py` summaries; update pipeline flow description

Do not rewrite sections that are unaffected. Do not invent example output — use round-number placeholder values consistent with the existing style.

---

## 3. Commit

Stage only `README.md` and commit with a message that summarizes which features prompted the update:

```bash
git add README.md
git commit -m "Update README for <summary of changes>"
```
