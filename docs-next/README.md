# Preview of the new documentation site

This directory holds a preview of the future RobotCode documentation site, built with [Astro](https://astro.build/) and [Starlight](https://starlight.astro.build/). It is generated from the current documentation in [`../docs`](../docs) and is not deployed; https://robotcode.io is still built from `docs/` with VitePress. The preview lets maintainers and the community try the new structure and look locally before it replaces the published site.

## Running the preview

You need Node.js 22.12 or newer. From this directory:

```bash
npm ci                              # install the dependencies (once)
npm run dev                         # development server at http://localhost:4321
npm run build && npm run preview    # production build, served at http://localhost:4321, with search
```

From the repository root, `npm run docs-next:install`, `npm run docs-next:dev`, `npm run docs-next:build` and `npm run docs-next:preview` do the same.

- `npm run dev` reloads changes to components and styles live. Changes in `../docs` or `content/` need a restart, because the content is converted when the server starts.
- The search works only in the production build (`build` and `preview`).
- `npm run preview` runs the server in the background; stop it with `npx astro preview stop`.
- Astro collects anonymous usage data unless you set `ASTRO_TELEMETRY_DISABLED=1` (or run `npx astro telemetry disable` once).

## Where the content comes from

Content is edited in `docs/` only. Before every `dev` and `build`, [`scripts/convert.mjs`](scripts/convert.mjs) converts the pages of `docs/` into the new structure and writes them to `src/content/docs/`, their images to `src/assets/` and the static files to `public/`. These directories are generated and git-ignored; do not edit them.

The conversion fails when a page in `docs/` has no entry in its page map or still contains VitePress syntax it cannot convert, and the build fails on broken internal links and anchors.

### Adding a page to `docs/`

Add an entry for the new file to `PAGES` in `scripts/convert.mjs`, next to the entries of its area:

```js
"03_reference/my-page.md": {
  id: "guides/my-page",        // URL /guides/my-page/
  label: "My Page",            // short sidebar label
  order: 60,                   // position in the sidebar group
  description: "One sentence that describes the page, used as meta description and on the overview page.",
},
```

Choose the area by what the reader comes to do: set up an editor or tool (`getting-started/`), do a task or learn a RobotCode tool (`guides/`), or look up exact specifications without narrative (`reference/`). The overview pages list the new page automatically. Release posts named `news/YYYY-MM-DD-whats-new-vX.Y.Z.md` need no entry; they get the tag `release`. An entry adds topic tags: one for each topic the post has its own section about, from `analysis`, `editor`, `vscode`, `intellij`, `cli`, `configuration`, `ci`, `debugging`, `ai-agents` and `performance`. Every post has exactly one kind tag: `release`, `april-fools` or `tips`.

Then check the result with `npm run build`.

### Hand-written pages

The home page and the overviews of Getting Started, Guides and Reference are written for the new site and live in [`content/`](content/). They replace `docs/index.md`, `docs/03_reference/index.md` and `docs/04_tip_and_tricks/index.md`; a change to one of those files in `docs/` has to be mirrored here. The requirements sections of `docs/02_get_started/index.md` are inserted into the Getting Started overview at its `{/* sections */}` marker. The not-found page is [`src/pages/404.astro`](src/pages/404.astro).

## Layout

- `astro.config.mjs`: site, sidebar, plugins (news, link check, `llms.txt`)
- `scripts/convert.mjs`: page map and conversion from `docs/`
- `content/`: hand-written pages
- `src/pages/404.astro`: the not-found page
- `src/components/`: the header with the top navigation, the home page hero with its gallery, the footer, the overview cards and the video embed
- `src/components/home/`: the sections of the home page (feature tour, AI agents, latest news) and the player of their demos
- `src/styles/custom.css`: brand colours and small style additions; `src/styles/home.css`: the layout of the home page
