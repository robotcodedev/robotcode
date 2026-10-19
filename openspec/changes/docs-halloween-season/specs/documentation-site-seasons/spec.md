# Spec Delta

## Purpose

Defines the seasonal looks of RobotCode's documentation site, starting with the Halloween season: when a season is active and how to preview it, which theme it starts with, what it shows on which pages, the switch that turns it off, and how it respects reduced motion.

## ADDED Requirements

### Requirement: Halloween season dates

The site SHALL treat October 24 through November 2, by the visitor's local date, as the Halloween season. Whether the season is active SHALL be decided in the visitor's browser on each page load, so that the published site switches the season on and off without being built again. Outside the season the site SHALL look and behave as it does without seasons.

#### Scenario: First day of the season
- **WHEN** a visitor opens the home page on October 24
- **THEN** the home page shows the Halloween season

#### Scenario: After the season
- **WHEN** a visitor opens the home page on November 3, from the same build
- **THEN** the home page shows no Halloween decorations and its usual subline, accent color and favicon

### Requirement: Season preview

Adding `season=halloween` to the query of a page address SHALL show the Halloween season on that page on any day, so that the season can be checked before it starts.

#### Scenario: Preview in summer
- **WHEN** a visitor opens `/?season=halloween` in July
- **THEN** the home page shows the Halloween season

### Requirement: Dark theme during the Halloween season

During the Halloween season, every page SHALL use the dark theme for a visitor who has not picked the light or the dark theme. A visitor who picked the light or the dark theme SHALL keep that theme. After the season, a visitor who picked no theme SHALL see the theme of their system again.

#### Scenario: Light system, no choice
- **WHEN** a visitor whose system prefers light colors and who never picked a theme opens a guide during the season
- **THEN** the guide is shown in the dark theme, without first showing the light theme

#### Scenario: Light theme picked
- **WHEN** a visitor who picked the light theme opens a page during the season
- **THEN** the page is shown in the light theme

### Requirement: Spooky mode switch

During the Halloween season the footer of every page SHALL offer a "Spooky mode" switch. Turning it off SHALL remove all seasonal decorations from the page at once and keep them off on all pages and later visits in that browser until it is turned on again. The switch SHALL NOT change the theme.

#### Scenario: Turning decorations off
- **WHEN** a visitor turns Spooky mode off on the home page and then opens a news post
- **THEN** neither page shows spiders, bats, the ghost, the pumpkin or the weather
- **AND** the subline, accent color and theme stay as they were

#### Scenario: Turning decorations on again
- **WHEN** the visitor turns Spooky mode on again
- **THEN** the decorations of the page come back

### Requirement: Reduced motion during the season

When the visitor's system asks for reduced motion, the seasonal decorations SHALL NOT move: nothing walks, flies, blows, swings or flickers, and no lightning is shown. The webs, the resting and hanging spiders, the pumpkin, the moon and the fog SHALL stay visible and still.

#### Scenario: Reduced motion on the home page
- **WHEN** a visitor whose system asks for reduced motion opens the home page during the season
- **THEN** no spider walks, no bat flies, no leaf blows and the pumpkin glows steadily
- **AND** the webs, the pumpkin, the moon and the fog are shown

### Requirement: Decorations stay out of the way

Seasonal decorations SHALL NOT take clicks, taps or keyboard focus away from the page, except where a visitor clicks a spider, the ghost or the pumpkin itself. Text under the fog SHALL stay readable, and every decoration SHALL be visible and readable in the light and in the dark theme. Decorations SHALL pause while the browser tab is hidden.

#### Scenario: Clicking a button under the fog
- **WHEN** a visitor clicks a link or button in the part of the window covered by fog
- **THEN** the link or button reacts as without the fog

#### Scenario: Light theme
- **WHEN** a visitor who picked the light theme opens the home page during the season
- **THEN** the spiders, bats, ghost, pumpkin, moon and fog are visible against the light background

### Requirement: Halloween look of the home page

During the Halloween season the home page SHALL choose its subline at random from Halloween sublines, slogans of well-known horror films turned into statements about RobotCode, instead of the usual sublines, and SHALL use a pumpkin accent color. The Halloween picture of the hero gallery SHALL be shown first when the site has one, and every page of the site SHALL show a pumpkin favicon.

