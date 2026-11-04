# Tasks

Commits only on the maintainer's request; the maintainer pushes.

## 1. Check the advice to name the skill

- [x] 1.1 Run a few short runs (3 per case) on Haiku 4.5 with the list over budget and only the named skill's name left in it: `robotcode` under a plugin folder with another name, so that it has no uses yet, and one of two invented skills of about 350 characters in the project's `.claude/skills`. Use the demo config and read tools only. Verify: the debug log shows `Skill listing over budget`, the listing in the session log shows only the name of the named skill, and the transcript shows whether that skill was loaded. The result goes into `playground/agent-skill-befunde.md`. If naming doesn't help, change the sentence in the text of `design.md` and show the maintainer before going on.
  - Done 2026-11-04: in all 6 runs the list was over budget and held only the name of the named skill. `robotcode` named: loaded 2/3, once Haiku read the results itself. The other skill named: loaded 3/3, ours 0/3, where the same task without naming gave ours 3/3 and the other 0/3. Naming helps, so the sentence stays.

## 2. The page

- [x] 2.1 Add the entry to `docs/src/content/docs/guides/ai-agents/troubleshooting.md`, right after the first entry, with the text from `design.md`. Verify: `git diff` shows this paragraph and no other text change on the page.
- [x] 2.2 Add the symptom to the page's `description`, after "answers without robotcode". Verify: `npm run docs:build` passes.
- [x] 2.3 Check the page in the docs dev server, without a window on the desktop. Verify: the entry shows as a paragraph like its neighbours, the code spans render, and the link leads to `skillListingBudgetFraction` in Claude Code's settings reference.

## 3. The plan

- [x] 3.1 Check that the result still matches the plan. Verify: `openspec validate troubleshooting-skill-list-limit --strict` passes, and each scenario of the requirement "Troubleshooting AI agents" can be followed on the page.

## Workflow follow-up

- Commit the page as `docs(website)` and the OpenSpec files separately as `docs(openspec)`, when the maintainer asks.
- Archive the change after the maintainer's review.
