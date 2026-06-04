# Installing robotcode in a project

Getting `robotcode` into a project's own Python environment — and the right sub-packages (extras) alongside it — so the CLI sees the project's libraries, resources, and local modules. This is the workflow for two situations: `command -v robotcode` (or `Get-Command robotcode` on Windows) comes up empty, **or** a `robotcode <X>` invocation fails with `Error: No such command 'X'` (which means the sub-package shipping `X` isn't installed).

## Contents

1. The non-negotiable: in-project install
2. Before installing: ask the user two things
3. Install command per package manager
4. Verify
5. If a command is missing later

## 1. The non-negotiable: in-project install

**robotcode must be installed *into* the project's environment** — not run in isolation. It needs access to everything the test suite imports: Robot Framework's standard libraries, third-party libs (`SeleniumLibrary`, `Browser`, etc.), the project's own `lib/` and `resources/` directories, and any local Python modules. Isolated runners like `uvx robotcode ...` or `pipx run robotcode ...` create a separate environment that can't see any of those, so they don't work for real projects — only an in-project install does.

## 2. Before installing: ask the user two things

The PyPI package `robotcode` is just the CLI core (`config`, `profiles`, plugin host). Every command group lives in a separate sub-package, pulled in via extras. Two decisions need explicit user input before you run any install command. Ask both in **one** user-prompt round-trip, not two.

**1. Install scope — dev dependency or venv-only?**

- **Dev dependency** — `uv add --dev` / `poetry add --group dev` / etc. Writes to `pyproject.toml` and the lockfile, so everyone on the team gets robotcode on their next sync. Right when the project is committing to robotcode as part of its dev tooling.
- **Venv-only** — `uv pip install` / `poetry run pip install` / plain `pip install` into the active venv. No project files touched, nothing to commit. Right for exploration, ad-hoc work, or when the user isn't ready to make robotcode a team-wide choice.

When in doubt, **venv-only is the safer default** — it's reversible (`pip uninstall`), produces no PR diff, and can be promoted to a dev dependency later if the user decides to keep using robotcode.

**2. Which extras?**

Minimum for this skill is `robotcode[runner,analyze,repl]`:

- `runner` — `robotcode robot` / `run` / `rebot` / `discover` / `libdoc` / `testdoc` / `results`
- `analyze` — `robotcode analyze code` and `robotcode analyze cache`
- `repl` — `robotcode repl` (interactive shell) **and** `robotcode robot-debug` / `run-debug` (the command-line debugger). Both ship in `repl` — the command-line debugger is **not** in the `debugger` extra below.

Other available extras the user may want included:

- `debugger` — `robotcode debug`, the Debug Adapter Protocol server the editor extensions drive for graphical step-debugging. This is **not** what `robotcode robot-debug` needs (that's the `repl` extra above); only add `debugger` for DAP/editor integration.
- `languageserver` — LSP for IDE integration (usually installed by the VS Code / Neovim extension automatically, not manually)
- `replserver` — network-attachable REPL
- `yaml` — YAML variable files
- `lint` — `robotframework-robocop` integration
- `rest` — reStructuredText documentation format
- `all` — everything; heavier but simplest if the user doesn't want to pick

Sensible option sets to offer in the prompt: *venv-only + minimum* (lowest commitment, good default), *dev-dependency + minimum* (team standard), *dev-dependency + all* (kitchen sink), plus an "Other" escape so the user can mix and match. **Don't silently pick either the minimum or `all`** — surface the trade-off.

## 3. Install command per package manager

Match the manager (look for `uv.lock`, `poetry.lock`, `hatch.toml`, `pdm.lock`, `Pipfile`, plain `requirements*.txt`) **and** the scope the user picked above. Don't `pip install` into an unrelated interpreter — invoke the project's runtime.

**As a dev dependency** (writes to `pyproject.toml` + lockfile):

```bash
uv add --dev "robotcode[runner,analyze,repl]"            # uv
poetry add --group dev "robotcode[runner,analyze,repl]"  # Poetry
pdm add -dG dev "robotcode[runner,analyze,repl]"         # PDM
```

**Into the active venv only** (no manifest changes):

```bash
uv pip install "robotcode[runner,analyze,repl]"          # uv
poetry run pip install "robotcode[runner,analyze,repl]"  # Poetry
pdm run pip install "robotcode[runner,analyze,repl]"     # PDM
pip install "robotcode[runner,analyze,repl]"             # any activated venv
```

Hatch and Pipenv use config-file-based dependency management — for dev-dependency scope, edit `hatch.toml` / `Pipfile` and sync; for venv-only, use `hatch run pip install ...` or `pipenv run pip install ...`.

## 4. Verify

```bash
robotcode --version
robotcode discover info     # shows the bound Robot Framework + Python
```

If `robotcode` is installed but not on `PATH`, the venv isn't active — invoke it via the manager (`uv run robotcode ...`, `poetry run robotcode ...`, `hatch run robotcode ...`, `pdm run robotcode ...`). The CLI itself is fully cross-platform.

## 5. If a command is missing later

robotcode itself can be installed while a command the agent needs isn't — the user did a partial install at some earlier point. The error looks like:

```
Error: No such command 'analyze'.
```

**Don't read this as a typo and don't retry with a different command name.** It means the corresponding sub-package isn't in the environment. Map the missing command to the extra that ships it:

| Command(s) | Needed extra |
| --- | --- |
| `robot` / `run` / `rebot` / `discover` / `libdoc` / `testdoc` / `results` | `runner` |
| `analyze code` / `analyze cache` | `analyze` |
| `repl` / `robot-debug` / `run-debug` | `repl` |
| `debug` (DAP server for editors) | `debugger` |
| `repl-server` | `replserver` |

Treat it the same way as a fresh install: **ask the user before adding the missing extra.** One user-prompt round-trip covers:

- **Scope** — dev dependency or venv-only (same trade-off as in step 2 above)
- **Just this extra, or bundle more?** — if the user is going to touch the manifest or venv anyway, they may want `debugger`/`languageserver` added at the same time rather than in another round-trip later

Then run the install command from step 3 with the new extras list. Most managers merge extras into an existing `robotcode` entry, so `uv add --dev "robotcode[analyze]"` (or whatever scope/extras the user picked) updates rather than reinstalls.