#### Scenario: Halloween subline
- **WHEN** a visitor opens the home page during the season
- **THEN** the subline under the tagline is one of the Halloween sublines, such as "I see dead keywords. RobotCode finds the keywords and variables nobody uses anymore — in your editor and in CI."

#### Scenario: Accent and favicon
- **WHEN** a visitor opens the home page during the season
- **THEN** the accent color of its buttons and links is pumpkin orange and the browser tab shows the pumpkin favicon

#### Scenario: Favicon on a guide
- **WHEN** the visitor then opens a guide
- **THEN** the browser tab still shows the pumpkin favicon and the guide keeps its usual accent color

### Requirement: Halloween creatures on the home page

During the Halloween season the home page SHALL show spider webs in a corner of the hero and of a band, a spider hanging from the hero web on its thread, a spider resting in the band web, walking robot spiders whose head is the Robot Framework face and whose legs step like a spider's, bats flying across now and then, and a ghost that now and then peeks out from behind a block of the page and hides again.

#### Scenario: Hanging spider
- **WHEN** the pointer comes close to the hanging spider
- **THEN** the spider climbs up its thread
- **AND** it lets itself down again after the pointer has left

#### Scenario: Walking spider meets the pointer
- **WHEN** the pointer comes close to a walking spider
- **THEN** the spider stops for a moment

#### Scenario: Ghost
- **WHEN** a visitor stays on the home page for a while
- **THEN** a ghost peeks out from behind a block, looks around and hides behind it again

### Requirement: Floating pumpkin

During the Halloween season the home page and the news pages SHALL show a pumpkin with the Robot Framework face carved in that glows like a candle inside. The pumpkin SHALL float in one of the two lower corners of the window, chosen at random on each page load, and SHALL stay in that corner while the page scrolls.

#### Scenario: Scrolling
- **WHEN** a visitor scrolls the home page
- **THEN** the pumpkin stays in its lower corner of the window

#### Scenario: Corner
- **WHEN** a visitor loads the home page several times
- **THEN** the pumpkin appears sometimes in the lower left and sometimes in the lower right corner

### Requirement: Halloween weather on the home page

During the Halloween season the home page SHALL show fog drifting along the bottom of the window, the moon behind the hero's gallery picture with clouds passing in front of it, gusts of wind now and then that blow leaves across the page and visibly move the hanging spider, the webs and the pumpkin's light, and far lightning behind the moon now and then. A lightning SHALL consist of at most two soft pulses.

#### Scenario: Gust of wind
- **WHEN** a gust of wind blows across the home page
- **THEN** leaves fly across the page and the hanging spider swings

#### Scenario: Lightning
- **WHEN** lightning is shown
- **THEN** the sky behind the moon brightens at most twice and softly

### Requirement: Treats

During the Halloween season, clicking a walking spider, the hanging spider, the resting spider, the ghost or the pumpkin SHALL show a short RobotCode tip as a treat, and every tip SHALL be true for the RobotCode release the site documents. A clicked walking spider SHALL run off the screen, and the pumpkin's tip SHALL appear where it does not cover the pumpkin. Typing "boo" on the home page SHALL send a flock of bats.

#### Scenario: Catching a walking spider
- **WHEN** a visitor clicks a walking spider
- **THEN** a tip such as "`robotcode discover tests` lists every test of your project without running it." appears
- **AND** the spider runs off the screen

#### Scenario: Pumpkin treat
- **WHEN** a visitor clicks the pumpkin
- **THEN** its light flares up and a tip appears above the pumpkin

#### Scenario: Boo
- **WHEN** a visitor types "boo" on the home page outside a text field
- **THEN** bats fly across the page

### Requirement: Halloween on news pages

During the Halloween season the news pages SHALL show a pumpkin at the date badges of the posts, a spider web in a corner, the floating pumpkin and the fog. The text of the posts SHALL stay unchanged.

#### Scenario: News post during the season
- **WHEN** a visitor opens a news post during the season
- **THEN** the page shows the web, the floating pumpkin and the fog
- **AND** the text of the post is the same as outside the season

### Requirement: Guides and reference without decorations

During the Halloween season the pages of Getting Started, Guides and Reference SHALL show no seasonal decorations; only their theme, their favicon and the Spooky mode switch in their footer follow the season.

#### Scenario: Reading a guide
- **WHEN** a visitor opens `/guides/analyzing-code/` during the season
- **THEN** the guide shows no spiders, bats, ghost, pumpkin or weather
