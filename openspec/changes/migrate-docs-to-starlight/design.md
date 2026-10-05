# Design: migrate-docs-to-starlight

## Context

See proposal.md. This change assumes `docs-starlight-preview` is applied: `docs-next/` holds the Starlight project (components, hand-written pages in `content/`, configuration), and `docs-next/scripts/convert.mjs` generates its pages from `docs/` on every run, with the page map, conversion rules and anchor handling described in that change's design. Structure, navigation, news, home page and overviews are decided there and do not change here. The home page was reworked in the preview after that change was archived (feature tour, AI agents section, demo windows); the switch publishes it as it is, and this change updates its requirements in `specs/documentation-site`. The commands and output in its demos are fixed, abridged snapshots of runs of an example project kept outside the repository; nothing of them is generated during the switch. Facts specific to the switch:

- **Generated pages and schema.** `scripts/create_cmdline_doc.py` rewrites the part of `docs/03_reference/cli.md` between `<!-- START -->` and `<!-- END -->`. `config.md` is the output of `robotcode config info desc` (CONTRIBUTING.md, "Regenerating the `robot.toml` option model"), which starts with `# robot.toml configuration settings` and has one `## <setting>` per setting. `scripts/create_robot_toml_json_schema.py` links every setting to `https://robotcode.io/03_reference/config#<_to_anchor(path)>` and names the page in its `$comment`. The current schema has 330 such links (the frozen `etc/robot.toml.json`, kept for older RobotCode versions since commit `fafb1681`, has 324). 226 of them point to a setting heading, which the preview's configuration reference carries as explicit IDs. 104 match no heading, on the current site either: 100 `profile-*` anchors, because the generator maps `profiles.<name>.<setting>` to `profile-<setting>` while `config.md` has only six `[profile].*` headings, plus `extend-expand-keywords-name`, `extend-expand-keywords-tag`, `extend-languages-expr` and `tool-robotcode-analyze`.
- **Links into the site from the repository.** `README.md` (`/02_get_started/`, `/03_reference/cli`, `/04_tip_and_tricks/`, `/05_contributing/`), `intellij-client/README.md` (`/02_get_started/`), `vscode-client/extension/index.ts` (`/news/`), `chat-plugins/robotcode/skills/robotcode/SKILL.md` (`/llms.txt`, `/llms-full.txt`), `chat-plugins/robotcode/README.md` line 27 (`/03_reference/cli`, vendored from `plugins/robotcode/README.md` in robotframework-agent-plugins), `AI_POLICY.md` (`docs/03_reference/cli.md` as an example of a generated file). `.claude/skills/create-release-notes/SKILL.md` writes posts to `docs/news/YYYY-MM-DD-whats-new-vX.Y.Z.md` with a body H1, recognises April Fools posts by an `aprilFools` field and asks for VitePress-compatible Markdown. Ten in-flight changes name `docs/0x_…` paths (proposal.md, Impact).
- **Search.** The current site uses Algolia DocSearch (app `7D5ZR1RO6N`, index `robotcode`); the preview uses Pagefind. Pagefind has no typo tolerance: in the demo, misspelled queries found unrelated prefixes. `@astrojs/starlight-docsearch` 0.8.0 is the official plugin (Starlight ≥0.38, Astro 6/7).
- **Deployment and CI.** `deploy-docs.yml` builds on every push to `main` and deploys to GitHub Pages only for `v*` tags or a manual run with `deploy: true`, uploading `docs/.vitepress/dist`; it uses Node 26 and `fetch-depth: 0`. `docs/public/CNAME` holds `robotcode.io`. Three jobs of `build-test-package-publish.yml` run `npm install` on Node 26, which installs the `docs` workspace.
- **Last-change dates.** Starlight reads a page's last change from `git log` of the page file without following renames.
- **News entry point.** After an update, the VS Code extension offers "What's New?", which opens `https://robotcode.io/news/` in VS Code's Simple Browser (`robotcode.showWhatsNew`). On the current site that page forwards to the newest post on load (a script in `docs/news/index.md`); in the preview `/news/` is starlight-blog's list of posts.

## Goals / Non-Goals

**Goals:**
- Replace the published site with the reviewed preview in one commit, leaving `docs/` as a plain Starlight project that is edited directly.
- Keep the JSON schema's anchors stable and every generator writing its page in place.
- Leave no reference to the old paths in the repository, except the changelog and the frozen schema.

