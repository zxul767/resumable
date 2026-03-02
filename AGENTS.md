# AGENTS.md

Repository-wide rules for contributors and coding agents.

## Priority
- User task instructions override this file.
- [STYLE_GUIDELINES.md](./STYLE_GUIDELINES.md) is the style source of truth.
- [ARCHITECTURE.md](./ARCHITECTURE.md) is the architecture source of truth.

## Workflow
- Install dependencies: `make install`
- Test: `make test`
- Lint: `make lint`
- Format: `make format`
- Type check: `make typecheck`
- Full verification: `make check`

## Change Rules
- Keep changes small and focused.
- Avoid unrelated refactors in feature, task,  etc., commits.
- When behavior changes, update tests and docs in the same change.
