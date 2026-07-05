---
description: Code review, quality gates, and commit conventions for the fabric-client project
applyTo: '**/*'
---

# Code Review & Quality Gates

## Pre-Commit Checklist

Before every commit, **all three** checks must pass with zero errors:

```bash
uv run ruff check --fix fabric_client/ tests/
uv run mypy fabric_client/
uv run pytest
```

If any check fails, fix the issues before committing.  Do **not** commit
with failing checks.

## Commit Log Convention

Commit messages must be written in **English** using a **two-section**
format:

```
<type>: <short summary>

- <change item 1>
- <change item 2>
- <change item 3>
```

### Summary Line

The first line is `<type>: <short summary>` where:

| Type       | Use when                                        |
|------------|-------------------------------------------------|
| `feat`     | New feature or capability                       |
| `fix`      | Bug fix                                         |
| `refactor` | Code restructure without behaviour change       |
| `docs`     | Documentation or instruction updates            |
| `chore`    | Build, tooling, or dependency changes           |
| `test`     | Adding or updating tests                        |

The summary should be **imperative** and **50 characters or fewer**.

### Change Items

After a blank line, list each logical change as a bullet point (`-`).
Each item describes **what** changed, not **how**.

### Examples

```
feat: add scoped datasets/reports/dataflows under Workspace

- Add WorkspaceDatasets, WorkspaceReports, WorkspaceDataflows to apis/scoped.py
- Wire scoped collections as properties on Workspace model
- Support await and async for on each scoped collection
```

```
fix: prevent rate-limit on single-page workspace listing

- Replace Paginator.collect_all with single GET in WorkspacesAPI.list
- Add RateLimitError retry with backoff in FabricClient._request
- Parse Fabric "blocked until" timestamp for accurate retry delay
```
