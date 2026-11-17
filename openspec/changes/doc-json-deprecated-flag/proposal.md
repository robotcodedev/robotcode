# Proposal: doc-json-deprecated-flag

## Why

The JSON output of `robotcode doc` does not say whether a keyword is deprecated (#694). A keyword entry has `name`, `anchor`, `args`, `short_doc`, `tags`, `doc`, `source` and `lineno` ([doc_cli.py:84](../../../packages/repl/src/robotcode/repl/doc_cli.py)). A deprecated keyword shows only in the text of `short_doc` and `doc`, and only in the form the library writes, for example `**DEPRECATED!!** Use `Expect Element` instead` after the conversion to Markdown. A tool or an agent that wants to list a library's keywords without the deprecated ones, or explain a `DeprecatedKeyword` hint, has to parse that text.

## What Changes

- In the JSON output of `doc lib`, `doc keywords` and `doc keyword`, the entry of a deprecated keyword gets `"deprecated": true`. The entries of other keywords don't have the field. Libdoc's own JSON spec files do the same.
- A keyword counts as deprecated exactly when keyword completion marks it as deprecated and RobotCode reports the `DeprecatedKeyword` hint on its calls.
- The guide on browsing documentation names the field.
- Unchanged: the other fields, the Markdown output and the TOML output's other fields. With `--format toml` the field follows the same rule.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `documentation-cli`: a new requirement for the `deprecated` field of keyword entries in JSON.

## Impact

- `packages/repl/src/robotcode/repl/doc_cli.py`: `KeywordEntry` and `_keyword_entries`.
- `docs/src/content/docs/guides/cli/browsing-documentation.md`: the sentence that lists the fields of a keyword entry.
- Tests: `tests/robotcode/repl/test_doc_cli.py`. Its check of the exact field set uses Collections, which has no deprecated keywords, and stays as it is.
- No change to the language server, the clients or the agent skill, which does not list the JSON fields.
