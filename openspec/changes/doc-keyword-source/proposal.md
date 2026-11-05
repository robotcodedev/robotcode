# Proposal

## Why

To see the code of a keyword, an agent or a user has to find it first. `output.xml` has a line only for tests, not for keywords, so `robotcode results log` names a keyword but doesn't say where it is. `robotcode doc keyword` shows its documentation, and only its JSON output has the path and the line. `.source` in the REPL and the debugger shows the code, but it needs a running REPL. In the runs for the AI agents tutorial, agents searched the project with `grep` for such things.

The maintainer decided on 2026-11-05 for a command of its own, so that an agent can get the code without reading the whole documentation, and asked that it also show a library or a resource as a whole.

## What Changes

- **A new command, `robotcode doc source TARGET [NAME]...`,** with the same targets as the other `doc` commands:
  - With NAME, it shows where the selected keywords are defined and their code with line numbers, without their documentation. A NAME selects keywords as in `robotcode doc keyword`.
  - Without NAME, it shows where the library, resource file or suite file is, and the whole file.
- **Output:** Markdown as in the other `doc` commands, also with `-o`, and an object with the same data with `--format json`.
- **Code that can't be shown,** for example of a library without a source file, is reported on standard error, and the exit code isn't 0. What can be shown is still shown.
- **The skill names the command** in its documentation lookup, and an eval case checks that agents use it.
- **The guide on browsing documentation** gets a section, and the generated CLI reference is regenerated.

Not part of this change:

- Finding a keyword without naming its library or resource. That needs the imports of a suite, and the log already names the owner of a keyword.
- Line numbers for keywords in `robotcode results`. `output.xml` doesn't have them.
- Showing the path and the line in the text output of `robotcode doc keyword`.
- `.source` in the REPL and the debugger, which stays as it is.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `documentation-cli`: the command group gets the subcommand `source`, with requirements on what it shows, on code that can't be shown, on paths and on its JSON.
- `agent-skill-guidance`: a requirement says that the skill's documentation lookup names the command.

## Impact

- `packages/repl/src/robotcode/repl/doc_cli.py`, and its tests in `tests/robotcode/repl/test_doc_cli.py`.
- `docs/src/content/docs/guides/cli/browsing-documentation.md`, and `docs/src/content/docs/reference/cli.md` through `hatch run create-cmd-line-docs`.
- `plugins/robotcode/skills/robotcode/SKILL.md` and a new case in `evals/robotcode/cases/` on `next` in `robotframework-agent-plugins`, and the vendored copy of the skill through `hatch run build:sync-chat-plugin`.
- No new dependency and no settings.
