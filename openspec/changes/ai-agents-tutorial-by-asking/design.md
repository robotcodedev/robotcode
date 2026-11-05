# Design

## Context

See `proposal.md` for the motivation. The pattern for the pages is the probe of step 4, `playground/tutorial-probe/finding-out-why-a-test-failed.md`, with a preview on the temporary page `working-with-the-agent/zz-probe.md`. Its measurements are in `playground/tutorial-probe/messwerte.md`. The findings on the current pages are in `playground/ai-agents-guide-befunde.md`.

What the current state means for this design:

- Nothing outside the guide links to an anchor in the seven steps, so their sections can change freely. `guides/ai-agents/index.mdx` links to the steps themselves, whose URLs stay.
- Of the roughly 20,400 words on the seven pages, about 14,900 are recordings.
- The frames `.rc-session`, `.rc-session-prompt` and `.rc-session-answer` are used only by the tutorial and carry over. `details.rc-session-details` is no longer needed.
- `robotcodedev/webshop-ai-example` has no flaky test yet. The local copy with it is described by `playground/tutorial-probe/flaky-test.diff`.
- The harness for the probe, a copy of `evals/robotcode/run.py` from `robotframework-agent-plugins`, is in the session's scratchpad, which can lose folders.

## Goals / Non-Goals

**Goals:**

- A reader who works through a step knows what to ask, what to look for in the answer and what to do next, and can apply that to their own project.
- Everything a step says about an agent's behavior has been seen in runs.

**Non-Goals:**

- A complete description of RobotCode's commands. That stays in the CLI guides and the reference.
- Measuring the skill. The runs check the tutorial's prompts and text, not the agents against each other.
- Infrastructure that checks the prompts automatically, or runs them again later.

## Decisions

### D1: The steps keep their order, titles and URLs

The two reviews of the guide found the order of the steps good, and it follows how people work on a project. Only the pages' insides change. Step 4 loses its part on the debugger to step 5.

### D2: A step has the shape of the probe

An introduction says what the reader wants and which part of it is theirs. The sections are named after what the reader does, such as "Ask what happened" or "Decide what is right". They consist of exchanges and short text on what to look for and what to do next. A closing section, "In your own project", gives the general form.

The fixed sections "What you learn", "How to ask the agent", "What the agent does" and "What to watch out for" go. They are what made the pages retell runs: "What the agent does" can only describe a run, and the actual lessons ended up in the last bullets.

### D3: No recordings

The maintainer decided this on 2026-11-05, after the probe had worked without them. The alternatives were to keep them collapsed and recorded anew, or to add a line per exchange with the commands the agent ran.

As a result, `<details>` blocks and the `session` and `excerpt` markers leave the pages, and so do the overview's sections on recordings and on how the example differs from them. The reader sees commands where the agent names them, and otherwise tries the prompts. The word "session" then means only `robotcode session` in the tutorial, and a talk with the agent is a "conversation", which settles finding W1 for these pages.

### D4: Each step starts from a fresh example project

A later step can't build on an earlier one, because agents change different things: a fix lands in the library or in the test, and each agent writes a different new test. Starting fresh also solves finding D9, where step 4 fixes a test that step 6 expects to fail. A step that needs a finished run gets it from its first prompt.

### D5: What the overview says once

How to set up and reset, why answers differ, and when to name the skill stand on the overview, and each step has one sentence that links there. A reader can land on any step, but repeating this seven times is what the reviews criticized (R3).

### D6: How prompts are tried

For each step, candidate prompts run turn by turn in a fresh copy of the example, once each with Sonnet, Opus, Haiku (with "Use the robotcode skill." in the prompt) and GitHub Copilot CLI, with the skill from `next` and `robotcode` from the sources. This is the setup of the probe. The results go to `playground/tutorial-probe/`, and the harness moves there as well, so that it survives the scratchpad. A prompt stays if it does what the text says in all four. Otherwise the prompt or the text changes.

Candidate prompts come from `playground/robotcode-demo/agent-sessions/prompts.md` and from what the findings ask for:

| Step | Starting point for the prompts | Finding it answers |
|---|---|---|
| 1 | "What does this project test?", "Which tests cover the cart requirements SHOP-201 to SHOP-203?", "Which tests don't name a requirement?", "What arguments does our `Create Order` keyword take?", "Try it out: what happens with a product that is sold out?" | F6, F28 |
| 2 | "How do I open a page, type into a field and check a text with the Browser library?", "Write a test for `requirements/SHOP-110.md`.", "What else did you change?", the REPL prompts on ordering, "Write a task that orders every product in `data/restock.csv` and logs the order ids, then run it." | D5, F19, F20, F21 |
| 3 | "Which tests are in our smoke test?", "Run them against staging.", "What does the `ci` profile change?", "Did they reach the staging shop?", "Run the web tests in Firefox." | D2, F9 |
| 4 | the probe | D6, D7 |
| 5 | see D7 | D3, D10 |
| 6 | "Check the project for problems before I push.", "Check it with the profile our CI uses too.", an instruction on what to fix, and one to mark an intended finding | F17, S5 |
| 7 | "Add a profile for our CI server: the staging shop, a browser without a window, and the results in `results/ci`.", "Show me the profile, and what a run with it gets.", "Which of these settings replace those in `robot.toml`, and which add to them?" | D4, F5 |

Step 1's prompt on a large project runs in the project of `large_project.py`. It stands on the page without an answer, because the reader can't follow it in the example.

Codex and opencode don't run in this. The maintainer's rule is that they come only at the very end, after asking.

### D7: Step 5 starts from `Express Order`

Finding D3 is that step 5 promises a failure and then walks through a passing test, so there is no problem to solve. The flaky test gives it a real question without adding another fault: stop `Express Order` at the status check, see what the shop returns, and have the agent call the check again at the stop. That the second call gives another answer is what the results of a run can't show.

Whether that carries is tried first. If it doesn't, the maintainer decides before another fault goes into the public example.

### D8: The answers of a step come from one run

The probe mixes runs: its first answer has one failure, and the table later says that `Express Order` also failed in that first run. The final page uses one run through the step, and for step 4 one in which the first run shows only `Login Works`, since the second failure is what the later prompt discovers. The text says that the reader's first run may show both.

### D9: Links as in the probe

The links stand in a sentence right after the answer. A code block can't hold a link and the answer stays as written, so they can't go inside it. Targets are the sections of `guides/cli/` where they exist: `analyzing-results`, `discovering-tests`, `browsing-documentation`, `analyzing-code`, `repl`, `robot-debug`, `sessions`. Otherwise it is `/reference/cli/#…`, as for `robot`, or `guides/robot-toml/profiles`. The docs build fails on broken internal links, so it checks them.

### D10: Which findings this covers

The findings on the seven steps and on the tutorial's overview are settled by the new text, or fall away with the text they were about. This includes the facts F5, F6, F9, F17, F19 to F23 and F28, the repetitions within the tutorial, and all of section F of the list. The findings on the other pages stay in the list for a change of their own.

## Risks / Trade-offs

- **The reader no longer sees the commands and their output unless the agent names them** → Step 4 teaches asking for them, and every named command links to its documentation. This is the maintainer's choice over the alternatives in D3.
- **A random failure makes runs differ in every step, not only in step 4** → The text of the other steps doesn't depend on whether `Express Order` failed in that run, and answers that mention it are chosen or shortened accordingly.
- **Answers from one run read as if the agent always answers that way** → The overview says that they differ, and the text only claims what holds across the four agents.
- **Only Claude Code and GitHub Copilot CLI are tried** → Copilot in VS Code and Codex are not, and neither is a real reader. The text speaks of the agent in general only as far as these runs support it.
- **Step 2 needs the Browser library, `rfbrowser init` and the shop's page** → The example's README covers that. Whether the agent can start the page itself is part of the trial.
- **Three display problems of the probe would repeat** → Long code lines run under the copy button, the diff view strips indentation, and inline code collapses the spaces in `Wait Until Keyword Succeeds    5x …`. The check in the dev server covers the first two, and the third is avoided by shortening such passages.
- **The site can be deployed by hand before the next release** → It would then describe the example with the flaky test only if the repository was pushed, and `robotcode session` isn't in 2.8.0. The docs deploy on a `v*` tag, so this only matters for a manual deployment.

## Migration Plan

The pages replace the old ones in place, with no redirects because the URLs stay. The public repository is pushed last, after the maintainer's confirmation, so that the current site doesn't describe a project that has already changed for longer than necessary. The main spec's `## Purpose` still speaks of recorded sessions and has to be edited by hand when the change is archived, because a delta can't change it.

## Open Questions

None. If the debugger prompts of D7 don't carry, that comes back to the maintainer as said there.
