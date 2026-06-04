# Analyzing Code

::: tip Installation
The `robotcode analyze` command comes from the optional **`analyze`** package. If it isn't installed yet, add it:

```bash
pip install robotcode[analyze]   # or: pip install robotcode[all]
```
:::

**`robotcode analyze code`** performs static analysis on a Robot Framework project: it parses the `.robot` and `.resource` files, resolves their imports, libraries, and variables, and reports diagnostics for problems such as unknown keywords, unresolved variables, wrong argument counts, duplicate or failing imports, and deprecated syntax. No tests are executed.

The analysis is performed by the same code that powers the RobotCode language server, so the diagnostics are identical to the ones shown in the editor (the VS Code extension, the IntelliJ plugin, or any other LSP client); `analyze code` applies that analysis to the whole project from the command line. Configuration and profile resolution work the same as for `robotcode robot`, so imports and variables resolve as they would at run time. The result is printed as a human-readable list or, for CI use, as a structured report (JSON, SARIF, GitHub annotations, or GitLab Code Quality).

Which diagnostics are reported, and at what severity, can be configured per project or inline in the source; this is shared with the language server and documented separately in [Controlling Diagnostics with Modifiers](diagnostics-modifiers.md).

**Who this is for:**

- **Developers** who want a fast "is my project sound?" check before committing or running anything.
- **CI/CD pipelines** that want to fail a build on broken keyword references or upload findings to a code-scanning dashboard.
- **Code review / security tooling** — the SARIF output plugs straight into GitHub code scanning; the GitLab format into Merge Request Code Quality widgets.
- **AI-driven workflows** — a coding agent gets a precise, machine-readable list of what's wrong instead of having to run the suite and parse a traceback.

