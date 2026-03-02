from .ast_statements import (
    Block,
    Declaration,
    FunctionDeclaration,
    FunctionKind,
    If,
    Program,
    Return,
    Statement,
    While,
    Yield,
)


class SemanticError(ValueError):
    """Raised when parsed source violates language semantic rules."""


def validate_program(program: Program) -> None:
    for declaration in program.declarations:
        _validate_declaration(declaration, enclosing_function_kind=None)


def _validate_declaration(
    declaration: Declaration,
    enclosing_function_kind: FunctionKind | None,
) -> None:
    if isinstance(declaration, FunctionDeclaration):
        _validate_function_declaration(declaration)
        _validate_block(declaration.body, enclosing_function_kind=declaration.kind)
        return

    _validate_statement(declaration, enclosing_function_kind)


def _validate_function_declaration(declaration: FunctionDeclaration) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for name in declaration.params:
        if name in seen:
            duplicates.add(name)
        seen.add(name)

    if duplicates:
        raise SemanticError(f"duplicate parameter names: {sorted(duplicates)}")


def _validate_block(
    block: Block,
    enclosing_function_kind: FunctionKind | None,
) -> None:
    for declaration in block.declarations:
        _validate_declaration(declaration, enclosing_function_kind)


def _validate_statement(
    statement: Statement,
    enclosing_function_kind: FunctionKind | None,
) -> None:
    if isinstance(statement, Block):
        _validate_block(statement, enclosing_function_kind)
        return

    if isinstance(statement, If):
        _validate_statement(statement.then_branch, enclosing_function_kind)
        if statement.else_branch is not None:
            _validate_statement(statement.else_branch, enclosing_function_kind)
        return

    if isinstance(statement, While):
        _validate_statement(statement.body, enclosing_function_kind)
        return

    if isinstance(statement, Return):
        if enclosing_function_kind is None:
            raise SemanticError("return is only allowed inside functions")
        return

    if isinstance(statement, Yield):
        if enclosing_function_kind != "gen":
            raise SemanticError("yield is only allowed inside generator functions")
        return

    return
