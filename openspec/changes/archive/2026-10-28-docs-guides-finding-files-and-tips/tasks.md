# Tasks

## 1. Finding Robot Files in Project Configuration

- [x] 1.1 Move `docs/src/content/docs/guides/ignoring-files.md` to `docs/src/content/docs/guides/robot-toml/ignoring-files.md` with `git mv` and set its `sidebar.order` to 100.15 (design D1, D2). Verify with `git status` that git records a rename, and in the dev server that the group Project Configuration lists Finding Robot Files right after Files and Project Root.
  - Done 2026-10-28: `git status` shows `R`; the dev server's sidebar on `/guides/robot-toml/ignoring-files/` lists Overview, Files and Project Root, Finding Robot Files (current), Settings, … in Project Configuration.
- [x] 1.2 Rewrite step 1 of the Quick start as design D4 says, with the link to `/guides/robot-toml/files/#the-project-root`. Verify that the page has no other description of the project root that differs from Files and Project Root (`grep -n -i root` over the page).
  - Done 2026-10-28: step 1 has the sentence of D4; the other mentions of the root (lines 29, 98, 105–106, 111, 126) only use the term. The anchor `the-project-root` exists on `/guides/robot-toml/files/`.
- [x] 1.3 Add the section on Finding Robot Files to `docs/src/content/docs/guides/robot-toml/index.mdx`, before "Pages of this guide", and change "The pages of this guide build on" to "The pages on `robot.toml` build on" (design D3). Verify that `/guides/robot-toml/` shows the section and a link card for Finding Robot Files after Files and Project Root.
  - Done 2026-10-28: section "The files RobotCode finds"; in the dev server the page has the section, the changed sentence, and the cards Files and Project Root, Finding Robot Files, Settings, … in this order.
- [x] 1.4 Replace `/guides/ignoring-files/` with `/guides/robot-toml/ignoring-files/`, anchors kept, in `guides/cli/analyzing-code.md`, `guides/cli/discovering-tests.md`, `guides/vscode/test-explorer.mdx` and `news/v2-6-2.md`. Verify with `grep -rn "guides/ignoring-files"` over `docs/src`, `README.md`, `CONTRIBUTING.md`, `vscode-client`, `intellij-client/src` and `packages` that no old path is left.
  - Done 2026-10-28: one link in each file, none with an anchor; the news post got only its link path. The `grep` finds no old path.

## 2. Tips & Tricks

- [x] 2.1 Set `tips: "Tips & Tricks"` in `GROUP_LABELS` of `docs/src/routeData.ts` and `title: Tips & Tricks` in `docs/src/content/docs/guides/tips/index.mdx` (design D5). Verify in the dev server that the sidebar names the group Tips & Tricks and that `/guides/tips/` has the title Tips & Tricks and the cards of its two pages.
  - Done 2026-10-28: the dev server's sidebar names the group Tips & Tricks; `/guides/tips/` has the `<title>` "Tips & Tricks | RobotCode", the heading Tips & Tricks and the two cards.

## 3. Notes in open changes

- [x] 3.1 In the notes of `openspec/changes/library-index/tasks.md` (task 8.1), `openspec/changes/library-keyword-set-declaration/tasks.md` (task 5.1) and `openspec/changes/markdown-suites/tasks.md` (task 5.1), change "Apart from the Guides overview, AI Agents and Finding Robot Files" to "Apart from the Guides overview and AI Agents". In `markdown-suites`, change the file path of Finding Robot Files to `docs/src/content/docs/guides/robot-toml/ignoring-files.md` (design D7). Verify that `openspec validate <change> --strict` passes for all three.
  - Done 2026-10-28: all three are valid with `--strict`; `library-index` still shows its older INFO about the documentation-cli MODIFIED target, which this change does not touch.

## 4. Checks

- [x] 4.1 Run `npm run docs:build` and verify that it passes with all internal links valid.
  - Done 2026-10-28: 80 pages, "All internal links are valid."; `docs/dist/guides/robot-toml/ignoring-files/` exists, `docs/dist/guides/ignoring-files/` does not.
- [x] 4.2 Verify in the built sidebar (`docs/dist/guides/index.html`) the scenario "Order in the sidebar": Overview, VS Code, PyCharm, Command Line, AI Agents, Project Configuration and Tips & Tricks, every group collapsed.
  - Done 2026-10-28 with scratchpad `guides/sidebar.py`: the Guides group of the built page lists exactly these entries in this order, every group a closed `<details>`.
- [x] 4.3 Run `openspec validate docs-guides-finding-files-and-tips --strict` and verify that it passes.
  - Done 2026-10-28: "Change 'docs-guides-finding-files-and-tips' is valid", exit code 0.

## Workflow follow-up

- After the archive, run `openspec validate --specs --strict` and verify that all main specs pass.
