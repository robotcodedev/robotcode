# Design

## Context

See proposal.md for the motivation and the specs for the required behavior. The look and the behavior were worked out with the user in a standalone prototype, kept at `playground/halloween/spider-prototype.html` (git-ignored; also published as a private artifact). It is the reference for shapes, colors, timings and the animation code; this design covers how it moves into the site.

The site today:

- Astro 7 with Starlight 0.42.6 and starlight-blog 0.30.2. `docs/astro.config.mjs` overrides `Header`, `Hero` and `Footer`; starlight-blog overrides only `MarkdownContent` (it would take `ThemeSelect` only with `navigation: "header-end"`, which the site does not use).
- `Hero.astro` builds the home page hero: the gallery pictures come from `src/assets/hero/` (the build fails when a listed file is missing), an inline script chooses the picture while the page is parsed, and a module script chooses one of `SUBLINES`. The news badge already decides in the browser whether a post is fresh, because the site is only built at a release.
- Starlight renders `ThemeProvider` at the end of `<head>`, after the favicon links. Its inline script sets `data-theme` from `localStorage["starlight-theme"]` (`light`, `dark`, or `''` for Auto) or the system preference. `ThemeSelect` applies the theme again when its element upgrades and follows system changes while the choice is Auto, so a season default set only in `<head>` would be undone a moment later.
- The home page is built from `.rc-band` sections and components under `src/components/home/`; news posts show their date as `time.sl-blog-metadata-date`, the home page its news as `.rc-news-badge` and `.rc-news time`.

## Goals / Non-Goals

**Goals:**
- The season is on and off by date without a new build, and it looks the same on the first paint as later (no flash of the light theme or of the usual accent).
- Outside the season, pages load nothing of the decorations beyond a few lines in `<head>` and a tiny loader.
- One rAF loop for everything that moves, paused when the tab is hidden, the switch is off or reduced motion is asked for.

**Non-Goals:**
- Other seasons now. The season check and the switch are named and stored generally (`data-season`, `robotcode-spooky`) so that another season could reuse them, but nothing else is generalized.
- Sound, third-party graphics, animation libraries.
- Keyboard access to the spiders, ghost and pumpkin: they are a decorative extra, and the treats only repeat tips from the documentation.
- Changes to the text of pages or posts; the search index and the LLM exports stay as they are.

## Decisions

### The season is decided in `<head>`, in an own `ThemeProvider`

An override of `ThemeProvider` (registered in `astro.config.mjs`) runs one inline script before the body is painted. It sets `data-season="halloween"` on `<html>` when the local date is from October 24 through November 2 or the query has `season=halloween`, sets `data-spooky="off"` when `localStorage["robotcode-spooky"]` is `off`, swaps the `href` of the favicon links to `/halloween-favicon.svg`, and sets the theme: a stored `light` or `dark` wins, otherwise the season's `dark`, otherwise the system's. It then provides `StarlightThemeProvider.updatePickers` as Starlight's does.

Alternatives: deciding at build time would need a deployment on October 24 and November 3; deciding in a module script after load would flash the light theme and the usual accent.

### An own `ThemeSelect` that knows the season

The override keeps Starlight's markup (`@astrojs/starlight/components/Select.astro` with the same three options and labels) and Starlight's storage format, but resolves Auto to dark while `data-season` is set and ignores changes of the system preference then. Patching the theme again after Starlight's `ThemeSelect` has run was rejected: it shows the light theme for a moment. Consequence, accepted: an explicit choice of Auto is stored as `''` like no choice, so it also gets the dark theme during the season.

### Colors in CSS, keyed on `data-season`

`src/styles/custom.css` gets the season's tokens under `:root[data-season="halloween"]`: the pumpkin accent (`--sl-color-accent*`, with a light-theme variant under the more specific `[data-theme="light"]`) only inside the home hero and bands, and the colors of the decorations for both themes, as in the prototype. Decorations are hidden by `:root[data-spooky="off"]` and by the absence of `data-season`.

### The decorations are loaded lazily from the footer

`Footer.astro` renders a new `src/components/season/Halloween.astro`: the "Spooky mode" switch (a button with `aria-pressed`, shown only while `data-season` is set) and a small module script. That script reads the page kind that Astro writes into a data attribute (`home` for the route `""`, `news` for routes under `news`, nothing for the rest) and, when the season is active and the switch is on, imports the decorations with a dynamic `import()`. Vite splits that code into its own chunk, so outside the season and on guides it is never requested. The switch toggles `data-spooky` and stores `robotcode-spooky`; the decorations listen for the change and stop or start.

The code is TypeScript under `src/components/season/halloween/`, split by subject: the loop and shared helpers, spiders (walking, hanging, resting, webs), bats, ghost, pumpkin, weather (fog, moon and clouds, wind and leaves, lightning) and treats. It is ported from the prototype; the swinging-leg walkers of the prototype are left out, the swinging legs stay for the hanging and the resting spider.