**Non-Goals:**
- Redirects from the old URLs.
- Changes to the structure, pages or components decided in `docs-starlight-preview`.
- Raising the Node version of the extension build jobs.

## Decisions

### D1: Switch in one commit, pages moved with `git mv`

1. Run the conversion one last time in a switch mode, from the unmoved tree into a temporary directory: without `editUrl` and `lastUpdated` (from now on `editLink.baseUrl` and the git history of the page files provide them), with the hand-written pages included and the Getting Started marker filled.
2. Move every old page, every referenced image and every file the conversion copies for the hand-written pages to its new place with `git mv`, following the page map of `docs-starlight-preview` and the conversion's list of those files (e.g. `docs/03_reference/repl.md` → `docs/src/content/docs/guides/repl.md`, `docs/04_tip_and_tricks/images/neovim-mason-import-errors.png` → `docs/src/assets/screenshots/neovim-mason-import-errors.png`, the nine hero pictures from `docs/public/` → `docs/src/assets/hero/`, the supporter logos and the home page's recordings and editor screenshots from `docs/images/` → `docs/src/assets/logos/` and `docs/src/assets/screenshots/`), so `git log --follow` keeps the history; then overwrite each moved file with its converted version from step 1 and add the hand-written pages from there.
3. Move the project files of `docs-next/` (`astro.config.mjs`, `src/content.config.ts`, `src/content/i18n/`, `src/pages/`, `src/components/`, `src/styles/`) into `docs/`, set `editLink.baseUrl` to `https://github.com/robotcodedev/robotcode/edit/main/docs/` (Starlight appends `src/content/docs/<page>`), merge the dependencies into `docs/package.json` (without `github-slugger`, which only the deleted conversion script uses). The page index for `/llms.txt`, which the conversion script wrote to `.generated/llms-index.md`, is then built by a small module `docs/scripts/llms-index.mjs` that `astro.config.mjs` calls: it reads title, description and sidebar order from the frontmatter of `src/content/docs/` and produces the same list in the same order. The check of the links in `src/pages/`, also part of the conversion script, becomes a `prebuild` script `docs/scripts/check-page-links.mjs`. Then delete `docs-next/` (with the conversion script and `content/`), `.vitepress/`, `news/posts.data.ts`, the replaced index pages, the old image directories (`docs/images/`, `docs/0x_*/images/`, once step 2 has moved out what the site uses), the images in `docs/public/` no page references (`robotcode-golf2.png`, `robotcode-vintage-christmas.png`) and the VitePress dependencies.

`docs/public/` keeps `CNAME`, the favicons, the Open Graph image and `schemas/robot.toml.json`. `docs/` stays the root workspace; the root `.gitignore` gets `docs/.astro/` (`dist/` is ignored already).

Rejected: keeping the generation from a VitePress tree — two syntaxes for every future edit; converting in place after the move — the page map is keyed by the old paths and the conversion clears its target; a fresh copy without `git mv` — loses the per-file history.

### D2: Generated references

`scripts/create_cmdline_doc.py` writes to `docs/src/content/docs/reference/cli.md`; the frontmatter (title, description, `sidebar`, `tableOfContents.maxHeadingLevel: 6`) sits above `<!-- START -->` and stays hand-maintained. A new `scripts/create_config_doc.py` (hatch script `create-config-docs`) runs `python -m robotcode.cli config info desc` with colour off, drops its H1, prepends the frontmatter and appends `{#<_to_anchor(name)>}` to every `## <setting>` heading, importing `_to_anchor` from `create_robot_toml_json_schema.py`; its output equals what the preview's conversion produced. It replaces the redirection `robotcode config info desc > docs/03_reference/config.md` in CONTRIBUTING.md; the output of `robotcode config info desc` itself does not change.

Rejected: emitting frontmatter and IDs from `robotcode config info desc` — that command's Markdown is also shown in terminals.

### D3: JSON schema links

`base_url` of `scripts/create_robot_toml_json_schema.py` becomes `https://robotcode.io/reference/config/`, also in its `$comment`; `_to_anchor` stays the single slug function for the schema and the configuration reference, so the 226 anchors of setting headings do not change. The generator's link paths are corrected for the 104 others: a setting inside a profile (`profiles.<name>.<setting>`) links to the top-level setting of the same name (`profile-args` → `args`), except the six profile-only settings with `[profile].*` headings (`profile-enabled-if` → `profile-enabled`); a nested key links to its parent setting (`extend-expand-keywords-name` → `extend-expand-keywords`, `extend-languages-expr` → `extend-languages`); `tool.robotcode-analyze` links to the first heading of its section. After that every anchor of the schema exists on the page, as `robot-toml-option-coverage` requires. `etc/robot.toml.json` stays unchanged; its links end on the not-found page.

