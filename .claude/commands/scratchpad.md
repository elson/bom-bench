---
name: scratchpad
description: Update SCRATCHPAD.md with current session notes
allowed-tools: Read, Write, Edit, Glob
---

## Context

- Current scratchpad contents: !`cat SCRATCHPAD.md 2>/dev/null || echo "(file does not exist)"`

## Your task

Update SCRATCHPAD.md to document the current session's work. This file serves as a working memory for AI agents.

### Structure

Organize the scratchpad with these sections:

1. **Current Focus** - What we're actively working on
2. **Recent Changes** - Files modified, decisions made
3. **Open Questions** - Unresolved issues or decisions pending
4. **Notes** - Any other relevant context

### Guidelines

- Keep entries concise and actionable
- Remove stale/completed items
- Preserve important context that would help future sessions
- Use bullet points for readability
- Include file paths where relevant

### Actions

1. Read the current SCRATCHPAD.md (if it exists)
2. Ask the user what to add/update if not clear from conversation
3. Write the updated content
