# Proposal: migrate-docs-to-starlight

## Why

The documentation site https://robotcode.io is built with VitePress 1.6.4, the last stable release (2025-08-05). The 1.x line gets no further releases: VitePress 2.0 has been in alpha since 2025-01-22 (alpha.20 on 2026-09-04), with no beta and no v1-to-v2 migration guide. VitePress 1.6.4 pins Vite 5, so `npm audit` reports four findings in the docs toolchain (esbuild ≤0.24.2, Vite ≤6.4.2 including one high, launch-editor) that have no fix on this line. They affect only the local dev server, not the published static site, but the only way out is an unsupported npm override to Vite 6, which is itself patched only until Vite 9.

Astro with Starlight is actively released (39 stable Starlight releases in the last 12 months, 0.42.4 on 2026-09-24, on Astro 7 and Vite 8), has a comparable user base (about 805k weekly npm downloads against VitePress' 850k), and adds what the current site lacks: build-time checks of internal links and anchors, validated frontmatter, per-page SEO metadata and optimized images. `docs-starlight-preview` builds the new site next to the current one, generated from `docs/`, so that the maintainer and the community can review it locally. This change makes that site the published one once the maintainer considers it ready; it is not planned for a specific release. Compatibility with the old site's URLs is explicitly not required.

## What Changes

- **Switch.** The preview becomes the site in `docs/`: every page and image is moved to its new place with `git mv`, then overwritten by a last run of the conversion; the result is committed and edited directly from then on, and the hand-written pages move there too. The conversion script, the VitePress project (`.vitepress/`, the old Markdown tree, `news/posts.data.ts`, the Vue theme and the VitePress dependencies) and `docs-next/` are removed. `docs/` stays the npm workspace, now with the Astro dependencies; `npm run docs:dev|docs:build|docs:preview` keep their names; the build output moves to `docs/dist`.
- **BREAKING — new URLs on robotcode.io.** The published site gets the structure of the preview (`/getting-started/`, `/guides/…`, `/reference/…`, `/about/`, `/contributing/`, `/news/vX-Y-Z/`). No redirects; old URLs get the not-found page. Most heading anchors change.
- **Generated references.** `scripts/create_cmdline_doc.py` writes to `docs/src/content/docs/reference/cli.md`. A new `scripts/create_config_doc.py` (hatch script `create-config-docs`) writes `reference/config.md` with Starlight frontmatter and the heading IDs the JSON schema links to. It replaces `robotcode config info desc > docs/03_reference/config.md`.
- **JSON schema.** The documentation links in `docs/public/schemas/robot.toml.json` point to `https://robotcode.io/reference/config/`. The anchors of setting headings stay as they are; the 104 of 330 links whose anchors match no heading today (settings inside profiles, nested keys) are pointed at the heading that documents them. `etc/robot.toml.json` stays unchanged.
- **Search.** Algolia DocSearch through the official Starlight plugin, with the existing index; the crawler is switched to the new URLs and recrawled after the deployment.
- **Links, process and tooling.** `README.md`, `intellij-client/README.md`, `CONTRIBUTING.md`, `AGENTS.md`, `AI_POLICY.md`, the README of the agent plugin (in robotframework-agent-plugins, re-synced into `chat-plugins/`) and the `create-release-notes` skill follow the new paths, syntax and tag vocabulary. The documentation paths in the ten in-flight changes that name `docs/0x_…` are rewritten page by page. `deploy-docs.yml` builds and uploads `docs/dist`; the preview workflow and the `docs-next` ignore entries and root scripts are removed.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `documentation-site` (introduced by `docs-starlight-preview`): the site is published at https://robotcode.io from `docs/` and replaces the VitePress site; the generated CLI and configuration references are pages of the site that the generators write directly.
- `robot-toml-option-coverage`: the scenario that regenerates the configuration reference names the new path of `config.md`, and a new requirement states that the documentation links in the JSON schema resolve to existing anchors of the configuration reference.

## Impact

- Depends on `docs-starlight-preview`, which must be applied and archived first.
- `docs/`: replaced by the Starlight project of the preview (`astro.config.mjs`, `src/content.config.ts`, `src/content/docs/`, `src/assets/`, `src/components/`, `src/styles/`, `public/` with `CNAME`, favicons, Open Graph image and `schemas/robot.toml.json`); `docs/package.json` gets the Astro dependencies plus `@astrojs/starlight-docsearch`; root `package-lock.json` changes; `docs-next/` removed.
- `scripts/create_cmdline_doc.py`, `scripts/create_robot_toml_json_schema.py` (`base_url`, link paths of profile settings and nested keys), new `scripts/create_config_doc.py`, `hatch.toml`, `.gitignore` (`docs/.astro/`).
- `.github/workflows/deploy-docs.yml` (artifact `docs/dist`, telemetry off; it uses Node 26); `.github/workflows/docs-next.yml` removed; `build-test-package-publish.yml`, `.vscodeignore`, `eslint.config.mjs` and the root `package.json` lose their `docs-next` entries. The three jobs of `build-test-package-publish.yml` that run `npm install` then install the docs workspace too; they run on Node 26, which Astro supports.
- `README.md`, `intellij-client/README.md`, `CONTRIBUTING.md`, `AGENTS.md`, `AI_POLICY.md`, `.claude/skills/create-release-notes/SKILL.md`, `plugins/robotcode/README.md` in robotframework-agent-plugins and its vendored copy `chat-plugins/robotcode/README.md`, the Purpose line of `openspec/specs/cli-reference-generation/spec.md`.
- Ten in-flight changes name `docs/0x_…` paths (`analyze-config-in-robot`, `doc-cli`, `library-index`, `library-keyword-set-declaration`, `library-loading-robustness`, `markdown-suites`, `repl-exit-status`, `repl-report-input-errors`, `repl-vars-user-at-debug-stop`, `vscode-doc-browser`); those not applied by then get their paths rewritten.
- Unchanged: `vscode-client/extension/index.ts` opens `https://robotcode.io/news/`, which stays valid. The agent skill's `SKILL.md` references only `https://robotcode.io/llms.txt` and `https://robotcode.io/llms-full.txt`, which stay available (`llms.txt` as a page index, `docs-starlight-preview`).
- External: links to old pages from released READMEs (PyPI, VS Code Marketplace, JetBrains Marketplace), from older schema versions in editors (including the frozen `etc/robot.toml.json`) and from third-party sites end on the not-found page. The Algolia crawler configuration is changed in the Algolia dashboard.
