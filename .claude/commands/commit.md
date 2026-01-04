---
name: commit
description: Create a git commit with context-aware message
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*)
---

Create a new git commit. First, gather context by running these bash commands in parallel:

1. `git status` - see staged/unstaged changes
2. `git diff HEAD` - see all changes including staged
3. `git branch --show-current` - get current branch name
4. `git log --oneline -10` - see recent commit message style

After gathering context:

1. Analyze the changes and draft a commit message that:
   - Follows the "conventional commit" structure
   - Focuses on the "why" rather than the "what"
   - Follows the style of recent commits in the repository

2. Stage relevant files if needed (ask user if unclear what to stage)

3. Create the commit with this format:
   ```
   git commit -m "$(cat <<'EOF'
   <commit message here>

   🤖 Generated with [Claude Code](https://claude.com/claude-code)

   Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
   EOF
   )"
   ```

4. Run `git status` after commit to verify success

Important:
- Do NOT commit files that may contain secrets (.env, credentials.json, etc.)
- Do NOT push unless explicitly asked
- Do NOT use --amend unless explicitly requested and safe to do so
- If there are no changes to commit, inform the user
