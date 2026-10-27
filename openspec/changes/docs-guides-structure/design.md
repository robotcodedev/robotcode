# Design

## Context

See proposal.md for the motivation and specs/ for the required behavior.

**How the sidebar is built today:** `docs/astro.config.mjs` builds the Guides group with `autogenerate: { directory: "guides" }`. Starlight 0.42.7 makes a subgroup of each subdirectory. It sorts a directory by the lowest `sidebar.order` among its pages (`getOrder` in `dist/utils/navigation.js`) and pages by their own `sidebar.order`. That is why the VS Code pages have the orders 0.5–9 and the PyCharm pages 9.1–9.9. A subgroup is labelled with its directory name. `docs/src/routeData.ts` maps `vscode`, `pycharm` and `robot-toml` to their display names.

**What builds on the paths:**
- `AreaOverview` lists the pages directly in an area or group, with a group as the card of its `index` page, sorted by `sidebar.order`.
- `scripts/llms-index.mjs` lists everything under `guides/` in order.
- The top navigation marks Documentation for every path under `/guides/`.

All three keep working when pages move into subdirectories of `guides/`.

**Links:** `starlight-links-validator` 0.27.0 checks links in Markdown and MDX files only. The home page components link moved guides (`src/components/home/FeatureTour.astro`: `/guides/robot-debug/`, `/guides/repl/`, `/guides/repl/#debugging-at-the-prompt`), and the build does not check those links. The links in `reference/cli.md` that point to moved guides are in its handwritten parts, outside the block that `scripts/create_cmdline_doc.py` replaces between `<!-- START -->` and `<!-- END -->`. No code, plugin or README links a moved page. The README links only `/guides/`, `/getting-started/…` and `/reference/cli/`; the IntelliJ README links `/guides/pycharm/…` and `/guides/robot-toml/`; the VS Code `package.json` links `/guides/vscode/troubleshooting/`.

**The site is live** at robotcode.io since v2.8.0 (2026-10-26). The maintainer decided against redirects for the moved pages.

## Goals / Non-Goals

**Goals:**
- Every guide belongs to a group or has a fixed place in the order of the Guides area. A new command guide goes into the Command Line group without anyone choosing an order number between unrelated pages.
- Readers of the command line get the same way in as readers of the editors: a Getting Started page and a group with an overview.

**Non-Goals:**
- Rewriting the moved guides. Only their links, their `sidebar.order` and two sidebar labels change.
- A uniform renumbering of every `sidebar.order` in the Guides area. Only the pages that move or need a new place get new orders.

## Decisions

### Groups from directories, not an explicit sidebar list

The new groups are subdirectories of `guides/`, built by the existing `autogenerate`, with labels from `GROUP_LABELS` in `routeData.ts` (`cli` → "Command Line", `tips` → "Robot Framework Tips"). Pages keep declaring their own order and label (`documentation-site`, "Area sidebar"), and `AreaOverview` and `llms-index.mjs` need no change.

Alternative: keep the files where they are and list the Guides sidebar by hand in `astro.config.mjs`. The paths would no longer match the groups, a new page would need an entry in the config, and the overview cards of `AreaOverview` would not know the groups.

### Paths and file moves

Files move with `git mv`, so that their history follows them:

| From `guides/` | To `guides/` | New path |
|---|---|---|
| `discovering-tests.md` | `cli/discovering-tests.md` | `/guides/cli/discovering-tests/` |
| `analyzing-code.md` | `cli/analyzing-code.md` | `/guides/cli/analyzing-code/` |
| `analyzing-results.md` | `cli/analyzing-results.md` | `/guides/cli/analyzing-results/` |
| `repl.md` | `cli/repl.md` | `/guides/cli/repl/` |
| `robot-debug.md` | `cli/robot-debug.md` | `/guides/cli/robot-debug/` |
| `browsing-documentation.md` | `cli/browsing-documentation.md` | `/guides/cli/browsing-documentation/` |
| `vscode-highlighting.mdx` | `vscode/highlighting.mdx` | `/guides/vscode/highlighting/` |
| `avoid-global-resource-file.mdx` | `tips/avoid-global-resource-file.mdx` | `/guides/tips/avoid-global-resource-file/` |
| `variable-not-found.md` | `tips/variable-not-found.md` | `/guides/tips/variable-not-found/` |

None of these pages imports a file by a relative path (the two `.mdx` pages import only `@astrojs/starlight/components`), so the move breaks no import.

The directory is `cli`, as in `/reference/cli/`, and short in links; its label is "Command Line", like the Getting Started page. `tips` holds the Robot Framework practice pages.

AI Agents, Wrapper and `.robotignore` keep their paths (`/guides/ai-agents/`, `/guides/wrapper/`, `/guides/ignoring-files/`). The home page and its spec link `/guides/ai-agents/`, and the maintainer chose to keep Wrapper and `.robotignore` as pages of their own after the robot.toml group.

### Orders

A group sorts by its lowest page order, so each group's overview carries the lowest order of its group. Unchanged orders are in parentheses.

