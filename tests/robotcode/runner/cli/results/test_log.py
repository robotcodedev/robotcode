"""Acceptance tests for `robotcode results log`.

These exercise the JSON body-item dispatch (one test per RF body-item type
where the tree shape is the interesting bit), the artefact-extraction code
path, and the render-only options (`--level`, `--max-depth`, `--raw-html`).

Body-item assertions read the JSON output because the dispatch logic lives
there; render-only flags are checked against TEXT output.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from ._helpers import count_entries_of_type, find_test, iter_body, strip_ansi
from .conftest import CliRunner, JsonRunner, needs_rf_70, needs_rf_72

# ---------------------------------------------------------------------------
# Helpers local to this file
# ---------------------------------------------------------------------------


def _test_body(data: Dict[str, Any], full_name: str) -> List[Dict[str, Any]]:
    test = find_test(data["tests"], full_name)
    assert test is not None, f"test {full_name} not found in {[t['fullName'] for t in data['tests']]}"
    return test.get("body") or []


def _entries_of_type(body: List[Dict[str, Any]], type_name: str) -> List[Dict[str, Any]]:
    return [e for e in iter_body(body) if e.get("type") == type_name]


def _first_entry_of_type(body: List[Dict[str, Any]], type_name: str) -> Optional[Dict[str, Any]]:
    matches = _entries_of_type(body, type_name)
    return matches[0] if matches else None


# ---------------------------------------------------------------------------
# Basic structure
# ---------------------------------------------------------------------------


def test_log_basic_lists_all_tests(json_result: JsonRunner, basic_output: Path) -> None:
    data = json_result("log", output_path=basic_output)
    full_names = {t["fullName"] for t in data["tests"]}
    assert full_names == {
        "Basic.Passing Test One",
        "Basic.Passing Test Two",
        "Basic.Passing Test Three",
        "Basic.Failing Test",
        "Basic.Skipped Test",
    }


def test_log_test_has_body_and_status(json_result: JsonRunner, basic_output: Path) -> None:
    data = json_result("log", output_path=basic_output)
    for t in data["tests"]:
        assert "body" in t
        assert t["status"] in ("PASS", "FAIL", "SKIP", "NOT RUN")


def test_log_keyword_with_arguments(json_result: JsonRunner, basic_output: Path) -> None:
    """`Should Be Equal foo foo` records its args on the KEYWORD entry."""
    data = json_result("log", output_path=basic_output)
    body = _test_body(data, "Basic.Passing Test Two")
    kw = _first_entry_of_type(body, "KEYWORD")
    assert kw is not None
    assert kw.get("args") == ["foo", "foo"]
    # Name is library-qualified: BuiltIn.Should Be Equal
    assert "Should Be Equal" in (kw.get("name") or "")


# ---------------------------------------------------------------------------
# Control structures available on every RF version
# ---------------------------------------------------------------------------


def test_log_body_for_in(json_result: JsonRunner, loops_and_branches_output: Path) -> None:
    """A FOR loop has flavor 'IN' and ITERATION children with `assign`."""
    data = json_result("log", output_path=loops_and_branches_output)
    body = _test_body(data, "Loops And Branches.For In Test")
    for_entry = _first_entry_of_type(body, "FOR")
    assert for_entry is not None
    assert for_entry.get("flavor") == "IN"
    iterations = _entries_of_type(for_entry.get("body") or [], "ITERATION")
    # 3 elements in @{ITEMS} → 3 iterations
    assert len(iterations) == 3
    # Each iteration carries the loop variable assignment
    assigns = [it.get("assign") for it in iterations]
    assert all(a == ["${item}"] for a in assigns)


def test_log_body_for_in_range(json_result: JsonRunner, loops_and_branches_output: Path) -> None:
    data = json_result("log", output_path=loops_and_branches_output)
    body = _test_body(data, "Loops And Branches.For In Range Test")
    for_entry = _first_entry_of_type(body, "FOR")
    assert for_entry is not None
    assert for_entry.get("flavor") == "IN RANGE"
    assert len(_entries_of_type(for_entry.get("body") or [], "ITERATION")) == 3


def test_log_body_if_else_chain(json_result: JsonRunner, loops_and_branches_output: Path) -> None:
    """IF / ELSE IF / ELSE branches are present and each carries a condition."""
    data = json_result("log", output_path=loops_and_branches_output)
    body = _test_body(data, "Loops And Branches.If Else Test")
    if_entry = _first_entry_of_type(body, "IF")
    assert if_entry is not None
    # IF root contains the three branches as children
    branches = if_entry.get("body") or []
    types = [b["type"] for b in branches]
    assert "IF" in types
    assert "ELSE IF" in types
    assert "ELSE" in types


# ---------------------------------------------------------------------------
# Modern statements (WHILE, TRY/EXCEPT/FINALLY, RETURN, BREAK, CONTINUE) —
# available on every supported RF version.
# ---------------------------------------------------------------------------


def test_log_body_while(json_result: JsonRunner, statements_modern_output: Path) -> None:
    data = json_result("log", output_path=statements_modern_output)
    body = _test_body(data, "Statements Modern.While Loop Test")
    while_entry = _first_entry_of_type(body, "WHILE")
    assert while_entry is not None
    assert "${i}" in (while_entry.get("condition") or "")
    # WHILE has ITERATION children
    assert _entries_of_type(while_entry.get("body") or [], "ITERATION")


def test_log_body_try_except_finally(json_result: JsonRunner, statements_modern_output: Path) -> None:
    data = json_result("log", output_path=statements_modern_output)
    body = _test_body(data, "Statements Modern.Try Except Test")
    try_entry = _first_entry_of_type(body, "TRY")
    assert try_entry is not None
    branches = try_entry.get("body") or []
    types = [b["type"] for b in branches]
    assert "EXCEPT" in types
    assert "FINALLY" in types
    # EXCEPT carries the matched patterns
    except_branch = next(b for b in branches if b["type"] == "EXCEPT")
    assert except_branch.get("patterns") == ["inner*"]
    assert except_branch.get("patternType") == "GLOB"


def test_log_body_return(json_result: JsonRunner, statements_modern_output: Path) -> None:
    data = json_result("log", output_path=statements_modern_output)
    body = _test_body(data, "Statements Modern.Return Test")
    # RETURN lives inside the KEYWORD body, recurse the whole tree
    return_entry = _first_entry_of_type(body, "RETURN")
    assert return_entry is not None
    assert return_entry.get("args") == ["early-value"]


def test_log_body_break_continue(json_result: JsonRunner, statements_modern_output: Path) -> None:
    data = json_result("log", output_path=statements_modern_output)
    body = _test_body(data, "Statements Modern.For With Continue And Break Test")
    assert count_entries_of_type(body, "CONTINUE") >= 1
    assert count_entries_of_type(body, "BREAK") >= 1


# ---------------------------------------------------------------------------
# RF 7.0+ VAR statement
# ---------------------------------------------------------------------------


@needs_rf_70
def test_log_body_var_statement(json_result: JsonRunner, statements_var_output: Path) -> None:
    """VAR records the variable name on `assign` and the value on `args`."""
    data = json_result("log", output_path=statements_var_output)
    body = _test_body(data, "Statements Var.Var Statement Test")
    var_entries = _entries_of_type(body, "VAR")
    assert len(var_entries) == 2
    first = var_entries[0]
    assert first.get("assign") == ["${local}"]
    assert first.get("args") == ["local-value"]
    # The SUITE-scoped VAR carries the scope marker
    suite_var = var_entries[1]
    assert suite_var.get("assign") == ["${suite_var}"]
    assert suite_var.get("scope") == "SUITE"


# ---------------------------------------------------------------------------
# RF 7.2+ GROUP block
# ---------------------------------------------------------------------------


@needs_rf_72
def test_log_body_group(json_result: JsonRunner, statements_group_output: Path) -> None:
    data = json_result("log", output_path=statements_group_output)
    body = _test_body(data, "Statements Group.Group Test")
    group_entry = _first_entry_of_type(body, "GROUP")
    assert group_entry is not None
    assert group_entry.get("name") == "Setup phase"
    # Group has its two Log calls inside
    assert len(_entries_of_type(group_entry.get("body") or [], "KEYWORD")) == 2


# ---------------------------------------------------------------------------
# Render-only options
# ---------------------------------------------------------------------------


def test_log_level_filter_drops_info_messages(json_result: JsonRunner, basic_output: Path) -> None:
    """`--level FAIL` removes INFO MESSAGE entries from the JSON tree."""
    info_data = json_result("log", output_path=basic_output)
    fail_data = json_result("log", "--level", "FAIL", output_path=basic_output)
    info_msgs = sum(count_entries_of_type(t.get("body") or [], "MESSAGE") for t in info_data["tests"])
    fail_msgs = sum(count_entries_of_type(t.get("body") or [], "MESSAGE") for t in fail_data["tests"])
    assert info_msgs > 0
    assert fail_msgs < info_msgs


def test_log_max_depth_collapses_text(text_result: CliRunner, basic_output: Path) -> None:
    """`--max-depth 1` collapses nested keyword bodies in TEXT output."""
    plain = strip_ansi(text_result("log", "--max-depth", "1", output_path=basic_output).stdout)
    assert "hidden" in plain
    assert "--max-depth 1" in plain


def test_log_full_paths_keeps_rel_source(json_result: JsonRunner, basic_output: Path) -> None:
    """`--full-paths` is a TEXT-render hint; JSON keeps both `source`
    (absolute) and `relSource` so consumers have a stable schema."""
    data = json_result("log", "--full-paths", output_path=basic_output)
    for t in data["tests"]:
        src = t.get("source")
        assert src is not None
        assert Path(src).is_absolute()
        assert t.get("relSource") is not None


def test_log_default_includes_rel_source(json_result: JsonRunner, basic_output: Path) -> None:
    data = json_result("log", output_path=basic_output)
    for t in data["tests"]:
        assert t.get("relSource") is not None


# ---------------------------------------------------------------------------
# Artefact extraction
# ---------------------------------------------------------------------------


def test_log_extract_writes_embedded_image(json_result: JsonRunner, artifacts_output: Path, tmp_path: Path) -> None:
    """`--extract DIR` decodes embedded base64 images to disk."""
    extract = tmp_path / "extracted"
    data = json_result("log", "--extract", str(extract), output_path=artifacts_output)
    assert data["extractedCount"] >= 1
    # Walk every ArtifactRef and verify the extractedTo file exists
    found = False
    for t in data["tests"]:
        for ref in t.get("artifacts") or []:
            if ref.get("embedded") and ref.get("extractedTo"):
                assert Path(ref["extractedTo"]).is_file()
                found = True
    assert found, "no embedded artefact was extracted"


def test_log_extract_external_missing_source_reported(
    json_result: JsonRunner, artifacts_output: Path, tmp_path: Path
) -> None:
    """External refs whose source path is unreachable get `missing-source`."""
    extract = tmp_path / "extracted"
    data = json_result("log", "--extract", str(extract), output_path=artifacts_output)
    # Find at least one file-kind ref with the expected skip reason
    reasons = []
    for t in data["tests"]:
        for ref in t.get("artifacts") or []:
            if ref.get("kind") == "file" and ref.get("skippedReason"):
                reasons.append(ref["skippedReason"])
    assert "missing-source" in reasons


def test_log_raw_html_skips_extraction(json_result: JsonRunner, artifacts_output: Path) -> None:
    """With `--raw-html`, embedded data URIs are NOT decoded into ArtifactRefs."""
    data = json_result("log", "--raw-html", output_path=artifacts_output)
    # Raw-HTML mode keeps the original markup in MESSAGE entries
    found_html = False
    for t in data["tests"]:
        for entry in iter_body(t.get("body") or []):
            if entry.get("type") == "MESSAGE" and entry.get("isHtml"):
                text = entry.get("text") or ""
                if "<img" in text or "<a " in text:
                    found_html = True
    assert found_html


# ---------------------------------------------------------------------------
# Filter integration smoke
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("filter_args", "expected_count"),
    [
        (["--status", "fail"], 1),
        (["--status", "pass"], 3),
        (["--test", "Failing*"], 1),
    ],
)
def test_log_filter_integration(
    filter_args: List[str], expected_count: int, json_result: JsonRunner, basic_output: Path
) -> None:
    data = json_result("log", *filter_args, output_path=basic_output)
    assert len(data["tests"]) == expected_count


# ---------------------------------------------------------------------------
# `--keyword-info` flag: doc / tags / timeout on KEYWORD entries
# ---------------------------------------------------------------------------


def test_log_keyword_info_off_by_default(json_result: JsonRunner, keyword_meta_output: Path) -> None:
    """Without `--keyword-info` the new fields are absent from JSON."""
    data = json_result("log", output_path=keyword_meta_output)
    test = find_test(data["tests"], "Keyword Meta.Tagged Caller")
    assert test is not None
    helper = next((e for e in iter_body(test.get("body") or []) if e.get("name") == "Helper With Metadata"), None)
    assert helper is not None
    assert "doc" not in helper
    assert "tags" not in helper
    assert "timeout" not in helper


def test_log_keyword_info_populates_doc_tags_timeout(json_result: JsonRunner, keyword_meta_output: Path) -> None:
    """`--keyword-info` adds the executed keyword's [Documentation]/[Tags]/[Timeout]."""
    data = json_result("log", "--keyword-info", output_path=keyword_meta_output)
    test = find_test(data["tests"], "Keyword Meta.Tagged Caller")
    assert test is not None
    helper = next((e for e in iter_body(test.get("body") or []) if e.get("name") == "Helper With Metadata"), None)
    assert helper is not None
    assert helper.get("doc") == "Helper keyword documentation token: KW_DOC_TOKEN_beta."
    assert helper.get("tags") == ["KWTagProbe"]
    assert helper.get("timeout") == "7 days"


