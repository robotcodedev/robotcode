# Tasks

## 1. Groups and moves

- [ ] 1.1 Move the nine pages with `git mv` as in the table of design.md ("Paths and file moves"), and verify with `git status` that git records them as renames.
- [ ] 1.2 Set the orders and labels of design.md ("Orders", "Sidebar labels"): Discovering Tests 15, AI Agents 90, Highlighting 6.5 with label "Highlighting", Debugging with label "Debugging". Verify in the built sidebar (`docs/dist/guides/index.html`) that the entries come in the order of the spec scenario "Order in the sidebar".
- [ ] 1.3 Add `cli: "Command Line"` and `tips: "Robot Framework Tips"` to `GROUP_LABELS` in `docs/src/routeData.ts`, and set `collapsed: true` on the Guides `autogenerate` in `docs/astro.config.mjs`. Verify in the dev server that `/guides/` shows every group collapsed and that `/guides/cli/repl/` expands only the Command Line group.

## 2. New overview pages

- [ ] 2.1 Write `docs/src/content/docs/guides/cli/index.mdx` ("Working on the Command Line", label "Overview", order 10) with the content of design.md: the task table links `/guides/robot-toml/command-line/` for running tests and `/guides/cli/analyzing-results/` for failed tests, and `<AreaOverview area="guides/cli" />` is at the end. Before writing, check each task-to-command pair against `robotcode --help`. Verify that `/guides/cli/` shows the six guide cards.
- [ ] 2.2 Write `docs/src/content/docs/guides/tips/index.mdx` ("Robot Framework Tips", label "Overview", order 200) with one paragraph and `<AreaOverview area="guides/tips" />`. Verify that `/guides/tips/` shows the cards of the two pages.
- [ ] 2.3 Rewrite the description and the intro of `docs/src/content/docs/guides/index.mdx` to name the groups in their order. Verify that `/guides/` shows one card per group and per single page, in sidebar order (`documentation-site`, "Area overview pages").

## 3. Links

- [ ] 3.1 Replace the nine old paths with the new ones, anchors kept, in `docs/src/content/docs/**/*.{md,mdx}` (news posts and the handwritten parts of `reference/cli.md` included), `docs/src/components/**/*.astro` and `CONTRIBUTING.md`. Change `guides/repl.md` to `guides/cli/repl.md` in the file example of `CONTRIBUTING.md` by hand, since it is not a link path. Verify with `grep` that none of the old paths is left outside `openspec/changes/archive/`.
- [ ] 3.2 Run `npm run docs:build` and verify that it passes with all internal links valid.
- [ ] 3.3 Check the `href`s under `/guides/` in `docs/dist/index.html` and `docs/dist/404.html` against the files in `docs/dist` with a short script in the scratchpad, and verify that every target exists. The links validator does not check component links.

## 4. Getting Started on the command line

- [ ] 4.1 In a scratch project with a virtual environment, check the commands design.md plans for the page: which commands each extra brings (`pyproject.toml` extras and `robotcode --help` after installing each one), `pip install` and `uv add` / `uv pip install` of `robotcode[runner]`, `robotcode --version`, `robotcode discover all`, `robotcode robot <path>` and `robotcode results summary`. Note the versions and outputs here.
- [ ] 4.2 Write `docs/src/content/docs/getting-started/command-line.md` ("Get Started on the Command Line", label "Command Line", order 25) with the content of design.md and the outputs from 4.1, ending with links to `/getting-started/configuration/`, `/guides/cli/` and `/reference/cli/`. Verify that the Getting Started sidebar lists it between PyCharm and Neovim.
- [ ] 4.3 Name the command line in the description and the sentence above the cards of `docs/src/content/docs/getting-started/index.mdx`. Verify that `/getting-started/` shows the page's card.
- [ ] 4.4 In `README.md`, link `https://robotcode.io/getting-started/command-line/` from "Command Line and Other Editors", and name the editors and the command line in the "Guides" line under "Documentation". Verify that the path matches the built page (`docs/dist/getting-started/command-line/index.html`).

## 5. Verification

- [ ] 5.1 Check the site in the running docs dev server (`npm run docs:dev`, localhost:4321) against the scenarios of the delta specs: the order and collapsed state of the Guides groups, the overviews `/guides/cli/` and `/guides/tips/`, `/guides/vscode/highlighting/` in the VS Code group after Configuration, the Getting Started entry, and the not-found page for `/guides/repl/`. Also verify that `/llms.txt` lists `/guides/cli/repl/`, and that the home page's REPL feature card leads to `/guides/cli/repl/`.
- [ ] 5.2 Run `openspec validate docs-guides-structure --strict` and verify that it passes.

## Workflow follow-up

- Commit the docs changes and the OpenSpec artifacts separately (`docs(website)` and `docs(openspec)`).
- Archive the change after 5.1.
