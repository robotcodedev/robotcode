# documentation-site-seasons Specification

## Purpose

Defines the seasonal looks of RobotCode's documentation site, starting with the Halloween season: when a season is active and how to preview it, which theme it starts with, what it shows on which pages, the switch that turns it off, and how it respects reduced motion.

## Requirements

### Requirement: Halloween season dates

The site SHALL treat October 20 through November 2, by the visitor's local date, as the Halloween season. Whether the season is active SHALL be decided in the visitor's browser on each page load, so that the published site switches the season on and off without being built again. Outside the season the site SHALL look and behave as it does without seasons.

#### Scenario: First day of the season
- **WHEN** a visitor opens the home page on October 20
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

During the Halloween season every page with decorations SHALL show a small "Spooky mode" switch next to the pumpkin, also while the decorations are off. Spooky mode SHALL be on until the visitor turns it off. Turning it off SHALL remove all seasonal decorations from the page at once, give the home page its usual pictures and subline, and keep it so on all pages and later visits in that browser until it is turned on again. The switch SHALL NOT change the theme.

#### Scenario: Switch next to the pumpkin
- **WHEN** a visitor opens the home page or a news post during the season
- **THEN** the Spooky mode switch floats next to the pumpkin, in the same lower corner of the window

#### Scenario: Turning decorations off
- **WHEN** a visitor turns Spooky mode off on the home page and then opens a news post
- **THEN** neither page shows spiders, bats, the ghost, the pumpkin or the weather
- **AND** the home page shows its usual pictures, in their usual size, its subline and its usual title
- **AND** the accent color and the theme stay as they were
- **AND** the switch is still shown in its corner, turned off

#### Scenario: Turning decorations on again
- **WHEN** the visitor turns Spooky mode on again
- **THEN** the decorations of the page and the Halloween posters come back

### Requirement: Reduced motion during the season

When the visitor's system asks for reduced motion, the seasonal decorations SHALL NOT move: nothing walks, flies, blows, swings or flickers, and no lightning is shown. The webs, the resting and hanging spiders, the pumpkin, the moon and the fog SHALL stay visible and still.

#### Scenario: Reduced motion on the home page
- **WHEN** a visitor whose system asks for reduced motion opens the home page during the season
- **THEN** no spider walks, no bat flies, no leaf blows and the pumpkin glows steadily
- **AND** the webs, the pumpkin, the moon and the fog are shown

### Requirement: Decorations stay out of the way

Seasonal decorations SHALL NOT take clicks, taps or keyboard focus away from the page, except where a visitor clicks a spider, a spider's speech bubble, the ghost or the pumpkin itself. Text under the fog SHALL stay readable, and every decoration SHALL be visible and readable in the light and in the dark theme. Decorations SHALL pause while the browser tab is hidden.

#### Scenario: Clicking a button under the fog
- **WHEN** a visitor clicks a link or button in the part of the window covered by fog
- **THEN** the link or button reacts as without the fog

#### Scenario: Light theme
- **WHEN** a visitor who picked the light theme opens the home page during the season
- **THEN** the spiders, bats, ghost, pumpkin, moon and fog are visible against the light background

### Requirement: Halloween look of the home page

During the Halloween season, while Spooky mode is on, the home page SHALL show only the Halloween posters in its gallery, larger than the usual pictures, SHALL leave out the subline under the tagline, because every poster carries one, SHALL show its title full of blood that runs down from its letters, and SHALL use a pumpkin accent color. Every page of the site SHALL show a pumpkin favicon.

#### Scenario: Halloween posters
- **WHEN** a visitor opens the home page during the season
- **THEN** one of the Halloween posters is shown, larger than the usual pictures, with its slogan such as "I see dead keywords."
- **AND** no subline is shown under the tagline

