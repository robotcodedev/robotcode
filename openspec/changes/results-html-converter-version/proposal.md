# Proposal: results-html-converter-version

## Why

`robotcode results log --extract DIR` creates only an empty `DIR` for screenshots of SeleniumLibrary and Browser when the optional `html-to-markdown` package is installed in a version older than 3.18, and the log shows the screenshot messages as empty `[INFO]` lines. Reported on Slack; reproduced on `main` with messages built like those of SeleniumLibrary 6.9.0 and Browser 20.6.0, which both start every screenshot message (file and embedded) with `</td></tr><tr><td colspan="3">` to break out of the table row of `log.html`:

| `html-to-markdown` | Result |
|---|---|
| not installed (built-in converter) | both screenshots extracted |
| 2.30.0 | empty: `ConversionOptions` has no `extract_images`, `TypeError` |
| 3.0.2 | empty: `convert()` returns a `dict`, `.content` fails |
| 3.17.2 | empty: the converter drops everything after the prefix |
| 3.18.0, 3.18.6 | both screenshots extracted |

In the three empty cases the conversion error is caught and the message falls back to stripping the tags, which records no artefacts. The `html` extra of `robotcode-runner` and the `html` dependency group of the repository allow `html-to-markdown>=2.0`. Raising that floor alone does not reach every installation: the bound only applies when the extra is installed, and `robotcode[all]==2.6.0` pulled in `robotcode-runner[html]`, so environments that upgraded from 2.6.0 can still have an old `html-to-markdown`.

## What Changes

- `robotcode results` uses `html-to-markdown` only when version 3.18 or newer is installed. With an older version, or one whose version cannot be read, it converts HTML messages with its built-in converter, as if `html-to-markdown` were not installed.
- The `html` extra of `robotcode-runner` and the `html` dependency group in the root `pyproject.toml` require `html-to-markdown>=3.18`.

Not part of this change: with `html-to-markdown` installed, a linked image (`<a href="x.png"><img src="x.png"></a>`) is rewritten twice, which leaves a broken `file://` URL in the message text and an extra artefact skipped as `missing-source`; the image itself is extracted.

## Capabilities

### New Capabilities

- `results-html-messages`: How `robotcode results log` converts HTML log messages and finds their artefacts, independent of whether and in which version `html-to-markdown` is installed.

### Modified Capabilities

<!-- none -->

## Impact

- `packages/runner/src/robotcode/runner/cli/results/_html.py`: the import of `html-to-markdown` checks its version.
- `packages/runner/pyproject.toml` (`html` extra) and `pyproject.toml` (`html` dependency group): floor `>=3.18`. The development and test environments get the newer version on their next sync.
- Tests: a screenshot-like test case in `tests/robotcode/runner/cli/results/suites/artifacts.robot` with tests in `test_log.py`, and a test for the version check.
- Docs: none; the results guide does not mention `html-to-markdown`.
