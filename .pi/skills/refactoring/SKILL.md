---
name: refactoring
description: Reorganizes files, renames functions, extracts components, and optimizes code. Use when improving code structure, reducing complexity, fixing smells, or preparing code for new features.
---

# Refactoring Skill

## Overview

This skill covers safe, incremental code improvement. Refactoring changes the structure of code without changing its external behavior. The goal is cleaner, more maintainable code — not new features.

## When to Use

- Code is hard to understand or modify
- Duplication across files or functions
- Functions are too long or do too much
- Naming is confusing or inconsistent
- Preparing code for a new feature (clean up first)
- Technical debt is slowing down development

## Golden Rule

**Refactor in small steps, test after every step.**

If you can't verify the code still works, you've refactored too far.

## Refactoring Techniques

### 1. Reorganize Files

When to reorganize:
- Related code is scattered across files
- A file has too many responsibilities
- Imports are circular or confusing
- The file structure doesn't match the mental model

**How to reorganize:**

1. **Map current structure** — list what's where and what depends on what
2. **Define target structure** — sketch the desired layout
3. **Move one piece at a time** — move a file, fix imports, verify, move the next
4. **Update exports** — `__init__.py`, public API surface, imports
5. **Run full test suite** — confirm nothing broke

**Example:**

```
# Before
modules/
├── email_assistant.py        # 800 lines, does everything
└── pdf_summarizer.py         # 600 lines, does everything

# After
modules/
├── email_assistant/
│   ├── __init__.py
│   ├── composer.py           # Composing emails
│   ├── sender.py             # Sending emails
│   └── parser.py             # Parsing emails
├── pdf_summarizer/
│   ├── __init__.py
│   ├── extractor.py          # Extracting text
│   └── summarizer.py         # Summarizing content
```

### 2. Rename Functions

When to rename:
- The name doesn't reveal intent
- The name is inconsistent with the codebase
- The name is misleading

**How to rename:**

1. **Pick the new name** — it should answer "what does this do?"
2. **Check usage** — find all callers across the codebase
3. **Rename in one pass** — update definition and all call sites
4. **Run tests** — confirm behavior is unchanged
5. **Update docs** — docstrings, README, API docs

**Naming principles:**

| Bad Name | Better Name | Why |
|----------|------------|-----|
| `process_data` | `transform_records` | What kind of data? What action? |
| `get_info` | `get_user_profile` | What info? |
| `do_stuff` | `validate_input` | What stuff? |
| `check` | `is_valid` | What is being checked? |
| `handle` | `on_submit` | What event? |

### 3. Extract Components

When to extract:
- A function is too long (> 30-50 lines)
- A block of code could be reused elsewhere
- A class has too many responsibilities
- Related logic is buried inside other logic

**How to extract:**

1. **Identify the chunk** — what's the cohesive piece?
2. **Name it** — the name should describe the extracted behavior
3. **Extract it** — move to a new function/class/module
4. **Update callers** — replace the old code with a call to the extraction
5. **Verify** — run tests, check imports, confirm behavior

**Common extractions:**

| From | To | Example |
|------|-----|---------|
| Long function | Multiple small functions | `process_order()` → `validate_order()`, `charge_payment()`, `send_confirmation()` |
| Duplicated logic | Shared utility | Copy-pasted validation in 3 files → `utils/validate.py` |
| God class | Multiple focused classes | `EmailAssistant` with 20 methods → `Composer`, `Sender`, `Parser` |
| Inline logic | Named constant | `"active"` string → `STATUS_ACTIVE = "active"` |
| Business logic | Service layer | Logic in UI code → `services/order_service.py` |

### 4. Optimize Code

When to optimize:
- Performance is actually a problem (measured, not guessed)
- A specific function is a bottleneck
- Memory usage is too high
- Startup time is unacceptable

**Optimization principles:**

1. **Measure first** — profile before optimizing. Don't guess.
2. **Optimize the hotspot** — 80% of time is usually in 20% of code
3. **Simplify before optimizing** — a clear algorithm beats a clever one
4. **Consider trade-offs** — speed vs. memory, speed vs. readability
5. **Benchmark after** — prove it's actually faster

**Common optimizations:**

| Problem | Solution | Impact |
|---------|----------|--------|
| N+1 queries | Batch query / eager loading | High |
| Repeated computation | Cache / memoize | High |
| Linear search in loop | Set / dict lookup | High |
| String concatenation in loop | `join()` | Medium |
| Loading large file fully | Stream / chunked read | High |
| Sync I/O in async code | Use async I/O | High |
| Repeated regex compilation | `re.compile()` once | Medium |
| Unnecessary object creation | Reuse / pool objects | Low-Medium |

## Refactoring Safety Checklist

Before and after every refactoring step:

- [ ] **Tests exist** — if not, write a regression test first
- [ ] **Tests pass** — before and after the change
- [ ] **One responsibility per change** — don't rename + reorganize + optimize in one go
- [ ] **Imports updated** — check `__init__.py`, public API, dependent files
- [ ] **No behavior change** — the output should be identical
- [ ] **No new dependencies** — unless intentional
- [ ] **Commit after each step** — so you can revert if needed

## Refactoring Decision Tree

```
Is the code working?
├── No → Fix the bug first, then refactor
└── Yes → Is it hard to maintain?
    ├── No → Don't refactor. Ship it.
    └── Yes → What's the main pain point?
        ├── Too long → Extract functions
        ├── Too complex → Simplify conditionals, extract methods
        ├── Duplicated → DRY it out, create shared utilities
        ├── Poorly named → Rename for clarity
        ├── Scattered → Reorganize files
        ├── Slow → Profile, then optimize the hotspot
        └── All of the above → Tackle one at a time
```

## Refactoring Anti-Patterns

| Anti-Pattern | Why It's Bad | Better Approach |
|-------------|-------------|-----------------|
| Big-bang refactor | Too many changes, hard to debug | Small, verifiable steps |
| Refactor without tests | You can't verify correctness | Write tests first |
| Premature optimization | Wasted effort on code that doesn't matter | Profile first |
| Over-engineering | Adding layers of abstraction for hypothetical needs | YAGNI — only extract what's needed now |
| Perfect is the enemy of good | Chasing ideal structure instead of shipping | Good enough + iterative improvement |

## Refactoring Rules

- **Refactor before adding features** — it's harder to add features to messy code
- **One change at a time** — each commit should do one thing
- **Keep the commit history clean** — don't mix refactoring with feature work
- **Document why** — commit messages should explain the refactoring, not just "refactor"
- **Know when to stop** — if the code is "good enough" and working, don't refactor just for the sake of it
- **Respect the existing style** — don't introduce a different formatting or naming convention in a refactor commit
