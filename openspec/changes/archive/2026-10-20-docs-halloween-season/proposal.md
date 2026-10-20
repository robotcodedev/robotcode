# Proposal

## Why

RobotCode v2.8.0 comes out in the Halloween season. A few playful Halloween touches on robotcode.io make the release a little event, the way the April Fools post did: small, friendly, switched on and off by themselves, and never in the way of reading.

## What Changes

- The site gets a **Halloween season** from October 20 to November 2. Whether it is the season is decided in the visitor's browser, so the built site switches on and off without a new deployment; `?season=halloween` shows the season on any day.
- **All pages, during the season**: the site starts in the dark theme unless the visitor picked a theme. On the pages with decorations, a small "Spooky mode" switch floats next to the pumpkin and turns all decorations off; the browser remembers it. With reduced motion nothing walks, flies, blows or swings.
- **Home page, during the season**:
  - Halloween posters of RobotCode, slogans of well-known horror films turned into statements about RobotCode, as the only and larger pictures of the gallery, the first at random, in place of the subline; a pumpkin accent color and a pumpkin favicon;
  - spider webs with a hanging spider and a resting spider, walking robot spiders with the Robot Framework face, bats now and then, and a ghost peeking out from behind blocks;
  - a pumpkin with the Robot Framework face carved in, floating in a lower corner of the window with a candle flicker;
  - Halloween weather: fog along the bottom, the moon behind the gallery picture with passing clouds, gusts of wind with leaves, far lightning now and then and sometimes a lightning bolt;
  - sound and a music box, on until the visitor turns them off and remembered: thunder after a bolt, spiders that patter and squeak, a ghost that says boo;
  - clicking a spider, the ghost or the pumpkin shows a "treat", a short true RobotCode tip; typing "boo" sends bats.
- **News pages, during the season**: the look of the home page without its hero and bands, so that a post shared as a link shows the whole season: a pumpkin at the news badges, webs with the hanging spider and the egg sac, walking spiders, bats, the ghost behind the screenshots and code blocks, the moon with clouds and lightning at the top of the page, the fog, the floating pumpkin, sound and music. The text of the posts stays as it is.
- **Guides and reference pages**: only the dark theme of the season.
- Outside the season the site looks exactly as today.

## Capabilities

### New Capabilities
- `documentation-site-seasons`: seasonal looks of the documentation site, starting with the Halloween season: when a season is active, how it is previewed, the theme it starts with, what it shows on which pages, the switch that turns it off, and how it respects reduced motion.

### Modified Capabilities
- `documentation-site`: while a season is active, the gallery of the home page shows only that season's pictures, the first at random.

## Impact

- `docs/src/components/`: the hero (`Hero.astro`: season picture and subline), the footer (`Footer.astro`: the "Spooky mode" switch next to the pumpkin and the loader of the decorations), a new ThemeProvider override for the season's default theme, and new components for the decorations.
- `docs/src/styles/`: season colors.
- `docs/astro.config.mjs`: the ThemeProvider override.
- `docs/src/assets/hero/halloween/`: the Halloween pictures.
- No new dependencies; no changes to the content of pages or posts.
