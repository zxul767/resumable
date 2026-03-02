# Language Specification (Draft)

## Program
A program is a list of declarations.

Declarations:
- function declaration (`fun` or `gen`)
- statement

Function kinds:
- `fun name(params) { ... }`
- `gen name(params) { ... }`

## Statements
- `var name = expr;`
- `name = expr;`
- `expr;`
- `if expr { declaration* } [else { declaration* }]`
- `while expr { declaration* }`
- `{ declaration* }`
- `return;` or `return expr;`
- `yield expr;`

Semicolons are required for non-block statements.

## Expressions
- literals: integers, strings, `true`, `false`, `nil`
- variable: `name`
- call: `name(arg1, arg2, ...)`
- grouping: `(expr)`
- unary: `-expr`
- binary: `+`, `-`, `*`, `/`, `mod`, `<`, `<=`, `==`

Precedence (high to low):
1. unary
2. `*`, `/`, `mod`
3. `+`, `-`
4. `<`, `<=`
5. `==`

Identifiers may end with one trailing `?` or `!`.

## Scope
- Lexical scoping.
- Each block creates a scope.
- Function calls create a call frame with parameter bindings.
- Assignment updates the nearest existing binding. Assigning an unknown name is an error.

## Function Semantics
`fun`:
- `return expr;` returns value.
- `return;` or fall-through returns `nil`.

`gen`:
- `yield expr;` emits a value and suspends.
- `return expr;` ends iteration with a final return value.
- `return;` or fall-through ends iteration.

## Built-ins
- `next(generator_instance)`:
  - returns next yielded value
  - raises host `StopIteration` on exhaustion (`StopIteration.value` carries generator return value when present)
- `collect(generator_instance)`:
  - drains generator
  - returns yielded values
  - appends final generator return value when present

## Semantic Rules
- `yield` is valid only inside `gen`.
- `return` is valid only inside function bodies.
- Duplicate parameter names are invalid.

These checks are done in semantic validation, not in the grammar.

## Errors
- Parse errors: invalid syntax.
- Semantic errors: invalid `yield`/`return` placement, duplicate params.
- Runtime errors: undefined names, invalid assignment target, wrong call args.

Runtime entry points:
- `run(...)`: raises exceptions.
- `run_for_cli(...)`: catches and prints syntax/runtime errors to `stderr`.
