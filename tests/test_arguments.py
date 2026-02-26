import pytest

from resumable.ast_expressions import Var
from resumable.ast_programs import build_range_function
from resumable.resumable import ResumableBlock, ResumableFunction, Yield


def test_new_requires_mapping() -> None:
    range_fn = build_range_function()
    with pytest.raises(ValueError, match=r"(?i)arguments|mapping"):
        range_fn.new(None)


def test_extra_arguments_are_rejected() -> None:
    range_fn = build_range_function()
    with pytest.raises(ValueError, match=r"(?i)unexpected|argument"):
        range_fn.new({"start": 0, "end": 2, "unused": 123})


def test_duplicate_parameter_names_are_rejected() -> None:
    with pytest.raises(ValueError, match=r"(?i)duplicate|parameter"):
        ResumableFunction(
            params=[Var("x"), Var("x")],
            body=ResumableBlock(
                [Yield(Var("x"))], own_environment=False, name="function"
            ),
            name="dup_param_fn",
        )


def test_missing_required_arguments_raise_value_error() -> None:
    range_fn = build_range_function()
    with pytest.raises(ValueError, match=r"(?i)required|missing"):
        range_fn.new({"start": 1})