Rejected: extra heading IDs for the missing anchors in `create_config_doc.py` — hidden anchors without visible headings, and the profile variants would duplicate every setting's anchor.

### D4: Algolia DocSearch

`@astrojs/starlight-docsearch` replaces Pagefind, with the existing app id, search key and index name. The crawler configuration in the Algolia dashboard is switched to Starlight's page structure and the new URLs; the index is recrawled right after the deployment.

Rejected: Pagefind — no typo tolerance.

### D5: Release-notes skill

`.claude/skills/create-release-notes/SKILL.md` writes `docs/src/content/docs/news/vX-Y-Z.md` with `title`, a one-sentence `description`, `date`, one kind tag and topic tags from the vocabulary of `docs-starlight-preview` (listed in the skill so it does not drift), an `<!-- excerpt -->` marker and no body H1, in Starlight syntax; it recognises joke posts by the `april-fools` tag and uses the converted posts as templates.

### D6: Links outside the site and other changes

`README.md` and `intellij-client/README.md` link `/getting-started/`, `/reference/cli/`, `/guides/` (link text "Guides" instead of "Tips & Tricks") and `/contributing/`. The agent plugin's README links its installation guide to `/reference/cli/`; it is changed in robotframework-agent-plugins and re-synced with `hatch run build:sync-chat-plugin`. `AI_POLICY.md` names `docs/src/content/docs/reference/cli.md` as the generated file. `CONTRIBUTING.md` describes the docs build and preview, the regeneration commands, where images go (`src/assets/`), the three areas and where a new page belongs, the Starlight syntax for asides, tabs, steps and code titles, `.mdx` only where components are needed, and `ASTRO_TELEMETRY_DISABLED`; its preview section goes. `AGENTS.md` names the docs commands. The Purpose line of `openspec/specs/cli-reference-generation/spec.md` names the new path of `cli.md`.