def test_log_keyword_info_renders_inline_in_text(robotcode_cli: CliRunner, keyword_meta_output: Path) -> None:
    """TEXT renderer shows [Documentation]/[Tags]/[Timeout] beneath the keyword."""
    result = robotcode_cli(
        ["results", "log", "--keyword-info", "--output", str(keyword_meta_output)],
    )
    out = strip_ansi(result.stdout)
    assert "[Documentation]" in out
    assert "KW_DOC_TOKEN_beta" in out
    assert "[Tags]" in out
    assert "KWTagProbe" in out
    assert "[Timeout]" in out
    assert "7 days" in out


def test_log_default_text_omits_keyword_info(robotcode_cli: CliRunner, keyword_meta_output: Path) -> None:
    """Without `--keyword-info`, the TEXT output never prints those lines —
    even for keywords that have a [Documentation] in their definition.

    Guards against an accidental change that always renders the keyword
    info (the inverse risk to the JSON default-off check above)."""
    result = robotcode_cli(["results", "log", "--output", str(keyword_meta_output)])
    out = strip_ansi(result.stdout)
    assert "[Documentation]" not in out
    assert "[Tags]" not in out
    assert "[Timeout]" not in out
    assert "KW_DOC_TOKEN_beta" not in out


def test_log_keyword_info_omits_lines_for_keywords_without_metadata(
    json_result: JsonRunner, keyword_meta_output: Path
) -> None:
    """Built-in keywords have a [Documentation] (from the library) but no
    [Tags] / [Timeout]. With `--keyword-info` JSON should include `doc`
    but leave `tags` / `timeout` absent (defaults dropped)."""
    data = json_result("log", "--keyword-info", output_path=keyword_meta_output)
    test = find_test(data["tests"], "Keyword Meta.Plain Test")
    assert test is not None
    log = next((e for e in iter_body(test.get("body") or []) if e.get("name") == "BuiltIn.Log"), None)
    assert log is not None
    assert log.get("doc")  # BuiltIn.Log has a docstring
    assert "tags" not in log
    assert "timeout" not in log


