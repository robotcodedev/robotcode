# Tasks

Everything in `robotframework-agent-plugins` happens on `next`. Commits only on the maintainer's request, asked for each one; the maintainer pushes.

## 1. The skill

- [x] 1.1 Apply `skill-draft.diff` to `plugins/robotcode/skills/robotcode/` on `next` (D1). Verify: `git diff --stat` shows `SKILL.md`, `references/repl.md` and `references/debugging.md`; the two references have 19 929 B and 19 938 B.
- [x] 1.2 Replace the sandbox paragraph in `references/repl.md` and the sentence in `references/debugging.md` with the texts of D2. Verify: `grep -n "outside the sandbox"` in the skill finds nothing.
- [x] 1.3 Remove what is left of the old way (D3): line 295 of `SKILL.md` and the sentence on the piped fallback in `references/repl.md`. Verify: `grep -n -i -E "piped fallback|terminal session"` in the skill finds nothing.
- [x] 1.4 On a finished run of the demo project, check that `robotcode results log --search <argument>` shows a test in which a keyword gets that argument, then add the sentence on search to `SKILL.md` (D4). Verify: the command output, kept in the findings.
- [x] 1.5 Add the sentence on names of suites to `SKILL.md` (D4). Verify: in the demo project, `robotcode discover suites` prints a name that starts with `Tests`, and `robotcode robot -s` with that name runs the suite.
- [x] 1.6 Check the limit and the links (D7). Verify: `wc -c` gives under 20 000 B for both references, and every changed link has its target in the file it points to.

## 2. The evals

- [x] 2.1 Add `--plugin-dir` to `evals/robotcode/run.py` and a line on it to the README (D5). Verify: `./run.py --case 01 --plugin-dir <plugin folder> --allow-all` runs, and the transcript shows the skill loaded from that folder.
- [x] 2.2 Change cases 07–10 to sessions and update the table in the README (D5). Verify: `python -m json.tool` on each case, and the regular expressions match `robotcode session start debug -bl "Tests.Login.Login Works"` and `robotcode session start repl`.
- [x] 2.3 Add cases 11 and 12 and their rows in the README (D5). Verify: `python -m json.tool`, and the value in case 12 occurs in the fixture's `results/output.xml` after `setup.sh`.
- [x] 2.4 Run cases 07–12 with Haiku, Sonnet and Opus against the working copy, without the variables of this agent session (D7). Verify: `run.py` exits with 0 for each model, and I read the rubric against the transcripts. A run with wrong behavior goes back to the text of the skill, a run with right behavior and a failed check to the regular expression.
  - Done 2026-11-02, with the maintainer's OK for one exception: `run.py` doesn't end with 0 reliably for Haiku on case 07 (1 of 3 runs with this skill, 0 of 2 with the old one; Sonnet and Opus pass). Cases 08–12 pass with all three models. Case 07 now names Robot Framework in its query, because Haiku and Sonnet didn't load the skill without that, with the old skill neither. Details in `playground/agent-skill-befunde.md`.

## 3. The trial

- [x] 3.1 Build a fresh lab from the working copy of the plugin and run `all.sh` with Claude Code, Copilot CLI and Codex on `repl`, `debug`, `block` and `again` (D7). Verify: the runs of Claude Code and Copilot are right and they stop their sessions. Codex drives its terminal, and on `again` it says that it can't reach the session. Results go in the findings.
- [x] 3.2 Run `debug` with the per-command sandbox on, in Claude Code and Copilot CLI (Codex has it on already). Verify: no agent tries to leave the sandbox or change its settings. Results go in the findings.
- [x] 3.3 Run `whole_sandbox.sh` with the three agents and the final skill. Verify: all three use sessions and get the task right, and `session list` outside shows none of them. Results go in the findings.
- [x] 3.4 On the Windows VM, run `debug` with the final skill in the sandboxes of Copilot and Codex, with the project's `.venv` in the project folder. Verify: each run ends with a correct answer or an honest report that it can't do it there, and without an attempt to leave the sandbox.

## 4. The guide

- [x] 4.1 Replace the section "Where sessions can't run" in `docs/src/content/docs/guides/cli/sessions.md` with the text of D6. Verify: `npm run docs:build` passes, and the section reads right in the dev server.

## 5. Into the repositories

- [x] 5.1 Ask for the commit of the skill (`docs(skill)`) and of the evals (`test(skill)`) in `robotframework-agent-plugins`. Verify: `python scripts/sync_manifests.py --check` passes, and the commits are signed.
- [x] 5.2 After the commit, sync the vendored copy with `hatch run build:sync-chat-plugin` and ask for the commit `chore(chat-plugin): sync robotcode skill from agent-plugins`. Verify: `chat-plugins/.upstream.json` names the new commit, and `hatch run build:sync-chat-plugin --check` passes.
- [x] 5.3 Ask for the commit of the guide and, separately, of the plan (`docs(openspec)`). Verify: `git show --stat` of each lists only its own paths.

## 6. The rework

After the maintainer's review. It changes parts of sections 1 and 2 (D8–D11).

- [x] 6.1 Take the text from the output `in-section` of `make_skill_variants.py` into `plugins/robotcode/skills/robotcode/` on `next`, with the shorter sandbox hints of D2 (D8–D11). Verify: `wc -c` gives under 20 000 B for both references; every link and its anchor in the skill has its target; `grep -n -E "Ctrl-D|auto-detect|agent backend|Gotchas|report\.html in"` in the skill finds nothing.
- [x] 6.2 Read the whole skill through once as an agent would: contents match the headings, no reference points to something that went, each rule of D10 stands once, and nothing the spec asks for is lost (the exit codes, `status`, `result`, `wait`, `interrupt`, `restart`, `session stop`, the warning against a bare start). Verify: a list of what I changed after reading, in the findings.
- [x] 6.3 Run cases 01–06 and 08–19 against the working copy (D7); ask before the runs with Codex, because they cost credits. Verify: I read the rubric against the transcripts where a check failed. A wrong way goes back to the text of the skill, a right way with a failed check to the check. Per agent, not below the skill before the rework; the results go in the findings.
- [x] 6.4 Fold in the maintainer's review (D8–D11): both ways to start in the mode list of `SKILL.md`, computed values in the section on configuration, the message `No such command` as it is now, and case 20 for a missing extra. In the harness, a sandbox that hides the other runs and the home folder, and Haiku with the skill named. Verify: case 20 with all agents, three runs each, with and without a sentence on asking in `SKILL.md`, to decide on it; cases 08–10 and 13–17 against the working copy; one run of each agent in the new sandbox; the results go in the findings.
- [x] 6.5 Ask for the commit of the skill (`docs(skill)`) in `robotframework-agent-plugins`; after it, sync the vendored copy with `hatch run build:sync-chat-plugin` and ask for the commit `chore(chat-plugin): sync robotcode skill from agent-plugins`, and for the commit of the plan (`docs(openspec)`). Verify: `python scripts/sync_manifests.py --check` and `hatch run build:sync-chat-plugin --check` pass, the commits are signed, and `chat-plugins/.upstream.json` names the new commit.

## Workflow follow-up

- Task 3.8 of `docs-ai-agents-guide` records the sessions with this skill, from the local plugin folder.
- `/opsx:archive skill-sessions`, then `openspec validate --specs --strict`.
