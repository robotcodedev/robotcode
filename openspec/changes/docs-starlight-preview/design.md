# Design: docs-starlight-preview

## Context

See proposal.md. The switch of the published site is `migrate-docs-to-starlight`, which builds on this change. Facts that shape the design, checked during exploration (2026-09-25/26) and in a demo that converted the complete current content to Starlight 0.42.4 on Astro 7.3.5 and was built, link-checked and reviewed in light, dark and mobile views:

- **Current site.** `docs/` is an npm workspace of the root package (`"workspaces": ["docs"]`, one root `package-lock.json`). VitePress 1.6.4 with `vitepress-sidebar`, `vitepress-plugin-tabs`, `vitepress-plugin-llmstxt`, `markdown-it-kbd`/`-abbr`/`-task-lists`, Algolia DocSearch, `cleanUrls`, `lastUpdated`, `editLink`, the Robot grammar `syntaxes/robotframework.tmLanguage.json` (`name: "Robot Framework"`, aliases `robot`, `robotframework`) and the Shiki themes `material-theme-lighter/darker`. The custom theme adds `RandomHeroImage.vue` (random picture; previous/next buttons and horizontal swipe with a 48 px minimum and a direction ratio of 1.35, click suppression after a swipe; a click opens a dialog closed by click or Escape, arrow keys switch pictures in it) and `RandomTagline.vue` through layout slots. `news/index.md` lists posts with a `createContentLoader` data loader and Vue in Markdown. 30 Markdown files, about 13,000 lines; `03_reference/cli.md` and `03_reference/config.md` are generated (`hatch run create-cmd-line-docs`, `robotcode config info desc`).
- **Content inventory.** 16 containers (14 with a custom title), 2 `details`, 6 `code-group` (2 with a single block) and 1 `:::tabs`, 7 `[[KEY]]`, 3 Shiki notation comments, 4 standalone code-block titles, 98 relative `.md` links (22 with anchors), 619 H2–H6 headings. `discovering-tests.md` (line 375) and `analyzing-results.md` (line 544) have a second top-level heading, `# JSON reference`. `cli.md` places commands at H3–H6. Placeholders such as `<PORT>` and `${{expr}}` occur in `cli.md`, `config.md` and `repl.md`. 14 same-page anchor links in `analyzing-results.md` and `discovering-tests.md` are broken on the current site (VitePress keeps `—` in heading IDs, the links omit it); two links point to `robot-debug.md#exception-breakpoints`, a heading that does not exist.
- **What the pages are.** A page-by-page analysis (Diátaxis types per section) found: eight of the eleven Reference pages are guides — `discovering-tests`, `analyzing-code`, `analyzing-results`, `repl` and `robot-debug` are command handbooks that call themselves "task-oriented guide" (55–70 % of their bodies are flag tables, exit codes and JSON schemas), `wrapper`, `ignoring-files` and `ai-agents` are how-tos; only `cli`, `config` and the core of `diagnostics-modifiers` are lookup material. Of the four Tips & Tricks pages, `01_avoiding_a_global_resource_file` is a 331-line best-practice essay, `02_why_variable_not_found` a 685-line troubleshooting article, `04_neovim_lsp_setup` a setup how-to by an external author (DudeNr33), and only `03_vscode_customizations` is a tip; its token scopes have drifted from the extension's `configurationDefaults`. `02_get_started/index.md` is a VS Code-only walkthrough. Several home feature cards link to pages that do not cover the feature.
- **Starlight 0.42 / Astro 7.** Content lives in `src/content/docs/`; a file's path is its URL. Every page needs a frontmatter `title`, rendered as the page's H1. Frontmatter also takes `description`, `sidebar.label`/`sidebar.order`, `editUrl` (per page, overrides `editLink.baseUrl`), `lastUpdated` (a date, overrides the git lookup), `tableOfContents` and `pagefind`. `autogenerate` sorts a sidebar group by file id unless pages set `sidebar.order`. There is no top navigation bar. Astro 7's default Markdown processor is Sätteri; `smartPunctuation` is on by default (it turned `--include` into `–include` at 170 places in the demo); `headingAttributes` enables `{#id}`. Heading IDs otherwise follow github-slugger. Relative `.md` links are not resolved. Components need `.mdx`, where `{` and `<word>` are parsed as JSX. Images referenced relatively from `src/` are optimized; files in `public/` are copied unchanged. Unconverted VitePress syntax renders as text without an error. Astro 7.3 needs Node ≥22.12 and collects anonymous telemetry unless `ASTRO_TELEMETRY_DISABLED` is set. Pagefind, Starlight's default search, builds its index in `astro build`; `astro dev` has no search.
- **Plugins.** `starlight-blog` 0.30.0 (prefix option, tags, authors, excerpt via `<!-- excerpt -->` or `excerpt:`, RSS when `site` is set; overrides `MarkdownContent` always and `ThemeSelect` unless `navigation: 'none'`; requires a real YAML date; `featured` only adds a sidebar group on blog pages and a badge), `starlight-links-validator` 0.26.0 (pages and anchors), `starlight-llms-txt` 0.12.0 (`/llms.txt`, `/llms-full.txt`, `/llms-small.txt`; requires `site`; its `exclude` affects only `llms-small.txt`). All declare `@astrojs/starlight >=0.41/0.42` and handle Sätteri.
- **Repository surroundings.** `.vscodeignore` excludes `docs/` from the VSIX but not other top-level directories; `eslint.config.mjs` ignores `**/docs/`; `build-test-package-publish.yml` has `paths-ignore: docs/**`, and three of its jobs run `npm install` on Node 20; `deploy-docs.yml` builds `docs/` on every push to `main` and deploys only for `v*` tags or a manual run. The Python packages build their sdists with `only-include = ["src"]`.

