# Proposal

## Why

Since `docs-guides-structure`, every guide on robotcode.io belongs to a group, except the Guides overview, AI Agents and Finding Robot Files. Finding Robot Files stands alone between the groups Project Configuration and Robot Framework Tips. It describes `.robotignore` and `.gitignore`: files in the project that every `robotcode` command and the language server read from the project root. That is project configuration, the subject of the group next to it.

## What Changes

- Finding Robot Files moves into the group Project Configuration, after "Files and Project Root". Its title, label and content stay. One exception: the Quick start calls the project root "the same directory you point Robot Framework at", which is not how RobotCode finds the root. It will name the project root as "Files and Project Root" describes it, and link there.
- The overview of Project Configuration says that the group also covers which Robot Framework files RobotCode finds in the project.
- The group Robot Framework Tips is renamed Tips & Tricks: its sidebar label and the title of its overview page. Its pages and its path `/guides/tips/` stay.
- The Guides sidebar then lists Overview, VS Code, PyCharm, Command Line, AI Agents, Project Configuration and Tips & Tricks.
- Links to the guide follow its new path. The old path is not redirected, as with the pages that `docs-guides-structure` moved.

Not part of this change:
- changing the content of Finding Robot Files beyond the project-root sentence and its links;
- moving AI Agents into a group;
- new pages for the group Tips & Tricks.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `documentation-site`: in the requirement "Guides grouped by tool and topic", the order of the sidebar, the place of Finding Robot Files and the name of the group Tips & Tricks change.

## Impact

- `docs/src/content/docs/guides/ignoring-files.md` moves to `guides/robot-toml/ignoring-files.md` (`git mv`) and gets a new `sidebar.order`.
- `docs/src/content/docs/guides/robot-toml/index.mdx` (paragraph on the new page), `guides/tips/index.mdx` (title), `docs/src/routeData.ts` (label of the group `tips`).
- Links in `guides/cli/analyzing-code.md`, `guides/cli/discovering-tests.md`, `guides/vscode/test-explorer.mdx` and `news/v2-6-2.md`.
- The notes about the Guides groups in the tasks of the open changes `library-index`, `library-keyword-set-declaration` and `markdown-suites`.
- No code. `npm run docs:build` checks the links.
