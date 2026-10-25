# Tasks

## 1. Spiders

- [x] 1.1 In `spiders.ts`, move the click reactions of the hanging, the resting and the walking spiders into pokes and give each kind a speaker (in the window and free, its box, held still while it speaks, the poke), the walkers part offering its walking spiders; let `treat()` in `world.ts` record the first treat of the page; verify in the browser that clicking each spider still drops it, hides it or chases it off, with a treat, as before.

## 2. Invitations

- [x] 2.1 Add the invitation part, created in `spiders()`: time counted from `dt` (the first bubble at 5 seconds, each next one 12 to 18 seconds after the previous one appeared, shown for 6 seconds), turns hanging, resting, walking that skip a spider out of the window or busy, the walking spider nearest the middle of the window held by its freeze, the bubble placed above its spider (below without room) and following it, a click on the bubble poking its spider, nothing in the still frame, and a shown bubble removed by `calm()` and after the first treat; style `.rc-hw-invite` in `halloween.css` like the treat bubble, with a tail and "Trick or treat?" in the accent color; verify in the dev server with `?season=halloween` on the home page and a news post: the first bubble after about 5 seconds, the turns of all three kinds with the walking spider standing while it speaks, the next spider when the hanging one is scrolled out of the window, a click on the bubble giving a treat and ending the invitations, a click on the ghost ending them too, no bubble with reduced motion, the bubble hidden with Spooky mode off, readable in the light and the dark theme and inside the window at 390 pixels, and no console errors.
- [x] 2.2 Run `npm run docs:build` and verify it passes.
