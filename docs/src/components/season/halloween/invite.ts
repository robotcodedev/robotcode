// Now and then a spider asks for a poke in a speech bubble next to it, so that visitors find the treats that clicked
// creatures leave: the first bubble after 5 seconds, each next one 12 to 18 seconds after the previous one appeared,
// shown for 6 seconds, until the first treat of the page. The kinds of spiders take turns, and a kind without a spider
// free in the window leaves its turn to the next. The time counts in the animation loop, so it pauses with it.
import { clamp, rand, world, type Part } from "./world";

const FIRST = 5;
const SHOWN = 6;
const FADE_MS = 300;
// the room between the bubble and its spider, the edges of the window and the page header
const GAP = 10;

// a spider that may ask now: its box in the window, holding it still while it asks, and the poke, its own reaction to
// a click
export interface Speaker {
  box(): DOMRect;
  hold(on: boolean): void;
  poke(e: PointerEvent): void;
}

// the spiders of one kind that may ask now, the best first
export type Speakers = () => Speaker[];

// the invitation of the spiders of `kinds`, in the order they take turns
export function invitations(kinds: Speakers[]): Part {
  const bubble = document.createElement("div");
  bubble.className = "rc-halloween rc-hw-invite";
  bubble.setAttribute("aria-hidden", "true");
  bubble.innerHTML = "<strong>Trick or treat?</strong> Poke me!";
  let speaker: Speaker | null = null;
  // a click on the bubble pokes the spider that asks
  bubble.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    speaker?.poke(e);
  });
  let clock = 0, due = FIRST, until = 0, turn = 0, width = 0, height = 0, placed = "";
  let removal: ReturnType<typeof setTimeout> | undefined;

  // the top of the room below the page header
  const ceiling = () => (document.querySelector<HTMLElement>(".header")?.offsetHeight ?? 0) + GAP;

  // a spider whose box lies in the window below the page header
  const inView = (s: Speaker) => {
    const r = s.box();
    return r.width > 0 && r.top >= ceiling() && r.bottom <= innerHeight - GAP && r.left >= GAP && r.right <= innerWidth - GAP;
  };

  // above the spider, below it where the header leaves no room, inside the window, its tail at the spider
  function place(s: Speaker) {
    const r = s.box();
    const top = ceiling();
    const cx = r.left + r.width / 2;
    const below = r.top - height - GAP < top;
    const x = clamp(cx - width / 2, GAP, innerWidth - width - GAP);
    const y = clamp(below ? r.bottom + GAP : r.top - height - GAP, top, innerHeight - height - GAP);
    const tail = clamp(cx - x, 14, width - 14);
    const at = `${x.toFixed(0)} ${y.toFixed(0)} ${tail.toFixed(0)} ${below}`;
    if (at === placed) return;
    placed = at;
    bubble.style.transform = `translate(${x.toFixed(0)}px, ${y.toFixed(0)}px)`;
    bubble.style.setProperty("--tail", `${tail.toFixed(0)}px`);
    bubble.toggleAttribute("data-below", below);
  }

  function show(s: Speaker) {
    speaker = s;
    s.hold(true);
    until = clock + SHOWN;
    clearTimeout(removal);
    bubble.classList.remove("rc-hw-out");
    document.body.appendChild(bubble);
    width = bubble.offsetWidth;
    height = bubble.offsetHeight;
    placed = "";
    place(s);
  }

  function hide(fade: boolean) {
    speaker?.hold(false);
    speaker = null;
    if (!fade) return bubble.remove();
    bubble.classList.add("rc-hw-out");
    removal = setTimeout(() => bubble.remove(), FADE_MS);
  }

  return {
    update(dt) {
      // in the still frame of reduced motion nobody asks
      if (dt === 0) return;
      clock += dt;
      if (world.treated) {
        if (speaker) hide(true);
        return;
      }
      if (speaker) {
        if (clock >= until) hide(true);
        else place(speaker);
        return;
      }
      if (clock < due) return;
      for (let i = 0; i < kinds.length; i++) {
        const k = (turn + i) % kinds.length;
        const s = kinds[k]().find(inView);
        if (!s) continue;
        turn = k + 1;
        due = clock + rand(12, 18);
        show(s);
        return;
      }
    },
    calm() {
      if (speaker) hide(false);
    },
  };
}
