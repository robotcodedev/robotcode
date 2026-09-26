# Proposal: docs-starlight-preview

## Why

The documentation site is to move from VitePress 1.6.4, whose 1.x line gets no further releases, to Astro + Starlight, with a new structure (exploration and weighing: `migrate-docs-to-starlight`, proposal.md). Before the published site is replaced, the maintainer wants to see the result over a longer period and let the community try it locally. The current site must keep being edited and released as it is until then, and the new site must not be part of the next release.

## What Changes

- **A preview site next to the current one.** A new directory `docs-next/` holds an Astro 7 + Starlight 0.42 project with its own `package.json` and lockfile. It is not part of the root npm workspace and is not deployed. `docs/` and its VitePress build and deployment stay unchanged.
- **Content generated from `docs/`.** A committed conversion script runs before every `dev` and `build` of the preview. It converts the current pages of `docs/` into the new structure: page map, frontmatter, VitePress syntax to Starlight syntax, links and anchors, images. `docs/` stays the only place where content is edited. A page in `docs/` without an entry in the page map, or unconverted VitePress syntax, fails the preview build; a new release post is mapped automatically. Whoever adds another page to `docs/` during the preview period adds its page-map entry, and the three in-flight changes that plan new pages (`doc-cli`, `library-keyword-set-declaration`, `library-index`) get that step in their tasks.
- **New structure, sorted by reader intent.** Getting Started (`/getting-started/`: overview with the requirements, `vscode`, `neovim`, `configuration`), Guides (`/guides/`: the command handbooks and wrapper, `.robotignore` and AI agents from today's Reference, plus the former Tips & Tricks articles), Reference (`/reference/`: CLI, `robot.toml`, diagnostic modifiers), `/about/`, `/contributing/`, news as `/news/v2-7-0/`.
- **Hand-written parts of the preview.** Home page (random hero picture with previous/next, swipe and an enlarged view, feature cards pointing to the pages that cover them), the three area overviews with link cards from page metadata, a not-found page, a top navigation bar on every page, footer and brand colours.
- **News as a blog.** `starlight-blog` under `/news/` with excerpts, pagination, tag pages and an RSS feed; one kind tag plus topic tags per post; the April Fools post gets a joke notice at its top.
- **Checks.** The preview build fails on broken internal links or anchors. The two links to the non-existent `robot-debug#exception-breakpoints` anchor are fixed in `docs/`, which also fixes them on the current site. A CI workflow builds the preview on changes to `docs/` or `docs-next/`, without deploying anything.
- **Isolation from the rest of the repository.** The extension CI ignores `docs-next/**`, as it ignores `docs/**`; `.vscodeignore` and the ESLint configuration exclude `docs-next/`. Root scripts `docs-next:install|dev|build|preview` and a README in `docs-next/` explain the local preview.
- **Search in the preview** uses Starlight's built-in Pagefind, because the Algolia index describes the live site.
- **LLM exports.** `/llms.txt` lists every page with title, URL and description, as the agent skill expects; `/llms-full.txt` and `/llms-small.txt` hold the text.
- **Not in this change:** publishing the new site, the generators of `cli.md` and `config.md`, the JSON schema, Algolia, links in READMEs, the release-notes skill and the paths in other changes. All of these belong to the switch in `migrate-docs-to-starlight`, which depends on this change.

## Capabilities

### New Capabilities

- `documentation-site`: The Starlight documentation site: page organization and paths, navigation, page metadata, area overviews, news, images, link and anchor check, literal command-line text, code blocks, search, LLM text exports, edit link and last change, home page and not-found page.

### Modified Capabilities

(none)

## Impact

- New `docs-next/`: `package.json` and `package-lock.json` (`astro`, `@astrojs/starlight`, `@astrojs/markdown-satteri`, `sharp`, `starlight-blog`, `starlight-links-validator`, `starlight-llms-txt`, `lite-youtube-embed`, `js-yaml`, `github-slugger`), `astro.config.mjs`, `src/content.config.ts`, `scripts/convert.mjs` (page map and rules), `content/` (hand-written pages), `src/components/`, `src/styles/`, `README.md`, `.gitignore` (generated `src/content/docs/` and `src/assets/`, `dist/`, `.astro/`, `node_modules/`).
- New `.github/workflows/docs-next.yml` (build only). `.github/workflows/build-test-package-publish.yml` (`paths-ignore` gets `docs-next/**`), `.vscodeignore`, `eslint.config.mjs`, root `package.json` (scripts only), `CONTRIBUTING.md` (a short section on the preview), `AGENTS.md` (task routing and commands for `docs-next/`).
- The documentation tasks of `doc-cli` (7.1), `library-keyword-set-declaration` (5.1) and `library-index` (8.1) get a page-map entry and a preview build check.
- `docs/03_reference/repl.md` and `docs/03_reference/robot-debug.md`: the two broken anchor links.
- Unchanged: the published site, `docs/` content and structure, the VitePress build and `deploy-docs.yml`, the generators, the JSON schemas, the VS Code and IntelliJ clients, the release process.
