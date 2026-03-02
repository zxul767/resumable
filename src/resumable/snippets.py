def range_generator_source(
    *,
    include_empty_sentinel: bool = False,
    include_return_end: bool = False,
) -> str:
    maybe_empty = (
        """
        if start == end {
            yield "empty";
        }
        """
        if include_empty_sentinel
        else ""
    )
    maybe_return = "return end;" if include_return_end else ""

    return f"""
    gen range(start, end) {{
        {maybe_empty}
        var i = start;
        while i < end {{
            yield i;
            i = i + 1;
        }}
        {maybe_return}}}
    """
