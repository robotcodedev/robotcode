# Tasks

## 1. Screenshot messages and floor of the html extra (spec: Screenshot messages that close the table row, Version of the html extra; design D2, D3)

- [x] 1.1 Add the test case `Screenshot Test` to `tests/robotcode/runner/cli/results/suites/artifacts.robot`: write `screenshot-1.png` into the folder of `${OUTPUT FILE}` and log, as HTML, `</td></tr><tr><td colspan="3"><a href="screenshot-1.png"><img src="screenshot-1.png" width="800px"></a>` and `</td></tr><tr><td colspan="3"><img alt="screenshot" src="data:image/png;base64,…" width="800px">` (the PNG of `Embedded Image Test`); verify that the existing tests in `test_log.py` that use `artifacts_output` still pass.
- [x] 1.2 Add `test_log_extract_screenshot_messages` to `tests/robotcode/runner/cli/results/test_log.py`: `log --extract DIR` on `artifacts_output` gives `Artifacts.Screenshot Test` one embedded artefact and one artefact of `screenshot-1.png`, each with an `extractedTo` that exists, and the embedded-image placeholder in the message text; verify that it fails in the current environment (`html-to-markdown` 3.17.2).
- [x] 1.3 Change `html = ["html-to-markdown>=2.0"]` to `>=3.18` in `[project.optional-dependencies]` of `packages/runner/pyproject.toml` and in `[dependency-groups]` of the root `pyproject.toml`; verify that `hatch run python -c "import html_to_markdown; print(html_to_markdown.__version__)"` prints 3.18 or newer after the sync and that 1.2 now passes.

## 2. Version check (spec: Supported html-to-markdown versions; design D1, D3)

- [x] 2.1 In the `try` block of `packages/runner/src/robotcode/runner/cli/results/_html.py`, import `__version__` from `html_to_markdown` and set `_HAS_EXT` only when `create_version_from_str(__version__)` has a major and minor of at least 3.18; an `InvalidVersionError` or `ImportError` leaves it false. Say in the module docstring that the external converter is used from 3.18 on; verify with 2.2.
- [x] 2.2 Add `tests/robotcode/runner/cli/results/test_html.py` (`pytest.importorskip("html_to_markdown")`): with `html_to_markdown.__version__` set by `monkeypatch` to `3.17.2`, `2.30.0` and `not-a-version`, `importlib.reload(_html)` gives `_HAS_EXT` false, and `_html.html_to_markdown` on the prefixed embedded message from 1.1 records one embedded artefact; with `3.18.0` `_HAS_EXT` is true. A fixture reloads `_html` after `monkeypatch` has restored the real version. Verify that the tests pass with 2.1 and the `3.17.2` case fails without it, and that `hatch run test:test tests/robotcode/runner/cli/results` passes both with the default file order and with `test_log.py` given before `test_html.py`.

## 3. Integration

- [x] 3.1 Run the reproduction of proposal.md with the full CLI (`robotcode results log --extract`) on the output of `artifacts.robot` in a scratch environment with the repository's packages installed editable, with `html-to-markdown` 2.30.0, 3.0.2, 3.17.2 and 3.18.6 (switched with `uv pip`) and once without it; verify that every run extracts both screenshots of `Screenshot Test`.
- [x] 3.2 Run `hatch run test:test` and `hatch run lint:all`; verify both are green.

## Workflow follow-up

- Archive the change after review; it creates the capability `results-html-messages`.
- The double rewrite of linked images with `html-to-markdown` (proposal.md, "Not part of this change") stays open.
