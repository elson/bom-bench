---
name: commit
description: Create a git commit with context-aware message
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*)
---

## Context

- Current git status: !`git status`
- Current git diff (staged and unstaged changes): !`git diff HEAD`
- Current branch: !`git branch --show-current`
- Recent commits: !`git log --oneline -10`

## Your task

1. Analyze the changes above and draft a commit message that:
   - Adheres to the "conventional commit" standard
   - Focuses on the "why" rather than the "what"
   - Follows the style of recent commits in the repository

2. Stage relevant files if needed (ask user if unclear what to stage)

3. Create the commit with this format:
   ```
   git commit -m "$(cat <<'EOF'
   <commit message here>

   🤖 Generated with [Claude Code](https://claude.com/claude-code)

   Co-Authored-By: %insert model name% <noreply@anthropic.com>
   EOF
   )"
   ```

4. Run `git status` after commit to verify success

Important:
- Do NOT commit files that may contain secrets (.env, credentials.json, etc.)
- Do NOT push unless explicitly asked
- Do NOT use --amend unless explicitly requested and safe to do so
- If there are no changes to commit, inform the user
