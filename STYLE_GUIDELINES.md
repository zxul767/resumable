# Coding Guidelines

## PYTHON
- USE type hints everywhere.
- AVOID mutable default arguments.
- PREFER dataclasses over plain classes.
- AVOID inheritance; prefer composition.
- NEVER USE `del` to silence unused parameter warnings. Prefix unused parameters with `_` instead if necessary.
- DO NOT introduce speculative style or lint “fixes” preemptively. Prefer straightforward code first; only add workaround patterns when the configured tools actually report a concrete issue.
- DO NOT add `from __future__ import annotations` by default. Use it only when it is technically required (e.g., unresolved forward references without quotes) or when a concrete tool/runtime constraint demands it.

# NAMING
- USE `snake_case` for functions.
- USE `PascalCase` for classes.
- DO NOT USE abbreviations unless they're well-known (e.g., `http` is acceptable, but `ctx` as an abbreviation of `context` is not.)
- DO USE prefix abbreviations when a word is long and is used very often, but only if the result is pronounceable (e.g., `env` for `environment`)
- DO CONSIDER surrounding context when deciding whether to use a short or a longer name (e.g., `context:RuntimeContext` in a function is fine; `runtime_context:RuntimeContext` would be overkill.)

## DESIGN
- USE pure functions whenever possible.
- USE explicit dependencies (no globals).
- PREFER short functions that conceptually do one thing.
- AVOID mixing different levels of abstraction in a single function.

## TESTS
- AVOID repeated setup in tests. If the same setup appears in multiple tests, extract a small helper function.
- KEEP helpers small and intention-revealing so each test remains readable at a glance.
- DO NOT extract one-off setup into helpers; inline it when used only once.

### Function Design Constitution
#### 1. Single Level of Abstraction
Each function operates at one conceptual level only. Do not mix domain logic with IO, formatting, parsing, or other low-level details.

#### 2. One Thing Rule
A function performs one conceptual task. If it validates + transforms + persists, split it.

#### 3. Layering
- Top-level: orchestration (calls other functions)
- Mid-level: pure transformations
- Low-level: mechanisms (IO, serialization, filesystem, time, regex, etc.)

> Domain logic must not depend on storage or format details.

#### 4. Refactoring Behavior
When abstraction levels are mixed:
- Extract helpers
- Isolate side effects
- Make top-level functions read like a sequence of intentions
