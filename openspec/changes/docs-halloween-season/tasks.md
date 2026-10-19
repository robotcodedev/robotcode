# Tasks

The prototype `playground/halloween/spider-prototype.html` is the reference for shapes, colors, timings and animation code. Checks in the browser use `npm run docs:build` and `npm run docs:preview`, opened in a headless Chromium with its own profile (not the user's browser), with `?season=halloween` unless a task says otherwise.

## 1. Season, theme and switch

- [ ] 1.1 Add an own `ThemeProvider` (registered in `docs/astro.config.mjs`) whose inline script sets `data-season="halloween"` for October 24 – November 2 or `?season=halloween`, `data-spooky="off"` from `localStorage["robotcode-spooky"]`, the season's favicon and the theme (stored light/dark, else dark in the season, else the system's), and keeps `StarlightThemeProvider.updatePickers`; verify in the browser that a light-preferring profile with no stored theme gets `data-theme="dark"` with `?season=halloween` and `light` without it, and that a stored `light` stays light.
- [ ] 1.2 Add an own `ThemeSelect` with Starlight's markup and storage format whose Auto resolves to dark during the season and ignores system changes then; verify in the browser that the theme does not flash to light after load during the season, that picking Light, Dark and Auto works, and that outside the season Auto follows the system.
- [ ] 1.3 Draw a pumpkin favicon with the Robot Framework face as `docs/public/halloween-favicon.svg`; verify it shows in the tab of a guide and of the home page with `?season=halloween`, and the usual favicon without it.
- [ ] 1.4 Add the season's colors to `docs/src/styles/custom.css` under `:root[data-season="halloween"]`, with the pumpkin accent only in the home hero and bands, both themes; verify with screenshots of the home page and a guide in both themes that the home page buttons are pumpkin orange and the guide keeps its accent.
- [ ] 1.5 Add `src/components/season/Halloween.astro` to `Footer.astro`: the "Spooky mode" switch, visible only during the season, storing `robotcode-spooky` and toggling `data-spooky`, and a module script that imports the decorations for the page kind (`home`, `news`) with a dynamic `import()` only when the season is active and the switch is on; verify that a guide and all pages outside the season do not request the decorations chunk (network log of the headless browser), and that the switch state survives a page change.

## 2. Home page hero

- [ ] 2.1 In `Hero.astro`, take an optional `src/assets/hero/robotcode-halloween.png` into the pictures with a season mark, drop season pictures outside their season in the inline picker and show the season's picture first during it; verify that the build passes without the file, and with a placeholder file that the picture comes first only with `?season=halloween` and the next button reaches the other pictures.
- [ ] 2.2 Add the fourteen Halloween sublines listed in design.md as a season list that the subline script uses instead of the usual sublines during the season; verify by reloading with `?season=halloween` that only Halloween sublines appear, and without the parameter outside the season only the usual ones.
- [ ] 2.3 Mark the gallery picture and the demo windows of `FeatureTour.astro` and `AgentDemo.astro` with `data-season-peek`; verify the build passes and the pages look unchanged outside the season.

## 3. Decorations

- [ ] 3.1 Port the loop and shared helpers from the prototype to `src/components/season/halloween/` (one rAF loop, pause on hidden tab, stop on switch off, reduced motion with its change listener, treat bubble with an optional anchor box); verify the page has no console errors with `?season=halloween` and that the loop stops when the tab is hidden and when the switch is turned off.
- [ ] 3.2 Port the spiders: webs in the hero corner and in the first `.rc-band`, the hanging spider (climbs when the pointer comes near, drops on click), the resting spider (hides in its corner on click) and the walking robot spiders with the Robot Framework face and stepping legs only (freeze near the pointer, flee on click, come back later, fewer on narrow screens); verify with close-up screenshots in both themes and a scripted click that a treat appears and the spider runs off.
- [ ] 3.3 Port the bats (a flock now and then, "boo" typed outside text fields sends one) and the ghost peeking from behind the `data-season-peek` blocks ("Boo!" and a tip on click); verify by typing "boo" and by waiting for the ghost in the headless browser, with screenshots in both themes.
- [ ] 3.4 Port the floating pumpkin (random lower corner per load, fixed while scrolling, slow soft candle flicker, flare and a tip above the pumpkin on click); verify with screenshots after scrolling and a click that the tip does not cover the pumpkin.
- [ ] 3.5 Port the weather: fog layers, the moon with clouds behind the gallery picture, gusts with leaves that move the hanging spider, the webs, the fog and the flame, and lightning of at most two pulses; verify with screenshots during a gust and a lightning in both themes and that links under the fog can still be clicked.
- [ ] 3.6 Put the treat tips in the treats module, each checked against `docs/src/content/docs/reference/cli.md` and the `robot.toml` reference; verify every command of the list in a shell (`robotcode … --help` or a dry run in a scratch project) and that the list matches the release.

## 4. News pages

- [ ] 4.1 Decorate news pages: a pumpkin at `time.sl-blog-metadata-date`, at the home page's `.rc-news-badge` and `.rc-news time`, a web in a corner, and the floating pumpkin and the fog through the `news` page kind; verify with screenshots of `/news/` and the v2.8.0 post that the text is unchanged and the decorations appear only with `?season=halloween`.

## 5. Integration checks

- [ ] 5.1 Run `npm run docs:build` and verify it passes, including the link check, with and without the Halloween picture file.
- [ ] 5.2 Check the home page, a news post and a guide with `?season=halloween` and without it, each in the light and the dark theme, at desktop and at 390 pixels width, with reduced motion emulated, and with Spooky mode off; verify that every scenario of `documentation-site-seasons` holds and that the pages without the season look as before (compare screenshots with the current site).

## Workflow follow-up

- Add the Halloween picture from the user to `docs/src/assets/hero/robotcode-halloween.png` when it arrives.
- Archive the change after the user's review.
