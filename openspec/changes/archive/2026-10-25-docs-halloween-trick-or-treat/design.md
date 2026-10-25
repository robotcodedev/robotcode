# Design

## Context

`spiders.ts` builds the corner web with the hanging spider and the egg sac (in the hero of the home page, in a layer over the top of a news page), the band web with the resting spider (home page only) and the walking spiders: two in a layer over the window, one below 600 pixels, and a spider that ran off comes back after six to nine seconds. Clicking the hanging, resting or a walking spider, the ghost or the pumpkin calls `treat()` in `world.ts`, which shows the treat bubble with the next tip. One animation loop (`main.ts`) calls `update(dt, now)` of every part about 30 times a second; it stops while the tab is hidden and while Spooky mode is off, and with reduced motion it calls `calm()` and draws one still frame. Every page is a full page load, so what a page view knows lives in the modules.

## Goals / Non-Goals

**Goals:**

- The bubble stays next to its spider while the spider swings or climbs.
- No work and no timers while no bubble is due; the invitations pause with the loop.

**Non-Goals:**

- A sound with the invitation.
- Remembering a treat across pages or visits; every page view asks until its first treat.
- Invitations from the ghost, the pumpkin, the bats or the egg sac.
- Changes to the treats or their tips.

## Decisions

- **One invitation part, fed by the spiders.** `spiders()` creates the part and gives it a speaker for the hanging spider, for the resting spider when there is a band, and for the walking spiders, which the walkers part offers. A speaker tells whether its spider is in the window and free, where it is on the screen, holds it still while it speaks, and pokes it. Alternative: every spider schedules its own invitations; rejected, the turns and the common end need one place anyway.
- **Time counts in the loop.** The part adds up `dt` in `update`: the first bubble at 5 seconds, each next one 12 to 18 seconds after the previous one appeared, shown for 6 seconds; the first plan, at 10 seconds, every 40 to 50 seconds and for 4 seconds, was too rare and too short in use. Because the loop stops while the tab is hidden or Spooky mode is off, a visitor who comes back does not get a bubble at once. Alternative: `setTimeout`; rejected, it runs on in a hidden tab and outside the loop's pauses.
- **Turns in a fixed order, skipping who can't.** Hanging, resting, walking. When a bubble is due, the first available speaker from the one whose turn it is speaks, and the turn passes to the one after it. Available means the spider's box lies in the window below the page header, with room for the bubble, and the spider is free: the resting spider sits (not hiding or away), a walking spider is not running off. Hatchlings of the egg sac run off from the start and never speak. Of the walking spiders the one nearest the middle of the window speaks. With no speaker available the bubble waits until one is.
- **The walking spider holds still by its freeze.** While it speaks it gets the freeze it already gets when the pointer comes near, so it slows down and stands, and walks on to its target afterwards. The hanging spider keeps climbing when the pointer comes near; the bubble follows it.
- **The bubble.** A fixed `div` in the body with the classes `rc-halloween rc-hw-invite`, so Spooky mode off hides it with the rest: the background, accent border and text color of the treat bubble, a tail towards the spider, "Trick or treat?" in the accent color and "Poke me!" after it. It is placed above the spider's box, below it where there is no room, kept inside the window, and moved in every frame while shown, its `transform` written only when it changes. It fades in and out in 0.3 seconds and is `aria-hidden`, like the creatures it speaks for.
- **A click on the bubble pokes its spider.** The bubble takes pointer events and calls the speaker's poke with the click, which is the spider's own click reaction (the hanging spider drops, the resting one hides, a walking one runs off) with its treat; the spiders' `pointerdown` handlers move into these pokes. Alternative: let clicks pass through the bubble; rejected, a visitor following "Poke me!" could hit a link under it.
- **The first treat ends the invitations.** `treat()` records the treat in `world`; the part removes a shown bubble in its next `update` and asks no more. Every treat counts; the egg sac gives none and does not end them.
- **Nothing with reduced motion.** The part does nothing in the still frame (`dt = 0`), and its `calm()` removes a shown bubble. Alternative: still bubbles on a timer; rejected, reduced motion keeps the page still, and the walking spiders are gone then.

## Risks / Trade-offs

- [The bubble covers a bit of the page for six seconds, on narrow screens part of the title, over which the hanging spider hangs] → one short line above the spider; a click on it gives the treat and ends the invitations.
- [A visitor who never clicks sees a bubble about every 15 seconds for as long as the page is open] → it ends with the first treat, comes only during the season, and Spooky mode off removes it.
- [The spider's position is read in every frame while a bubble shows] → one `getBoundingClientRect` per frame for six seconds, nothing in between.
