# Tasks

## 1. Group and pages

- [ ] 1.1 Move `docs/src/content/docs/guides/ai-agents.md` to `docs/src/content/docs/guides/ai-agents/index.mdx` with `git mv`, set its label "Overview" (order 90 and title stay), and add `"ai-agents": "AI Agents"` to `GROUP_LABELS` in `docs/src/routeData.ts` (design D1). Verify with `git status` that git records a rename, and in the dev server that the sidebar shows the group AI Agents between Command Line and Project Configuration and that `/guides/ai-agents/` shows the page.
- [ ] 1.2 Write `guides/ai-agents/setting-up.md` from the current page's setup sections, with their headings, plus "In PyCharm" and "Checking that it works" (D2), and remove these sections from the overview. Verify in the dev server that `#matching-your-robotcode-version`, `#adding-the-marketplace-from-vs-code` and `#in-pycharm` exist on `/guides/ai-agents/setting-up/`.
- [ ] 1.3 Write `guides/ai-agents/how-the-skill-works.md` (D2) with the heading "AI-agent detection" and its table, and remove "How it works" and "AI-agent detection" from the overview. Before writing, check each statement about the skill against `SKILL.md` in robotframework-agent-plugins (`next`). Verify that `#ai-agent-detection` exists on `/guides/ai-agents/how-the-skill-works/`.
- [ ] 1.4 Write `guides/ai-agents/troubleshooting.md` with the five entries of today, by symptom and with links to the new pages, and remove Troubleshooting from the overview. Verify that every link on the page resolves in the dev server.
- [ ] 1.5 Create `guides/ai-agents/working-with-the-agent.md` with its introduction (the example project in a few sentences, a link to the Briefing page) and the six section headings of D3, without sessions yet. Rewrite the overview as in D2: the abilities link to these sections, and `<AreaOverview area="guides/ai-agents" />` is at the end. Verify that `/guides/ai-agents/` shows the agents, the three steps and five link cards in sidebar order (spec "From the overview").
- [ ] 1.6 Change the links of D10 and add `ai-agents/` to "Groups of guides" in `CONTRIBUTING.md`. Verify with `grep -rn "guides/ai-agents/#"` over `docs/src`, `README.md` and `CONTRIBUTING.md` that no link points to an anchor of the old page, and run `npm run docs:build` with all internal links valid.

## 2. Recording setup

- [ ] 2.1 Write the preparation part of `playground/robotcode-demo/agent-sessions/record.sh` (D5, D6): the session project in the scratchpad from the listed project files, the absolute sources in its `pyproject.toml`, `uv sync`, `rfbrowser init`, an empty `XDG_CONFIG_HOME` and the shop served at `BASE_URL`. Verify in the copy that `robotcode --version` reports the checkout's version, `robotcode discover tests` lists 13 tests, `robotcode robot` fails only `Login Works`, and no `CLAUDE.md` or `AGENTS.md` other than the project's lies in the copy or above it.
- [ ] 2.2 Write the `AGENTS.md` of the session project (D5). Verify each statement against `robot.toml`, `pyproject.toml`, the suites and `libraries/ShopLibrary.py`.
- [ ] 2.3 Write `guides/ai-agents/briefing.md` from "Give the agent project context", with the instruction files per agent and the complete `AGENTS.md` of 2.2 (D2), and remove the section from the overview. Before writing, check in the current documentation of Claude Code, GitHub Copilot and Codex which instruction file each reads. Verify that `/guides/ai-agents/briefing/` shows the file in full (spec "Instruction file of the example project").
- [ ] 2.4 Create the Claude Code configuration of D6. Ask the maintainer to log in once with `CLAUDE_CONFIG_DIR=<dir> claude`, since this session cannot do the login. Then add the marketplace and install the plugin. Verify that `claude plugin list` in that configuration shows only `robotcode`, `claude mcp list` shows no server, and the folder holds no `CLAUDE.md` or rules.
- [ ] 2.5 Write the session part of `record.sh` (D6): the outer variables removed, one `claude -p --input-format stream-json --output-format stream-json` process per session that gets the next prompt when the answer before has arrived, the allow list, the restore and the removal of the per-project data between sessions, the `.jsonl` into `agent-sessions/`. Verify with a trial session:
  - "Which tests are tagged smoke?" shows the skill loaded and a `robotcode discover` command, no MCP server and no other instructions;
  - a background command started for the first prompt still runs at the second;
  - a second trial session does not see the first.
