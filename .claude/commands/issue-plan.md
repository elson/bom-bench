---
description: Create a plan for a GitHub issue
allowed-tools: Read, Glob, Grep, Bash(gh:*)
---

# Issue Workflow

Create a plan for issue: $ARGUMENTS

## Instructions

### 1. Enter plan mode

If you are not already, enter "plan mode".
- You are only allowed to analyze the codebase, read files, and suggest plans.
- You must not use any tools that modify files (like Edit or Write).
- Your response should be a plan for how a developer could implement the issue.
- Do not attempt to implement it yourself.

### 2. Read the Issue

First, fetch and understand the issue:

Use `gh issue view` to:
- Get issue details (title, description, acceptance criteria).
- Check linked issues, prs etc.
- Review any comments or attachments.

Summarize:
- What needs to be done.
- Acceptance criteria.
- Any blockers or dependencies.

### 2. Explore the Codebase

Explore:
- Search for related code.
- Understand the current implementation.
- Identify files that need changes.

### 3. Create plan

Think hard:
- Create a detailed plan for implementing the issue requirements.
- Post the complete, unabridged plan as a comment on the issue.

## Example Workflow

```
Me: /issue-plan 7

Claude:
1. Fetching issue #7 from GitHub...
   Title: Add user profile avatar upload
   Description: Users should be able to upload a profile picture...
   Acceptance Criteria:
   - [ ] Upload button on profile page
   - [ ] Support JPG/PNG up to 5MB
   - [ ] Show loading state during upload

2. Searching codebase for profile-related code...
   Found: src/screens/Profile/ProfileScreen.tsx
   Found: src/components/Avatar/Avatar.tsx

3. Creating plan...
   Adding comment: "Plan complete, comment added ready for review"
```
