# Coding Guidelines

## PYTHON
- Use type hints everywhere.
- Avoid mutable default arguments.
- Prefer dataclasses over plain classes.
- Avoid inheritance unless it adds clear value.
- Never use `del` to silence unused parameters. Use a leading `_` if needed.
- Do not apply speculative lint/style workarounds. Add them only when a configured tool reports a concrete issue.
- Do not add `from __future__ import annotations` by default. Add it only when required.

# NAMING
- Use `snake_case` for functions.
- Use `PascalCase` for classes.
- Avoid abbreviations unless they are widely understood.
- Short names are fine when context makes meaning obvious (for example `context: RuntimeContext`).

## DESIGN
- Prefer pure functions when practical.
- Avoid circular imports. If boundaries change, update `ARCHITECTURE.md`.
- Use explicit dependencies; avoid globals.
- Keep functions short and focused.
- Do not mix multiple abstraction levels in one function.

## TESTS
- Avoid repeated setup. Extract helpers only when setup is reused.
- Inline one-off setup.
- Keep helpers small and intention-revealing.
- Keep top-level functions orchestration-focused and isolate side effects.
- Do not depend on `PYTHONPATH=src` or `sys.path` mutation in tests.