def test_log_keyword_info_combines_with_search(robotcode_cli: CliRunner, keyword_meta_output: Path) -> None:
    """`--keyword-info` + `--search` co-exist: the search filters the test
    set, and `--keyword-info` still renders the keyword metadata on the
    surviving tests. Regression guard against either flag clobbering the
    other in `render_log`."""
    result = robotcode_cli(
        [
            "results",
            "log",
            "--keyword-info",
            "--search",
            "KW_DOC_TOKEN_beta",
            "--output",
            str(keyword_meta_output),
        ],
    )
    out = strip_ansi(result.stdout)
    # `KW_DOC_TOKEN_beta` only appears in the helper keyword's doc, so
    # `Plain Test` should not survive the search.
    assert "Tagged Caller" in out
    assert "Plain Test" not in out
    # And the surviving test's keyword info is rendered.
    assert "[Documentation]" in out
    assert "KW_DOC_TOKEN_beta" in out


# ---------------------------------------------------------------------------
# `--suite-info` flag: suite headers (name/doc/metadata/source) in TEXT & JSON
# ---------------------------------------------------------------------------


def test_log_suite_info_off_by_default(json_result: JsonRunner, keyword_meta_output: Path) -> None:
    """Without `--suite-info` JSON has neither `suites` nor per-test `suite`."""
    data = json_result("log", output_path=keyword_meta_output)
    assert "suites" not in data
    for t in data["tests"]:
        assert "suite" not in t


