# Tasks: migrate-docs-to-starlight

## 1. Prerequisites

- [ ] 1.1 Confirm that `docs-starlight-preview` is applied and archived (`openspec/specs/documentation-site/spec.md` exists) and that the maintainer has accepted the preview; verify `npm run docs-next:build` succeeds without link errors on the current `main`

## 2. Switch `docs/`

- [ ] 2.1 Add a switch mode to the conversion and run it from the unmoved tree into a temporary directory (D1 step 1); verify that the output contains every page of the page map, the hand-written pages with the Getting Started requirements filled in, and no `editUrl` or `lastUpdated`
- [ ] 2.2 Move every old page, every referenced image and every file the conversion copies for the hand-written pages (logos, the home page's recordings and editor screenshots) to its new place with `git mv`, overwrite each page with its converted version and add the hand-written pages (D1 step 2); verify with `git diff --cached -M --name-status -- docs` that pages and images appear as renames (`R`), that nothing is left under `docs/0[1-5]_*/` and that `docs/images/` holds nothing the site uses
- [ ] 2.3 Move the project files of `docs-next/` into `docs/`, set `editLink.baseUrl` to `https://github.com/robotcodedev/robotcode/edit/main/docs/`, merge the dependencies into `docs/package.json` (plus `@astrojs/starlight-docsearch`), move the page index for `/llms.txt` into `docs/scripts/llms-index.mjs` and the link check of `src/pages/` into `docs/scripts/check-page-links.mjs` (D1 step 3), add `docs/.astro/` to the root `.gitignore`, and delete what D1 step 3 lists (D1 step 3); verify that `npm install` at the repository root succeeds, `npm ls vitepress` finds nothing, `docs/public/` holds only `CNAME`, the favicons, the Open Graph image and `schemas/`, `npm run docs:build` succeeds without link errors, `/llms.txt` lists the same pages as the preview's, the edit link of the built `getting-started/neovim` page points to `…/edit/main/docs/src/content/docs/getting-started/neovim.mdx`, and `git status` shows no generated files after the build

- [ ] 2.4 Convert every animated GIF a page shows into an MP4 with the GIFs' browser timing, replace the GIFs in `docs/src/assets/screenshots/` and show the recordings as muted looping videos (D8); verify that `git grep -n '\.gif' -- docs/src` finds only `with-customization.gif` and `without-customization.gif`, that each MP4 lasts as long as its GIF plays in a browser (the sum of its frame delays with every delay of 0.01 s or less counted as 0.1 s), and that the About and Getting Started pages play them in `npm run docs:preview`

## 3. Generated references and schema

- [ ] 3.1 Change the output path of `scripts/create_cmdline_doc.py` to `docs/src/content/docs/reference/cli.md` (D2); verify that `hatch run create-cmd-line-docs` (with the newest supported Robot Framework in the default environment) changes nothing in the converted page
- [ ] 3.2 Add `scripts/create_config_doc.py` and the hatch script `create-config-docs` (D2); verify that running it twice produces identical files, that its output equals the converted `reference/config.md`, and that the site builds
- [ ] 3.3 Correct the link paths of `scripts/create_robot_toml_json_schema.py` for settings inside profiles, nested keys and `tool.robotcode-analyze`, set `base_url` to `https://robotcode.io/reference/config/` (also in `$comment`), and regenerate with `hatch run create-json-schema` (D3); verify with a one-off check that every `#anchor` of a documentation link in `docs/public/schemas/robot.toml.json` exists as an `id` in the built `docs/dist/reference/config/index.html` (before the correction, 104 of 330 do not), and that `etc/robot.toml.json` is unchanged

## 4. Search

- [ ] 4.1 Configure `@astrojs/starlight-docsearch` with the existing app id, search key and index name instead of Pagefind (D4); verify in `npm run docs:preview` that the search opens the DocSearch dialog and returns results from the index (they point to old paths until the recrawl of 8.2)

## 5. Skill, links and other changes

- [ ] 5.1 Update `.claude/skills/create-release-notes/SKILL.md` (D5); verify by writing a throwaway post as the skill describes, building the site with it (it appears first on `/news/` with its tags and its description as meta description) and deleting it again
- [ ] 5.2 Update the links in `README.md` and `intellij-client/README.md`, the path in `AI_POLICY.md`, and the installation link in `plugins/robotcode/README.md` of robotframework-agent-plugins, then re-sync with `hatch run build:sync-chat-plugin` (D6); verify that `git grep -nE 'robotcode\.io/0[1-5]_|docs/0[1-5]_' -- ':!CHANGELOG.md' ':!etc/robot.toml.json' ':!openspec/'` finds nothing and that `hatch run build:sync-chat-plugin --check` passes
- [ ] 5.3 Update `CONTRIBUTING.md` and `AGENTS.md`, removing their `docs-next` sections (D6); verify that each command named there runs
- [ ] 5.4 Change the path in the Purpose of `openspec/specs/cli-reference-generation/spec.md` to `docs/src/content/docs/reference/cli.md`; verify with `openspec validate --specs`
- [ ] 5.5 Rewrite the documentation paths and commands in the artifacts of the in-flight changes not yet applied, page by page as listed in D6; verify that `git grep -n 'docs/0[1-5]_' -- openspec/changes ':!openspec/changes/archive'` finds only this change and that `openspec validate` passes for each edited change

## 6. Workflows and cleanup

- [ ] 6.1 In `deploy-docs.yml` upload `docs/dist` and set `ASTRO_TELEMETRY_DISABLED=1`; remove `.github/workflows/docs-next.yml`, the `docs-next` entries of `build-test-package-publish.yml`, `.vscodeignore` and `eslint.config.mjs`, and the root `docs-next:*` scripts (D7); verify by running the build steps locally (`npm ci`, `npm run docs:build`), checking that `docs/dist/index.html`, `docs/dist/404.html` and `docs/dist/CNAME` exist and that `docs/dist` contains no hero PNG or GIF outside `_astro/`, and that `git grep -n docs-next` finds only OpenSpec artifacts

## 7. Verification

- [ ] 7.1 Check in `npm run docs:preview` the scenarios of `openspec/specs/documentation-site/spec.md` except Search (verified in 8.2 after the recrawl), last-change dates (verified in 8.1) and the home page, whose scenarios this change replaces, the pre-deployment scenarios of this change's `specs/documentation-site/spec.md` (edit link, generated reference pages, home page and its demos) and the scenarios of `specs/robot-toml-option-coverage/spec.md` (regenerated schema and reference document `rebot.console` and `rebot.quiet`, every schema anchor exists); record the results in the `/opsx:verify` report and verify `openspec validate migrate-docs-to-starlight --strict`

## 8. Go-live

- [ ] 8.1 After the maintainer has committed the switch and merged it to `main` with the release that ships `robotcode doc` and `robotcode discover --by-test-metadata`, verify that `git log --follow` of a moved page shows its history before the switch; run `deploy-docs.yml` manually with `deploy: true`; verify that `https://robotcode.io/getting-started/`, `https://robotcode.io/reference/config/`, `https://robotcode.io/news/rss.xml` and `https://robotcode.io/llms-full.txt` respond, that `https://robotcode.io/03_reference/config` returns the not-found page, that `https://robotcode.io/news/` shows the newest post first, and that the edit link and last-change date of `https://robotcode.io/getting-started/neovim/` point to `docs/src/content/docs/getting-started/neovim.mdx` and its last commit
- [ ] 8.2 Switch the Algolia DocSearch crawler configuration to the Starlight page structure and the new URLs and recrawl (D4); verify that a search for `console-colors` on the live site returns `/reference/config/#console-colors` and that no result points to an old path
