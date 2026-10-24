# Design

## Context

`packages/runner/src/robotcode/runner/cli/results/_html.py` decides once at import which converter it defines: `_HAS_EXT` is true when `from html_to_markdown import ConversionOptions, convert` succeeds, and the module then defines only the `html-to-markdown` branch of `_convert`, otherwise only the built-in `_StdlibToMd` branch. `html_to_markdown()` catches any exception of the conversion and strips the tags instead, which records no artefacts. `results.py` uses the module as `_html.…`.

The development and test environments install the `all` dependency group, which includes the `html` group, so the test matrix runs with `html-to-markdown` (3.17.2 today) and never with the built-in converter.

`html_to_markdown.__version__` exists in 2.30.0, 3.0.2, 3.17.2 and 3.18.x (checked). With the screenshot prefix, 2.0.0, 2.15.0, 2.30.0 (each with its own API) and the first release of every 3.x minor up to 3.17, plus 3.17.2, return empty content; 3.18.0 is the first that keeps it. 3.0 and 3.1 return a `dict`, 3.3.0 raises a `KeyError` in `convert()`, and 3.6.0 cannot be imported (checked). The release list holds plain `X.Y.Z` versions and `3.8.0rc1`/`rc2`. 3.18.0 has `cp310-abi3` wheels for Linux (x86_64, aarch64), macOS (x86_64, arm64) and Windows (amd64) and requires Python 3.10 or newer.

## Goals / Non-Goals

**Goals:**
- One decision at import that covers every way an old `html-to-markdown` can get into an environment.

**Non-Goals:**
- Supporting the 2.x or 3.0–3.17 API or behaviour of `html-to-markdown`.
- A message to the user that an old `html-to-markdown` is ignored.
- The double rewrite of linked images (see proposal.md).

## Decisions

### D1: Version check where the import is

In the `try` block of `_html.py`, also import `__version__` from `html_to_markdown` and set `_HAS_EXT` only when `create_version_from_str(__version__)` (`robotcode.core.utils.version`, which the runner reaches through `robotcode-robot`) gives a major and minor of at least 3.18. An `InvalidVersionError` or a missing `__version__` counts like an old version. The rest of the module stays as it is: below 3.18 it defines the built-in branch, exactly as without the package.

- The robocop integration checks the version of its optional package the same way (`robocop_helper.py`).
- `importlib.metadata.version("html-to-markdown")` would work too; `__version__` needs no distribution metadata and is present in every version checked.
- Testing the behaviour instead (convert a sample message at import and look at the result) was rejected: it costs a conversion on every start, and 2.x to 3.1 and 3.3.0 fail before any result, in different ways.
- Adapting to the older APIs was rejected: every version before 3.18 also drops the screenshot messages.

`create_version_from_str` rejects suffixes it does not know (such as `.post1`); such a version would use the built-in converter, which gives a correct result. `3.8.0rc1` parses and stays below 3.18.

### D2: Floor without upper bound or pin

`html-to-markdown>=3.18` in the `html` extra of `packages/runner/pyproject.toml` and in the `html` dependency group of the root `pyproject.toml`. No exact pin: it would conflict with other packages in the same environment that need `html-to-markdown` and hold back fixes. No upper bound: no newer version is known to break. Other third-party dependencies also give only a lower bound.

### D3: Tests

- **Acceptance:** a test case `Screenshot Test` in `tests/robotcode/runner/cli/results/suites/artifacts.robot` that writes `screenshot-1.png` into the folder of `${OUTPUT FILE}` (`OperatingSystem.Split Path` and `Evaluate`; the fixtures pass `--output` as an absolute path, so `${OUTPUT DIR}` is another folder, and external references are resolved against the folder of the result file; `Create File` is not used because its own `file://` link would be another artefact of the test, and `$var` in `Evaluate` fails on Robot Framework 5.0 with Python 3.14) and logs the two messages of the spec scenarios with the `</td></tr><tr><td colspan="3">` prefix. A test in `test_log.py` checks that both artefacts of that test have an `extractedTo` that exists. The test environments run it with the installed `html-to-markdown`, which is ≥ 3.18 after D2.
- **Version check:** a new `tests/robotcode/runner/cli/results/test_html.py` (skipped without `html-to-markdown`) sets `html_to_markdown.__version__` to `3.17.2`, `2.30.0` and `not-a-version` with `monkeypatch`, reloads `_html` with `importlib.reload`, and checks that `_HAS_EXT` is false and that the prefixed embedded message records an embedded artefact; with `3.18.0` `_HAS_EXT` is true. A fixture reloads `_html` again after `monkeypatch` has restored the real version, so later tests see the normal module.
- **Real old versions:** once by hand, the reproduction of proposal.md in a scratch environment with the repository's packages installed editable, switching `html-to-markdown` between 2.30.0, 3.0.2, 3.17.2, 3.18.6 and none with `uv pip`.

## Risks / Trade-offs

- [A user with an old `html-to-markdown` gets the built-in converter without being told] → The result is correct; the built-in converter covers the HTML Robot Framework libraries log. `pip install -U "robotcode-runner[html]"` brings the newer version.
- [A later `html-to-markdown` release breaks the screenshot messages again] → The acceptance test of D3 runs with whatever version the environments resolve and catches it.
- [Reloading `_html` in a test leaves another module with stale references] → `results.py` accesses the module through its attribute (`_html.html_to_markdown`), and the fixture reloads it back to the real state.

## Migration Plan

None. The development environments install the newer `html-to-markdown` on their next `hatch run`.