## Goals / Non-Goals

**Goals:**
- A preview of the future site that anyone can build locally from a checkout, always showing the current content of `docs/`.
- No effect on the published site, the release and the extension builds. The only new obligation for people who edit `docs/`: a new page other than a release post needs a page-map entry.
- Everything the switch needs later — structure, page map, conversion rules, components — is built and reviewed here.

**Non-Goals:**
- Publishing or deploying the preview, redirects, Algolia (all `migrate-docs-to-starlight`).
- Changes to the generators, the JSON schemas, READMEs, the release-notes skill or other changes' paths (`migrate-docs-to-starlight`).
- Rewriting content; the content problems the analysis found are listed under "Follow-up work".

## Decisions

### D1: A standalone Astro project in `docs-next/`

`docs-next/` has its own `package.json` and `package-lock.json` with `astro`, `@astrojs/starlight`, `@astrojs/markdown-satteri`, `sharp`, `starlight-blog`, `starlight-links-validator`, `starlight-llms-txt` and `lite-youtube-embed`, plus `js-yaml` and `github-slugger` for the conversion script, pinned to the minors verified during exploration (Astro 7.3, Starlight 0.42), and is not added to the root `workspaces`. `js-yaml` stays on major 4, the one Astro uses, because Astro's prerendered server code resolves `js-yaml` from the project root. An `overrides` entry pins `@astrojs/markdown-satteri` to the direct dependency: the `@astrojs/mdx` 7 that `starlight-blog` brings declares it as a `^0.3` peer, which npm 10 (Node 22, the CI) and npm 12 resolve differently, so without the entry a lockfile written by one fails `npm ci` in the other. A `vite.build.rolldownOptions.onwarn` filter drops rolldown's `MODULE_LEVEL_DIRECTIVE` warning about the `use astro:head-inject` directive Astro 7.3 still prepends to MDX pages but no longer reads (withastro/astro#18087), once per MDX page; the filter goes when the fix is released. Root scripts `docs-next:install|dev|build|preview` call `npm --prefix docs-next …` for convenience. Layout: `astro.config.mjs`, `src/pages/404.astro` (the not-found page, D9), `src/content.config.ts` (with Starlight's optional `i18n` collection; `src/content/i18n/en.json` overrides no UI string but keeps the collection from being empty, which Astro 7 reports as a warning on every build), `scripts/convert.mjs`, `content/` (hand-written pages), `src/components/`, `src/styles/custom.css`, `README.md`; `src/content/docs/`, `src/assets/` and `public/` are generated.

Rejected: a root workspace — the root `npm install` of every contributor and of the Node-20 CI jobs would pull about 375 more packages and print `EBADENGINE` for Astro; a branch — it would fall behind `docs/` and need regular merges; a one-time copy of the content — see D3.

### D2: Three areas by reader intent

Each page goes to the area that matches what the reader comes to do (full map in "Page map" below):

- **Getting Started** (`/getting-started/`): set up an editor or tool and a first project — an overview (`index.mdx`), `vscode` (the current walkthrough, titled "Get Started with VS Code"), `neovim` (moved from Tips & Tricks) and `configuration` (the `robot.toml` introduction). The overview takes over the walkthrough's "Requirements" and "Optional Python Packages" sections, which apply to every editor.
- **Guides** (`/guides/`): do a task or learn a RobotCode tool — the command handbooks (`discovering-tests`, `analyzing-code`, `analyzing-results`, `repl`, `robot-debug`), project setup (`wrapper`, `ignoring-files`, `ai-agents`) and Robot Framework practice (`avoid-global-resource-file`, `variable-not-found`, `vscode-highlighting`), with an overview titled "Guides".
- **Reference** (`/reference/`): look up exact specifications without narrative — `cli`, `config`, `diagnostics-modifiers` and the overview.
- `about`, `contributing` and the news posts (`news/v<major>-<minor>-<patch>`, the April Fools post `news/v2-5-0-april-1st`) complete the site.

A mixed page goes to the area of the part that keeps its URL when the page is split later: the command handbooks start with "Quick start" and recipes, so they are guides, and splitting off their flag tables and JSON schemas later adds Reference pages without moving the guide. Order inside a group comes from `sidebar.order` with gaps (Getting Started: overview 0, vscode 10, neovim 30, configuration 90 — free slots for JetBrains at 20 and the CLI at 40; Guides: command handbooks 10–50, project setup 110–130, Robot Framework practice 210–230); short labels from `sidebar.label`. The sidebar configuration lists `about`, the three groups with `autogenerate` per directory, and `contributing`.

The tips stay documentation. Three of the four are not tips, and the two long articles are what the diagnostics `VariableNotFound` and `PossibleCircularImport` should link to, so they need a URL without a date. As blog posts they would need a date — with the authoring date they land on page 2 of `/news/`, with a new date they appear as news in the RSS feed — and `featured` pins nothing where readers look: it adds a sidebar group on blog pages only, while `/news/` stays sorted by date. Later, short dated posts tagged `tips` can announce a tip and link to the guide. `vscode-customizations` becomes `vscode-highlighting`, since the page covers only token colours.

Rejected: the numbered folders — their numbers exist only to order the VitePress sidebar and end up in every URL; command handbooks in Reference under command names (`/reference/analyze/`, …) — keeps "task-oriented guides" in Reference, and a later split would move the guide half to a new URL; four Diátaxis areas with Explanation — no page is predominantly explanation; areas by surface (Editor, Command Line, Configuration, Automation) — fuzzy borders (diagnostic modifiers, profiles and `.robotignore` belong to several) and the most moves; tips as featured blog posts — see above.

### D3: Content generated from `docs/` on every run

`docs-next/scripts/convert.mjs` runs as npm `predev` and `prebuild` (about a second for the whole tree). It clears and rewrites `src/content/docs/`, `src/assets/` and `public/`, which are git-ignored:

- Every Markdown file under `docs/` needs an entry in the script's page map (`PAGES`: old path → page id, title, sidebar label and order, description, tags, excerpt, special rules), except release posts named `news/YYYY-MM-DD-whats-new-vX.Y.Z.md`, which map to `news/vX-Y-Z` with the tag `release` and the excerpt marker after their first paragraph when they have no entry. A file without an entry fails the run with its path.
- The hand-written pages in `docs-next/content/` (home and the three overviews) are copied in with `editUrl` and `lastUpdated` added unless the page sets them, and the Getting Started overview's marker is filled with the requirements sections; `docs/index.md`, `docs/03_reference/index.md`, `docs/04_tip_and_tricks/index.md` and `docs/news/index.md` are replaced by them and not converted.
- Frontmatter per page: `title`, `description`, `sidebar`, news `date`/`tags`/`excerpt`, `editUrl` pointing to the source file on GitHub (`…/edit/main/docs/<old path>`, or `docs-next/content/<file>` for hand-written pages), `lastUpdated` from `git log -1 --format=%cs -- <source>`, set only when `git rev-parse --is-shallow-repository` prints `false` (a shallow clone would give every page the date of its newest commit). The description comes from the page map, else from the source's own `description` frontmatter, else — for an automatically mapped release post — from the first sentence of its first paragraph.
- Conversion rules:

| VitePress | Starlight |
|---|---|
| body `# H1`, frontmatter `title` | frontmatter `title` (page map, else existing title, else H1), H1 removed |
| further `# H1` (`# JSON reference`) | demoted to `##`, its subtree shifted one level down |
| `::: tip Title` / `::: warning` / `::: info` / `::: danger` | `:::tip[Title]` / `:::caution` / `:::note` / `:::danger` |
| `::: details Title` | `<details><summary>Title</summary>` … `</details>` |
| `::: code-group` with n > 1 blocks, `:::tabs` with `=== Label` | `<Tabs>`/`<TabItem label>` (code groups with `syncKey="os"`), page becomes `.mdx` |
| `::: code-group` with 1 block, `` ```lang [title] `` | `` ```lang title="title" `` |
| `[!code error]` / `[!code focus]` comment | comment removed, line listed in `del={n}` / `mark={n}` |
| `[[KEY]]` | `<kbd>KEY</kbd>` |
| ordered list after "follow these steps" (keyed by its first item in the page map) | wrapped in `<Steps>`, page becomes `.mdx` |
| relative or absolute link to a page, `https://robotcode.io/<old>` | `/<new-id>/`, anchor mapped as in D4 |
| image `![](images/x.gif)` | copied to `src/assets/screenshots/x.gif` (lower case, `_` → `-`), referenced relatively |
| `<!-- … -->` in `.mdx` | `{/* … */}` |

- Page-specific rules from the page map: the "Requirements" and "Optional Python Packages" sections of the VS Code walkthrough are cut out and inserted into the Getting Started overview at a marker; the April Fools post gets its joke notice as first paragraph (D7); `reference/cli` gets `tableOfContents.maxHeadingLevel: 6`, since its commands sit at H3–H6.
- Static files: `docs/public/robotcode-logo.svg`, `robotcode-logo-mini.png`, `robotcode-logo.jpg` and `schemas/robot.toml.json` go to `public/`, and `robotcode-logo.svg` also to `src/assets/` for Starlight's `logo` option; the nine hero pictures listed in `RandomHeroImage.vue` (not `robotcode-golf2.png` and `robotcode-vintage-christmas.png`) go to `src/assets/hero/`, the supporter logos of `docs/images/` to `src/assets/logos/`; images no page references are not copied.
- A page index for `/llms.txt` (title, URL and description of every page, in sidebar order) is written to `docs-next/.generated/llms-index.md` (git-ignored), which `astro.config.mjs` passes to `starlight-llms-txt` as `details`.
- After converting, the script scans its output outside code for patterns only VitePress uses — `:::` followed by whitespace (its own asides are written `:::tip[…]`), `:::` followed by a container name Starlight lacks (`info`, `warning`, `details`, `code-group`, `tabs`, `raw`, `v-pre`), `[[`, `[!code`, a line starting with `=== `, `{#` in `.mdx` — and fails if it finds any; the build then fails on broken links (D6).

Pages that need no component stay `.md` (all generated pages, all pages with `<PORT>`-style placeholders). The demo's script (`scratchpad/demo/scripts/convert.mjs`) implements most of these rules and is the starting point.

Rejected: a one-time conversion committed into `docs-next/` — the preview can run for months while `docs/` keeps changing (release posts, regenerated references, the in-flight changes that edit `docs/03_reference/*`), which would mean editing every change twice or a stale preview; runtime remark/Sätteri plugins for VitePress syntax — they keep two syntaxes alive and several have peer ranges behind Sätteri 0.10.

### D4: Heading IDs and anchors

Starlight generates heading IDs. The conversion maps every existing anchor link to the new ID of its target heading: for each page it computes the github-slugger ID of every heading in document order and indexes it under the normalized (lower-case, alphanumerics only) form of the heading text, its VitePress ID and its new ID; a link's anchor is looked up by its normalized form. This also repairs the 14 anchors that are broken on the current site. A link whose anchor matches no heading is left as it is, so the link check reports it.

The configuration reference is the exception: its setting headings get explicit IDs by the rule of `_to_anchor` in `scripts/create_robot_toml_json_schema.py` (lower case, `.` → `-`, other punctuation dropped; `## tool.robotcode-analyze.cache.cache-dir {#tool-robotcode-analyze-cache-cache-dir}`), enabled by Sätteri's `headingAttributes`. These IDs equal the anchors of the current page, so the schema links that point to a setting heading today keep working. The schema's other anchors — 104 of its 330, mostly `profile-*` for settings inside profiles, plus nested keys — match no heading on the current page either; `migrate-docs-to-starlight` fixes them.

### D5: Navigation — own Header with a top bar, sidebar per area

A `Header` override (`src/components/Header.astro`) is a copy of Starlight 0.42's `Header.astro` plus a `TopNav` component: News `/news/`, Documentation `/getting-started/`, Support & Contribute `/contributing/`, Q&A (GitHub Discussions, Q&A category) and the version menu (version from the root `package.json`; Changelog, Contributing). Documentation is marked current on `/about/`, `/getting-started/…`, `/guides/…` and `/reference/…`. There is no Home entry: the site title links to `/` on every page. From 72rem width the entries are a link bar before the social icons, below that a compact `<details>` menu next to the search button, so it is also present on the home page, which has no mobile sidebar menu. News pages get their sidebar from `starlight-blog`; documentation pages get the configured sidebar; the home page uses `template: splash` and has none.

Rejected: `starlight-sidebar-topics` — puts the areas into the sidebar, which the maintainer rejected after seeing it in the demo; a `SocialIcons` override (`starlight-ui-tweaks`) — links only from `md` width, none on the splash page, collides with `starlight-blog`'s overrides; community themes with a navbar — no dropdowns and large override surfaces. The copy is the part most exposed to Starlight's breaking minors.

### D6: Link and anchor check; fix in `docs/`

`starlight-links-validator` runs with its default `failOnError: true`; its `exclude` lists only the routes `starlight-blog` generates (`/news/`, `/news/[0-9]*/`, `/news/tags/**`, `/news/authors/**`, `/news/rss.xml`), which it does not know, so links to the posts themselves stay checked. The two links to `robot-debug.md#exception-breakpoints` (in `docs/03_reference/repl.md` and `docs/03_reference/robot-debug.md`) are fixed in `docs/` — pointing at the section that describes exception breakpoints, or without the anchor — because no conversion rule can invent their target, and the current site benefits too.

### D7: News with `starlight-blog`

`starlight-blog` with `prefix: "news"`, `title: "News"`, `navigation: "none"` (the top bar has News), one global author (Daniel Biehl, GitHub avatar) and the default five posts per page; no post is `featured`. Posts get `date` (YAML date), tags and an excerpt: the `<!-- excerpt -->` marker after the first paragraph, or an `excerpt:` field from the page map where the first paragraph does not work as one (`v2-6-0`, 178 words; the April Fools post, "Hello everyone,").

Tags: exactly one kind tag — `release` (every version announcement, patch releases included), `april-fools` (joke posts, never combined with `release`), `tips` (reserved for short dated tip posts that link to a guide) — plus a topic tag for each topic the post has its own section about: `analysis`, `editor`, `vscode`, `intellij` (reserved), `cli`, `configuration`, `ci`, `debugging`, `ai-agents`, `performance`. No bugfix tag. The tags of the existing posts are in "Page map"; a new release post gets `release` automatically (D3) and its topic tags through a page-map entry.

The April Fools post invents options (`prediction-depth`, `sponsored-keywords`, `robotcode analyze social`) and would end up in `/llms-full.txt`. The conversion puts a first paragraph in front of it stating that it is an April Fools' joke and that none of the features exist.

### D8: Area overview cards from page metadata

`getting-started/index.mdx`, `guides/index.mdx` and `reference/index.mdx` (hand-written in `content/`) render their link cards through a small component that reads the docs collection, filters by the area prefix, leaves out the overview itself and sorts by `sidebar.order`, so a new page appears without editing the overview. The Getting Started overview contains the requirements sections of D3 above the cards; the Guides and Reference overviews have a short introduction.

### D9: Home page, 404, search, images, theming, LLM exports

- **Home:** `content/index.mdx` with `template: splash` and `hero` (title, tagline, actions with icons; Get Started → `/getting-started/`). A `Hero` override wraps Starlight's `Hero` and ports `RandomHeroImage.vue` and `RandomTagline.vue` as a custom element, passed to Starlight's `Hero` as the hero's HTML image so that Starlight's layout places it: random picture from `src/assets/hero/` on load (all rendered as optimized images), previous/next buttons, horizontal swipe with the same thresholds and click suppression, an enlarged view as a `<dialog>` closed by click or Escape with arrow-key navigation, and a random subline. Features as `<CardGrid>`/`<Card>` with Starlight icons, linking to the pages that cover them: REPL & notebooks → `/guides/repl/`, Run, debug & test explorer → `/getting-started/vscode/` and `/guides/robot-debug/`, One config everywhere → `/getting-started/configuration/`, Multi-IDE → `/getting-started/`, Powerful CLI → `/reference/cli/`; Project-wide refactoring links nowhere, since no page covers refactoring. The RoboCon video with `lite-youtube` through a small `YouTubeVideo` component, which imports the script and CSS of `lite-youtube-embed` so they are bundled; a `Footer` override adds the license line.
- **404:** `src/pages/404.astro`, a `StarlightPage` (splash, no edit link or last-change date, not indexed by Pagefind): this documentation keeps evolving, so pages and links can move; use the search, or start from Getting Started, Guides, Reference or News. It is not part of the docs collection, so it stays out of `/llms-full.txt` and `/llms-small.txt` (whose plugin reads the whole collection), and `astro dev` shows it for unknown paths too. `disable404Route: true` turns off Starlight's own 404 route. The link check reads only the docs collection, so the page's four links to the areas are not checked.
- **Search:** Pagefind, Starlight's default, available in `build`/`preview`. The Algolia index describes the published site; switching to Algolia is part of `migrate-docs-to-starlight`.
- **Theme and code:** brand colours as `--sl-color-accent-*` in `custom.css`; the Robot grammar, a small `gitignore` grammar for the `.robotignore` examples (comments, negation, wildcards; Shiki has none) and the two Material themes through `expressiveCode.shiki.langs`/`themes`; Sätteri with `smartPunctuation: false` and `headingAttributes: true`.
- **Social links:** built-in icons `github`, `seti:python` (PyPI), `vscode`, `jetbrains`, `openCollective`; `starlight-blog` adds the RSS icon.
- **LLM exports:** `starlight-llms-txt` provides `/llms.txt` with the page index of D3 as `details`, `/llms-full.txt` and `/llms-small.txt`. Without the index, its `llms.txt` would link only to the two text sets, while the agent skill describes `llms.txt` as a navigation index for individual pages.
- **Site URL:** `site: "https://robotcode.io"`, so canonical links, the feed and the LLM exports already carry the final URLs.

### D10: Preview workflow, CI and isolation

- `docs-next/README.md`: Node ≥22.12, `npm ci`, `npm run dev` (reloads components and styles live; edits in `docs/` or `docs-next/content/` need a restart, since the conversion runs at start) or `npm run build && npm run preview` (with search), that content is edited in `docs/`, how to add a page-map entry, and `ASTRO_TELEMETRY_DISABLED=1`. `CONTRIBUTING.md` gets a short section pointing to it and saying that a new page in `docs/` needs a page-map entry and that changes to the home page or an overview in `docs/` must be mirrored in `docs-next/content/`.
- `.github/workflows/docs-next.yml`: on pushes and pull requests that touch `docs/**`, `docs-next/**` or the workflow, on Node 22 with `ASTRO_TELEMETRY_DISABLED=1`, `npm ci` and `npm run build` in `docs-next/`; nothing is uploaded or deployed.
- `build-test-package-publish.yml` gets `docs-next/**` in `paths-ignore`, `.vscodeignore` gets `docs-next/`, `eslint.config.mjs` ignores `**/docs-next/`, each next to the existing `docs` entry.
- `AGENTS.md` (Task Routing, Docs): `docs-next/` is the Starlight preview; content is edited only in `docs/`; the page map is `docs-next/scripts/convert.mjs`; `src/content/docs/`, `src/assets/` and `public/` of `docs-next/` are generated. Common Commands: `npm run docs-next:dev|docs-next:build|docs-next:preview`.
- The documentation tasks of `doc-cli` (7.1), `library-keyword-set-declaration` (5.1) and `library-index` (8.1), which add pages to `docs/03_reference/`, get a page-map entry (id and area by the rule of D2, title, label, order, description) and a `npm run docs-next:build` check.

## Risks / Trade-offs

- [The hand-written home page and overviews do not follow edits to `docs/index.md`, `docs/03_reference/index.md` or `docs/04_tip_and_tricks/index.md`.] → The page-map entries of those files say so; CONTRIBUTING.md asks to mirror such edits. They change rarely.
- [The conversion script is code that exists only until the switch and must keep up with new syntax in `docs/`.] → Its self-check and the link check fail the CI build when it falls behind; at the switch its output is committed and the script deleted (`migrate-docs-to-starlight`).
- [Starlight 0.x ships breaking changes in minors (0.38–0.42 each had some); Astro majors came 104 days apart.] → Pinned minors; the copied `Header.astro` is diffed against upstream on upgrades.
- [Plugins with one npm maintainer (`starlight-blog`, `starlight-links-validator`, `starlight-llms-txt`).] → Each is replaceable by little own code.
- [Previewers need Node ≥22.12.] → Stated in the README; the current site's tooling is unaffected.
- [Two 1920×1080 GIFs exceed sharp's pixel limit and are shipped unoptimized (Astro writes the original GIF under a `.webp` name; browsers detect the format and animate it).] → Acceptable; re-encoding them is independent work.
- [`.mdx` pages treat `{` and `<word>` as JSX; a later edit in `docs/` could break one.] → Only pages that need components become `.mdx`; the CI build catches it.
- [Last-change dates come from git; a shallow clone would give every page the same date.] → The conversion sets them only in full clones; pages of a shallow clone show no date, and the CI build does not need them.
- [A new page in `docs/` without a page-map entry turns the preview CI red, although the VitePress build passes.] → The failure names the file; CONTRIBUTING.md, AGENTS.md and the tasks of the three changes that plan pages say what to add.

## Migration Plan

Additive: `docs-next/` and the CI workflow are new; the only changes outside are the ignore entries, root scripts, a CONTRIBUTING section and the two link fixes in `docs/`. Rollback: delete `docs-next/` and `docs-next.yml` and revert the ignore entries and scripts.

## Follow-up work

Found by the page analysis; not part of this change or of the switch.

- Split the reference halves off the guides: the `# JSON reference` parts of `discovering-tests` and `analyzing-results` (to `/reference/discover-json/`, `/reference/results-json/`), `repl`'s "Prompt features" (`/reference/repl-prompt/`), `robot-debug`'s "Debug commands" (`/reference/debugger-commands/`); state the attached/detached exception-breakpoint rule once instead of six times.
- New pages: `/getting-started/intellij/` (the hero offers "Install JetBrains"), `/getting-started/cli/` (from `cli.md` "Installation", with the `robotcode-runner[html]` extra), `/guides/ci/` (the CI recipes of the three handbooks), `/guides/profiles/` and `/reference/config-files/` (the advanced half and the loading order of `configuration`), `/guides/running-tests/` (`robotcode robot`/`run`), a VS Code features guide (Test Explorer, profile selection, settings, graphical debugger), one reference page for CLI-wide behaviour (pager and colour, AI-agent detection, environment variables).
- Consolidate the analysis-cache knowledge that exists only in the posts v2.5.0, v2.6.2 and v2.7.0 into `analyzing-code`, and correct its "prune" statement.
- Decide whether `/about/` merges into the home page or the Getting Started overview; it overlaps heavily with the home feature cards and contains a time-bound Jupyter statement.
- Content fixes: the VS Code walkthrough's "Python way" tab creates `.venv` but activates `myenv`, a stray `"""` in the `.gitignore` tip and the advice to commit the virtual environment; the PYTHONPATH note and `[Return]` in `avoid-global-resource-file`; "Inline variable" in `variable-not-found`; `:` as PYTHONPATH separator on Windows in `neovim`; the `robotcode-dev` link in `contributing`; `include`/`extend-include` vs `includes`/`extend-includes` in `configuration`; the drifted scopes of `vscode-highlighting`; `diagnostics-modifiers`' heading nesting, output example and missing `-mi/-me/-mw/-mI/-mh` flags.
- Once Guides passes about 15 pages, sidebar subgroups (Commands, Project setup, Writing Robot Framework) through explicit sidebar items, without changing URLs.

## Page map

| Source | Page | Title / sidebar label | Order | Tags |
|---|---|---|---|---|
| `docs-next/content/index.mdx` (replaces `docs/index.md`) | `/` (splash) | – | – | – |
| `docs-next/content/getting-started/index.mdx` (+ requirements sections of `02_get_started/index.md`) | `/getting-started/` | Getting Started / Overview | 0 | – |
| `docs/02_get_started/index.md` | `/getting-started/vscode/` | Get Started with VS Code / VS Code | 10 | – |
| `docs/04_tip_and_tricks/04_neovim_lsp_setup.md` | `/getting-started/neovim/` | (title) / Neovim | 30 | – |
| `docs/02_get_started/configuration.md` | `/getting-started/configuration/` | (title) / Configuration | 90 | – |
| `docs-next/content/guides/index.mdx` (replaces `docs/04_tip_and_tricks/index.md`) | `/guides/` | Guides / Overview | 0 | – |
| `docs/03_reference/discovering-tests.md` | `/guides/discovering-tests/` | (title) / Discovering Tests | 10 | – |
| `docs/03_reference/analyzing-code.md` | `/guides/analyzing-code/` | (title) / Analyzing Code | 20 | – |
| `docs/03_reference/analyzing-results.md` | `/guides/analyzing-results/` | (title) / Analyzing Results | 30 | – |
| `docs/03_reference/repl.md` | `/guides/repl/` | (title) / REPL | 40 | – |
| `docs/03_reference/robot-debug.md` | `/guides/robot-debug/` | (title) / Command-line Debugging | 50 | – |
| `docs/03_reference/wrapper.md` | `/guides/wrapper/` | (title) / Wrapper | 110 | – |
| `docs/03_reference/ignoring-files.md` | `/guides/ignoring-files/` | (title) / .robotignore | 120 | – |
| `docs/03_reference/ai-agents.md` | `/guides/ai-agents/` | (title) / AI Agents | 130 | – |
| `docs/04_tip_and_tricks/01_avoiding_a_global_resource_file.md` | `/guides/avoid-global-resource-file/` | (title) / Avoid a Global Resource File | 210 | – |
| `docs/04_tip_and_tricks/02_why_variable_not_found.md` | `/guides/variable-not-found/` | (title) / Variable Not Found | 220 | – |
| `docs/04_tip_and_tricks/03_vscode_customizations.md` | `/guides/vscode-highlighting/` | (title) / VS Code Highlighting | 230 | – |
| `docs-next/content/reference/index.mdx` (replaces `docs/03_reference/index.md`) | `/reference/` | Reference / Overview | 0 | – |
| `docs/03_reference/cli.md` | `/reference/cli/` | (title) / CLI | 1 | – |
| `docs/03_reference/config.md` | `/reference/config/` | (title) / robot.toml | 2 | – |
| `docs/03_reference/diagnostics-modifiers.md` | `/reference/diagnostics-modifiers/` | (title) / Diagnostic Modifiers | 3 | – |
| `docs/01_about/index.md` | `/about/` | (title) / About | – | – |
| `docs/05_contributing/index.md` | `/contributing/` | (title) / Support & Contribute | – | – |
| `docs-next/src/pages/404.astro` | not-found page | Page not found | – | – |
| `docs/news/index.md`, `docs/news/posts.data.ts` | replaced by `starlight-blog` | – | – | – |
| `docs/news/2026-03-31-whats-new-v2.5.0.md` | `/news/v2-5-0/` | (title) | – | release, performance, analysis, editor, cli |
| `docs/news/2026-04-01-whats-new-v2.5.0.md` | `/news/v2-5-0-april-1st/` | (title) | – | april-fools |
| `docs/news/2026-04-02-whats-new-v2.5.1.md` | `/news/v2-5-1/` | (title) | – | release, analysis, editor |
| `docs/news/2026-06-09-whats-new-v2.6.0.md` | `/news/v2-6-0/` | (title) | – | release, cli, analysis, ci, debugging, ai-agents, editor, vscode |
| `docs/news/2026-06-15-whats-new-v2.6.2.md` | `/news/v2-6-2/` | (title) | – | release, vscode, analysis, configuration |
| `docs/news/2026-07-15-whats-new-v2.7.0.md` | `/news/v2-7-0/` | (title) | – | release, configuration, cli, analysis, vscode |

## Page descriptions

Drafted from each page's content and fact-checked against it in the demo (the three overviews and the 404 page written for the new structure); reviewed again with the converted pages.

- `about`: Overview of what RobotCode offers for Robot Framework in VS Code, IntelliJ and on the command line: completion, navigation, diagnostics, debugging, REPL.
- `contributing`: Ways to support RobotCode: sponsor it on Open Collective or GitHub Sponsors, or contribute code, documentation, bug reports, feedback and community help.
- `getting-started`: Requirements for RobotCode and where to start: set it up in VS Code or Neovim, then create the robot.toml for your project.
- `getting-started/vscode`: Install the RobotCode extension for VS Code, set up a Python virtual environment with Robot Framework, select the interpreter and run your first test.
- `getting-started/neovim`: Use the RobotCode language server in Neovim 0.11+ without Mason import errors, via a project-local install or a global install with PYTHONPATH set.
- `getting-started/configuration`: Set up robot.toml for your Robot Framework project: core settings, profiles with inheritance and precedence, running tests and config file loading order.
- `guides`: Guides to RobotCode's commands and project setup: discovery, analysis, results, REPL, debugging, wrappers, .robotignore, AI agents and Robot Framework practice.
- `guides/discovering-tests`: List the suites, tests, tasks, tags and source files Robot Framework would pick up with robotcode discover, without running anything, as a tree or as JSON.
- `guides/analyzing-code`: Run static analysis with robotcode analyze code, tune severities and exit codes, and produce JSON, SARIF, GitHub or GitLab reports for CI pipelines.
- `guides/analyzing-results`: Summarize, list, walk, aggregate and diff Robot Framework run results with robotcode results in the terminal or CI, using filters, search and JSON output.
- `guides/repl`: Call Robot Framework keywords line by line in robotcode repl: import libraries, keep variables across lines, run REPL scripts, capture a log and debug.
- `guides/robot-debug`: Debug Robot Framework suites in the terminal with robotcode robot-debug: break on a line, keyword or failure, step, and inspect the stack and variables.
- `guides/wrapper`: Run tests through a wrapper command like xvfb-run or your own script, set in robot.toml or on the CLI, to bring the test environment up and tear it down.
- `guides/ignoring-files`: Keep build output, dependencies and other folders out of discovery, analysis and the language server using gitignore-style patterns in .robotignore.
- `guides/ai-agents`: Set up the RobotCode chat plugin for Copilot Chat, Claude Code and other agents so they run, discover, debug and inspect tests via the robotcode CLI.
- `guides/avoid-global-resource-file`: Why one catch-all resource file causes circular imports, ambiguous keywords and slow analysis, how to modularize it, and how to suppress the warnings.
- `guides/variable-not-found`: Why RobotCode's static analysis flags VariableNotFound for variables that work at runtime, and how Variables sections, defaults and RETURN avoid it.
- `guides/vscode-highlighting`: Add token color rules to VS Code settings.json to set font styles for Robot Framework keywords, test case names, section headers and documentation.
- `reference`: Look up every robotcode command and option, every robot.toml setting, and the syntax of robotcode: diagnostic modifier comments.
- `reference/cli`: All robotcode commands and options, from robot, rebot and discover to analyze, debug, repl and results, and which package to install for each.
- `reference/config`: Every robot.toml setting with its type and examples: profiles, robot, rebot, libdoc and testdoc options, and the tool.robotcode-analyze settings.
- `reference/diagnostics-modifiers`: Use robotcode: comments to ignore diagnostics or change their severity per line, block or file, or set the same rules project-wide in robot.toml.
- `404`: This documentation keeps evolving, so pages can move: search for the topic or start from Getting Started, Guides, Reference or News.
- `news/v2-7-0`: RobotCode 2.7.0 adds a wrapper option to run tests inside a prepared environment, makes the analysis cache reliable, and fixes Test Explorer subset runs.
- `news/v2-6-2`: Bug fixes in 2.6.1 and 2.6.2: the Test Explorer recovers after server restarts, corrupt caches rebuild, and stale profiles no longer block test runs.
- `news/v2-6-0`: RobotCode 2.6.0 adds the results command, CI-ready analysis reports, a CLI debugger, chat plugins for AI agents, and an experimental SemanticModel preview.
- `news/v2-5-1`: RobotCode 2.5.1 fixes false VariableNotFound diagnostics for templates with embedded arguments, multi-word BDD prefix matching, and CURDIR on Windows.
- `news/v2-5-0-april-1st`: April Fools version of the 2.5.0 notes with made-up features like predictive caching and emotional code completion, plus a link to the real release.
- `news/v2-5-0`: RobotCode 2.5.0 adds a persistent analysis cache and faster keyword matching, plus Literal completion, CLI unused keyword checks and cache commands.
