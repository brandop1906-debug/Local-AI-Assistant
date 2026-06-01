---
name: test-driven-development
description: Implements test-driven development — writes tests before code, runs tests, and fixes failing tests. Use when adding features, refactoring, or ensuring code quality through testing.
---

# Test-Driven Development Skill

## Overview

This skill defines a TDD workflow: write tests first, make them pass, then refactor. It covers test creation, execution, debugging failures, and maintaining a clean test suite.

## When to Use

- Adding a new feature or function
- Refactoring existing code
- Fixing a bug (write a regression test first)
- Ensuring a PR or change doesn't break existing behavior

## TDD Cycle

### 1. Write the Test First

Before writing any implementation, write the test(s):

```python
def test_feature_name(input, expected_output):
    assert feature_name(input) == expected_output
```

- **Start small** — one test case per assertion
- **Test the happy path first** — then edge cases
- **Be specific** — assert exact outputs, not just "no error"
- **Use descriptive names** — `test_empty_input_raises_value_error`, not `test_1`

### 2. Run — Watch it Fail

Run the test and confirm it fails. A failing test proves:
- The test is actually testing something
- The feature doesn't exist yet
- Your test framework is configured correctly

### 3. Write Minimal Code

Write the **minimum** code to make the test pass. Don't over-engineer:

```python
def feature_name(input):
    # Just enough to pass the current test
    return expected_output
```

### 4. Run — Watch it Pass

Run the test again. It should pass. If it doesn't, debug until it does.

### 5. Refactor

Now that you have a green test:
- Clean up the implementation
- Improve naming, structure, efficiency
- **Run tests again** — refactor only while tests are green

### 6. Repeat

Add the next test case (edge case, another scenario) and repeat from step 2.

## Test Writing Guidelines

### What to Test

- **Happy path** — normal inputs, expected outputs
- **Edge cases** — empty inputs, null/None, zero, negative numbers, boundary values
- **Error cases** — invalid inputs should raise the right exceptions
- **Side effects** — does it modify state? write to a file? make an API call?

### Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── test_feature_name.py     # Tests for a feature
├── test_another_feature.py
└── test_existing_module.py  # Regression tests
```

### Assertions

```python
# Specific assertions > generic "no error" checks
assert result.status_code == 200
assert len(users) == 3
assert user.name == "Alice"
assert raises(ValueError, lambda: bad_function(""))
```

### Test Data

```python
# Use fixtures or data classes for complex test data
@pytest.fixture
def sample_user():
    return User(id=1, name="Alice", email="alice@example.com")

# For large datasets, use external files
@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("", ""),
    ("123", "123"),
])
def test_transform(input, expected):
    assert transform(input) == expected
```

## Running Tests

### Standard Workflow

```bash
# Run all tests
pytest

# Run specific file
pytest tests/test_feature.py

# Run specific test
pytest tests/test_feature.py::test_specific_case

# Run with coverage
pytest --cov=modules --cov-report=term-missing

# Run with verbose output
pytest -v

# Run only failures from last run
pytest --lf
```

### Debugging Failing Tests

When a test fails:

1. **Read the failure output** — pytest gives you the diff, traceback, and assertion details
2. **Identify the root cause** — is it a bug in the code or a bug in the test?
3. **Fix the code** — make the minimal change to pass
4. **Re-run** — confirm the fix works
5. **Run the full suite** — ensure nothing else broke

### Common Failure Patterns

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `ModuleNotFoundError` | Missing import or wrong path | Check `PYTHONPATH` or `sys.path` |
| `AssertionError` with diff | Wrong expected value or logic bug | Compare diff, trace the actual path |
| `Timeout` / hangs | Infinite loop or blocking I/O | Check loops, add timeout fixtures |
| `fixture not found` | Missing `@pytest.fixture` or wrong scope | Verify fixture definition and scope |
| `AttributeError` | Wrong object or None return | Check return values, initialization |

## Regression Testing

When fixing a bug, always add a regression test:

```python
def test_regression_bug_123():
    """Regression test for bug #123 — empty list caused IndexError."""
    result = process_items([])
    assert result == []
```

Include:
- The bug number or issue reference
- What the bug was
- What the test prevents from happening again

## Test Structure for Your Project

Based on the project structure, tests should go in:

```
tests/
├── test_email_assistant/
│   ├── test_compose.py
│   ├── test_send.py
│   └── test_parse.py
├── test_pdf_summarizer/
│   ├── test_summarize.py
│   └── test_extract.py
├── test_quote_generator/
├── test_business_brain/
├── test_chat_ai/
└── conftest.py
```

## Rules

- **Tests should be deterministic** — no randomness, no time-dependent logic without mocking
- **Tests should be isolated** — one test shouldn't depend on another's state
- **Tests should be fast** — keep them under a few seconds each
- **Tests should be readable** — another developer should understand what's being tested
- **Never skip tests to ship faster** — a failing test is a flag, not a blocker to delete
- **Run the full suite** before merging, not just the tests you touched