def test_log_suite_info_populates_json(json_result: JsonRunner, keyword_meta_output: Path) -> None:
    """`--suite-info` adds `suites` (with doc/metadata) and `suite` per test."""
    data = json_result("log", "--suite-info", output_path=keyword_meta_output)

    suites = data.get("suites") or []
    assert len(suites) == 1
    s = suites[0]
    assert s["fullName"] == "Keyword Meta"
    assert s["name"] == "Keyword Meta"
    assert s["status"] == "PASS"
    assert "SUITE_DOC_TOKEN_alpha" in (s.get("doc") or "")
    assert s.get("metadata") == {"OwnerTeam": "payments-squad", "BuildBadge": "green"}

    # Every test carries the parent suite's `fullName` for cross-reference.
    for t in data["tests"]:
        assert t["suite"] == "Keyword Meta"


def test_log_suite_info_renders_text_header(robotcode_cli: CliRunner, keyword_meta_output: Path) -> None:
    """TEXT renders a `Suite:` header with name, doc and metadata, then
    indents the tests underneath it."""
    result = robotcode_cli(["results", "log", "--suite-info", "--output", str(keyword_meta_output)])
    out = strip_ansi(result.stdout)
    assert "Suite: Keyword Meta" in out
    assert "[Documentation] Suite-level documentation token: SUITE_DOC_TOKEN_alpha." in out
    assert "[Metadata] OwnerTeam = payments-squad" in out
    assert "[Metadata] BuildBadge = green" in out
    # Tests get printed indented under the suite header.
    assert "  Test: Keyword Meta.Tagged Caller" in out
    assert "  Test: Keyword Meta.Plain Test" in out


