# Tasks

## 1. The command

- [ ] 1.1 Move the selection of keywords by name and the report of names without a match out of `keyword` in `packages/repl/src/robotcode/repl/doc_cli.py` into a helper (D4). Verify that the existing tests of `doc keyword` in `tests/robotcode/repl/test_doc_cli.py` still pass.
- [ ] 1.2 Add the function that finds the lines of a keyword (D2), for Python with `ast` and for Robot Framework files with `get_resource_model`. Add tests for a decorated method, a keyword with a docstring, a keyword followed by blank lines, the last keyword of a file, a suite file and a JSON resource file, using `tmp_path`. Verify with the tests on the focused environment.
- [ ] 1.3 Add `robotcode doc source TARGET [NAME]...` with its Markdown output (D3), paths (D5) and the options of `doc keyword`, with the data in proper dataclasses. Add tests for the scenarios of "Source of keywords", "Source of a library or a resource" and "Paths in the source output", also with `-o`. Verify with the tests on the focused environment.
- [ ] 1.4 Add the JSON output and the report of code that can't be shown. Add tests for the scenarios of "JSON of the source" and "Code that cannot be shown". Verify with the tests on the focused environment, and that separators and line endings in the tests don't depend on the platform.
- [ ] 1.5 Run `hatch run lint:all` and `hatch run test:test`. Verify that both pass, also on the oldest Robot Framework version in the matrix.

## 2. The documentation

- [ ] 2.1 Add a section on `source` to `docs/src/content/docs/guides/cli/browsing-documentation.md`, with output of a real run, and mention it in the page's introduction. Verify in the dev server, light and dark.
- [ ] 2.2 Regenerate the CLI reference with `hatch run create-cmd-line-docs`. Verify that `reference/cli.md` has the new command and that `npm run docs:build` passes.

## 3. The skill

- [ ] 3.1 Add the command to "Documentation lookup priority" in `plugins/robotcode/skills/robotcode/SKILL.md` on `next` in `robotframework-agent-plugins`, without telling agents to avoid reading files. Verify with the skill's validator that it stays valid.
- [ ] 3.2 Add an eval case to `evals/robotcode/cases/` that asks where a keyword of the project is defined and what its code does, with `must_run` on `robotcode doc source`. Run it with Sonnet, Opus, Haiku (with the skill named in the prompt) and GitHub Copilot CLI, using `--plugin-dir` and `robotcode` from the sources. Verify that it passes with the new line and record what happens without it.
- [ ] 3.3 Sync the vendored copy with `hatch run build:sync-chat-plugin`. Verify that `git diff` shows only this skill change there.

## Workflow follow-up

- Commits only on the maintainer's request: code, docs and OpenSpec files separately, the skill in `robotframework-agent-plugins`.
- The maintainer pushes.
- Codex and opencode for the eval case only if the maintainer asks for them, at the very end.