- [ ] 2.6 Write `agent-sessions/to_markdown.py` (D4, D8) and `agent-sessions/check_shortened.py`, which checks that every line of a shortened session except the `…` lines appears, in order, in the complete one. Verify both on the trial transcript of 2.5.
- [ ] 2.7 Create `playground/agent-skill-befunde.md` with the findings known before the first recording (D9): the missing "how" for interactive sessions with the tools of each agent, and the REPL prompt that is missing when its input is not a terminal, with the trial scripts. Verify that each entry names its source (skill file and section, code line, or trial script).
- [ ] 2.8 Write `agent-sessions/large_project.py` (D7). Verify that the generated project has about 5000 tests in about 500 suites, that a full run takes about a minute and fails only the tests meant to fail, and that `robotcode analyze code` reports no errors in it.

## 3. Sessions

- [ ] 3.1 Record "From a requirement", "A task" and "Keywords in the REPL" (D3), convert and shorten them (D4), and add them with their notes to "Writing tests and tasks". For "A task", add `data/restock.csv` to the session project first. A session with a finding goes into the findings list and stays off the page (D9). Verify each added session with `check_shortened.py` against its complete Markdown.
- [ ] 3.2 Record "Smoke tests on staging" and, from the state after "From a requirement", "Another browser"; add them to "Running tests". Verify each with `check_shortened.py`.
- [ ] 3.3 Record "A failing test" after a full run, then "Comparing runs" with that run kept in `results/nightly/`, and "Debugging step by step"; add them to "Failing tests", except a session with a finding (D9). Verify each added session with `check_shortened.py` and that the sessions show the commands of the spec scenarios "Failing test", "Comparing runs" and "Debugging step by step".
- [ ] 3.4 Record "Coverage", "Keywords" and, in the generated project, "A large project"; add them to "Knowing the project". Verify each with `check_shortened.py`.
- [ ] 3.5 Record "Before a push" and "A profile for the CI server"; add them to "Code quality" and "Configuration". Verify each with `check_shortened.py`, and that the profile of the second session works with `robotcode -p <profile> config show` in its session project.
- [ ] 3.6 Put the prompts of "What you can ask" that no session shows below their sections, and add the version line (D4, D8). Verify the version line against the init events of the transcripts and `robotcode --version`.
- [ ] 3.7 Complete `playground/agent-skill-befunde.md` from all transcripts (D9): each place where the agent went against the skill or where its guidance was missing or wrong, with the session and the transcript lines. Report the list to the maintainer. Verify that every session left off the page has an entry.
- [ ] 3.8 Only after the changes that improve the skill or the CLI for the findings of 3.7 are applied: record the sessions with a finding again, add those that no longer show one, and update the version line. Verify as in 3.1–3.6. Until then, this task and the change stay open.

## 4. Checks

- [ ] 4.1 Run `npm run docs:build` and verify that it passes with all internal links valid.
- [ ] 4.2 Verify in the built sidebar (`docs/dist/guides/index.html`) the scenario "Order in the sidebar" of `documentation-site`, and on `docs/dist/guides/ai-agents/index.html` the order of the six pages (spec "Pages in the sidebar").
- [ ] 4.3 Run `openspec validate docs-ai-agents-guide --strict` and verify that it passes.

## Workflow follow-up

- After the archive, run `openspec validate --specs --strict` and verify that all main specs pass.
