---
name: code-review
description: Reviews code for bugs, suggests improvements, and enforces style rules. Use when reviewing PRs, before committing changes, or when asking for feedback on your code.
---

# Code Review Skill

## Overview

This skill provides a structured approach to reviewing code. It catches bugs, spots inefficiencies, suggests improvements, and enforces consistent style — all in a systematic way rather than ad hoc comments.

## When to Use

- Before committing or pushing changes
- Reviewing someone else's code or a PR
- Asking for feedback on a feature before shipping
- Periodic health checks on existing codebases

## Review Checklist

### 1. Bugs & Correctness

Look for:
- **Logic errors** — conditions that never trigger, wrong comparisons, off-by-one
- **Edge cases** — empty inputs, null/None values, zero-length collections, boundary values
- **Error handling** — unhandled exceptions, swallowed errors, missing try/catch
- **Type mismatches** — passing wrong types, missing null checks, implicit conversions
- **Resource leaks** — unclosed files/connections, missing cleanup, memory leaks

### 2. Performance

Look for:
- **N+1 queries** — loops that query the database each iteration
- **Unnecessary allocations** — creating objects in tight loops
- **Blocking operations** — sync I/O in async contexts, heavy computation on main thread
- **Inefficient data structures** — linear search where a set/hash would help
- **Redundant work** — recalculating the same value, re-parsing already-parsed data

### 3. Improvements & Refactoring

Look for:
- **Duplication** — same logic repeated across files or functions
- **Over-complexity** — functions doing too much, nested conditionals, god classes
- **Missing abstractions** — hardcoded values that should be constants/config
- **Naming** — unclear variable/function names, inconsistent conventions
- **Dead code** — unused imports, unreachable branches, commented-out blocks

### 4. Style & Conventions

Look for:
- **Consistency** — naming patterns, formatting, docstrings, import order
- **PEP 8 / project style guide** — follow the project's established conventions
- **Documentation** — docstrings for public functions, comments for non-obvious logic
- **File organization** — logical grouping, reasonable file sizes, clear module boundaries

## Output Format

Present your review in this structure:

```markdown
## Code Review: [File/Feature Name]

### 🐛 Bugs (Critical)
| Line | Issue | Severity | Fix |
|------|-------|----------|-----|
| 42   | Null pointer dereference | High | Add null check before access |

### ⚡ Performance (Medium)
| Line | Issue | Suggestion |
|------|-------|------------|
| 15-20 | N+1 query pattern | Batch query outside loop |

### 💡 Improvements (Low)
- Rename `process_data` to `transform_records` for clarity
- Extract validation logic into a dedicated `validate_input()` function
- Add docstring to `calculate_metrics()`

### 📐 Style
- Inconsistent import ordering (should be stdlib → third-party → local)
- Missing type hints on public functions

### Summary
- **Bugs**: 2 critical, 1 minor
- **Performance**: 1 optimization worth making
- **Style**: 2 minor issues
- **Verdict**: [Approve / Approve with changes / Request changes]
```

## Rules

- **Be specific** — cite exact lines or code snippets, not vague concerns
- **Prioritize** — bugs first, then performance, then improvements, then style
- **Be constructive** — suggest fixes, don't just point out problems
- **Respect the codebase** — don't suggest style changes that conflict with existing conventions
- **Know when to stop** — if the code is fine, say so. Don't nitpick for the sake of it
- **Flag security issues** — SQL injection, XSS, hardcoded secrets, auth bypasses always get a 🐛 entry

## Severity Guide

| Level | When to use |
|-------|-------------|
| **Critical** — Will cause crashes, data loss, or security issues |
| **High** — Will cause incorrect behavior in real scenarios |
| **Medium** — Works now but will break or hurt performance later |
| **Low** — Good practice, not urgent |
