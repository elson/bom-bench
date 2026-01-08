---
description: Work on a GitHub issue end-to-end
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(git:*), Bash(gh:*), Bash(uv:*), Bash(python:*), Bash(make:*)
---

# Issue Workflow

Work on issue: $ARGUMENTS

## Instructions

### 1. Read the Issue

First, fetch and understand the issue:

Use `gh issue view` to:
- Get issue details (title, description, acceptance criteria)
- Check linked issues, prs etc
- Review any comments or attachments
- IMPORTANT: Check if an implementation plan has already been added in the comments

Summarize:
- What needs to be done
- Acceptance criteria
- Any blockers or dependencies

### 2. Explore the Codebase

Before coding:
- Reference the existing plan if available
- Search for related code
- Understand the current implementation
- Identify files that need changes
.
### 3. Create a Branch

```bash
git checkout -b {user-name}/{issue-id}-{brief-description}
```

### 4. Implement the Changes

- Write tests first (TDD)
- Follow project patterns (check relevant skills)
- Use code-simplifier sub-agent to make code concise, readable, and efficient
- Make incremental commits

### 5. Update the Issue

As you work:
- Add comments with progress updates
- Log any blockers or questions

### 6. Create PR and Link

When ready:
- Create PR with `gh pr create`
- Link the PR to the issue
- Add issue ID to PR title: `feat(ISSUE-#): description`

### 7. If You Find a Bug

If you discover an unrelated bug while working:
1. Create a new issue with details
2. Link it to the current issue if related
3. Note it in the PR description
4. Continue with original task

## Example Workflow

```
Me: /issue-implement 7

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

3. Creating branch: claude/ISSUE-7-avatar-upload

4. [Implements feature following project standard practices]

5. Updating Issue status...
   Adding comment: "Implementation complete, PR ready for review"

6. Creating PR and linking to ISSUE-7...
   PR #456 created: feat(ISSUE-7): add avatar upload to profile
```
