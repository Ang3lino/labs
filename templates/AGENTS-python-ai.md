# AGENTS.md

> Generic AI project guidelines. Copy to each new project and adapt the Project section.

## Project

<!-- Replace this section per project -->

- **Name**: project-name
- **Description**: What it does in one sentence.
- **Commands**:

```bash
uv sync                    # Install deps
uv run project-name        # Run CLI
uv run pytest tests/ -v    # Tests
uv run ruff check . --fix  # Lint
uv run ruff format .       # Format
uv run basedpyright .      # Type check
```

## Philosophy

- **YAGNI**: Before writing code — does it need to exist? Does the standard library do it? Can it be one line?
- **FP first**: Pure functions, data in / data out. Classes only when state is genuinely needed.
- **Minimum that works**: No unrequested abstractions, no avoidable dependencies, no boilerplate.
- **`ponytail:` comments**: Mark intentional simplifications or design trade-offs.

## Stack

| Layer | Tool |
|---|---|
| Runtime | Python 3.12+ |
| Package manager | uv |
| Build backend | hatchling |
| Linter + formatter | ruff (no black) |
| Type checker | basedpyright |
| Test runner | pytest |
| HTTP client | httpx (not requests) |
| CLI | typer (not argparse) |
| Config / validation | pydantic |
| Env vars | python-dotenv (when needed) |
| Tracking | MLflow |
| Local inference | Ollama |

## Project Layout

src-layout by default. Flat only for true single-file `# /// script` tools.

```
project-name/
├── pyproject.toml
├── src/project_name/
│   ├── __init__.py
│   ├── main.py         # CLI entrypoint
│   ├── config.py       # Pydantic config
│   └── ...
├── tests/
│   ├── test_*.py       # pytest unit tests
│   └── smoke.py        # Integration tests (if needed, requires real services)
└── README.md
```

## pyproject.toml Template

```toml
[project]
name = "project-name"
version = "0.1.0"
description = ""
requires-python = ">=3.12"
dependencies = [
    "httpx",
    "pydantic",
    "typer",
]

[project.scripts]
project-name = "project_name.main:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/project_name"]

[tool.ruff]
line-length = 88

[tool.ruff.format]
quote-style = "double"

[tool.basedpyright]
pythonVersion = "3.12"
typeCheckingMode = "standard"

[dependency-groups]
dev = [
    "basedpyright",
    "ruff",
    "pytest",
]
```

## Code Style

### Typing

- Modern syntax only: `str | None`, `tuple[str, float]`, `list[int]`.
- Never import from `typing` unless you need `TypeVar`, `Protocol`, or `TypeAlias`.
- All function signatures must have type hints. basedpyright enforces this.

### Functions

- Should fit on one screen (~40 lines). If longer, split or mark with `ponytail:` explaining why.
- One function = one thing.
- Return data, not side effects.

### Files

- 250 LOC max (pure code, excluding blanks and comments).
- One file = one responsibility.
- Exceeding = split into modules or mark with `ponytail: intentionally large`.

### Config

```python
from pydantic import BaseModel

class Config(BaseModel):
    ollama_model: str = "mistral"
    ollama_host: str = "http://localhost:11434"
    temperature: float = 0.3

config = Config()
```

No raw dicts for config. Pydantic catches typos at access time and gives autocomplete.

### CLI

```python
import typer

def main(file: str, model: str = "llama3.2"):
    ...

typer.run(main)
```

No argparse. Typer gives the same result with type-safe args and auto `--help`.

### Docstrings

Only when behavior isn't obvious from the function name + signature:

```python
# Skip — signature says it all:
def extract_text(image: Image.Image) -> tuple[str, float]: ...

# Write — non-obvious behavior:
def has_changed(image: Image.Image) -> bool:
    """Compare against last capture via MD5 hash, not pixel diff."""
```

### Error Handling

- Catch specific exceptions, never bare `except`.
- Return `None` or a result type for recoverable errors.
- Let it crash for unrecoverable errors.

### Imports

Standard library → third-party → local, separated by blank lines:

```python
import hashlib
from pathlib import Path

import httpx
from pydantic import BaseModel

from project_name.config import Config
```

## Testing

- **pytest** for unit tests. Always in `tests/` directory.
- **Smoke scripts** allowed for integration tests that need real hardware/services (GPUs, Ollama, APIs).
- No test = no confidence the code works after changes.

```bash
uv run pytest tests/ -v
```

## Constraints

- No `from typing import Optional, List, Dict, Tuple` — use builtins.
- No black — ruff handles formatting.
- No raw config dicts — use pydantic.
- No argparse — use typer.
- No requests — use httpx.
- No setuptools — use hatchling.
- No docstrings that repeat the function name.
- No `ponytail:` abuse — only for genuine trade-offs, not laziness.
