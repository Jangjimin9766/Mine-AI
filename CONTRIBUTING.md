# Team Collaboration Workflow Guide

This document outlines the standard workflow for our team to ensure code quality, efficient collaboration, and stability.

## 1. Issue Management (Task Board)
Every piece of work (feature, bug fix, task) must start with a GitHub Issue.
- **Title**: Clear and concise (e.g., "Add Login Page", "Fix User API 500 Error").
- **Description**: Detailed requirements, acceptance criteria, or reproduction steps.
- **Assignee**: Assign yourself or the person working on it.
- **Labels**: Use labels like `feature`, `bug`, `documentation`.

## 2. Branching Strategy
We use a **Feature Branch** workflow.
- **Main Branch (`main`)**: Always deployable, stable code. Direct pushes are BLOCKED.
- **Feature Branches**: Created from `main`.
    - **Naming Convention**: `feature/issue-number-short-description` or `fix/issue-number-short-description`.
    - Example: If Issue #12 is "Add Login", branch name: `feature/12-add-login`.
    - **How to Create**: On the Issue page in GitHub, click "Create a branch" under the "Development" section in the right sidebar. This links them automatically!

## 3. Development & Commits
- Make small, frequent commits.
- **Commit Messages**: Reference the issue number if possible.
    - Example: `feat: implement login form (closes #12)`
    - Use conventional commits (feat, fix, docs, style, refactor, test, chore).

## 4. Pull Request (PR) & Code Review
When work is done:
1.  **Push** your branch to GitHub.
2.  **Open a Pull Request**:
    - **Base**: `main`
    - **Compare**: `feature/12-add-login`
    - **Description**: "Closes #12". Describe what was changed and how to test.
3.  **Automated Checks (CI)**:
    - GitHub Actions will automatically run Unit Tests.
    - **Checks MUST Pass** (Green) before merging.
4.  **Code Review**:
    - Request review from at least 1 team member.
    - Reviewers check for logic errors, code style, and potential bugs.
    - **Approval is REQUIRED** to merge.
5.  **Merge**:
    - Once approved and checks pass, click "Squash and merge" (preferred to keep history clean) or "Merge pull request".

## 5. Branch Protection Rules (One-time Setup)
The Repository Owner must configure this in **Settings -> Branches -> Add branch protection rule**:
- **Branch name pattern**: `main`
- [x] **Require a pull request before merging**
- [x] **Require approvals** (1 review required)
- [x] **Require status checks to pass before merging** (Select `Run Tests` after the first CI run)
