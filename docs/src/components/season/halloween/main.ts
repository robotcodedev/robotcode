// The decorations of the Halloween season, loaded by Halloween.astro on the home page and the news pages while the
// season is active and Spooky mode is on. One animation loop drives every part; it pauses while the tab is hidden and
// while Spooky mode is off, and with reduced motion it shows one still frame instead.
import "./halloween.css";
import { bats } from "./bats";
import { bloodTitle } from "./blood";
import { ghost } from "./ghost";
import { pumpkin } from "./pumpkin";
import { createWeb, spiders } from "./spiders";
import { homeWeather, pageWeather } from "./weather";
import { el, world, type Page, type Part } from "./world";

let parts: Part[] | null = null;
let raf = 0;
let last = 0;

// the gradients that the spiders and the pumpkin share
function addGradients() {
  const svg = el("svg", { class: "rc-halloween rc-hw-defs", "aria-hidden": "true", width: 0, height: 0 });
  svg.innerHTML = `<defs>
    <linearGradient id="rc-hw-shell" x1="0" y1="0" x2="0.35" y2="1">
      <stop offset="0" style="stop-color: var(--hw-shell-a)"/><stop offset="1" style="stop-color: var(--hw-shell-b)"/>
    </linearGradient>
    <linearGradient id="rc-hw-skin" x1="0" y1="0" x2="0.2" y2="1">
      <stop offset="0" style="stop-color: var(--hw-pumpkin-a)"/><stop offset="1" style="stop-color: var(--hw-pumpkin-b)"/>
    </linearGradient>
    <radialGradient id="rc-hw-inner" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" style="stop-color: var(--hw-glow-inner)"/><stop offset="1" style="stop-color: var(--hw-glow-outer)"/>
    </radialGradient>
    <radialGradient id="rc-hw-flame" cx="0.5" cy="0.6" r="0.75">
      <stop offset="0" style="stop-color: var(--hw-flame-a)"/><stop offset="0.55" style="stop-color: var(--hw-flame-a)"/>
      <stop offset="1" style="stop-color: var(--hw-flame-b)"/>
    </radialGradient>
  </defs>`;
  document.body.appendChild(svg);
}

function build(page: Page): Part[] {
  addGradients();
  const list: (Part | null)[] = [];
  if (page === "home") {
    const hero = document.querySelector<HTMLElement>(".rc-hero");
    const band = document.querySelector<HTMLElement>(".rc-band");
    const gallery = document.querySelector<HTMLElement>("rc-hero-gallery");
    const title = hero?.querySelector<HTMLElement>("h1");
    list.push(...homeWeather(gallery), ...spiders(hero, band), bats(), ghost(), pumpkin(), title ? bloodTitle(title) : null);
  } else {
    // a news page: a web at the top left of the page, the corner web in a layer over the table of contents, which
    // would take its clicks, and the screenshots and code blocks of a post for the ghost to hide behind
    const main = document.querySelector<HTMLElement>("main");
    const top = document.createElement("div");
    top.className = "rc-halloween rc-hw-page-top";
    document.body.appendChild(top);
    if (main) {
      createWeb(main, "top-left", 200);
      main.querySelectorAll<HTMLElement>(".sl-markdown-content figure").forEach((f) => (f.dataset.seasonPeek ??= "left top"));
    }
    list.push(...pageWeather(main), ...spiders(top, null), bats(), ghost(), pumpkin());
  }
  return list.filter((p): p is Part => p !== null);
}

const active = () =>
  document.documentElement.dataset.season !== undefined && document.documentElement.dataset.spooky !== "off";

// The decorations move at about 30 pictures a second: smooth enough for them, and every picture makes the browser
// paint what moved, so that 60 or the 120 of a fast display would only cost more.
const STEP = 1 / 30;

function frame(now: number) {
  raf = requestAnimationFrame(frame);
  const elapsed = (now - last) / 1000;
  if (elapsed < STEP - 0.004) return;
  last = now;
  const dt = Math.min(0.05, elapsed);
  for (const p of parts!) p.update(dt, now);
}

// runs the loop when the decorations may move, or shows their still state
function sync() {
  cancelAnimationFrame(raf);
  raf = 0;
  if (!parts || !active()) return;
  if (world.reduced()) {
    for (const p of parts) {
      p.calm?.();
      p.update(0, performance.now());
    }
    return;
  }
  if (document.hidden) return;
  last = performance.now();
  raf = requestAnimationFrame(frame);
}

export function startHalloween(page: string): void {
  if (!parts) {
    world.page = page as Page;
    parts = build(world.page);
    document.addEventListener("visibilitychange", sync);
    document.addEventListener("rc-spooky", sync);
    world.motionQuery.addEventListener("change", sync);
  }
  sync();
}
