# Tasks

## 1. The example and the harness

- [x] 1.1 Fetch `robotcodedev/webshop-ai-example` from GitHub into a local clone, apply `playground/tutorial-probe/flaky-test.diff` and change the README so that it no longer speaks of the guide's sessions but still doesn't name what is wrong. Verify with 20 runs of all tests that `Login Works` fails in all of them, `Express Order` in some and no other test in any, and that `robotcode analyze code` still reports `Submit Ordr`. Don't push yet.
- [x] 1.2 Move the probe's harness (the copy of `evals/robotcode/run.py`, the turn-by-turn script and the analysis) from the scratchpad to `playground/tutorial-probe/` and point it at the clone of 1.1. Verify with one short run by one agent that it starts from a fresh copy, without the agent variables of this session in its environment.

## 2. Step 4: Finding Out Why a Test Failed

- [x] 2.1 Run the probe's prompts once more with the example of 1.1 until there is one run through the step that fits D8, and record it in `playground/tutorial-probe/messwerte.md`. Verify that each answer that refers to an earlier result fits what the earlier answer shows.
- [x] 2.2 Replace `working-with-the-agent/finding-out-why-a-test-failed.md` with the probe, using the answers of 2.1 and a new `description`, with the setup sentence reduced to a link to the overview, and with a sentence saying that the first run may show only `Login Works` failing. The note on smaller models leaves the page. Verify in the dev server, light and dark, that all links lead to their sections, that the page has no recording, and that the diff keeps its indentation and no code line runs under the copy button.

## 3. Step 1: Getting to Know the Project

- [x] 3.1 Try the prompts of D6 in a fresh copy with the four agents, and the prompt on a large project in the project of `large_project.py`. Record the results. Verify that for each prompt kept, what the planned text says holds in all four.
- [x] 3.2 Write the page in the shape of D2, with links to the commands the shown answers name. Verify in the dev server, light and dark, and check that it no longer says that `discover` shows what a run sees for variables (F6).

## 4. Step 2: Writing a Test from a Requirement

- [x] 4.1 Try the prompts of D6 with the four agents, with the shop's page running as the README says, and find out whether an agent can start the page itself. Record the results. Verify that for each prompt kept, what the planned text says holds in all four, and that the REPL keeps running between the prompts.
- [x] 4.2 Write the page in the shape of D2, covering the learning of the library, the REPL, the test from the requirement, its check and run, what else changed, and a task. Verify in the dev server, light and dark, including its links.

## 5. Step 3: Running What You Need

- [x] 5.1 Try the prompts of D6 with the four agents. Record the results. Verify that for each prompt kept, what the planned text says holds in all four, and find the reason why a run with the `ci` profile doesn't reach the staging shop.
- [x] 5.2 Write the page in the shape of D2, with that reason in its own text (D2 of the findings). Verify in the dev server, light and dark, including its links.

## 6. Step 5: Debugging Step by Step

- [x] 6.1 Try the prompts of D7 on `Express Order` with the four agents. Record the results. Verify that the run stays paused between the prompts and that the debugger shows something the results of a run don't. If this doesn't carry, stop and bring the facts to the maintainer before anything else goes into the example.
- [x] 6.2 Write the page in the shape of D2, starting from that question, with a prompt that ends the debugger. Verify in the dev server, light and dark, including its links.

## 7. Step 6: Checking Before a Push

- [x] 7.1 Try the prompts of D6 with the four agents. Record the results. Verify that for each prompt kept, what the planned text says holds in all four, and that the finding marked as intended no longer shows in the next check.
- [x] 7.2 Write the page in the shape of D2. Verify in the dev server, light and dark, including its links.

## 8. Step 7: A Profile for the CI Server

- [x] 8.1 Try the prompts of D6 with the four agents. Record the results. Verify that for each prompt kept, what the planned text says holds in all four, and check the answers on what a profile replaces against `guides/robot-toml/profiles.md`.
- [x] 8.2 Write the page in the shape of D2, with the resulting profile on the page and the rule on replacing and adding in its own text (F5). Verify in the dev server, light and dark, including its links.

## 9. Around the steps

- [x] 9.1 Rewrite `working-with-the-agent/index.mdx`: how to follow along, starting over, why answers differ, when to name the skill, and that some things in the example are wrong on purpose; the sections on recordings and on how the example differs from them go, and the `TODO:` on the release stays. Update the page's `description`. Verify in the dev server that the links from the steps lead to the section on following along.
- [x] 9.2 Update the summaries of the steps in `guides/ai-agents/index.mdx` and the sentence in `guides/ai-agents/briefing.md` that speaks of the recordings. Verify that a search of the group for "recorded" and "the sessions" finds nothing that refers to recordings.
- [x] 9.3 In `docs/src/styles/custom.css`, remove the rule for `details.rc-session-details` and change the comment on the frames, which names the sessions and their generator. Verify in the dev server that the frames still show in both themes.
- [x] 9.4 Remove the temporary page `working-with-the-agent/zz-probe.md`. Verify with `git status` that it is gone.

- [x] 9.5 Show the `robotcode` commands the agent ran between each prompt and its answer, linked to their documentation, from the transcripts of the runs (D11), with a rule in `custom.css` and a sentence on the overview. Verify in the dev server, light and dark, and with `npm run docs:build` that the links lead to their targets.

## 10. The whole tutorial

- [x] 10.1 Read the seven pages one after another for repetition, tense, statistics and retelling, against the spec's requirements. Verify with a search that none of them has `<details`, a `session` or `excerpt` marker, or a count of runs.
- [x] 10.2 Run `npm run docs:build`. Verify that it passes, which also checks the internal links.
- [x] 10.3 Have the maintainer read the pages in the dev server, and apply what comes of it.
- [x] 10.4 Ask the maintainer to confirm, then push the clone of 1.1 to `robotcodedev/webshop-ai-example`. Verify from a clean clone, following the README, that the scenario "A clean clone" holds, and that the push started no workflow.
- [x] 10.5 Stop the dev server this session started, and check with `npx astro dev status` in `docs/` that none of mine is left.

## Workflow follow-up

- Commits only on the maintainer's request: the docs and the OpenSpec files separately, the latter as `docs(openspec)`.
- When archiving, edit the `## Purpose` of the main spec by hand, because it still speaks of recorded sessions.
- Codex and opencode only if the maintainer asks for them, at the very end.