| Place | Page | `sidebar.order` |
|---|---|---|
| 1 | Guides overview | (0) |
| 2 | VS Code group | (0.5–9); Highlighting 6.5, after Configuration (6) |
| 3 | PyCharm group | (9.1–9.9) |
| 4 | Command Line group | overview 10, Discovering Tests 15 (was 10), Analyzing Code (20), Analyzing Results (30), REPL (40), Debugging (50), Browsing Documentation (60) |
| 5 | AI Agents | 90 (was 130) |
| 6 | robot.toml group | (100–100.7) |
| 7 | Wrapper, .robotignore | (110), (120) |
| 8 | Robot Framework Tips group | overview 200, Avoid a Global Resource File (210), Variable Not Found (220) |

Highlighting comes after Configuration because it changes how the editor looks; Troubleshooting stays last (`vscode-user-guide`, "VS Code group in the Guides area"). Getting Started: "Get Started on the Command Line" gets order 25, between PyCharm (20) and Neovim (30).

### Sidebar labels

Inside the group, "Command-line Debugging" becomes "Debugging", and "VS Code Highlighting" becomes "Highlighting". The page titles stay as they are, since they name the command or the editor on their own, in search results and in `llms.txt`.

### Collapsed groups

`autogenerate: { directory: "guides", collapsed: true }`. Starlight then renders each subgroup as a closed `<details>`, except one that contains the current page (`SidebarSublist.astro`: `open={sidebarGroupHasCurrent(entry) || !entry.collapsed}`). With five groups and over 40 pages, an expanded Guides tree would push Reference far down.

### The Command Line overview

`guides/cli/index.mdx`, title "Working on the Command Line", label "Overview". The VS Code and PyCharm groups use the same title form ("Working in VS Code", "Working in PyCharm"). Content:
- The `robotcode` commands run in the project's Python environment, next to Robot Framework and the libraries. Like the editors, they read the project's `robot.toml` files and the selected profiles (`-p`). Installing them: the Getting Started page. All options: `/reference/cli/`.
- A table "task → command → guide": run tests (`robotcode robot`, `/guides/robot-toml/command-line/`), see what a run would pick up (`discover`), check the code (`analyze code`), find out why tests failed (`results`), try keywords (`repl`), debug a run in the terminal (`robot-debug`), read the documentation of a library (`doc`), run through a wrapper (`/guides/wrapper/`), let an AI agent work through the CLI (`/guides/ai-agents/`).
- `<AreaOverview area="guides/cli" />`.

### The Robot Framework Tips overview

`guides/tips/index.mdx`, title "Robot Framework Tips", label "Overview". It has one paragraph: practices for structuring Robot Framework code so that RobotCode's analysis can follow it, and why some of its findings appear. Then `<AreaOverview area="guides/tips" />`.

### The Getting Started page for the command line

`getting-started/command-line.md`, title "Get Started on the Command Line", label "Command Line", order 25. Plain Markdown, one section per step, so each has an anchor. Content:
- **Who it is for:** the terminal, CI pipelines and scripts. Other editors connect to the language server; see the Neovim page.
- **Install:** into the project's Python environment, the same one that has Robot Framework. A table of the packages and the commands each brings, taken from `pyproject.toml` and checked against the installed commands. Commands for pip and for uv (`uv add`, `uv pip install`), as on the dev builds page. No pipx or `uvx`, because RobotCode has to run next to the project's Robot Framework and libraries (the same reason as on the dev builds page). The `[all]` extra is mentioned as the way to get everything.
- **Check:** `robotcode --version`.
- **First look:** `robotcode discover all` shows the suites and tests that Robot Framework would run.
- **First run:** `robotcode robot <path>`, then `robotcode results summary` for the outcome.
- **Next:** `/getting-started/configuration/` for a `robot.toml`, `/guides/cli/`, and `/reference/cli/`.

Every command on the page is run in a scratch project before it goes on the page.

### Overview texts and README

- `guides/index.mdx`: the description and the intro name the groups in their order (editors, command line, AI agents, project configuration, Robot Framework tips).
- `getting-started/index.mdx`: the description and the sentence above the cards name the command line next to the editors.
- `README.md`: "Command Line and Other Editors" links the new page, and the line "Guides" under "Documentation" names the editors and the command line.

### Rewriting the links

A list of the nine old paths and their new ones is applied to `docs/src/content/docs/**/*.{md,mdx}`, `docs/src/components/**/*.astro` and `CONTRIBUTING.md`. A link keeps its anchor. The archived OpenSpec changes keep their old paths, since they record what was true then. `npm run docs:build` then checks the content pages. A short script checks the `href`s under `/guides/` in the built home page and the 404 page against the files in `docs/dist`.

## Risks / Trade-offs

- [Links from outside the repository to the nine old paths break, for example from forum posts written since 2026-10-26] → The maintainer's decision; the not-found page says that pages move and offers the search and the area overviews.
- [A later guide gets an order that sorts it before its group's overview] → Each group's overview has the lowest order of its group, and the Command Line group leaves space between its orders.
- [Readers miss a page inside a collapsed group] → Each group's overview lists its pages as cards, and the Guides overview has a card for each group.
