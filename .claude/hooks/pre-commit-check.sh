#!/usr/bin/env bash
# .claude/hooks/pre-commit-check.sh
#
# PreToolUse hook: fires before every Bash tool call.
# Detects major staged changes before a git commit and prompts to update docs.

input=$(cat)

# Extract the bash command from tool_input.command (python is always available in this project)
cmd=$(python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" <<< "$input" 2>/dev/null | tr -d '\r')
[ $? -ne 0 ] && exit 0

# Only intercept git commit invocations
echo "$cmd" | grep -qE 'git\s+commit\b' || exit 0

# Get staged file list
staged=$(git diff --cached --name-only 2>/dev/null)
[ -z "$staged" ] && exit 0
file_count=$(echo "$staged" | wc -l | tr -d ' ')

# Major-change heuristics
core=0; parsers=0; skills=0
echo "$staged" | grep -qE "^src/investment_manager/(models|pipeline|registry|cli)\.py$" && core=1
echo "$staged" | grep -qE "^src/investment_manager/parsers/[a-z_]+\.py$"               && parsers=1
echo "$staged" | grep -qE "^\.claude/skills/"                                           && skills=1

reasons=()
[ $core    -gt 0 ]  && reasons+=("core module changed (models/pipeline/registry/cli)")
[ $parsers -gt 0 ]  && reasons+=("parser added or modified")
[ $skills  -gt 0 ]  && reasons+=("skill added or modified")
[ "$file_count" -ge 5 ] && reasons+=("${file_count} files staged")

if [ ${#reasons[@]} -gt 0 ]; then
    reason=$(IFS=", "; echo "${reasons[*]}")
    printf "Major change detected (%s).\n" "$reason" >&2
    printf "Run /update-readme and /update-claude-md to keep docs in sync, then retry the commit.\n" >&2
    printf "If docs are already up to date, proceed.\n" >&2
    exit 2
fi

exit 0
