# Proposal

## Why

RobotCode v2.8.0 comes out in the Halloween season. A few playful Halloween touches on robotcode.io make the release a little event, the way the April Fools post did: small, friendly, switched on and off by themselves, and never in the way of reading.

## What Changes

- The site gets a **Halloween season** from October 24 to November 2. Whether it is the season is decided in the visitor's browser, so the built site switches on and off without a new deployment; `?season=halloween` shows the season on any day.
- **All pages, during the season**: the site starts in the dark theme unless the visitor picked a theme. A "Spooky mode" switch in the footer turns all decorations off; the browser remembers it. With reduced motion nothing walks, flies, blows or swings.
- **Home page, during the season**:
  - Halloween sublines instead of the usual ones, slogans of well-known horror films turned into statements about RobotCode and chosen at random; a pumpkin accent color and a pumpkin favicon;
  - a Halloween picture of RobotCode as the first picture of the gallery, once the user delivers it;
  - spider webs with a hanging spider and a resting spider, walking robot spiders with the Robot Framework face, bats now and then, and a ghost peeking out from behind blocks;
  - a pumpkin with the Robot Framework face carved in, floating in a lower corner of the window with a candle flicker;
  - Halloween weather: fog along the bottom, the moon behind the gallery picture with passing clouds, gusts of wind with leaves, and far lightning now and then;
  - clicking a spider, the ghost or the pumpkin shows a "treat", a short true RobotCode tip; typing "boo" sends bats.
- **News pages, during the season**: a pumpkin at the news badges, a web in a corner, the floating pumpkin and the fog. The text of the posts stays as it is.
- **Guides and reference pages**: only the dark theme of the season.
- Outside the season the site looks exactly as today.

## Capabilities

### New Capabilities
- `documentation-site-seasons`: seasonal looks of the documentation site, starting with the Halloween season: when a season is active, how it is previewed, the theme it starts with, what it shows on which pages, the switch that turns it off, and how it respects reduced motion.

### Modified Capabilities
- `documentation-site`: the home page shows a season's own picture first while that season is active, instead of a random picture.

## Impact

- `docs/src/components/`: the hero (`Hero.astro`: season picture and subline), the footer (`Footer.astro`: the "Spooky mode" switch and the decorations), a new ThemeProvider override for the season's default theme, and new components for the decorations.
- `docs/src/styles/`: season colors.
- `docs/astro.config.mjs`: the ThemeProvider override.
- `docs/src/assets/hero/`: the Halloween picture, when it arrives.
- No new dependencies; no changes to the content of pages or posts.