#### Scenario: Bloody title
- **WHEN** a visitor looks at the home page during the season
- **THEN** the title "RobotCode" is blood red, and blood runs down from where its letters stand on the baseline
- **AND** drops gather at the end of a trace and fall, and the trace stays and dries darker instead of vanishing
- **AND** the traces end above the tagline

#### Scenario: Accent and favicon
- **WHEN** a visitor opens the home page during the season
- **THEN** the accent color of its buttons and links is pumpkin orange and the browser tab shows the pumpkin favicon

#### Scenario: Favicon on a guide
- **WHEN** the visitor then opens a guide
- **THEN** the browser tab still shows the pumpkin favicon and the guide keeps its usual accent color

### Requirement: Halloween creatures on the home page

During the Halloween season the home page SHALL show spider webs in the top right corner of the window above the hero and in a corner of a band, a spider hanging from the hero web on its thread, a spider resting in the band web, walking robot spiders whose head is the Robot Framework face and whose legs step like a spider's, bats flying across now and then, and a ghost that now and then peeks out from behind a block of the page and hides again.

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
- **AND** it peeks out in the upper two thirds of the window, where the fog does not hide it
- **AND** it never hides behind a block that it would show through, such as the hero picture with its transparent parts

### Requirement: Floating pumpkin

During the Halloween season the home page and the news pages SHALL show a pumpkin with the Robot Framework face carved in that glows like a candle inside. The pumpkin SHALL float in one of the two lower corners of the window, chosen at random on each page load, and SHALL stay in that corner while the page scrolls.

#### Scenario: Scrolling
- **WHEN** a visitor scrolls the home page
- **THEN** the pumpkin stays in its lower corner of the window

#### Scenario: Corner
- **WHEN** a visitor loads the home page several times
- **THEN** the pumpkin appears sometimes in the lower left and sometimes in the lower right corner

### Requirement: Halloween weather on the home page

During the Halloween season the home page SHALL show fog drifting and slowly billowing along the bottom of the window, the moon behind the hero's gallery picture, unless that picture shows its own moon, with clouds passing in front of it in a sky as wide as the window, gusts of wind that blow leaves across the page and move the hanging spider, the webs and the pumpkin's light, and lightning now and then that lights the sky of the whole hero. A lightning SHALL consist of at most two soft pulses.

#### Scenario: Gust of wind
- **WHEN** a gust of wind blows across the home page
- **THEN** leaves fly across the page and the hanging spider swings

#### Scenario: Lightning
- **WHEN** lightning is shown
- **THEN** the sky of the hero brightens at most twice and softly

#### Scenario: Poster with a moon
- **WHEN** the gallery shows a Halloween poster with a moon of its own
- **THEN** the moon of the sky fades out until the gallery shows a poster without one

#### Scenario: Wide window
- **WHEN** a visitor opens the home page in a window much wider than the page content
- **THEN** the hero web hangs in the top right corner of the window
- **AND** the moon's glow, the clouds and the lightning show no edges inside the window

### Requirement: Treats

During the Halloween season, clicking a walking spider, the hanging spider, the resting spider, the ghost or the pumpkin SHALL show a short RobotCode tip as a treat, and every tip SHALL be true for the RobotCode release the site documents. A clicked walking spider SHALL run off the screen, and the pumpkin's tip SHALL appear where it does not cover the pumpkin. Typing "boo" on the home page or a news page SHALL send a swarm of bats.

#### Scenario: Catching a walking spider
- **WHEN** a visitor clicks a walking spider
- **THEN** a tip such as "`robotcode discover tests` lists every test of your project without running it." appears
- **AND** the spider runs off the screen

#### Scenario: Pumpkin treat
- **WHEN** a visitor clicks the pumpkin
- **THEN** its light flares up and a tip appears above the pumpkin

#### Scenario: Boo
- **WHEN** a visitor types "boo" on the home page outside a text field
- **THEN** a swarm of bats flies across the page

