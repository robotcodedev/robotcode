# Tasks

Commits only on the maintainer's request; the maintainer pushes robotcode. Nothing goes public before task 2.1.

## 1. The repository's files

- [ ] 1.1 Build the files in the session's scratchpad as `design.md` says, including `README.md`, `LICENSE` and a new `uv.lock`. Verify: compared with what `record.sh` `restore` builds, only the differences in the table of `design.md` show, plus `data/restock.csv` and `LICENSE`; `AGENTS.md` is the same as on `briefing.md`; no file holds a local path.
- [ ] 1.2 Follow the README from a clean copy, with a user configuration of its own and without agent variables. Verify: the scenario "Running it from a clean clone" holds, and the shop's page answers on port 8080. `rfbrowser init` isn't run here, because it only downloads the browsers.

## 2. Publishing

- [ ] 2.1 Show the maintainer the file list and the README, and only after they confirm, create `robotcodedev/webshop-ai-example` as a public repository and push one signed commit. Verify: `gh repo view` shows it public, with Actions on, and `gh run list` shows no run after the push.
- [ ] 2.2 Clone it from GitHub into a new folder and follow the README again. Verify: the scenario "Running it from a clean clone" holds on the clone.

## 3. The guide

- [ ] 3.1 Add the text from `design.md` to `working-with-the-agent/index.mdx`, `ai-agents/index.mdx` and `briefing.md`, and the `TODO:` in `working-with-the-agent/index.mdx` as an MDX comment that doesn't render. Verify: `git diff` shows only these sentences and the comment; `npm run docs:build` passes.
- [ ] 3.2 Check the pages in the docs dev server, without a window on the desktop. Run `npx astro dev status` in `docs/` first, test against what runs there, and don't stop a server that was already running. Verify: both links lead to the repository, the anchor `#the-example-project` works, and the `TODO:` doesn't show on the page.

## 4. The plan

- [ ] 4.1 Check that the result still matches the plan. Verify: `openspec validate webshop-ai-example-repo --strict` passes, and each scenario of "The example project is public" can be followed.

## Workflow follow-up

- Commit the pages as `docs(website)` and the OpenSpec files separately as `docs(openspec)`, when the maintainer asks.
- Archive the change after the maintainer's review.
- With the next release: raise RobotCode in the repository to the released version and refresh `uv.lock`.
- Then plan the text pass over the guide as a change of its own.
