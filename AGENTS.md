# AGENTS.md

## Scope And Priority
- This file defines repository-wide working rules for coding agents and contributors.
- Direct user instructions for a task take precedence over this file.
- [STYLE_GUIDELINES.md](./STYLE_GUIDELINES.md) is the source of truth for coding style and naming.
- If a rule here conflicts with the style guide, prefer the style guide unless the task explicitly requires otherwise.

## Style And Typing
- Read and follow [STYLE_GUIDELINES.md](./STYLE_GUIDELINES.md) before making code changes.

## Architecture Boundaries
- Keep module responsibilities separated:
  - `src/resumable/ast_expressions.py`: non-resumable expression AST.
  - `src/resumable/resumable.py`: resumable runtime primitives/statements.
  - `src/resumable/runtime.py`: runtime support constructs (`Env`, `RuntimeContext`).
  - `src/resumable/ast_programs.py`: AST builders for sample programs.
  - `src/resumable/writer.py`: debug/output writer utilities.
- Prefer explicit dependency injection (for example, pass `RuntimeContext`) over globals.
- Avoid introducing circular imports; move shared types/helpers to `runtime.py` or another neutral module when needed.

## Packaging And Imports
- Use package imports via `resumable...` and relative imports within package modules.
- Do not rely on `PYTHONPATH=src` or test-time `sys.path` mutation.
- Keep code under `src/resumable/` aligned with `pyproject.toml` package config.

## Workflow Commands
- Install/update dependencies: `make install`
- Run tests: `make test`
- Lint: `make lint`
- Format: `make format`
- Type check: `make typecheck`
- Run full verification: `make check`

## Testing Expectations
- Put tests in `tests/` using `pytest`.
- When changing behavior, update/add tests in the same change.
- Prefer readable tests with minimal setup and self-contained ASTs unless helpers are reused.
- Keep assertions behavior-focused; avoid brittle assertions tied to incidental internals.

## Change Discipline
- Keep diffs minimal and task-focused.
- Avoid unrelated refactors in the same change.
- Preserve existing debug behavior unless there is explicit agreement to change it.
- If tooling or style ambiguity appears, prefer simple code and verify with `make check`.

## Documentation Expectations
- Update docs/comments/tests when behavior or public interfaces change.
- Keep examples (including demo code) consistent with the tested API.
