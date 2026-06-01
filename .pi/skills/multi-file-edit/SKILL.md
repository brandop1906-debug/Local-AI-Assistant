---
name: multi-file-edit
description: Propose, apply, and track multiple file edits in coordinated batches. Use when a feature touches multiple files, when changes are interdependent, or when you want to present diffs for review before applying.
---

# Multi-File Edit Skill

## Overview

This skill defines a structured workflow for making changes across multiple files. It ensures diffs are reviewed, applied safely in dependency order, and tracked so nothing is lost or duplicated.

## When to Use

- A feature touches 3+ files
- Changes in one file depend on changes in another
- You want to propose a full diff set for review before applying
- The scope is large enough that scattered edits risk inconsistency

## Workflow

### Step 1: Inventory Changes

Before writing anything, list every file that needs changes:

```
## Proposed Changes

| # | File | Type | Depends On |
|---|------|------|------------|
| 1 | modules/core/config.json | modify | — |
| 2 | modules/core/engine.py | modify | — |
| 3 | modules/new_feature/__init__.py | create | — |
| 4 | modules/new_feature/handler.py | create | 3 |
| 5 | config.json | modify | 1, 2 |
| 6 | tests/test_new_feature.py | create | 4 |
```

### Step 2: Present Diffs

Show each diff clearly with a header:

```markdown
### Diff 1: modules/core/config.json

```diff
--- a/modules/core/config.json
+++ b/modules/core/config.json
@@ -3,6 +3,9 @@
     "debug": false,
+    "new_feature": {
+        "enabled": true
+    },
     "timeout": 30
```

### Diff 2: modules/core/engine.py

```diff
--- a/modules/core/engine.py
+++ b/modules/core/engine.py
@@ -1,5 +1,6 @@
+from modules.new_feature.handler import process
...
```
```

### Step 3: Apply in Dependency Order

Only apply diffs whose dependencies are already satisfied. Follow the order from the inventory table:

1. Files with no dependencies → apply first
2. Files depending on already-applied files → apply next
3. Continue until all diffs are applied

### Step 4: Verify

After applying all diffs:
- Check that imports resolve correctly
- Verify no broken references
- Run existing tests if available
- Confirm the full feature works end-to-end

## Rules

- **Always present diffs before applying** — never silently modify files
- **Group related changes** — don't split one logical change across multiple unreviewed batches
- **Track what you've done** — keep the inventory table updated as you go
- **Rollback plan** — if verification fails, know what to undo first
- **One feature, one set** — all diffs for a single feature should be in one review cycle

## Diff Format

Use standard unified diff format. Always include:
- Full file paths (relative to project root)
- `--- a/` and `+++ b/` headers
- Context lines (3 lines above/below change)
- Clear `+`/`-` markers
