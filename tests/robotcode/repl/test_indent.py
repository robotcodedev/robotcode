"""Tests for the block-aware indent helpers used by Stage 4 multi-line."""

import pytest

from robotcode.repl._indent import compute_indent, has_open_block

# ---------------------------------------------------------------------------
# compute_indent — depth tracking + width parameter
# ---------------------------------------------------------------------------


def test_compute_indent_empty_buffer_returns_no_indent() -> None:
    assert compute_indent([]) == ""


def test_compute_indent_balanced_buffer_returns_no_indent() -> None:
    assert compute_indent(["FOR    ${i}    IN RANGE    3", "    Log    ${i}", "END"]) == ""


def test_compute_indent_single_for_opens_one_level() -> None:
    assert compute_indent(["FOR    ${i}    IN RANGE    3"]) == "    "


@pytest.mark.parametrize("opener", ["FOR", "WHILE", "IF", "TRY", "GROUP"])
def test_compute_indent_all_block_openers_increment_depth(opener: str) -> None:
    assert compute_indent([f"{opener}    something"]) == "    "


def test_compute_indent_is_case_insensitive() -> None:
    """Robot's keyword matching is case-insensitive — the indent counter
    must follow suit (otherwise lowercase `for` wouldn't trigger indent)."""
    assert compute_indent(["for    ${i}    IN RANGE    3"]) == "    "
    assert compute_indent(["fOr    ${i}    IN RANGE    3"]) == "    "


def test_compute_indent_nested_blocks_stack() -> None:
    assert (
        compute_indent(
            [
                "FOR    ${i}    IN RANGE    2",
                "    IF    ${i} == 1",
            ]
        )
        == "        "  # 8 spaces — depth 2 times width 4
    )


def test_compute_indent_end_decrements() -> None:
    assert (
        compute_indent(
            [
                "FOR    ${i}    IN RANGE    2",
                "    IF    ${i} == 1",
                "        Log    inner",
                "    END",  # closes the IF — back to depth 1
            ]
        )
        == "    "
    )


def test_compute_indent_branch_markers_do_not_change_depth() -> None:
    """`ELSE` / `ELSE IF` / `EXCEPT` / `FINALLY` stay at the current
    depth — they're inside a block, not opening or closing one."""
    for branch in ("ELSE", "ELSE IF", "EXCEPT", "FINALLY"):
        assert (
            compute_indent(
                [
                    "IF    ${x}",
                    "    Log    body",
                    f"    {branch}",
                ]
            )
            == "    "
        )


def test_compute_indent_blank_lines_ignored() -> None:
    assert compute_indent(["FOR    ${i}    IN RANGE    3", "", "    Log    a"]) == "    "


def test_compute_indent_leading_whitespace_doesnt_obscure_first_cell() -> None:
    """A line typed at a deeper level (with leading spaces) still has
    the same first-cell semantics."""
    assert compute_indent(["    FOR    ${i}    IN RANGE    3"]) == "    "


def test_compute_indent_tab_separator_works() -> None:
    """`\\t` is also a Robot cell separator."""
    assert compute_indent(["FOR\t${i}\tIN RANGE\t3"]) == "    "


def test_compute_indent_stray_end_clamps_at_zero() -> None:
    """A stray END at depth 0 is a syntax error but the counter must
    not go negative — that would seed a negative-width indent string."""
    assert compute_indent(["END"]) == ""


def test_compute_indent_custom_width() -> None:
    assert compute_indent(["FOR    ${i}    IN RANGE    3"], width=2) == "  "
    assert compute_indent(["FOR", "    IF    ${x}"], width=2) == "    "


# ---------------------------------------------------------------------------
# has_open_block — used by prompt_toolkit's smart-Enter logic
# ---------------------------------------------------------------------------


def test_has_open_block_empty_string_is_closed() -> None:
    assert has_open_block("") is False


def test_has_open_block_plain_keyword_is_closed() -> None:
    assert has_open_block("Log    hello") is False


def test_has_open_block_unclosed_for_is_open() -> None:
    assert has_open_block("FOR    ${i}    IN RANGE    3") is True


def test_has_open_block_for_with_end_is_closed() -> None:
    assert has_open_block("FOR    ${i}    IN RANGE    3\n    Log    ${i}\nEND") is False


def test_has_open_block_nested_partially_closed() -> None:
    """One outer FOR + inner IF + inner END → still depth 1 (outer open)."""
    assert has_open_block("FOR    ${i}    IN RANGE    3\n    IF    ${x}\n        Log\n    END") is True


def test_has_open_block_all_branches_at_balanced_depth() -> None:
    """`IF` + body + `ELSE` + body + `END` → balanced, no open block."""
    assert has_open_block("IF    ${x}\n    Log    a\nELSE\n    Log    b\nEND") is False
