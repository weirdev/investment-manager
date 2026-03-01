#!/usr/bin/env bash
# .claude/hooks/pre-commit-check.sh
#
# PreToolUse hook: fires before every Bash tool call.
# Blocks git commits that change source code without first updating docs.

input=$(cat)

# Extract the bash command from tool_input.command
cmd=$(python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" <<< "$input" 2>/dev/null | tr -d '\r')
[ $? -ne 0 ] && exit 0

# Only intercept git commit invocations
echo "$cmd" | grep -qE 'git\s+commit\b' || exit 0

# Get staged file list
staged=$(git diff --cached --name-only 2>/dev/null)
[ -z "$staged" ] && exit 0

# Determine if this commit touches anything that requires docs to be updated.
# Covers every Python module in the package (not just the original 4 core files).
source_py=0; skills=0
echo "$staged" | grep -qE "^src/investment_manager/.*\.py$" && source_py=1
echo "$staged" | grep -qE "^\.claude/skills/"               && skills=1

reasons=()
[ $source_py -gt 0 ] && reasons+=("source module changed")
[ $skills    -gt 0 ] && reasons+=("skill added or modified")

[ ${#reasons[@]} -eq 0 ] && exit 0   # nothing that needs doc updates — allow

# Docs freshness check: README.md and CLAUDE.md must have been committed AFTER
# the current HEAD. This is satisfied once /update-readme and /update-claude-md
# have run; their commits land after HEAD in the graph, so HEAD becomes an
# ancestor of the doc commits.
head_sha=$(git rev-parse HEAD 2>/dev/null)
readme_sha=$(git log -1 --format="%H" -- README.md 2>/dev/null)
claude_sha=$(git log -1 --format="%H" -- CLAUDE.md 2>/dev/null)

if [ -n "$head_sha" ] && [ -n "$readme_sha" ] && [ -n "$claude_sha" ]; then
    if git merge-base --is-ancestor "$head_sha" "$readme_sha" 2>/dev/null && \
       git merge-base --is-ancestor "$head_sha" "$claude_sha" 2>/dev/null; then
        exit 0   # docs were committed after HEAD — allow the commit
    fi
fi

reason=$(IFS=", "; echo "${reasons[*]}")
printf "Commit blocked: docs are out of date (%s).\n" "$reason" >&2
printf "Run /update-readme and /update-claude-md, then retry the commit.\n" >&2
exit 2
