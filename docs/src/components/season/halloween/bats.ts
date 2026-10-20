// Bats: now and then a small flock flies across the window with flapping wings; typing "boo" outside a text field sends
// a whole swarm at once.
import { el, rand, windowLayer, world, type Part } from "./world";

const WING = "M-2 -1.5 C-8 -9 -18 -12 -28 -8 C-25 -5 -24 -1 -25 3 C-21 0 -17 0 -14 4 C-12 1 -8 0 -5 4 C-4 2.5 -3 1.5 -2 2 Z";

interface Bat {
  g: SVGGElement;
  left: SVGPathElement;
  right: SVGPathElement;
  t: number;
  x: number;
  y: number;
  vx: number;
  amp: number;
  freq: number;
  ph: number;
  flap: number;
  scale: number;
}

export function bats(): Part {
  const layer = windowLayer("rc-hw-layer");
  const flying: Bat[] = [];
  let next = performance.now() + rand(3500, 6000);

  // a flock of two to four bats, or a swarm of 14 to 22 (fewer on narrow screens) spread over a wider band
  function send(swarm = false) {
    if (world.reduced()) return;
    const W = innerWidth, H = innerHeight;
    const dir = Math.random() < 0.5 ? 1 : -1;
    const n = swarm ? Math.max(8, Math.round((14 + Math.random() * 8) * Math.min(1, W / 1000))) : 2 + Math.floor(Math.random() * 3);
    const baseY = swarm ? rand(H * 0.25, H * 0.45) : rand(110, Math.max(120, H * 0.45));
    const spread = swarm ? Math.min(170, H * 0.2) : 50;
    const gap = swarm ? [18, 42] : [40, 90];
    for (let i = 0; i < n; i++) {
      const g = el("g", {}, layer);
      const left = el("path", { d: WING, fill: "var(--hw-bat)" }, g);
      const right = el("path", { d: WING, fill: "var(--hw-bat)" }, g);
      el("ellipse", { cx: 0, cy: 1, rx: 3.4, ry: 5.4, fill: "var(--hw-bat)" }, g);
      el("path", { d: "M-3 -4 L-3.6 -9.5 L-1 -6.4 L1 -6.4 L3.6 -9.5 L3 -4 Z", fill: "var(--hw-bat)" }, g);
      el("circle", { cx: 0, cy: -4.2, r: 3.3, fill: "var(--hw-bat)" }, g);
      el("circle", { cx: -1.2, cy: -4.6, r: 0.75, fill: "var(--hw-bat-eye)" }, g);
      el("circle", { cx: 1.2, cy: -4.6, r: 0.75, fill: "var(--hw-bat-eye)" }, g);
      flying.push({
        g, left, right, t: 0,
        x: dir > 0 ? -60 - i * rand(gap[0], gap[1]) : W + 60 + i * rand(gap[0], gap[1]),
        y: baseY + rand(-spread, spread),
        vx: dir * rand(170, 250),
        amp: rand(12, 30),
        freq: rand(1.4, 2.8),
        ph: rand(0, 6),
        flap: 2 * Math.PI * rand(4, 6),
        scale: rand(0.85, 1.4),
      });
    }
  }

  // "boo" typed anywhere but in a text field; a focused select, such as the theme picker after a change, does not count
  let typed = "";
  addEventListener("keydown", (e) => {
    const target = e.target as HTMLElement | null;
    if (target?.closest("input, textarea, [contenteditable]") || e.key.length !== 1) return;
    typed = (typed + e.key.toLowerCase()).slice(-3);
    if (typed === "boo" && document.documentElement.dataset.spooky !== "off") {
      send(true);
      next = performance.now() + rand(14000, 26000);
    }
  });

  return {
    update(dt, now) {
      if (dt === 0) return;
      if (now >= next) {
        send();
        next = now + rand(14000, 26000);
      }
      const W = innerWidth;
      for (let i = flying.length - 1; i >= 0; i--) {
        const b = flying[i];
        b.t += dt;
        b.x += b.vx * dt;
        const y = b.y + Math.sin(b.t * b.freq + b.ph) * b.amp;
        const dy = Math.cos(b.t * b.freq + b.ph) * b.amp * b.freq;
        const tilt = ((Math.atan2(dy, Math.abs(b.vx)) * 180) / Math.PI) * 0.7 * Math.sign(b.vx);
        const a = Math.sin(b.t * b.flap) * 40;
        b.left.setAttribute("transform", `rotate(${a.toFixed(1)} -2 0)`);
        b.right.setAttribute("transform", `scale(-1 1) rotate(${a.toFixed(1)} -2 0)`);
        b.g.setAttribute("transform", `translate(${b.x.toFixed(1)} ${y.toFixed(1)}) rotate(${tilt.toFixed(1)}) scale(${b.scale.toFixed(2)})`);
        if ((b.vx > 0 && b.x > W + 140) || (b.vx < 0 && b.x < -140)) {
          b.g.remove();
          flying.splice(i, 1);
        }
      }
    },
    calm() {
      for (const b of flying.splice(0)) b.g.remove();
    },
  };
}
