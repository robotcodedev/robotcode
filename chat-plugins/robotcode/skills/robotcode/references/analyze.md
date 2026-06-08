# Static analysis — `robotcode analyze code`

`robotcode analyze code [PATHS]` parses the project's `.robot` and `.resource` files, resolves their imports, libraries, and variables, and reports diagnostics — **without executing anything**. It catches what a plain text scan can't, because resolution runs with the project's installed Robot Framework, `robot.toml`, and active profiles. Comes from the optional **`analyze`** package (`pip install robotcode[analyze]`, or `[all]`).

Reach for it on "find issues", "check my robot code", "any undefined keywords / wrong arguments?", "are there unused keywords or variables?", and as a pre-commit / CI gate before running.

## Contents

- What it reports
- Running it & narrowing scope
- Focusing the output (severity, code)
- Unused keywords & variables
- Severity & suppression (modifiers)
- Exit code (CI gating)
- Machine-readable output
- Cache
- Common workflows

## What it reports

One diagnostic per line — `path:line:col: [SEVERITY] CODE: message` — then a summary line `Files: N, Errors: N, Warnings: N, Infos: N, Hints: N`. The severity tag is the **full word** (`[ERROR]`, `[WARNING]`, `[INFO]`, `[HINT]`), so `grep '\[E\]'` matches nothing — use `--severity` (below) instead of grepping.

Typical diagnostics:

- **Undefined / unknown keywords** (`KeywordNotFound`) and ambiguous matches (`MultipleKeywords`)
- **Unresolved variables** (`VariableNotFound`)
- **Wrong argument counts** on a keyword call
- **Duplicate or failing imports** (library / resource / variables)
- **Deprecated syntax**
- **Unused keywords / variables** (`KeywordNotUsed` / `VariableNotUsed`) — opt-in, see below

## Running it & narrowing scope

```bash
robotcode analyze code                              # no path → whatever robot.toml `paths` covers
robotcode analyze code tests/acceptance/billing/    # narrow by path
robotcode analyze code --filter '**/*.robot'        # narrow by glob
```

`analyze code` accepts paths on the command line, so it composes with git to lint only changed files — see *Common workflows*.

## Focusing the output

```bash
robotcode analyze code --severity error          # only errors — in output, summary, AND exit code
robotcode analyze code --code KeywordNotFound     # only this diagnostic code (severity unchanged)
```

Prefer `--severity` / `--code` over piping through `grep`: they also shrink the summary and the exit code, not just the printed lines.

## Unused keywords & variables

Off by default — opt in:

```bash
robotcode analyze code --collect-unused
```

Surfaces `KeywordNotUsed` / `VariableNotUsed`. Great for cleanup, but **noisy** on libraries/resources that *intentionally* export keywords for other projects — ignore it on those paths (`-mi KeywordNotUsed`) or persist the policy in config (below).

## Severity & suppression (modifiers)

Pick the **lowest** scope that solves the problem:

| Scope | How |
| --- | --- |
| One line | end-of-line comment — `Log    ${x}    # robotcode: ignore[VariableNotFound]` |
| A block | a standalone `# robotcode: ignore[KeywordNotFound]` line **indented** inside the block — suppresses to the block's end |
| Rest of the file | the same standalone comment at **column 0** — suppresses to end of file |
| One command run | `robotcode analyze code -mi MultipleKeywords` |
| Project-wide | `robot.toml` → `[tool.robotcode-analyze.modifiers]`, `ignore = ["MultipleKeywords"]` |

**Re-classify** instead of ignoring: `-me` → error, `-mw` → warning, `-mI` → info, `-mh` → hint (the matching keys under `[tool.robotcode-analyze.modifiers]`: `error`, `warning`, `information`, `hint`). Mind the case: lowercase `-mi` *ignores* a code, capital `-mI` re-classifies it to info.

## Exit code (CI gating)

The exit code is a **bitmask** — `1` errors, `2` warnings, `4` infos, `8` hints. Check **bits**, not exact values. (Unlike `robotcode robot`, whose exit code is the failed-test count.)

Mask severities out of the exit code so only what you care about fails the build:

```bash
robotcode analyze code -xm warn -xm info -xm hint   # only errors fail
```

Or persistently:

```toml
[tool.robotcode-analyze.code]
exit-code-mask = ["warn", "info", "hint"]
```

`-xe` / `extend-exit-code-mask` appends to the config's mask instead of replacing it.

## Machine-readable output

```bash
robotcode --format json analyze code                # JSON to stdout (global --format, like results/discover)
```

For JSON, use the global **`--format json`** *before* the subcommand — the same option as for `results` / `discover`. `--full-paths` emits absolute paths instead of project-relative ones; `--show-tracebacks` restores the Robot Framework tracebacks and `PYTHONPATH` dumps the concise output hides (only when you need a diagnostic's full body).

## Cache

`analyze code` reuses analyzed library/resource data across runs for speed. After refactoring imports, upgrading libraries, or switching branches the cache can mislead — diagnostics that don't make sense, or expected ones missing:

```bash
robotcode analyze cache clear              # wipe cache contents
robotcode analyze code --no-cache-namespaces   # one-off fresh run, cache untouched
```

Inspect with `robotcode analyze cache info` (or `list` / `path`); `cache prune` removes the whole cache directory.

## Common workflows

Two orchestrated flows live in [workflows.md](workflows.md):

- **Lint only the files about to commit** (workflow C) — feed `analyze code` the changed `.robot` / `.resource` files from `git diff`.
- **Full-project sweep & cleanup** (workflow D) — baseline → errors first → `--collect-unused` → suppress noise → gate CI → refresh a stale cache.