### Decorations make their own elements; markup only marks where they go

Everything that moves is created at runtime: a fixed full-window SVG for walking spiders, bats and leaves, the fog layers, the pumpkin and the treat bubbles are appended to `<body>`; the webs are placed in the hero and in the first `.rc-band`; the moon and the clouds go behind the gallery picture inside `rc-hero-gallery`, next to its glow. The only markup changes are `data-season-peek="<sides>"` on the blocks the ghost hides behind (the gallery picture and the demo windows, `figure.rc-window`, of the feature tour and of the AI agent demo), so the ghost does not depend on class names of other components. Nothing created takes focus or pointer events except the spiders, the ghost and the pumpkin.

### Season picture and subline in `Hero.astro`

A Halloween picture is optional: when `src/assets/hero/robotcode-halloween.png` exists, it joins the pictures with a `season` mark; when it does not, the build works as today. The inline picker drops season pictures outside their season and shows the season's picture first during it, so the gallery's count and the previous and next buttons stay consistent. The sublines get a season list; during the season the module script draws only from it, so that every visit shows the season in the text too. The list, agreed with the user (film in brackets; every statement about RobotCode is true, for example unused keywords in CI with `robotcode analyze code --collect-unused`):

1. In headless mode, no one can hear your tests scream. RobotCode can — in your editor, on the command line and in CI. (Alien)
2. It's alive! Your Robot Framework suite — with the same intelligence in your editor, on the command line and in your CI pipeline. (Frankenstein)
3. I see dead keywords. RobotCode finds the keywords and variables nobody uses anymore — in your editor and in CI. (The Sixth Sense)
4. Something strange in your test suite? Who you gonna call? RobotCode — in your editor, on the command line and in CI. (Ghostbusters)
5. Just when you thought it was safe to merge to main… RobotCode checks your suites before they bite. (Jaws 2)
6. Flaky tests? Be afraid. Be very afraid. Or debug them with RobotCode, keyword by keyword. (The Fly)
7. Here's RobotCode! The complete Robot Framework toolkit for your editor, the command line and CI. (The Shining)
8. Everyone is entitled to one good scare — just not from your CI pipeline. RobotCode checks your suites in the editor first. (Halloween)
9. Your tests were warned. RobotCode told them in the editor — long before CI could doom them. (Friday the 13th)
10. Succumb to the darkness. Robot Framework testing in your editor, on the command line and in CI — tonight in the dark theme. (Nosferatu, 2024)
11. A symphony of testing: editor, command line and CI play the same tune with RobotCode. (Nosferatu, 1922)
12. Something beyond comprehension is happening in your test suite? Set a breakpoint in the keyword and debug it with RobotCode. (The Exorcist)
13. Kiss your test nightmares goodbye — with the same intelligence in your editor, on the command line and in CI. (Evil Dead II)
14. Trapped in a red build. Surrounded by failures. Low on coffee. RobotCode shows you where each test failed. Groovy. (Army of Darkness)

### Weather and motion as in the prototype

Fog is a canvas-made, horizontally tileable noise texture used as a CSS mask over a fog color, in a faint layer in front of the content (below the spiders and the pumpkin) and a thin one at the bottom edge; it drifts by moving the mask position. Lightning is a Web Animations API animation of a sky layer with two pulses at most. Wind is one value that leaves, the hanging spider, the webs, the fog and the pumpkin's flame read. With reduced motion (also when it changes while the page is open) the loop renders one still frame and stops.

### Treats are a fixed list of verified tips

The tips live in the treats module. Each one is checked against `docs/src/content/docs/reference/cli.md` and the `robot.toml` reference before it goes in; the list of the prototype is the starting point. They are created on click, so they are not part of the page's text.

## Risks / Trade-offs

- [starlight-blog or Starlight change their markup, so a selector or the `ThemeSelect` copy no longer fits] → the decorations only run in the season; check the season with `?season=halloween` after each update of these packages and before every October.
- [Moving things distract or slow down weak devices] → limited counts (fewer spiders on narrow screens), the loop pauses in hidden tabs, the switch, reduced motion.
- [Lightning and flicker could bother visitors sensitive to flashes] → lightning is at most two soft pulses, far below three flashes per second; the pumpkin flickers slowly and softly.
- [Arachnophobia] → the switch turns everything off at once and stays off.
- [Explicit Auto looks like no choice] → accepted; a visitor who wants the light theme picks Light.
- [The Halloween picture arrives late] → the gallery works without it; it is added as one file when it comes.

## Migration Plan

Nothing to migrate. The season code stays in the site and comes back every year by itself. Rolling back is reverting the change; outside the season it has no visible effect anyway.
