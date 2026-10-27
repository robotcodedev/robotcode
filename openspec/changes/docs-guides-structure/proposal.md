# Proposal

## Why

The Guides area of robotcode.io has groups for VS Code, PyCharm and `robot.toml`, but the six guides to the `robotcode` commands, the AI agents guide, the wrapper and `.robotignore` pages, two pages on Robot Framework practice and the VS Code highlighting tip stand between them as single pages. Their order comes only from `sidebar.order` numbers, and the sidebar does not show which pages belong to the command line. A reader who works on the command line, in CI or with an AI agent finds no place of their own, and Getting Started has a page for each editor but none for the command line.

## What Changes

- The Guides sidebar holds groups per tool and per topic, in this order: Overview, **VS Code**, **PyCharm**, **Command Line** (new), the page **AI Agents**, **robot.toml**, the pages **Wrapper** and **.robotignore**, and **Robot Framework Tips** (new). Groups are collapsed; the group of the open page is expanded.
- The six command guides move to `/guides/cli/` (discover, analyze code, results, REPL, command-line debugging, `doc`). A new overview page "Working on the Command Line" leads the group.
- The highlighting tip moves into the VS Code group as `/guides/vscode/highlighting/`. Until now it was a page of its own outside the group (`vscode-user-guide`, "Writing code in VS Code").
- "Avoiding a Global Resource File" and "Why is my variable shown as "not found"?" move to `/guides/tips/`, under a new overview page "Robot Framework Tips".
- AI Agents, Wrapper and `.robotignore` keep their paths and get fixed places in the order.
- A new page in Getting Started, "Get Started on the Command Line", between PyCharm and Neovim. It covers installing the packages a task needs into the project's Python environment, a first look at the project, a first run, and where to go next. The README's section "Command Line and Other Editors" links to it.
- Moved pages are not redirected: their old paths get the site's not-found page, which already says that pages can move. All links within the site, in the home page components, in `CONTRIBUTING.md` and in the README follow the new paths.

Not part of this change:
- changing the content of the moved guides beyond their links and sidebar labels;
- moving the pages of Getting Started or Reference;
- splitting the AI agents guide into several pages.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `documentation-site`: the Guides area is grouped by tool and topic, Getting Started gets a page for the command line, and the scenarios that name moved paths name the new ones.
- `vscode-user-guide`: the VS Code group contains the highlighting page, and the scenarios that link to moved guides name the new paths.
- `documentation-site-seasons`: the scenario "Reading a guide" names the new path of the `analyze code` guide.

## Impact

- `docs/astro.config.mjs` (collapsed groups), `docs/src/routeData.ts` (labels of the new groups).
- `docs/src/content/docs/guides/`: nine pages move (`git mv`), two new overview pages, new orders and labels; `guides/index.mdx` and `getting-started/index.mdx` describe the new layout; `getting-started/command-line.md` is new.
- Links in about 25 content pages, in the handwritten parts of `reference/cli.md`, in `src/components/home/FeatureTour.astro`, in `CONTRIBUTING.md` and in `README.md`.
- No code. `npm run docs:build` checks the links of the content pages; the links of the home page components need a check of their own.
