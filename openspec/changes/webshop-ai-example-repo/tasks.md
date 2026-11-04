# Tasks

Commits only on the maintainer's request; the maintainer pushes robotcode. Nothing goes public before task 2.1.

## 1. The repository's files

- [x] 1.1 Build the files in the session's scratchpad as `design.md` says, including `README.md`, `LICENSE` and a new `uv.lock`. Verify: compared with what `record.sh` `restore` builds, only the differences in the table of `design.md` show, plus `data/restock.csv` and `LICENSE`; `AGENTS.md` is the same as on `briefing.md`; no file holds a local path.
- [x] 1.2 Follow the README from a clean copy, with a user configuration of its own and without agent variables. Verify: the scenario "Running it from a clean clone" holds, and the shop's page answers on port 8080. `rfbrowser init` isn't run here, because it only downloads the browsers.
  - Done 2026-11-04: with robotcode 2.9.0.dev115, `robotcode robot`, `-p dev` and `-p ci` each gave 13 tests, 12 passed, with only `Login Works` failing; `analyze code` reported `Submit Ordr`; `robotcode session` is there; the page answered on port 8080; `uv sync` left `uv.lock` unchanged.

## 2. Publishing

- [x] 2.1 Show the maintainer the file list and the README, and only after they confirm, create `robotcodedev/webshop-ai-example` as a public repository and push one signed commit. Verify: `gh repo view` shows it public, with Actions on, and `gh run list` shows no run after the push.
  - Done 2026-11-04, after the maintainer confirmed: public, branch `main`, Actions on, one signed commit, verified on GitHub, no run after the pushes. GitHub didn't list the workflow after the first push, which came 5 seconds after creating the repository, not even 12 minutes later. With the maintainer's OK, the commit was replaced with the same content (same tree, 42b890d55 to a6ed853cb) and pushed with `--force-with-lease`, and the workflow then showed as active. After the maintainer questioned `pip` in the workflow and agreed to the change, a second signed commit c88917b32 installs the project with `uv`, also without a run on GitHub.
- [x] 2.2 Clone it from GitHub into a new folder and follow the README again. Verify: the scenario "Running it from a clean clone" holds on the clone.
  - Done 2026-11-04: a clone from GitHub gave the same results as the clean copy in 1.2, and GitHub detects the licence as Apache-2.0.

## 3. The guide

- [x] 3.1 Add the text from `design.md` to `working-with-the-agent/index.mdx`, `ai-agents/index.mdx` and `briefing.md`, and the `TODO:` in `working-with-the-agent/index.mdx` as an MDX comment that doesn't render. Verify: `git diff` shows only these sentences and the comment; `npm run docs:build` passes.
- [x] 3.2 Check the pages in the docs dev server, without a window on the desktop. Run `npx astro dev status` in `docs/` first, test against what runs there, and don't stop a server that was already running. Verify: both links lead to the repository, the anchor `#the-example-project` works, and the `TODO:` doesn't show on the page.
  - Done 2026-11-04: tested against the dev server already running on port 4322, which keeps running. Checked over HTTP, not in a browser.

## 4. The plan

- [x] 4.1 Check that the result still matches the plan. Verify: `openspec validate webshop-ai-example-repo --strict` passes, and each scenario of "The example project is public" can be followed.
  - Done 2026-11-04: all five scenarios hold. The workflow was not started by hand, because it would fail on purpose; that it can be started rests on GitHub showing it as active with `on: workflow_dispatch`.

## 5. Resources by name

- [x] 5.1 In the repository, put `resources` on the `python-path`, import the resources by name, and push a new signed commit, as the maintainer agreed. Verify: a clean clone gives the results of the scenario "Running it from a clean clone", and no run starts.
  - Done 2026-11-04: commit 495daaf13, the same results as before, and `robotcode doc keyword orders.resource "Create Order"` works.
- [x] 5.2 Name the difference on `working-with-the-agent/index.mdx`, and in `references/authoring.md` on `next`, say that rules defined elsewhere come first and correct the line on imports. Verify: `npm run docs:build` passes, and the page shows the sentence in the dev server.
- [x] 5.3 After the skill's commit on `next`, sync the vendored copy with `hatch run build:sync-chat-plugin`. Verify: `chat-plugins/.upstream.json` names that commit, and `diff` of the two `authoring.md` files shows nothing.
  - Done 2026-11-04: `chat-plugins/.upstream.json` names c8369ebf4, and the two `authoring.md` files are the same.

## Workflow follow-up

- Commit the pages as `docs(website)` and the OpenSpec files separately as `docs(openspec)`, when the maintainer asks.
- Archive the change after the maintainer's review.
- With the next release: raise RobotCode in the repository to the released version and refresh `uv.lock`.
- Then plan the text pass over the guide as a change of its own, with the sessions recorded anew; `playground/robotcode-demo` needs the changes to imports and workflow first.
