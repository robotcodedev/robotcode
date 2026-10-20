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

An override of `ThemeProvider` (registered in `astro.config.mjs`) runs one inline script before the body is painted. It sets `data-season="halloween"` on `<html>` when the local date is from October 20 through November 2 or the query has `season=halloween`, sets `data-spooky="off"` when `localStorage["robotcode-spooky"]` is `off`, swaps the `href` of the favicon links to `/halloween-favicon.svg`, and sets the theme: a stored `light` or `dark` wins, otherwise the season's `dark`, otherwise the system's. It then provides `StarlightThemeProvider.updatePickers` as Starlight's does.

Alternatives: deciding at build time would need a deployment on October 20 and November 3; deciding in a module script after load would flash the light theme and the usual accent.

### An own `ThemeSelect` that knows the season

The override keeps Starlight's markup (`@astrojs/starlight/components/Select.astro` with the same three options and labels) and Starlight's storage format, but resolves Auto to dark while `data-season` is set and ignores changes of the system preference then. Patching the theme again after Starlight's `ThemeSelect` has run was rejected: it shows the light theme for a moment. Consequence, accepted: an explicit choice of Auto is stored as `''` like no choice, so it also gets the dark theme during the season.

### Colors in CSS, keyed on `data-season`

`src/styles/custom.css` gets the pumpkin accent under `:root[data-season="halloween"]:has(.rc-hero)` (`--sl-color-accent*`, with a light-theme variant under the more specific `[data-theme="light"]`), so it applies to the whole home page and the home page's surfaces that mix the accent follow it. The colors of the decorations for both themes, as in the prototype, live in the stylesheet of the lazily loaded decorations. Decorations are hidden by `:root[data-spooky="off"]` and by the absence of `data-season`.

### The decorations are loaded lazily from the footer

`Footer.astro` renders a new `src/components/season/Halloween.astro`: the "Spooky mode" switch and a small module script. That script reads the page kind that Astro writes into a data attribute (`home` for the route `""`, `news` for routes under `news`, nothing for the rest) and, when the season is active and the switch is on, imports the decorations with a dynamic `import()`. Vite splits that code into its own chunk, so outside the season and on guides it is never requested. The switch toggles `data-spooky` and stores `robotcode-spooky`; the decorations listen for the change and stop or start.

The switch (a small button with `aria-pressed`) floats next to the pumpkin, on the side towards the middle of the window, and stays there while the decorations are off, so that they can be turned on again. It is not part of the lazily loaded decorations, because those are not loaded while Spooky mode is off. For the same reason the loader, not the pumpkin, chooses the pumpkin's corner on each page load and writes it to `data-pumpkin-corner` on `<html>`; the pumpkin and the switch both read it. The switch is shown only on pages with decorations (the page kind is set) while `data-season` is set; there is no switch in the footer of guides.

The code is TypeScript under `src/components/season/halloween/`, split by subject: the loop and shared helpers, spiders (walking, hanging, resting, webs), bats, ghost, pumpkin, weather (fog, moon and clouds, wind and leaves, lightning) and treats. It is ported from the prototype; the swinging-leg walkers of the prototype are left out, the swinging legs stay for the hanging and the resting spider.

### Decorations make their own elements; markup only marks where they go

Everything that moves is created at runtime: a fixed full-window SVG for walking spiders, bats and leaves, the fog layers, the pumpkin and the treat bubbles are appended to `<body>`; the webs are placed in the hero and in the first `.rc-band`, and the hero web is moved by script to the top right corner of the window below the header; the moon and the clouds go behind the gallery picture inside `rc-hero-gallery`, next to its glow, in a sky box that the script stretches to the left and right edge of the window and that clips only there, so that the moon's glow, the clouds and the lightning have no edges inside the window; there is a cloud for about every 480 pixels of window width. The only markup changes are `data-season-peek="<sides>"` on the blocks the ghost hides behind (the demo windows, `figure.rc-window`, of the feature tour and of the AI agent demo; not the gallery picture, whose transparent parts would show the ghost), so the ghost does not depend on class names of other components. The ghost comes out only where the spot lies in the upper two thirds of the window, below the header, with room beside the block: about 80 % of it for four to six seconds, the first time after a second or two and then every six to ten seconds. Nothing created takes focus or pointer events except the spiders, the egg sac, the ghost and the pumpkin. The egg sac hangs from the top strand of the hero web, inside the web's group so that it sways with it; its hatchlings are walking spiders at 45 % of their size that start fleeing at once, slower than a fleeing walker, in a fan downwards and to the left, and are removed when they leave the window. They do not count as walking spiders, so they neither replace nor delay them. On the home page the pumpkin brings a neon sign "type boo" that pumpkin.ts creates next to it and that lights up, with a start-up flicker, while the pointer is on the pumpkin; it shows only for `(hover: hover) and (pointer: fine)`, because "boo" needs a keyboard, and the treat of a click replaces it. "boo" sends a swarm of 14 to 22 bats (at least eight on narrow screens) in a wider band, the flocks that come on their own stay at two to four. "boo" ignores only text fields (`input`, `textarea`, `[contenteditable]`): a focused `<select>`, which the theme picker keeps after a change, takes no text.

