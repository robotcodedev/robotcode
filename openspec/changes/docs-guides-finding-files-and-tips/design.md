# Design

## Context

- **Groups:** The Guides groups are subdirectories of `docs/src/content/docs/guides/`. `autogenerate` builds them, and `GROUP_LABELS` in `docs/src/routeData.ts` labels them; `tips` → "Robot Framework Tips" and `robot-toml` → "Project Configuration".
- **Order:** The sidebar and `<AreaOverview>` order pages by `sidebar.order`, and a group sorts by the lowest order of its pages.
- **Project Configuration today:** Overview 100, Files and Project Root 100.1, Settings 100.2, Profiles 100.3, How Settings Combine 100.4, On the Command Line 100.5, Recipes 100.6, Troubleshooting 100.7.
- **Finding Robot Files today:** `guides/ignoring-files.md`, label "Finding Robot Files", title "How RobotCode Finds Robot Framework Files", order 120.
- **Links to the guide:**
  - `guides/cli/analyzing-code.md`, `guides/cli/discovering-tests.md`, `guides/vscode/test-explorer.mdx`, `news/v2-6-2.md`;
  - no link outside `docs/` (README, CONTRIBUTING, extension and plugin code).
  - The page itself links only to absolute paths and to its own anchors, so the move does not break its links.
- **Project root in the code:**
  - `robotcode robot` checks ignore files from the project root that `robotcode` found down to each suite folder. In `packages/runner/src/robotcode/runner/cli/robot.py`, the base path of `BuilderCache` is `_app.root_folder`.
  - `robotcode discover files` passes `root=root_folder` to `iter_files`. In `packages/core/src/robotcode/core/ignore_spec.py`, `iter_files` applies the ignore files of every folder from that root down to the given paths.
  - The language server and `robotcode analyze code` start at the workspace folder: `robot_workspace.py` and `robot_framework_language_provider.py` call `iter_files(folder.uri.to_path(), …)`.
  - So the root is not "the same directory you point Robot Framework at", as the Quick start of Finding Robot Files says. `robotcode robot tests` in a project whose `robot.toml` is in the parent folder of `tests` reads the `.robotignore` of that parent folder.

## Goals / Non-Goals

**Goals:**
- Finding Robot Files is a page of Project Configuration and is listed by the group's overview.
- The page and Files and Project Root describe the project root alike.

**Non-Goals:**
- Covering in the page that the language server starts at the workspace folder and not at a root above it. The page did not say this before, and in the usual setup, with `robot.toml` in the workspace folder, the two are the same folder.
- Changing the Guides overview (`guides/index.mdx`), the README or `CONTRIBUTING.md`. Their texts name the subjects and the folders (`robot-toml/`, `tips/`), not the group labels, and stay correct.

## Decisions

### D1: The page keeps its file name and goes into `robot-toml/`

`git mv docs/src/content/docs/guides/ignoring-files.md docs/src/content/docs/guides/robot-toml/ignoring-files.md`, so its path becomes `/guides/robot-toml/ignoring-files/`. The maintainer does not mind the URL.

Alternatives:
- Renaming the folder `robot-toml`, so that the path names the group. This moves the eight pages of the group and their links on 14 pages.
- Renaming the file after the label, for example `finding-files.md`.

Both change more than the move needs.

### D2: Order 100.15, right after Files and Project Root

The page builds on the project root, which Files and Project Root explains. 100.15 sorts between 100.1 and 100.2 in the sidebar and in `<AreaOverview>`.

### D3: The overview of Project Configuration keeps its title and gets one section

- **Title:** "Configuring Projects with robot.toml" stays, since every section of the overview is about `robot.toml`.
- **New section:** Before "Pages of this guide" comes a short section. It says that which `.robot` and `.resource` files RobotCode finds in the project, what it skips by default and how `.gitignore` and `.robotignore` keep folders out is on [Finding Robot Files](/guides/robot-toml/ignoring-files/).
- **Example project:** "The pages of this guide build on a project that tests a web shop" becomes "The pages on `robot.toml` build on …", because Finding Robot Files does not use that example.

### D4: The Quick start names the project root as Files and Project Root does

Step 1 of the Quick start reads: "Create a file named `.robotignore` in your **project root**, the folder that `robotcode` finds as described in [The project root](/guides/robot-toml/files/#the-project-root), usually the folder of your `robot.toml`. This is where discovery and analysis begin, so a `.robotignore` here governs the whole project."

The rest of the page already says "project root" without a definition and stays.

### D5: Tips & Tricks: label and overview title only

`GROUP_LABELS.tips` and the `title` of `guides/tips/index.mdx` become "Tips & Tricks". The overview's description and text stay, and so does the path `/guides/tips/`.

### D6: The scenario "Robot Framework Tips group" keeps its name

OpenSpec cannot rename a scenario of a MODIFIED requirement: validation fails, and archive refuses to drop the old name. So the scenario keeps its name and names the new title in its THEN line.

### D7: The notes in open changes follow

`library-index` (task 8.1), `library-keyword-set-declaration` (task 5.1) and `markdown-suites` (task 5.1) each have a note "Apart from the Guides overview, AI Agents and Finding Robot Files, every guide is a page of a group".
- All three notes then say "Apart from the Guides overview and AI Agents".
- The note in `markdown-suites` also names the page's new file path.

## Risks / Trade-offs

- [Links from outside to `/guides/ignoring-files/` end on the not-found page] → Accepted, as for the pages `docs-guides-structure` moved. The not-found page says that pages can move, and the site search finds the page by `.robotignore`, which its description keeps.
- [The scenario name "Robot Framework Tips group" no longer matches the group's label] → Accepted (D6). Its steps name `/guides/tips/` and the title Tips & Tricks.