The documentation paths in the artifacts of the in-flight changes not yet applied are rewritten page by page following the page map (`repl.md`, `robot-debug.md`, `analyzing-code.md`, `discovering-tests.md`, `ai-agents.md` and the planned `browsing-documentation.md` go to `guides/`; `cli.md`, `config.md` and `index.md` to `reference/`; references to the "Requirements" or "Optional Python Packages" sections of `02_get_started/index.md` to `getting-started/index.mdx`, all other references to that file to `getting-started/vscode.mdx`; a planned page such as `library-keyword-sets.md` or `library-entry-points.md` goes where its page-map entry put it, by the rule of the preview's D2 — Reference only for a specification without task narrative, otherwise Guides); an instruction to add a line to `docs/03_reference/index.md` becomes "declare `title`, `description` and `sidebar.order`", and `hatch run robotcode config info desc > docs/03_reference/config.md` becomes `hatch run create-config-docs`. Changes applied before the switch have their page edits carried along by the conversion, and a page they added keeps the area its page-map entry gave it.

### D7: Deployment and cleanup

`deploy-docs.yml` uploads `docs/dist` and sets `ASTRO_TELEMETRY_DISABLED=1`. `.github/workflows/docs-next.yml`, the `docs-next` entries in `build-test-package-publish.yml`, `.vscodeignore` and `eslint.config.mjs`, and the root `docs-next:*` scripts are removed; the existing `docs` entries stay. After the merge the site is deployed manually (`workflow_dispatch`, `deploy: true`), then the crawler runs.

### D8: Screen recordings as MP4

Every animated GIF a page shows becomes an MP4 once, during the switch: the three recordings of Getting Started (`python-create-env.gif`, `robotcode-add-to-workspace.gif`, `robotcode-first-test-case.gif`). The video keeps the timing browsers give the GIF: a frame delay of 10 ms or less plays as 100 ms, so the old `autocomplete1.gif`, encoded as 10.6 s, ran 38.8 s on the site. The pages show a recording as a muted video in a loop, like the GIF, importing the file (so they are `.mdx`). The MP4s replace the GIFs in `src/assets/screenshots/`; the single-frame GIFs `with_customization.gif` and `without_customization.gif` stay images. The home page and the About page show recordings of the example project instead, `vscode-code-intelligence.mp4`, `vscode-run-tests.mp4` and `vscode-debug.mp4` in `docs/images/` since the preview; the conversion imports the About page's `<video>` files like images, and they move with the other files the site uses (D1 step 2).

The conversion runs once, so no script is kept. Per GIF: read the frame delays with `ffprobe -v error -select_streams v:0 -show_entries frame=duration_time -of csv=p=0 <gif>`, count every delay of 0.01 s or less as 0.1 s, extract the frames with `ffmpeg -i <gif> -fps_mode passthrough frames/%05d.png`, write an ffmpeg concat list with each frame and its delay (`file '<png>'` / `duration <s>`, the last frame once more at the end), and encode with `ffmpeg -f concat -safe 0 -i list.txt -fps_mode vfr -an -c:v libx264 -preset veryslow -crf 24 -pix_fmt yuv420p -movflags +faststart <mp4>`. A GIF whose header declares non-square pixels (`python-create-env.gif`: 63:64) also gets `-vf setsar=1`: browsers show GIF pixels square, but ffmpeg carries the ratio into the video. In the preview this made 1.5 MB of the old `autocomplete1.gif`'s 5.0 MB and 356 KB of `running_tests.gif`'s 875 KB, with sharp text.

Rejected: keeping the GIFs — five times the size, and a GIF cannot start over when shown; the encoded timing — plays up to four times faster than the GIF did on the site; WebM (VP9) — larger than H.264 for these recordings, and H.264 plays everywhere.

### D9: Newest release notes at a fixed address

`astro.config.mjs` declares `/news/latest/` as a redirect to the newest release post. `docs/scripts/latest-news.mjs` reads the target from the frontmatter of the posts (the newest `date` among the posts tagged `release`, drafts left out), so every build points it at the newest release notes, and a later post of another kind, such as `tips` or `april-fools`, never becomes the target. For a static build Astro writes the redirect as a page with `<meta http-equiv="refresh">`, `noindex` and a canonical link, which works without JavaScript and inside the Simple Browser. `robotcode.showWhatsNew` opens `https://robotcode.io/news/latest/`; the extension version that does so ships with the release whose tag deploys the new site.

Rejected: forwarding `/news/` itself — the News entry of the top navigation would no longer reach the list; a URL built from the extension's version — not every release has a post of its own (the v2.6.2 post also covers v2.6.1).

## Risks / Trade-offs

- [Old links end on the not-found page: READMEs of released versions on PyPI and the marketplaces, older schemas in editors until they fetch the new one, the frozen `etc/robot.toml.json`, third-party sites.] → Accepted by the maintainer. The not-found page offers the search and the main areas.
- [Go-live gap: README links change on push to `main`, the site only on the next deploy; the Algolia index points to old URLs until the recrawl.] → Deploy manually right after merging, then trigger the crawler.
- [All pages show the switch date as their last change, since Starlight does not follow renames.] → Accepted; dates become meaningful with the next edit of each page.
- [Starlight 0.x breaking minors now affect the published site.] → Pinned minors; the copied `Header.astro` is diffed against upstream on upgrades.
- [The docs workspace adds about 375 packages to the root lockfile, which three CI jobs of `build-test-package-publish.yml` install too.] → Accepted; they run on Node 26, which Astro supports.
- [The home page's demos show `robotcode doc` and `robotcode discover --by-test-metadata`, which no release ships as of 2026-10-04.] → The switch goes live together with the release that ships both.
- [A later release changes the output of a command the demos show.] → The demo text is adapted by hand, like a documentation or news page; the example project behind it is not part of the repository.

## Migration Plan

1. Confirm `docs-starlight-preview` is applied and the preview is accepted.
2. Switch `docs/` (D1), adapt and run the generators and the schema generator (D2, D3), configure DocSearch (D4).
3. Update the skill, links, process docs and the other changes' paths (D5, D6); adapt the workflows and remove the preview's entries (D7).
4. `npm run docs:build` without link errors, visual review, merge with the release that ships `robotcode doc` and `robotcode discover --by-test-metadata`, deploy manually, update the DocSearch crawler and recrawl.

Rollback: revert the commit and run the deploy workflow manually; the previous site is deployed again, and the crawler configuration is switched back.