### Season picture and subline in `Hero.astro`

Season pictures lie in a folder named after the season below `src/assets/hero/` (the Halloween posters in `hero/halloween/`); one glob finds them with the usual pictures, they get the folder name as `season` mark, and their alt texts are kept by path in `SEASON_ALTS`. The inline picker keeps during a season only its pictures, the first at random, and outside of it only the usual ones, so the gallery's count and the previous and next buttons stay consistent. With Spooky mode off the home page is the usual one even in the season: the inline picker and the gallery choose the usual pictures when `data-spooky` is `off`, the gallery keeps all pictures (`data-all-pictures`) and chooses again on `rc-spooky`, and the season's CSS applies only to `:root[data-season]:not([data-spooky="off"])`. During a season the posters get half of the hero instead of five twelfths and are shown larger (`max-height: 38rem` instead of `24rem`, 400 × 600 pixels on wide screens) and the subline is left out, both by CSS on `data-season`, which ThemeProvider sets before the page is painted; the posters carry the slogans. With Spooky mode on, the title is full of blood: `custom.css` paints the letters with a blood gradient (`background-clip: text`, so the title stays text and there is no flash before the decorations load) and gives the title room below, and `blood.ts` adds an SVG inside the title whose traces use the same gradient over the height of the title, so a trace has the color of the letter where it leaves it. The traces start where the rendered letters stand on the baseline, in any font: every character is drawn at its place onto a canvas, and the ink just above the baseline (measured with an empty inline block) gives the stems, legs and round bottoms. A trace has a lip where it leaves the letter, a stream that tapers and sways a little, and a bead at its end that swells into a teardrop with a gloss; it runs down slowly, drops gather at its end and fall one after another as teardrops that stretch while they fall, then it dries darker (an overlay that is clear at the baseline, so the trace still meets the letter in its color) and stays; when every foot has a trace, fresh blood runs down an old one. Traces end above the tagline; falling drops fall through and fade below it. With reduced motion four traces hang still. A poster whose file name ends in `_moon` shows a moon of its own: the gallery sets `data-picture-moon` while it is shown, and the moon of the sky fades out. The slogans of the posters, agreed with the user (film in brackets; every statement about RobotCode is true, for example unused keywords in CI with `robotcode analyze code --collect-unused`):

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
13. Kiss your nerves goodbye? Not with RobotCode — the same intelligence in your editor, on the command line and in CI. (Evil Dead II)
14. Trapped in a red build. Surrounded by failures. Low on coffee. RobotCode shows you where each test failed. Groovy. (Army of Darkness)

### Weather and motion as in the prototype

Fog is a canvas-made, horizontally tileable noise texture used as a CSS mask over a fog color, in a faint layer in front of the content (below the spiders and the pumpkin) and a thin one at the bottom edge; it drifts and billows slowly, every texture swelling from the bottom and thickening and thinning in a period of 22 to 38 seconds of its own, all as CSS animations of transforms and opacity (a texture is a tile wider than the window that slides by one tile), so that the compositor plays them without the script and without painting the masked fog again. Lightning is a Web Animations API animation of a soft glow centred on the moon and large enough to light the whole hero, with two pulses at most, the first after six to ten seconds and then every 15 to 30 seconds. Wind is one value that leaves, the hanging spider, the webs and the pumpkin's flame read. With reduced motion (also when it changes while the page is open) the loop renders one still frame and stops.

### Keeping the load low

