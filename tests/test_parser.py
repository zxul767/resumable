import pytest
from lark import UnexpectedInput

from resumable.frontend.ast_expressions import Binary, Literal
from resumable.frontend.ast_statements import FunctionDeclaration, Program, Return
from resumable.frontend.parser import parse_program, parse_tree
from resumable.snippets import range_generator_source


# ===== Program Structure =====
def test_parse_empty_program() -> None:
    program = parse_program("")
    assert isinstance(program, Program)
    assert program.declarations == []


def test_parse_fun_and_gen_declarations() -> None:
    source = f"""
    fun add_one(x) {{
      return x + 1;
    }}

    {range_generator_source(include_return_end=True)}
    """
    program = parse_program(source)
    declarations = program.declarations

    assert len(declarations) == 2
    assert isinstance(declarations[0], FunctionDeclaration)
    assert declarations[0].kind == "fun"
    assert declarations[0].name == "add_one"
    assert isinstance(declarations[1], FunctionDeclaration)
    assert declarations[1].kind == "gen"
    assert declarations[1].name == "range"


# ===== Statement Syntax =====
def test_semicolons_are_required_for_simple_statements() -> None:
    source = """
    fun bad() {
      var x = 1
      return x;
    }
    """
    with pytest.raises(UnexpectedInput):
        parse_tree(source)


# ===== Expression Parsing =====
def test_precedence_mul_before_add() -> None:
    program = parse_program("fun f() { return 1 + 2 * 3; }")
    function_declaration = program.declarations[0]
    assert isinstance(function_declaration, FunctionDeclaration)
    return_statement = function_declaration.body.declarations[0]
    assert isinstance(return_statement, Return)

    assert isinstance(return_statement.value, Binary)
    assert return_statement.value.op == "+"
    assert isinstance(return_statement.value.left, Literal)
    assert return_statement.value.left.value == 1
    assert isinstance(return_statement.value.right, Binary)
    assert return_statement.value.right.op == "*"


def test_precedence_comparison_binds_after_addition() -> None:
    program = parse_program("fun f() { return 1 + 2 < 4; }")
    function_declaration = program.declarations[0]
    assert isinstance(function_declaration, FunctionDeclaration)
    return_statement = function_declaration.body.declarations[0]
    assert isinstance(return_statement, Return)

    assert isinstance(return_statement.value, Binary)
    assert return_statement.value.op == "<"
    assert isinstance(return_statement.value.left, Binary)
    assert return_statement.value.left.op == "+"


def test_parse_mod_keyword_operator() -> None:
    program = parse_program("fun f() { return 5 mod 3; }")
    function_declaration = program.declarations[0]
    assert isinstance(function_declaration, FunctionDeclaration)
    return_statement = function_declaration.body.declarations[0]
    assert isinstance(return_statement, Return)


# ===== If Syntax =====
def test_if_without_parentheses_parses() -> None:
    program = parse_program(
        "fun f(n) { if n <= 1 { return n; } else { return n - 1; } }"
    )
    declaration = program.declarations[0]
    assert isinstance(declaration, FunctionDeclaration)


def test_if_requires_block_body() -> None:
    source = "fun f(n) { if n <= 1 return n; }"
    with pytest.raises(UnexpectedInput):
        parse_tree(source)


# ===== Identifier Rules =====
def test_identifier_can_have_trailing_question_mark() -> None:
    program = parse_program("fun writable?(repo) { return repo; }")
    declaration = program.declarations[0]
    assert isinstance(declaration, FunctionDeclaration)
    assert declaration.name == "writable?"


def test_identifier_can_have_trailing_exclamation_mark() -> None:
    program = parse_program("fun update_repo!(repo) { return repo; }")
    declaration = program.declarations[0]
    assert isinstance(declaration, FunctionDeclaration)
    assert declaration.name == "update_repo!"


def test_call_allows_trailing_question_or_exclamation_mark() -> None:
    program = parse_program(
        """
        fun demo(repo) {
           if writable?(repo) == true {
              return update_repo!(repo);
           }
           return repo;
        }
        """
    )
    declaration = program.declarations[0]
    assert isinstance(declaration, FunctionDeclaration)