This guide covers **`analyze code`**. The `analyze` group has one other subcommand, [`cache`](#managing-the-analysis-cache), for inspecting and clearing the on-disk analysis cache — covered briefly at the end.

For the exhaustive, auto-generated option list see the [CLI reference](cli.md#code).

## Quick start

```bash
# Analyze the current project (default paths from the active profile)
robotcode analyze code

# Analyze a specific folder or file
robotcode analyze code tests/acceptance
robotcode analyze code tests/acceptance/login.robot

# Only look at certain files
robotcode analyze code --filter "**/*.resource"

# Also report unused keywords and variables
robotcode analyze code --collect-unused

# Treat a specific diagnostic as ignored / as an error
robotcode analyze code -mi MultipleKeywords
robotcode analyze code -me VariableNotFound

# Machine-readable output
robotcode analyze code --output-format json
robotcode analyze code --output-format sarif --output-file robotcode.sarif
```

If you don't pass any paths, `analyze code` analyzes the **whole project** — every `.robot` / `.resource` file under the project root, minus the configured exclude patterns. (This is unlike `robotcode robot`, which would run only the default paths/suites from your profile.)

## How `analyze code` finds your project

`analyze code` reuses the full RobotCode configuration pipeline:

1. It locates the project root and the `robot.toml` / `pyproject.toml` files the same way every other `robotcode` command does.
2. It applies the active **profile(s)** (`--profile`) and the `[tool.robotcode-analyze]` settings.
3. It honours `--variable`, `--variablefile` and `--pythonpath` (mirroring the corresponding `robot` options) so that imports and variable resolution behave exactly as they would at run time.

This matters: a keyword that only resolves because of a `--pythonpath` entry or a variable file resolves during analysis too, instead of being wrongly reported as missing.

The project's imports and libraries are always resolved up front, across the whole project — that part can't be narrowed. The per-file diagnostics are then computed only for the files selected by `paths` / `--filter`, so a narrower selection does make a run faster.

## What it checks

The diagnostics are exactly those the language server produces. Among the most common:

- **`KeywordNotFound`** — a keyword call that resolves to nothing.
- **`MultipleKeywords`** — an ambiguous keyword name matching several definitions.
- **`VariableNotFound`** / **`VariableNotReplaced`** — references to variables that don't exist or can't be resolved statically.
- **import diagnostics** — `LibraryAlreadyImported`, `ResourceAlreadyImported`, `ImportContainsErrors`, circular imports, …
- **deprecation warnings** — `DeprecatedReturnSetting`, `DeprecatedHeader`, `DeprecatedHyphenTag`, …
- **model errors** — empty tests/keywords, invalid headers, and other structural problems.

This is *static* analysis, so it isn't the last word: actually running the suite — or even discovering it with [`robotcode discover`](discovering-tests.md) — can surface errors that `analyze code` doesn't. Building the real test suite runs additional, suite-wide checks (for example duplicate test case names), and a `PreRunModifier` may have changed the suite before it's executed — neither of which the per-file static analysis sees. A clean `analyze code` result is a strong signal, not a guarantee that a run will start without errors.

### Unused keywords and variables

By default `analyze code` does **not** flag unused definitions. Unlike the per-file diagnostics, deciding whether a keyword or variable is unused needs the reference data of the *whole* project — not just the selected files — so it can't take the `paths` / `--filter` shortcut, and it adds an extra pass that is noticeably slower on projects with many keywords and variables. Enable it explicitly:

```bash
robotcode analyze code --collect-unused
```

This adds two diagnostics:

- **`KeywordNotUsed`** — a keyword defined in the project that nothing references.
- **`VariableNotUsed`** — a variable/argument that's never read. Names that are intentionally unused (`${_}`, `${_ignored}`) are skipped.

They behave like any other diagnostic — you can remap or ignore them with the [modifiers](#severities-and-diagnostic-modifiers) (e.g. `-mh KeywordNotUsed`) or `# robotcode:` comments.

You can also turn this on permanently in `robot.toml`:

```toml
[tool.robotcode-analyze.code]
collect_unused = true
```

## Severities and diagnostic modifiers

Every diagnostic has one of four severities — **Error**, **Warning**, **Information**, **Hint** — and you can remap any diagnostic code to a different severity (or silence it entirely). On the command line:

| Flag | Effect |
|---|---|
| `-mi`, `--modifiers-ignore CODE` | Ignore this diagnostic code entirely |
| `-me`, `--modifiers-error CODE` | Treat as **Error** |
| `-mw`, `--modifiers-warning CODE` | Treat as **Warning** |
| `-mI`, `--modifiers-information CODE` | Treat as **Information** |
| `-mh`, `--modifiers-hint CODE` | Treat as **Hint** |

Each flag can be given multiple times. The same mapping is available — and usually better kept — in `robot.toml`:

```toml
[tool.robotcode-analyze.modifiers]
ignore = ["VariableNotFound"]
error = ["MultipleKeywords"]
hint = ["KeywordNotUsed"]
```

`*` is a wildcard that matches every code, so `-mi "*"` silences all diagnostics. Re-introducing specific codes at a chosen severity then gives you an allow-list:

```bash
# show only KeywordNotFound — reported as a warning
robotcode analyze code -mi "*" -mw KeywordNotFound
```

This is a *remap* (the kept codes take the severity you assign). If you instead want to keep a code at its original severity, use the [`--code` filter](#reporting-only-some-diagnostics).

Because the severity is configurable, the text and SARIF/GitHub/GitLab output always carries the **effective** severity, not a hard-coded one. For the full modifier system — including inline `# robotcode:` comments — see [Controlling Diagnostics with Modifiers](diagnostics-modifiers.md).

### Reporting only some diagnostics

Two flags narrow the result to a subset. Unlike the modifiers above (which *remap* a code's severity), these *filter*: whatever you don't list is dropped from the output, the summary **and** the exit code alike — the severity of what remains is unchanged.

- **`--severity`** — keep only the given severities. Values: `error`, `warn`/`warning`, `info`/`information`, `hint`.
- **`--code`** — keep only the given diagnostic codes (e.g. `KeywordNotFound`); matching is case-insensitive.

Both are repeatable and comma-separated. When both are given they combine with **AND** — a diagnostic must match both.

```bash
robotcode analyze code --severity warning,hint               # only warnings and hints
robotcode analyze code --code KeywordNotFound                # only KeywordNotFound, with its real severity
robotcode analyze code --code KeywordNotUsed --severity hint  # only KeywordNotUsed that are hints
```

When neither is given, everything is reported.

## Exit codes

`analyze code` exits with a **bitwise combination** of these values, so a single status tells you which severities were present:

| Bit | Value | Meaning |
|---|---|---|
| — | `0` | **SUCCESS** — nothing reported |
| `1` | `ERRORS` | at least one error |
| `2` | `WARNINGS` | at least one warning |
| `4` | `INFOS` | at least one information |
| `8` | `HINTS` | at least one hint |

For example, errors **and** warnings give `1 | 2 = 3`.

To stop certain severities from affecting the exit code — e.g. so warnings don't fail the build — use an **exit-code mask**:

```bash
# Warnings/infos/hints no longer change the exit code; only errors do
robotcode analyze code --exit-code-mask warn,info,hint

# Same, but additive to the mask configured in robot.toml
robotcode analyze code --extend-exit-code-mask hint
```

Valid mask values: `error`, `warn` (alias `warning`), `info` (alias `information`), `hint`, `all`. In `robot.toml`:

```toml
[tool.robotcode-analyze.code]
exit_code_mask = ["warn", "info", "hint"]   # CI fails only on errors
```

Any non-zero exit means something was reported, which is what makes a CI step fail by default. To branch on a specific severity, test the corresponding bit — in bash:

```bash
robotcode analyze code
code=$?
(( code & 1 )) && echo "errors present"
(( code & 2 )) && echo "warnings present"
```

## Output formats

The local `--output-format` flag selects how results are rendered. It **overrides the global `--format`** for this command:

| Value | Output |
|---|---|
| `concise` *(default)* | Human-readable list, one finding per line, sorted by `(file, line, column)` |
| `json` | Compact structured result (`diagnostics` + `summary`) |
| `json-indent` | Same, pretty-printed |
| `sarif` | SARIF 2.1.0 log — for GitHub code scanning and other SARIF consumers |
| `github` | GitHub Actions workflow annotations (`::error file=…`) |
| `gitlab` | GitLab Code Quality report (JSON array) |

`--output-file FILE` writes the report to a file instead of stdout (for the `json`, `json-indent`, `sarif`, `github` and `gitlab` formats) — handy for uploading a CI artifact. A missing target directory yields a clear error rather than a traceback.

```bash
robotcode analyze code --output-format sarif --output-file reports/robotcode.sarif
```

## Text output (`concise`)

The default format prints one finding per line:

```
tests/login.robot:4:5: [ERROR] KeywordNotFound: No keyword with name 'Lgin User' found.
tests/login.robot:7:1: [WARNING] KeywordNotUsed: Keyword 'Helper' is not used.
Files: 12, Errors: 1, Warnings: 1, Infos: 0, Hints: 0 (in 0.42s)
```

- Each line is `path:line:column: [SEVERITY] Code: message`; the severity tag is colored (red/yellow/blue/cyan).
- Output is **sorted by `(file, line, column)`**, so it's stable regardless of internal analysis order.
- Workspace-level problems that aren't tied to a single file (e.g. a broken command-line variable file) are prefixed with `.:`.
- Related locations are shown on indented `->` lines.
- The summary line is colored after the highest severity present.

By default RobotCode trims the Python traceback and `PYTHONPATH` listing that Robot Framework appends to import errors. Pass `--show-tracebacks` to keep the full message.

## SARIF

`--output-format sarif` emits a [SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/sarif-v2.1.0-errata01-os.html) log — the format GitHub code scanning, Azure DevOps and the VS Code SARIF Viewer consume.

```bash
robotcode analyze code --output-format sarif --output-file robotcode.sarif
```

Paths are written relative to the project root, which is what GitHub code scanning expects (use `--full-paths` for absolute paths). Once uploaded, an alert stays stable as long as the finding does — an unrelated edit that merely shifts its line number won't create a duplicate.

## GitHub Actions annotations

`--output-format github` emits [workflow annotations](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands). Printed in a GitHub Actions job, they appear inline on the affected lines in the PR diff and in the run summary.

```bash
robotcode analyze code --output-format github
```

Each diagnostic becomes one annotation line:

```
::error file=tests/login.robot,line=4,col=5,endColumn=14,title=KeywordNotFound::No keyword with name 'Lgin User' found.
```

## GitLab Code Quality

`--output-format gitlab` emits a [Code Quality report](https://docs.gitlab.com/ci/testing/code_quality/) that GitLab renders in the Merge Request Code Quality widget.

```bash
robotcode analyze code --output-format gitlab --output-file gl-code-quality.json
```

Each diagnostic becomes one entry in the JSON array:

```json
[
  {
    "description": "No keyword with name 'Lgin User' found.",
    "check_name": "KeywordNotFound",
    "fingerprint": "…",
    "severity": "major",
    "location": { "path": "tests/login.robot", "lines": { "begin": 4 } }
  }
]
```

## CI recipes

### GitHub: upload to code scanning

Produce a SARIF file and upload it so the findings appear under **Security → Code scanning**. The `security-events: write` permission is required for the upload, and `continue-on-error` lets the upload run even when `analyze code` exits non-zero because it found problems.

```yaml
name: RobotCode Analyze
on: [push, pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      security-events: write      # required for upload-sarif
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: "3.x"
      # Set up the project with whatever package manager it uses (pip, uv,
      # poetry, pdm, hatch, ...); analysis just needs robotcode[analyze] available.
      - run: pip install robotcode[analyze]
      - run: robotcode analyze code --output-format sarif --output-file robotcode.sarif
        continue-on-error: true
      - uses: github/codeql-action/upload-sarif@v4
        with:
          sarif_file: robotcode.sarif
```

### GitHub: inline PR annotations

Print the `github` format directly — the diagnostics show up as inline annotations on the run and in the PR diff. No upload and no extra permissions needed.

```yaml
name: RobotCode Analyze
on: [push, pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: "3.x"
      # Set up the project with whatever package manager it uses (pip, uv,
      # poetry, pdm, hatch, ...); analysis just needs robotcode[analyze] available.
      - run: pip install robotcode[analyze]
      - run: robotcode analyze code --output-format github
```

### GitLab: Code Quality artifact

Write the GitLab report and expose it as a `codequality` artifact; GitLab renders it in the Merge Request Code Quality widget.

```yaml
robotcode-analyze:
  image: python:3
  script:
    # set up the project with whatever package manager it uses (pip shown here)
    - pip install robotcode[analyze]
    - robotcode analyze code --output-format gitlab --output-file gl-code-quality.json
  artifacts:
    reports:
      codequality: gl-code-quality.json
```

### Fail the build on errors only

```bash
# Exit non-zero only for errors; warnings/infos/hints are reported but ignored
robotcode analyze code --exit-code-mask warn,info,hint
```

### Get just the counts

```bash
robotcode analyze code --output-format json | jq '.summary'
```

## Managing the analysis cache

To speed up repeat analysis, RobotCode caches resolved library/variable imports (and, with `--cache-namespaces`, analyzed namespaces) on disk. The `analyze cache` subcommands let you inspect and clear it:

```bash
robotcode analyze cache info     # where the cache lives and how big it is
robotcode analyze cache list     # what's cached
robotcode analyze cache path     # print the cache directory
robotcode analyze cache clear    # remove it (e.g. after changing ignored-libraries)
robotcode analyze cache prune    # drop stale entries only
```

Clearing the cache is the usual fix after changing cache-affecting settings such as `ignore-arguments-for-library`.

## Configuration via `robot.toml`

Everything controllable on the command line (and more) lives under `[tool.robotcode-analyze]`:

```toml
[tool.robotcode-analyze]
exclude-patterns = ["**/generated/**"]
global-library-search-order = ["MyPreferredLibrary"]
load-library-timeout = 30

[tool.robotcode-analyze.code]
collect_unused = true
exit_code_mask = ["warn", "info", "hint"]

[tool.robotcode-analyze.modifiers]
ignore = ["VariableNotFound"]
error = ["MultipleKeywords"]

[tool.robotcode-analyze.cache]
ignored-libraries = ["MyDynamicLibrary"]
```

See the [`robot.toml` configuration reference](config.md) for the complete list of settings.

## JSON reference

`--output-format json` (or `json-indent`) emits a single object with two keys, using the same LSP `Diagnostic` shape as `robotcode discover` and `robotcode results`:

```json
{
  "diagnostics": {
    "tests/login.robot": [
      {
        "range": { "start": { "line": 3, "character": 4 },
                   "end":   { "line": 3, "character": 13 } },
        "message": "No keyword with name 'Lgin User' found.",
        "severity": 1,
        "code": "KeywordNotFound",
        "source": "robotcode"
      }
    ]
  },
  "summary": { "files": 12, "errors": 1, "warnings": 0, "infos": 0, "hints": 0 }
}
```

Field notes:

- Keys in `diagnostics` are source paths (project-relative POSIX, or absolute with `--full-paths`). Workspace-level diagnostics key on `.`.
- `severity` follows the LSP enum: `1` = Error, `2` = Warning, `3` = Information, `4` = Hint.
- Positions are **0-based** (LSP convention), unlike SARIF/GitHub which are 1-based.
- The JSON always carries the full diagnostic message — `--show-tracebacks` does not apply.
- `summary` is always present, even for a clean run (all counts `0`), so consumers get a stable schema.
