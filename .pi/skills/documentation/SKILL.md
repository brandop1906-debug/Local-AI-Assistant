---
name: documentation
description: Generates README files, writes docstrings, and creates API documentation. Use when documenting a new module, creating project docs, or adding documentation to existing code.
---

# Documentation Skill

## Overview

This skill covers three types of documentation: project-level (README), code-level (docstrings), and API-level (endpoints, interfaces, and usage guides). Good documentation is clear, accurate, and actionable.

## 1. README Generation

### When to Generate

- New project or module
- Project structure changes significantly
- Adding a major feature that needs documentation

### README Structure

```markdown
# [Project/Module Name]

[One-sentence description of what this project does.]

## Features

- [Feature 1]
- [Feature 2]
- [Feature 3]

## Installation

```bash
pip install [package]
# or
git clone [repo] && cd [dir] && pip install -r requirements.txt
```

## Usage

### Quick Start

```python
from module import ClassOrFunction

result = ClassOrFunction(input)
print(result)
```

### Examples

```python
# Example 1
...

# Example 2
...
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `setting_name` | `value` | What it does |

## Project Structure

```
project/
├── modules/
│   ├── module_name/
│   │   ├── __init__.py
│   │   ├── core.py
│   │   └── utils.py
├── tests/
├── requirements.txt
└── README.md
```

## API Reference

See [API Docs](#api-reference) or [docs/](docs/)

## Contributing

1. Fork the repo
2. Create a feature branch
3. Add tests for your changes
4. Submit a PR

## License

[License type]
```

### README Writing Rules

- **First line** = what it is, no fluff
- **Installation** = copy-pasteable commands
- **Usage** = minimal example that works
- **Keep it short** — link to detailed docs instead of dumping everything
- **Update with changes** — a stale README is worse than no README

## 2. Docstrings

### Format — Google Style

```python
def function_name(param1: str, param2: int) -> bool:
    """One-line summary of what the function does.

    Longer description if needed. Explain the why, not the how.
    The how is in the code.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        Description of return value.

    Raises:
        ValueError: When param1 is empty.
        TypeError: When param2 is not an integer.

    Examples:
        >>> function_name("hello", 42)
        True
    """
```

### When to Write Docstrings

- **Every public function** — no exceptions
- **Every public class** — at minimum a one-line summary
- **Every module** — top-of-file docstring describing purpose
- **Internal/private functions** — only if the logic isn't self-evident

### Docstring Rules

| Rule | Example |
|------|---------|
| One-line summary ends with `.` | `"""Calculate the total price."""` |
| Args section for every parameter | `Args:\n    name: Description.` |
| Returns section if not `None` | `Returns:\n    The computed result.` |
| Raises section if exceptions exist | `Raises:\n    ValueError: On invalid input.` |
| Examples for non-obvious usage | `Examples:\n    >>> func(1, 2)\n    3` |
| Don't repeat the signature | `"""Add two numbers."""` not `"""Add a and b together."""` |

### Class Docstrings

```python
class MyClass:
    """Short description of the class.

    Longer description if the class has nuanced behavior.

    Attributes:
        attr1: Description of attr1.
        attr2: Description of attr2.

    Examples:
        >>> obj = MyClass()
        >>> obj.do_something()
    """

    def __init__(self, attr1: str, attr2: int = 0):
        """Initialize MyClass.

        Args:
            attr1: Description.
            attr2: Description. Defaults to 0.
        """
```

### Module Docstrings

```python
"""Email Assistant module.

Handles composing, sending, and parsing email messages.

Usage:
    from email_assistant import EmailAssistant

    assistant = EmailAssistant()
    assistant.send(to="user@example.com", subject="Hello")
"""
```

## 3. API Documentation

### When to Create

- New API endpoints or public interfaces
- Changes to existing API contracts
- Before sharing with external consumers

### API Doc Format

```markdown
# API: [Endpoint/Interface Name]

## Overview

[What this API does in one paragraph.]

## Endpoint

`[METHOD] /path/to/endpoint`

### Request

**Headers:**
| Header | Required | Description |
|--------|----------|-------------|
| `Content-Type` | Yes | `application/json` |
| `Authorization` | Yes | Bearer token |

**Body:**
```json
{
    "field_name": "string value",
    "another_field": 42
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `field_name` | `string` | Yes | What it does |
| `another_field` | `integer` | No | What it does. Default: 0 |

### Response

**Success (200):**
```json
{
    "result": "value",
    "status": "success"
}
```

**Error (400):**
```json
{
    "error": "Invalid input",
    "details": "field_name is required"
}
```

**Error (500):**
```json
{
    "error": "Internal server error"
}
```

### Examples

```bash
curl -X POST https://api.example.com/path \
  -H "Content-Type: application/json" \
  -d '{"field_name": "value"}'
```

### Rate Limits

- [X requests per minute]
- [Any throttling behavior]
```

### Interface/API Doc for Libraries

```markdown
# API Reference: [Module Name]

## Classes

### `ClassName`

[One-line description.]

**Methods:**

#### `method_name(param: type) -> return_type`

[What it does.]

**Args:**
- `param` (type): Description

**Returns:**
- (return_type) Description

**Raises:**
- `ExceptionType`: When condition

---

## Functions

### `function_name(param: type) -> return_type`

[What it does.]

**Args:**
- `param` (type): Description

**Returns:**
- (return_type) Description

## Usage

```python
from module import ClassName, function_name

obj = ClassName()
result = obj.method_name("input")
```
```

## Documentation Rules

- **Write for the reader** — assume they've never seen this code
- **Examples over explanations** — a working example is worth a paragraph
- **Keep it current** — stale docs mislead more than no docs
- **Link, don't duplicate** — reference the code, don't re-state it
- **Update with code changes** — every PR that changes behavior should update docs
- **Use consistent formatting** — same style across all docs in the project
- **Don't document the obvious** — `x = x + 1` doesn't need a docstring saying "adds one to x"

## Documentation Checklist

Before considering documentation complete:

- [ ] README has installation and usage instructions
- [ ] Public classes have docstrings with Args/Returns/Raises
- [ ] Public functions have docstrings with Args/Returns
- [ ] Module has a top-level docstring
- [ ] API docs have request/response examples
- [ ] All examples are copy-pasteable and correct
- [ ] Links to related docs are working
- [ ] No outdated information
