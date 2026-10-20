// A ghost that now and then peeks out from behind a block marked with `data-season-peek="<sides>"`, looks around and
// hides again. It sits next to the block in the block's parent, below the block, so the block covers it until it moves
// out at one of the given sides. With sound on it says "boooo" as it comes out. A click on it says "Boo!", louder, and
// leaves a treat.
import { boo } from "./sound";
import { rand, treat, world, type Part } from "./world";

const GHOST = `<svg viewBox="0 0 64 76" aria-hidden="true">
  <path d="M8 38 C8 17 19 4 32 4 C45 4 56 17 56 38 L56 68 Q51 75 46 68 Q41 75 36 68 Q32 74 28 68 Q23 75 18 68 Q13 75 8 68 Z" fill="var(--hw-ghost)" stroke="var(--hw-ghost-rim)" stroke-width="1.2"/>
  <circle cx="18" cy="41" r="3.4" fill="var(--hw-ghost-cheek)"/>
  <circle cx="46" cy="41" r="3.4" fill="var(--hw-ghost-cheek)"/>
  <g class="rc-hw-eyes">
    <ellipse cx="24" cy="30" rx="3.6" ry="5" fill="var(--hw-ghost-ink)"/>
    <ellipse cx="40" cy="30" rx="3.6" ry="5" fill="var(--hw-ghost-ink)"/>
    <circle cx="25.2" cy="28" r="1.2" fill="var(--hw-ghost)"/>
    <circle cx="41.2" cy="28" r="1.2" fill="var(--hw-ghost)"/>
  </g>
  <ellipse cx="32" cy="45" rx="3" ry="3.8" fill="var(--hw-ghost-ink)" opacity="0.85"/>
</svg>`;

const WIDTH = 64, HEIGHT = 76;

export function ghost(): Part | null {
  const hosts = [...document.querySelectorAll<HTMLElement>("[data-season-peek]")];
  if (!hosts.length) return null;
  const ghost = document.createElement("div");
  ghost.className = "rc-halloween rc-hw-ghost";
  ghost.innerHTML = GHOST;
  const eyes = ghost.querySelector<SVGGElement>(".rc-hw-eyes")!;
  let shown = false, until = 0, look = 0, next = performance.now() + rand(1500, 3000);

  function hide(now: number) {
    ghost.classList.remove("rc-hw-show");
    shown = false;
    next = now + rand(6000, 10000);
  }

  // the places where the ghost can come out now: in the upper two thirds of the window and below the header, so that
  // the fog at the bottom does not hide it, and with room beside the block; `at` is the ghost's distance from the
  // block's left edge (top side) or top edge (left and right side)
  function spots() {
    const minY = document.querySelector<HTMLElement>(".header")?.offsetHeight ?? 0, maxY = (innerHeight * 2) / 3;
    const list: { host: HTMLElement; side: string; at: number }[] = [];
    for (const host of hosts) {
      const r = host.getBoundingClientRect();
      if (r.width < WIDTH * 1.5 || r.height < HEIGHT * 1.2) continue;
      for (const side of (host.dataset.seasonPeek ?? "top").split(" ")) {
        if (side === "top") {
          if (r.top - HEIGHT > minY && r.top < maxY) list.push({ host, side, at: r.width * rand(0.15, 0.75) - WIDTH / 2 });
          continue;
        }
        if (side === "left" ? r.left < WIDTH : r.right > innerWidth - WIDTH) continue;
        const from = Math.max(minY, r.top + r.height * 0.08), to = Math.min(maxY - HEIGHT, r.top + r.height * 0.5);
        if (from <= to) list.push({ host, side, at: rand(from, to) - r.top });
      }
    }
    return list;
  }

  function peek(now: number) {
    const list = spots();
    if (!list.length) {
      next = now + 2000;
      return;
    }
    const { host, side, at } = list[Math.floor(Math.random() * list.length)];
    const parent = host.parentElement!;
    if (getComputedStyle(parent).position === "static") parent.style.position = "relative";
    host.classList.add("rc-hw-peek-host");
    // the ghost starts inside the block's box, behind it
    const left = side === "top" ? host.offsetLeft + at : side === "right" ? host.offsetLeft + host.offsetWidth - WIDTH : host.offsetLeft;
    const top = side === "top" ? host.offsetTop : host.offsetTop + at;
    ghost.className = `rc-halloween rc-hw-ghost rc-hw-${side}`;
    ghost.style.left = `${left.toFixed(0)}px`;
    ghost.style.top = `${top.toFixed(0)}px`;
    ghost.style.setProperty("--hw-tilt", `${side === "left" ? -14 : side === "right" ? 14 : rand(-10, 10).toFixed(0)}deg`);
    eyes.style.transform = "";
    host.before(ghost);
    ghost.getBoundingClientRect();
    ghost.classList.add("rc-hw-show");
    boo(false);
    shown = true;
    until = now + rand(4000, 6000);
    look = now + 1000;
  }

  ghost.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    boo(true);
    treat(e.clientX, e.clientY, "Boo!");
    hide(performance.now());
  });

  return {
    update(dt, now) {
      if (dt === 0) return;
      if (!shown) {
        if (now >= next && !world.reduced()) peek(now);
        return;
      }
      if (now >= look) {
        eyes.style.transform = `translate(${rand(-2.6, 2.6).toFixed(1)}px, ${rand(-1, 1.4).toFixed(1)}px)`;
        look = now + rand(550, 950);
      }
      if (now >= until) hide(now);
    },
    calm() {
      if (shown) hide(performance.now());
    },
  };
}
