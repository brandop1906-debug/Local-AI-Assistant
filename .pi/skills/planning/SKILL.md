---
name: planning
description: Breaks down complex tasks into actionable steps, creates implementation plans, identifies dependencies and risks, and produces structured roadmaps. Use when starting a new feature, refactoring, or tackling anything that requires multi-step planning.
---

# Planning Skill

## Overview

This skill provides structured approaches to planning complex tasks. It helps decompose goals, estimate effort, identify risks, and produce clear implementation roadmaps.

## When to Use

- Starting a new feature or major change
- Refactoring large codebases
- Anything that requires coordinating multiple steps or dependencies
- When you need to present a plan for review before implementing

## Planning Workflow

### 1. Understand the Goal

Restate the user's objective in your own words. Identify:
- What success looks like
- Any constraints (time, resources, technical limitations)
- Implicit requirements the user may not have stated

### 2. Decompose into Tasks

Break the goal into logical sub-tasks. For each task:
- Give it a clear, actionable name
- Write a 1-2 sentence description
- Identify prerequisites (what must be done first)
- Flag potential risks or unknowns

### 3. Structure the Plan

Present the plan using this format:

```markdown
## Plan: [Title]

### Objective
[One-sentence summary of the goal]

### Tasks

#### Phase 1: [Phase name]
- [ ] **Task 1**: [Brief description]
  - Prerequisites: none
  - Risk: low
- [ ] **Task 2**: [Brief description]
  - Prerequisites: Task 1
  - Risk: medium

#### Phase 2: [Phase name]
- [ ] **Task 3**: [Brief description]
  - Prerequisites: Task 2
  - Risk: low

### Dependencies
[List external dependencies, APIs, packages, etc.]

### Risks & Mitigations
- **Risk**: [Description]
  **Mitigation**: [How to address it]

### Next Steps
1. [Immediate next action]
2. [Follow-up action]
```

### 4. Review with User

Before implementing, present the plan and ask:
- Does this cover everything you need?
- Are there priorities that should change?
- Any risks you want to address first?

## Tips

- Keep tasks small enough to complete in a single session
- Call out unknowns explicitly — they're opportunities for research tasks
- Consider parallel work where possible
- Include verification steps (tests, reviews, checks)
- For large projects, propose an iterative approach with checkpoints
