# Architecture

## Layers
- `resumable.frontend`: grammar, parser, AST, semantic validation.
- `resumable.runtime`: evaluation and execution of the frontend AST.

Dependency rule:
- Runtime may import frontend AST types.
- Frontend must not import runtime.

## Main Runtime APIs
- `run(...)`: library/test entry point. Exceptions propagate.
- `run_for_cli(...)`: CLI entry point. Catches exceptions and prints to `stderr`.

## Runtime Modules
- `runtime/core.py`: shared runtime types (`Value`, `Env`, `RuntimeContext`, `CallableValue`, `ProgramState`).
- `runtime/expression_evaluator.py`: expression evaluation (`eval_expr`).
- `runtime/statement_executor.py`: statement/declaration execution, `FunctionValue`, `ReturnSignal`.
- `runtime/interpreter.py`: orchestration (`run`, `run_for_cli`).
- `runtime/stdlib.py`: built-ins (`next`, `collect`).
- `runtime/generator_compiler.py`: generator lowering bridge and `GeneratorValue`.
- `runtime/resumable.py`: resumable execution model.

## Frontend Modules
- `frontend/grammar.lark`: grammar.
- `frontend/ast_expressions.py`: expression AST nodes.
- `frontend/ast_statements.py`: statement/declaration AST nodes.
- `frontend/parser.py`: parse and AST transform (`parse_tree`, `parse_program`, `parse_and_validate`).
- `frontend/semantic.py`: semantic validation rules.

## Execution Flow
1. Parse and validate source.
2. Create global `Env` and install stdlib.
3. Execute declarations/statements via `statement_executor`.
4. Evaluate expressions via `eval_expr`.
5. Execute functions/generators:
- `fun` returns directly.
- `gen` returns `GeneratorValue`.
- `next` follows host `StopIteration` semantics.
- `collect` returns yielded values and appends final return value when present.

## Current Limits
- No closures.
- No `yield from`.
- No optional semicolons yet.
- Nested function declarations are not supported inside compiled generator bodies.
- No language-level exception syntax.