#### Scenario: Boo hint
- **WHEN** a visitor with a mouse points at the pumpkin on the home page or a news page
- **THEN** a flickering neon sign "type boo" lights up above the pumpkin
- **AND** it goes out when the pointer leaves the pumpkin or the pumpkin is clicked

#### Scenario: Boo after picking a theme
- **WHEN** a visitor has just picked a theme in the theme selector and types "boo"
- **THEN** bats fly across the page

### Requirement: Spiders ask for a poke

During the Halloween season the home page and the news pages SHALL now and then show a spider saying "Trick or treat? Poke me!" in a speech bubble next to it, for about six seconds: first about five seconds after the page opens, then about every 15 seconds, until the visitor has got a treat on the page. The hanging spider, the resting spider and the walking spiders SHALL take turns. With reduced motion no spider SHALL ask.

#### Scenario: First invitation
- **WHEN** a visitor stays on the home page or a news post for about five seconds without clicking a creature
- **THEN** a spider in the window says "Trick or treat? Poke me!" in a speech bubble next to it
- **AND** the bubble disappears after about six seconds

#### Scenario: Taking turns
- **WHEN** the visitor stays on the home page for a minute, with the hanging and the resting spider in the window
- **THEN** the hanging spider, the resting spider and a walking spider ask in turn, about every 15 seconds

#### Scenario: Walking spider asks
- **WHEN** it is a walking spider's turn
- **THEN** the spider stops while its bubble is shown and walks on afterwards

#### Scenario: Spider out of view
- **WHEN** the spider whose turn it is is not in the window, such as the hanging spider after the visitor scrolled down
- **THEN** the next spider in the window asks instead

#### Scenario: Poking the bubble
- **WHEN** the visitor clicks the speech bubble
- **THEN** its spider reacts as when it is clicked, and a treat appears

#### Scenario: After a treat
- **WHEN** the visitor clicks a spider, the ghost or the pumpkin and gets a treat
- **THEN** a speech bubble shown at that moment disappears
- **AND** no spider asks again on that page

#### Scenario: Reduced motion
- **WHEN** a visitor whose system asks for reduced motion stays on the home page
- **THEN** no spider asks

### Requirement: Lightning bolts

During the Halloween season the home page and the news pages SHALL now and then show a jagged lightning bolt in the sky of the hero or at the top of the page, behind the page content, with a strong flash, about once or twice a minute. With reduced motion no bolt SHALL be shown.

#### Scenario: Lightning bolt
- **WHEN** a visitor stays on the home page for a while
- **THEN** a lightning bolt strikes in the sky of the hero and the sky lights up

### Requirement: Sound

During the Halloween season the home page and the news pages SHALL offer a switch next to the "Spooky mode" switch that turns all sound off and on. Sound SHALL be on until the visitor turns it off, SHALL start as soon as the browser allows it, and SHALL be remembered. While it and Spooky mode are on, thunder SHALL follow a lightning bolt, a far rumble a soft lightning, walking spiders SHALL patter, the ghost SHALL boo, and clicked spiders and the egg sac SHALL make a short sound.

#### Scenario: First visit
- **WHEN** a visitor opens the home page during the season for the first time and clicks on the page
- **THEN** the sound switch shows sound on, and sound and music start

#### Scenario: Following a link
- **WHEN** sound plays on the home page and the visitor follows a link to a news post
- **THEN** sound and music go on there without another click, where the browser allows it

#### Scenario: Sound off
- **WHEN** a visitor turns sound off
- **THEN** no sound and no music plays, also on other pages and on later visits

#### Scenario: Thunder
- **WHEN** sound is on and a lightning bolt strikes
- **THEN** thunder rolls a moment later

#### Scenario: Spider sound
- **WHEN** sound is on and a visitor clicks a spider
- **THEN** the spider scurries off with a patter and a squeak

#### Scenario: Walking patter
- **WHEN** sound is on and a robot spider walks across the window
- **THEN** its steps patter softly from the side of the window where it walks

