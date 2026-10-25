# Proposal

## Why

During the Halloween season every clicked spider, the ghost and the pumpkin leave a treat, a short RobotCode tip, but nothing on the page tells visitors that the creatures can be clicked, so most of them never find a tip. A spider that now and then asks for a poke invites them to try.

## What Changes

- During the Halloween season, while Spooky mode is on, a spider now and then says "Trick or treat? Poke me!" in a small speech bubble next to it, on the home page and the news pages.
- The spiders take turns: the hanging spider, the resting spider of the home page and a walking spider, which stops while it speaks. A spider that is not in the window at its turn leaves it to the next one.
- The first invitation comes about 5 seconds after the page opens, the next ones about every 15 seconds, each for 6 seconds. Once the visitor has got a treat on the page, the spiders stop asking.
- A click on the speech bubble counts as a poke of its spider.
- With reduced motion the spiders don't ask.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `documentation-site-seasons`: a new requirement for spiders that invite visitors to poke them for a treat; "Decorations stay out of the way" lets a spider's speech bubble take a click, like the spider itself.

## Impact

- `docs/src/components/season/halloween/`: the spiders (`spiders.ts`), the treat bubble (`world.ts`) and the styles (`halloween.css`).
- The treats, their tips and the other decorations stay as they are.