Every change to the SVG of a decoration makes the browser paint and raster that part again, so the decorations change as little as they can: the loop runs at about 30 pictures a second, the pumpkin at about 20; attributes are written only when their value changes (`put` in `world.ts`), slow changes such as a growing blood trace in coarse steps (whole pixels); a walking spider draws its eight legs in four shapes (outline, upper and lower segments, knees) instead of 32; the LEDs of the spiders shine steadily; the clouds move ten times a second; parts at rest stay still (the egg sac sways only in the wind or when it stirs, the hanging spider's legs rest while it hangs quietly); nothing animates a filter or a backdrop blur in every picture (the pumpkin flickers in opacity under a fixed glow, the title has no shadow filter, the switches no blurred background); and the fog runs in the compositor. Measured with performance traces in headless Chromium at 1920 × 1080 pixels, the home page with all decorations went from about 480 to about 220 milliseconds of work per second in six-second windows (about 270 over twenty seconds, gusts and bats included); the fog, which cost the most, now costs nothing measurable.

### Sound from the Web Audio API, switched on by the visitor

The sounds are synthesized in `sound.ts`, so the site ships no audio files: thunder is looped brown noise through a falling low-pass filter with the lows lifted, a few swells over its first half and a long tail (seven to nine and a half seconds near, three and a half to five far), and a near strike adds a short, dull crack; a spider's patter is short bursts of band-passed white noise with a squeak from a rising triangle oscillator; the egg sac pops with a falling sine; a walking spider patters with a faint band-passed tick, in four of ten cases followed by a second, whenever a group of its feet sets down (at most every 90 milliseconds, only inside the window), panned to where it walks; the ghost's "boooo" is two detuned saws with a vibrato through the two formants of an u, rising a little and sinking, with breath, a low thump for the b and a hall shared by the sounds. Sound and music are on until the visitor turns them off, because the season is meant to be seen and heard in full, also from a post shared as a link; every switch is at hand and remembered (`robotcode-spooky-sound`, `robotcode-spooky-music`; `data-sound` and `data-music` on `<html>`). The speaker switches all sound, the music switch the music within it, and with the speaker off the music switch turns both on. Browsers start audio only after a user gesture, so the audio context is created on the first click, tap end or key press, or at once when the browser reports an earlier activation (`navigator.userActivation.hasBeenActive`, which Chromium carries over a link of the same site, so the music goes on after a page change); while sound is on but has not played yet, `sound.ts` sets `data-sound-waiting` on `<html>`, and Halloween.astro shows "Click anywhere for sound" ("Tap" for a coarse pointer) above the switches, and suspended when sound and music or Spooky mode go off or the tab is hidden. Lightning bolts are a zigzag SVG path with one branch in the sky box, starting at the top of the hero (on narrow screens far above the box around the picture), shown with a two-pulse Web Animations API animation together with a stronger flash.

### A music box from the Web Audio API

The music box plays an own little waltz in D minor (sixteen bars of three beats, the tune in the fifth and sixth octave over a waltz accompaniment), so there is nothing to license. A tine is a sine with a partial at 4.02 times its frequency that fades fast and a short high-passed click of the pin; every note is a few cents out of tune, and one slow oscillator lets all tines wobble together like an old mechanism; a convolver with two and a half seconds of decaying noise gives it a hall. A scheduler plans the notes of the next 0.4 seconds every 100 milliseconds. Each round slows down over its last two bars; every third round the spring runs down: it slows much more, sinks by up to 45 cents, falls silent and is wound up with a ratchet before the next round. It pauses with the audio context while the tab is hidden and goes quiet while thunder rolls. The speaker switch is labelled "Sound effects" next to the music switch.

### News pages get the whole season

A news post is what gets shared, so the news pages show everything but the hero and the bands. The sky goes into `main`, a box along the top of the page (`rc-hw-sky-page`) with a smaller moon (84 instead of 118 pixels, so that it stays above the line Starlight draws under the title) right of the title, half out of the window on narrow screens; `main-pane` isolates it, so it lies behind the text as in the hero. The corner web with the hanging spider and the egg sac hangs in a layer at the top of the body (`rc-hw-page-top`), because the table of contents is a transparent fixed panel over the top right corner that would take its clicks; the web at the top left of `main` stays. The screenshots and code blocks of a post (`figure` in the content) get `data-season-peek="left top"` at runtime. The switches leave the footer for the end of `<body>` at runtime, because Starlight renders the footer in the stacking context of the content, below the sidebar and the decorations.

### Treats are a fixed list of verified tips

The tips live in the treats module. Each one is checked against `docs/src/content/docs/reference/cli.md` and the `robot.toml` reference before it goes in; the list of the prototype is the starting point. They are created on click, so they are not part of the page's text.

## Risks / Trade-offs

- [starlight-blog or Starlight change their markup, so a selector or the `ThemeSelect` copy no longer fits] → the decorations only run in the season; check the season with `?season=halloween` after each update of these packages and before every October.
- [Moving things distract or slow down weak devices] → limited counts (fewer spiders on narrow screens), the loop pauses in hidden tabs, the switch, reduced motion.
- [Lightning and flicker could bother visitors sensitive to flashes] → lightning is at most two soft pulses, far below three flashes per second; the pumpkin flickers slowly and softly.
- [Arachnophobia] → the switch turns everything off at once and stays off.
- [Explicit Auto looks like no choice] → accepted; a visitor who wants the light theme picks Light.
- [More season pictures come later] → a file dropped into the season folder shows up at once, with a general alt text until it gets its own.

## Migration Plan

Nothing to migrate. The season code stays in the site and comes back every year by itself. Rolling back is reverting the change; outside the season it has no visible effect anyway.