#### Scenario: Ghost boo
- **WHEN** sound is on and the ghost peeks out
- **THEN** it says "boooo", and louder when a visitor clicks it

#### Scenario: Spooky mode off
- **WHEN** a visitor turns Spooky mode off
- **THEN** no sound plays and the sound switch is hidden

### Requirement: Sound hint

While sound is on but the browser holds it back until a click, the pages with decorations SHALL show a hint above the switches to click anywhere for sound, on touch screens to tap, and SHALL hide it once sound plays, while sound is off and while Spooky mode is off.

#### Scenario: Direct visit
- **WHEN** a visitor with sound on opens a news post from a shared link
- **THEN** "Click anywhere for sound" shows above the switches
- **AND** it disappears with the first click, when sound and music start

#### Scenario: Page change
- **WHEN** sound plays and the visitor follows a link of the site to a page where the browser lets it go on
- **THEN** no hint shows

### Requirement: Music box

During the Halloween season the home page and the news pages SHALL offer a music switch beside the sound switch for a music box tune, made in the browser, that plays in a loop while sound is on. Music SHALL be on until the visitor turns it off, and the choice SHALL be remembered; with sound off, the music switch SHALL turn sound and music on. The music SHALL pause while the tab is hidden, SHALL stop while Spooky mode is off, and SHALL become quieter while thunder rolls.

#### Scenario: Music off
- **WHEN** a visitor turns the music off
- **THEN** the music stops and stays off on other pages and on later visits, while the sounds go on

#### Scenario: Sound back on
- **WHEN** a visitor who turned the music off turns sound off and on again
- **THEN** the sounds come back and the music stays off

#### Scenario: Music with sound off
- **WHEN** a visitor with sound off turns the music on
- **THEN** sound and music turn on and the music box fades in

#### Scenario: Thunder over music
- **WHEN** thunder rolls while the music plays
- **THEN** the music becomes quieter until the thunder fades

### Requirement: Egg sac in the corner web

During the Halloween season the web in the top right corner of the window on the home page and the news pages SHALL hold an egg sac in which something stirs now and then. Clicking the egg sac SHALL burst it: three to five small robot spiders hatch from it and run off the page, and the sac grows again within half a minute. While it grows, clicking it SHALL hatch nothing. With reduced motion the egg sac SHALL be shown and SHALL hatch nothing.

#### Scenario: Bursting the egg sac
- **WHEN** a visitor clicks the egg sac
- **THEN** three to five small spiders scatter from it and run off the page
- **AND** the egg sac is gone and grows again within half a minute

#### Scenario: Growing egg sac
- **WHEN** a visitor clicks the egg sac while it grows again
- **THEN** no spiders hatch

### Requirement: Halloween on news pages

During the Halloween season the news pages SHALL show the decorations of the home page except those of its hero and bands: pumpkins at the date badges, a web at the top left of the page and the corner web with the hanging spider and the egg sac, walking spiders, bats, the ghost behind the screenshots and code blocks of a post, the moon with clouds and lightning at the top of the page, the fog, the floating pumpkin, sound and music. The text of the posts SHALL stay unchanged.

#### Scenario: News post during the season
- **WHEN** a visitor opens a news post during the season
- **THEN** the page shows the webs, walking spiders, the moon and the fog, the floating pumpkin and the switches
- **AND** the text of the post is the same as outside the season

#### Scenario: Shared link
- **WHEN** a visitor opens the link of a news post, shared on social media, during the season
- **THEN** the post shows the whole Halloween look, and sound and music start with the first click

### Requirement: Guides and reference without decorations

During the Halloween season the pages of Getting Started, Guides and Reference SHALL show no seasonal decorations and no Spooky mode switch; only their theme and their favicon follow the season.

#### Scenario: Reading a guide
- **WHEN** a visitor opens `/guides/analyzing-code/` during the season
- **THEN** the guide shows no spiders, bats, ghost, pumpkin or weather