def test_log_default_text_omits_suite_header(robotcode_cli: CliRunner, keyword_meta_output: Path) -> None:
    """Default TEXT (no flag) keeps the flat-tests layout — no `Suite:` line."""
    result = robotcode_cli(["results", "log", "--output", str(keyword_meta_output)])
    out = strip_ansi(result.stdout)
    assert "Suite:" not in out
    assert "[Metadata]" not in out
    # Tests are still listed (unindented) without a wrapping header.
    assert "Test: Keyword Meta.Tagged Caller" in out


def test_log_suite_info_groups_nested_suites_separately(json_result: JsonRunner, nested_output: Path) -> None:
    """Each leaf suite gets its own entry; tests reference the correct parent."""
    data = json_result("log", "--suite-info", output_path=nested_output)
    suites = data.get("suites") or []
    full_names = {s["fullName"] for s in suites}
    # The nested fixture has at least `Nested.Child.A` and `Nested.Child.B`.
    assert {"Nested.Child.A", "Nested.Child.B"}.issubset(full_names)

    # Tests reference their immediate parent suite, not the root.
    by_test = {t["fullName"]: t["suite"] for t in data["tests"]}
    assert by_test["Nested.Child.A.Test In A One"] == "Nested.Child.A"
    assert by_test["Nested.Child.B.Test In B One"] == "Nested.Child.B"


def test_log_suite_info_omits_doc_metadata_when_absent(
    json_result: JsonRunner, loops_and_branches_output: Path
) -> None:
    """A suite without `Metadata` gets no `metadata` field (defaults dropped)."""
    data = json_result("log", "--suite-info", output_path=loops_and_branches_output)
    s = (data.get("suites") or [None])[0]
    assert s is not None
    assert "metadata" not in s


def test_log_keyword_info_populates_setup_keywords(json_result: JsonRunner, keyword_meta_output: Path) -> None:
    """`--keyword-info` populates SETUP entries too (Tagged Caller's
    `[Setup]    Helper With Metadata` carries the user keyword's
    documentation/tags/timeout)."""
    data = json_result("log", "--keyword-info", output_path=keyword_meta_output)
    test = find_test(data["tests"], "Keyword Meta.Tagged Caller")
    assert test is not None
    setup = next((e for e in iter_body(test.get("body") or []) if e.get("type") == "SETUP"), None)
    assert setup is not None
    assert setup.get("doc") == "Helper keyword documentation token: KW_DOC_TOKEN_beta."
    assert setup.get("tags") == ["KWTagProbe"]
    assert setup.get("timeout") == "7 days"
