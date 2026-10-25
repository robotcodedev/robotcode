// Spiders and webs: a web in a corner of the hero with a spider hanging from it, a web in a corner of the first band
// with a spider resting in it, and robot spiders walking over the page with legs that step like a spider's. The robot
// spider's head is the Robot Framework face. Everything is drawn in body units facing +x. Now and then a spider asks
// for a poke (invite.ts).
import { invitations, type Speaker, type Speakers } from "./invite";
import { patter, pop, scurry } from "./sound";
import { clamp, el, put, rand, RF_FACE, treat, windowLayer, world, type Part } from "./world";

// the face's top points to the rear, so that it reads upright on the spider hanging head down
const BODY = `
  <ellipse cx="-16" cy="0" rx="13" ry="10.5" fill="url(#rc-hw-shell)" stroke="var(--hw-shell-rim)" stroke-width="0.9"/>
  <path d="M-26 -5.5 Q-16 -9 -6.5 -5.5 M-26 5.5 Q-16 9 -6.5 5.5" fill="none" stroke="var(--hw-shell-line)" stroke-width="0.8"/>
  <circle class="rc-hw-led" cx="-21" cy="0" r="2.1" fill="var(--hw-led)"/>
  <circle cx="-1.5" cy="0" r="3.2" fill="var(--hw-joint)"/>
  <g transform="matrix(0 -0.95 0.95 0 -1.4 11.4)">
    <path d="M6.6 2.68 H17.4 L21.32 6.6 V17.4 L17.4 21.32 H6.6 L2.68 17.4 V6.6 Z" fill="var(--hw-face)" stroke="var(--hw-shell-rim)" stroke-width="1" stroke-linejoin="round"/>
    <path fill="var(--hw-face-ink)" d="${RF_FACE}"/>
  </g>`;

// hips and resting feet of the right side, front to back; the legs leave the head at these angles from the walking
// direction and spread out radially (the left side mirrors y)
const LEG_ANGLES = [34, 74, 112, 148];
const rad = (d: number) => (d * Math.PI) / 180;
const HIPS = LEG_ANGLES.map((a) => [9 + 6 * Math.cos(rad(a)), 6 * Math.sin(rad(a))]);
const FEET = LEG_ANGLES.map((a) => [9 + 32 * Math.cos(rad(a)), 32 * Math.sin(rad(a))]);
const UPPER = 14, LOWER = 15, LEG_WIDTH = 2.2;

// the knee of a two-segment leg from hip h to foot f, bent towards the outward direction (ox, oy)
function knee(hx: number, hy: number, fx: number, fy: number, l1: number, l2: number, ox: number, oy: number) {
  const dx = fx - hx, dy = fy - hy;
  let d = Math.hypot(dx, dy);
  const max = l1 + l2 - 0.01;
  if (d > max) {
    fx = hx + (dx / d) * max;
    fy = hy + (dy / d) * max;
    d = max;
  }
  d = Math.max(d, 0.01);
  const a = Math.atan2(fy - hy, fx - hx);
  const b = Math.acos(clamp((l1 * l1 + d * d - l2 * l2) / (2 * l1 * d), -1, 1));
  const k1 = [hx + l1 * Math.cos(a + b), hy + l1 * Math.sin(a + b)];
  const k2 = [hx + l1 * Math.cos(a - b), hy + l1 * Math.sin(a - b)];
  const out1 = (k1[0] - hx) * ox + (k1[1] - hy) * oy, out2 = (k2[0] - hx) * ox + (k2[1] - hy) * oy;
  const k = out1 >= out2 ? k1 : k2;
  return [k[0], k[1], fx, fy];
}

interface LegParts {
  rim: SVGPathElement;
  upper: SVGPathElement;
  lower: SVGPathElement;
  knees: SVGPathElement;
  kneeRadius: number;
}

// the legs of a spider in four shapes, however many legs: an outline for dark backgrounds, the thicker upper segments,
// the thinner lower ones and the knee joints; a walking spider so changes four shapes in a picture, not 32
function legParts(parent: Element, scale: number): LegParts {
  const w = LEG_WIDTH * scale;
  const style = { fill: "none", "stroke-linecap": "round", "stroke-linejoin": "round" };
  return {
    rim: el("path", { ...style, stroke: "var(--hw-leg-rim)", "stroke-width": w + 1.6 * scale }, parent),
    upper: el("path", { ...style, stroke: "var(--hw-leg)", "stroke-width": w }, parent),
    lower: el("path", { ...style, stroke: "var(--hw-leg)", "stroke-width": w * 0.68 }, parent),
    knees: el("path", { fill: "var(--hw-knee)" }, parent),
    kneeRadius: 1.6 * scale,
  };
}

// every leg as [hip x, hip y, knee x, knee y, foot x, foot y]
function drawLegs(p: LegParts, legs: number[][]) {
  const r = p.kneeRadius.toFixed(1), d = (p.kneeRadius * 2).toFixed(1);
  let rim = "", upper = "", lower = "", knees = "";
  for (const [hx, hy, kx, ky, fx, fy] of legs) {
    const h = `${hx.toFixed(1)} ${hy.toFixed(1)}`, k = `${kx.toFixed(1)} ${ky.toFixed(1)}`;
    const f = `${fx.toFixed(1)} ${fy.toFixed(1)}`;
    rim += `M${h} L${k} L${f}`;
    upper += `M${h} L${k}`;
    lower += `M${k} L${f}`;
    knees += `M${(kx - p.kneeRadius).toFixed(1)} ${ky.toFixed(1)} a${r} ${r} 0 1 0 ${d} 0 a${r} ${r} 0 1 0 -${d} 0`;
  }
  put(p.rim, "d", rim);
  put(p.upper, "d", upper);
  put(p.lower, "d", lower);
  put(p.knees, "d", knees);
}

interface SwingLeg {
  g: SVGGElement;
  hx: number;
  hy: number;
  grp: number;
}

// legs that swing around their hips, for spiders that hang or rest; `curl` pulls the feet in
function swingLegs(group: Element, curl: number): SwingLeg[] {
  const legs: SwingLeg[] = [];
  for (let i = 0; i < 4; i++) {
    for (const s of [-1, 1]) {
      const g = el("g", {}, group);
      const hx = HIPS[i][0], hy = HIPS[i][1] * s;
      const fx = hx + (FEET[i][0] - hx) * curl, fy = hy + (FEET[i][1] * s - hy) * curl;
      const [kx, ky, gx, gy] = knee(hx, hy, fx, fy, UPPER, LOWER, 0, s);
      drawLegs(legParts(g, 1), [[hx, hy, kx, ky, gx, gy]]);
      legs.push({ g, hx, hy, grp: (i + (s > 0 ? 1 : 0)) % 2 });
    }
  }
  return legs;
}

function swing(legs: SwingLeg[], phase: number, amp: number) {
  for (const l of legs) {
    const a = amp * Math.sin(phase + (l.grp ? Math.PI : 0));
    put(l.g, "transform", `rotate(${a.toFixed(1)} ${l.hx.toFixed(1)} ${l.hy.toFixed(1)})`);
  }
}

// a spider of hanging or resting kind: its legs, its body and the circle that takes clicks
function stillSpider(parent: Element, curl: number) {
  const g = el("g", {}, parent);
  const legs = swingLegs(el("g", {}, g), curl);
  el("g", {}, g).innerHTML = BODY;
  const hit = el("circle", { class: "rc-hw-hit", cx: -4, cy: 0, r: 30 }, g);
  return { g, legs, hit };
}

export interface Web {
  svg: SVGSVGElement;
  g: SVGGElement;
  at(spoke: number, ring: number): [number, number];
}

// a web in a corner of `host`, spreading from the corner over a quarter circle
export function createWeb(host: HTMLElement, corner: "top-right" | "bottom-left" | "top-left", size: number): Web {
  const right = corner === "top-right";
  const bottom = corner === "bottom-left";
  host.classList.add("rc-hw-web-host");
  const svg = el("svg", {
    class: `rc-halloween rc-hw-web rc-hw-web-${corner}`,
    viewBox: `0 0 ${size} ${size * (bottom ? 1 : 1.47)}`,
    "aria-hidden": "true",
  });
  host.appendChild(svg);
  const ox = right ? size : 0, oy = bottom ? size : 0;
  const a0 = right ? Math.PI / 2 : bottom ? -Math.PI / 2 : 0;
  const spokes: { a: number; len: number }[] = [];
  const count = size > 260 ? 7 : 6, rings = size > 260 ? 9 : 7, r = size * (bottom ? 0.91 : 0.78);
  const g = el("g", {}, svg);
  for (let i = 0; i < count; i++) {
    const edge = i === 0 || i === count - 1;
    const a = a0 + ((Math.PI / 2) * i) / (count - 1) + (edge ? 0 : rand(-0.05, 0.05));
    const len = r * (edge ? 1 : rand(0.86, 1));
    spokes.push({ a, len });
    el("path", { class: "rc-hw-strand", d: `M${ox} ${oy} L${(ox + Math.cos(a) * len).toFixed(1)} ${(oy + Math.sin(a) * len).toFixed(1)}` }, g);
  }
  const point = (sp: { a: number; len: number }, d: number): [number, number] => [
    ox + Math.cos(sp.a) * Math.min(d, sp.len),
    oy + Math.sin(sp.a) * Math.min(d, sp.len),
  ];
  const radii: number[] = [];
  for (let j = 1; j <= rings; j++) {
    const d = r * Math.pow(j / rings, 1.08) * 0.97;
    radii.push(d);
    const [sx, sy] = point(spokes[0], d);
    let path = `M${sx.toFixed(1)} ${sy.toFixed(1)}`;
    for (let i = 1; i < spokes.length; i++) {
      const [ex, ey] = point(spokes[i], d * rand(0.97, 1.03));
      const am = (spokes[i - 1].a + spokes[i].a) / 2;
      path += ` Q${(ox + Math.cos(am) * d * 0.88).toFixed(1)} ${(oy + Math.sin(am) * d * 0.88).toFixed(1)} ${ex.toFixed(1)} ${ey.toFixed(1)}`;
    }
    el("path", { class: "rc-hw-strand", d: path }, g);
  }
  return { svg, g, at: (i, j) => point(spokes[i], radii[j]) };
}

// the spider on its thread below the hero web: it climbs up when the pointer comes near and drops on a click
function hangingSpider(web: Web, origin: [number, number]): Part & { speakers: Speakers } {
  const [ax, ay] = web.at(3, 4);
  const thread = el("line", { class: "rc-hw-thread", x1: ax, y1: ay, x2: ax, y2: ay + 170 }, web.svg);
  const spider = stillSpider(web.svg, 0.82);
  const s = { L: 170, Lt: 170, vL: 0, th: 0.12, vth: 0, nearAt: -1e9, phase: 0 };
  const poke = (e: PointerEvent) => {
    s.vL += 650;
    s.nearAt = -1e9;
    scurry(4);
    treat(e.clientX, e.clientY);
  };
  spider.hit.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    poke(e);
  });
  // it may always ask, and keeps climbing up when the pointer comes near
  const speaker: Speaker = { box: () => spider.hit.getBoundingClientRect(), hold() {}, poke };
  return {
    speakers: () => [speaker],
    update(dt, now) {
      const m = web.svg.getScreenCTM();
      const ex = ax + Math.sin(s.th) * s.L, ey = ay + Math.cos(s.th) * s.L;
      if (world.pointer && m) {
        const p = new DOMPoint(ex, ey + 20).matrixTransform(m);
        if (Math.hypot(world.pointer.x - p.x, world.pointer.y - p.y) < 110) s.nearAt = now;
      }
      if (dt === 0) {
        Object.assign(s, { L: 170, th: 0, vL: 0, vth: 0 });
      } else {
        s.Lt = now - s.nearAt < 1400 ? 34 : 170;
        s.vL += (40 * (s.Lt - s.L) - 7 * s.vL) * dt;
        s.L = clamp(s.L + s.vL * dt, 20, 330);
        if (Math.random() < dt * 0.12) s.vth += rand(-0.25, 0.25);
        s.vth += (-(900 / Math.max(s.L, 25)) * Math.sin(s.th) - 0.7 * s.vth + world.wind.v * 2.4) * dt;
        s.th = clamp(s.th + s.vth * dt, -0.9, 0.9);
      }
      const climbing = Math.abs(s.vL) > 25;
      s.phase += dt * (climbing ? 16 : 2.2);
      // the legs move while it climbs or swings, and rest while it hangs quietly
      swing(spider.legs, s.phase, dt === 0 ? 0 : climbing ? 14 : Math.abs(s.vth) > 0.05 ? 3 : 0);
      const tx = ax + Math.sin(s.th) * s.L, ty = ay + Math.cos(s.th) * s.L;
      const dir = Math.atan2(Math.cos(s.th), Math.sin(s.th));
      const cx = tx + Math.cos(dir) * 28, cy = ty + Math.sin(dir) * 28;
      put(thread, "x2", tx.toFixed(1));
      put(thread, "y2", ty.toFixed(1));
      put(spider.g, "transform", `translate(${cx.toFixed(1)} ${cy.toFixed(1)}) rotate(${((dir * 180) / Math.PI).toFixed(1)})`);
      // the gust shakes the web
      const wobble = world.wind.v * Math.sin(now / 105) * 1.5;
      put(web.g, "transform", `rotate(${wobble.toFixed(1)} ${origin[0]} ${origin[1]})`);
    },
  };
}

// the spider resting in the band web: on a click it hides in the corner and comes back after a few seconds
function restingSpider(web: Web, origin: [number, number]): Part & { speakers: Speakers } {
  const [nx, ny] = web.at(2, 3);
  const spider = stillSpider(web.svg, 0.9);
  const s = { t: 0, mode: "sit" as "sit" | "hide" | "away" | "back", until: 0, phase: 0, twitch: 0 };
  const poke = (e: PointerEvent) => {
    if (s.mode !== "sit") return;
    // with reduced motion the spider stays where it is
    if (!world.reduced()) s.mode = "hide";
    scurry();
    treat(e.clientX, e.clientY);
  };
  spider.hit.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    poke(e);
  });
  const speaker: Speaker = { box: () => spider.hit.getBoundingClientRect(), hold() {}, poke };
  return {
    // it asks only while it sits in its web
    speakers: () => (s.mode === "sit" ? [speaker] : []),
    update(dt, now) {
      const speed = dt === 0 ? 100 : 2.6;
      const step = dt === 0 ? 1 : dt;
      if (s.mode === "hide") {
        s.t = Math.min(1, s.t + step * speed);
        if (s.t >= 1) {
          s.mode = "away";
          s.until = now + 4000;
        }
      } else if (s.mode === "away") {
        if (now > s.until) s.mode = "back";
      } else if (s.mode === "back") {
        s.t = Math.max(0, s.t - step * speed * 0.45);
        if (s.t <= 0) s.mode = "sit";
      }
      const e = s.t * s.t * (3 - 2 * s.t);
      const x = nx + (origin[0] + 6 - nx) * e, y = ny + (origin[1] - 6 - ny) * e;
      const moving = s.mode === "hide" || s.mode === "back";
      if (!moving && dt > 0 && Math.random() < dt * 0.25) s.twitch = 0.5;
      s.twitch = Math.max(0, s.twitch - dt);
      s.phase += dt * (moving ? 18 : 9);
      swing(spider.legs, s.phase, dt === 0 ? 0 : moving ? 15 : s.twitch > 0 ? 6 : 0);
      put(spider.g, "transform", `translate(${x.toFixed(1)} ${y.toFixed(1)}) rotate(${s.mode === "hide" ? 135 : -45}) scale(${(0.8 - 0.35 * e).toFixed(3)})`);
      put(spider.g, "opacity", (1 - 0.85 * e).toFixed(2));
      const wobble = -world.wind.v * Math.sin(now / 105) * 1.2;
      put(web.g, "transform", `rotate(${wobble.toFixed(1)} ${origin[0]} ${origin[1]})`);
    },
  };
}

interface Leg {
  i: number;
  s: number;
  grp: number;
  fx: number;
  fy: number;
  lift: number;
  st: { fx: number; fy: number; t: number; d: number } | null;
}

// a robot spider walking over the page: each foot stays planted until the body has moved too far, then four legs step
// at once while the other four hold
class Walker {
  k = innerWidth < 600 ? 0.8 : 1.1;
  seed = Math.random() * 100;
  x: number;
  y: number;
  tx = 0;
  ty = 0;
  h: number;
  speed = 0;
  vx = 0;
  vy = 0;
  base = rand(42, 64);
  pause = 0;
  freeze = 0;
  burst = 0;
  fleeing = false;
  fleeSpeed = 340;
  sinceTap = 0;
  gone = false;
  // held still while it asks for a poke
  held = false;
  g: SVGGElement;
  body: SVGGElement;
  legs: Leg[] = [];
  lines: LegParts;
  speaker: Speaker;

  // `hatch`: a hatchling of the egg sac, small, that runs off from where it hatched in the direction `angle`
  constructor(layer: SVGSVGElement, hatch?: { x: number; y: number; angle: number }) {
    const W = innerWidth, H = innerHeight;
    if (hatch) {
      this.k *= 0.45;
      this.x = hatch.x;
      this.y = hatch.y;
      this.fleeing = true;
      this.fleeSpeed = rand(150, 230);
      this.tx = hatch.x + Math.cos(hatch.angle) * 3000;
      this.ty = hatch.y + Math.sin(hatch.angle) * 3000;
    } else {
      const side = Math.floor(Math.random() * 4);
      this.x = side === 0 ? -60 : side === 1 ? W + 60 : rand(80, W - 80);
      this.y = side === 2 ? -60 : side === 3 ? H + 60 : rand(120, H - 80);
      this.pickTarget();
    }
    this.h = Math.atan2(this.ty - this.y, this.tx - this.x);
    this.g = el("g", {}, layer);
    const legsG = el("g", {}, this.g);
    this.lines = legParts(legsG, this.k);
    this.body = el("g", {}, this.g);
    el("g", {}, this.body).innerHTML = BODY;
    const hit = el("circle", { class: "rc-hw-hit", cx: -4, cy: 0, r: 30 }, this.body);
    hit.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      this.flee(e);
    });
    this.speaker = { box: () => hit.getBoundingClientRect(), hold: (on) => (this.held = on), poke: (e) => this.flee(e) };
    for (let i = 0; i < 4; i++) {
      for (const s of [-1, 1]) {
        const leg: Leg = { i, s, grp: (i + (s > 0 ? 1 : 0)) % 2, fx: 0, fy: 0, lift: 0, st: null };
        [leg.fx, leg.fy] = this.ideal(leg, 0);
        this.legs.push(leg);
      }
    }
  }

  toWorld(lx: number, ly: number): [number, number] {
    const c = Math.cos(this.h), s = Math.sin(this.h);
    return [this.x + this.k * (lx * c - ly * s), this.y + this.k * (lx * s + ly * c)];
  }

  ideal(leg: Leg, lead: number): [number, number] {
    const [x, y] = this.toWorld(FEET[leg.i][0], FEET[leg.i][1] * leg.s);
    return [x + this.vx * lead, y + this.vy * lead];
  }

  pickTarget() {
    const W = innerWidth, H = innerHeight;
    for (let n = 0; n < 8; n++) {
      this.tx = rand(60, Math.max(61, W - 60));
      this.ty = rand(90, Math.max(91, H - 60));
      if (Math.hypot(this.tx - this.x, this.ty - this.y) > 160) break;
    }
  }

  flee(e: PointerEvent) {
    if (this.fleeing) return;
    this.fleeing = true;
    const dx = this.x - e.clientX, dy = this.y - e.clientY;
    const d = Math.hypot(dx, dy) || 1;
    this.tx = this.x + (dx / d) * 3000;
    this.ty = this.y + (dy / d) * 3000;
    scurry();
    treat(e.clientX, e.clientY);
  }

  update(dt: number, now: number) {
    const W = innerWidth, H = innerHeight;
    const p = world.pointer;
    if (!this.fleeing && p && Math.hypot(p.x - this.x, p.y - this.y) < 80 * this.k) {
      this.freeze = Math.max(this.freeze, rand(0.8, 1.6));
    }
    if (this.held && !this.fleeing) this.freeze = Math.max(this.freeze, 0.3);
    let target = 0;
    if (this.fleeing) target = this.fleeSpeed;
    else if (this.freeze > 0) this.freeze -= dt;
    else if (this.pause > 0) {
      this.pause -= dt;
      if (this.pause <= 0) this.pickTarget();
    } else if (Math.hypot(this.tx - this.x, this.ty - this.y) < 16) {
      this.pause = Math.random() < 0.65 ? rand(0.5, 2.6) : 0;
      if (this.pause <= 0) this.pickTarget();
    } else {
      if (this.burst <= 0 && Math.random() < dt * 0.15) this.burst = rand(0.3, 0.7);
      target = this.base * (this.burst > 0 ? 2.3 : 1);
    }
    this.burst -= dt;
    this.speed += (target - this.speed) * Math.min(1, dt * 7);
    const want = Math.atan2(this.ty - this.y, this.tx - this.x);
    const diff = Math.atan2(Math.sin(want - this.h), Math.cos(want - this.h));
    const turn = (this.fleeing ? 10 : 3) * dt;
    if (target > 0) this.h += clamp(diff, -turn, turn) + Math.sin(now / 700 + this.seed) * 0.25 * dt;
    this.vx = Math.cos(this.h) * this.speed;
    this.vy = Math.sin(this.h) * this.speed;
    this.x += this.vx * dt;
    this.y += this.vy * dt;
    if (!this.fleeing && (this.tx < 0 || this.tx > W || this.ty < 0 || this.ty > H)) this.pickTarget();
    if (this.fleeing && (this.x < -140 || this.x > W + 140 || this.y < -140 || this.y > H + 140)) {
      this.g.remove();
      this.gone = true;
      return;
    }
    this.step(dt);
    this.render();
  }

  step(dt: number) {
    const thr = (this.fleeing ? 7 : 8) * this.k;
    const dur = this.fleeing ? 0.055 : Math.max(0.07, 0.15 - this.speed / 1200);
    const busy = [0, 0];
    let landed = false;
    for (const l of this.legs) if (l.st) busy[l.grp] += 1;
    for (const l of this.legs) {
      const [ix, iy] = this.ideal(l, 0.08);
      if (l.st) {
        l.st.t += dt / l.st.d;
        const t = Math.min(1, l.st.t);
        const e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
        l.fx = l.st.fx + (ix - l.st.fx) * e;
        l.fy = l.st.fy + (iy - l.st.fy) * e;
        l.lift = Math.sin(Math.PI * t);
        if (t >= 1) {
          l.st = null;
          l.lift = 0;
          busy[l.grp] -= 1;
          landed = true;
        }
      } else if (Math.hypot(ix - l.fx, iy - l.fy) > thr && busy[1 - l.grp] === 0) {
        l.st = { fx: l.fx, fy: l.fy, t: 0, d: dur };
        busy[l.grp] += 1;
      }
    }
    // feet set down patter, while the spider is in the window
    this.sinceTap += dt;
    if (landed && this.sinceTap > 0.09 && this.x > 0 && this.x < innerWidth && this.y > 0 && this.y < innerHeight) {
      this.sinceTap = 0;
      patter(this.x / innerWidth, this.k < 0.6);
    }
  }

  render() {
    put(this.body, "transform", `translate(${this.x.toFixed(1)} ${this.y.toFixed(1)}) rotate(${((this.h * 180) / Math.PI).toFixed(1)}) scale(${this.k})`);
    const sin = Math.sin(this.h), cos = Math.cos(this.h);
    drawLegs(
      this.lines,
      this.legs.map((l) => {
        const [hx, hy] = this.toWorld(HIPS[l.i][0], HIPS[l.i][1] * l.s);
        return [hx, hy, ...knee(hx, hy, l.fx, l.fy, UPPER * this.k * (1 + 0.14 * l.lift), LOWER * this.k, -l.s * sin, l.s * cos)];
      }),
    );
  }
}

// the walking spiders of the page: two (one on narrow screens), and a spider that ran off comes back later
function walkers(): Part & { speakers: Speakers } {
  const layer = windowLayer("rc-hw-layer");
  const list: Walker[] = [];
  const due: number[] = [];
  const wanted = innerWidth < 600 ? 1 : 2;
  const start = performance.now();
  for (let i = 0; i < wanted; i++) due.push(start + 500 + i * 1100);
  const fromMiddle = (w: Walker) => Math.hypot(w.x - innerWidth / 2, w.y - innerHeight / 2);
  return {
    // the spiders that walk, not those running off, the one nearest the middle of the window first
    speakers: () =>
      list
        .filter((w) => !w.fleeing)
        .sort((a, b) => fromMiddle(a) - fromMiddle(b))
        .map((w) => w.speaker),
    update(dt, now) {
      for (let i = due.length - 1; i >= 0; i--) {
        if (now >= due[i] && list.length < 3) {
          list.push(new Walker(layer));
          due.splice(i, 1);
        }
      }
      for (const w of list.slice()) {
        w.update(dt, now);
        if (w.gone) {
          list.splice(list.indexOf(w), 1);
          due.push(now + rand(6000, 9000));
        }
      }
    },
    calm() {
      // with reduced motion nothing walks; the spiders that walked come back when motion is allowed again
      for (const w of list.splice(0)) {
        w.g.remove();
        due.push(performance.now() + rand(500, 1600));
      }
    },
  };
}

const SAC = `
  <g class="rc-hw-sac-sway">
    <line class="rc-hw-thread" x1="0" y1="0" x2="0" y2="8"/>
    <g class="rc-hw-sac-body">
      <ellipse cx="0" cy="21" rx="10" ry="13.5" fill="var(--hw-sac)" stroke="var(--hw-sac-line)" stroke-width="0.8"/>
      <path d="M-9 15 Q0 22 9 14 M-10 22 Q0 29 10 21 M-7 29 Q0 35 7 29 M-4 9 Q2 21 -3 34 M4 9 Q8 21 3 34"
        fill="none" stroke="var(--hw-sac-line)" stroke-width="0.6"/>
      <ellipse cx="-3.5" cy="15" rx="2.6" ry="4.5" fill="rgb(255 255 255 / 45%)"/>
    </g>
  </g>`;

// the egg sac hanging from the top strand of the hero web: something stirs in it now and then; a click bursts it, three
// to five small spiders scatter from it and run off the page, and it grows again within half a minute
function eggSac(web: Web): Part {
  const [ax, ay] = web.at(6, 4);
  const g = el("g", { transform: `translate(${ax.toFixed(1)} ${ay.toFixed(1)})` }, web.g);
  g.innerHTML = SAC;
  const sway = g.querySelector<SVGGElement>(".rc-hw-sac-sway")!;
  const body = g.querySelector<SVGGElement>(".rc-hw-sac-body")!;
  const hit = el("circle", { class: "rc-hw-hit", cx: 0, cy: 21, r: 18 }, g);
  const layer = windowLayer("rc-hw-layer");
  const hatchlings: Walker[] = [];
  const s = { grow: 1, pop: 0, regrow: 25, twitch: 0, stir: performance.now() + rand(3000, 7000), t: 0 };
  hit.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    if (world.reduced()) return;
    if (s.grow < 1) {
      s.twitch = 0.5;
      return;
    }
    const m = g.getScreenCTM();
    if (!m) return;
    const c = new DOMPoint(0, 21).matrixTransform(m);
    // they scatter downwards and to the left, away from the corner, each in its own share of the fan
    const n = 3 + Math.floor(Math.random() * 3);
    for (let i = 0; i < n; i++) {
      const angle = ((75 + (110 * (i + rand(0.2, 0.8))) / n) * Math.PI) / 180;
      hatchlings.push(new Walker(layer, { x: c.x + rand(-4, 4), y: c.y + rand(-4, 4), angle }));
    }
    s.grow = 0;
    s.pop = 1;
    s.regrow = rand(20, 30);
    pop();
  });
  return {
    update(dt, now) {
      for (const h of hatchlings.slice()) {
        h.update(dt, now);
        if (h.gone) hatchlings.splice(hatchlings.indexOf(h), 1);
      }
      if (dt === 0) {
        sway.removeAttribute("transform");
        body.removeAttribute("transform");
        body.style.opacity = "";
        return;
      }
      s.t += dt;
      if (s.pop > 0) s.pop = Math.max(0, s.pop - dt / 0.25);
      else if (s.grow < 1) s.grow = Math.min(1, s.grow + dt / s.regrow);
      if (s.grow >= 1 && now >= s.stir) {
        s.twitch = 0.5;
        s.stir = now + rand(3000, 7000);
      }
      s.twitch = Math.max(0, s.twitch - dt);
      // bursting, it swells and fades; growing again, it starts small and pale below its thread
      const grown = s.grow * s.grow * (3 - 2 * s.grow);
      const scale = s.pop > 0 ? 1 + 0.3 * (1 - s.pop) : 0.2 + 0.8 * grown;
      const angle = Math.sin(s.t * 42) * 7 * s.twitch - world.wind.v * 6;
      put(sway, "transform", `rotate(${angle.toFixed(1)})`);
      put(body, "transform", `translate(0 8) scale(${scale.toFixed(2)}) translate(0 -8)`);
      put(body, "opacity", (s.pop > 0 ? s.pop : 0.3 + 0.7 * grown).toFixed(2));
    },
    calm() {
      for (const h of hatchlings.splice(0)) h.g.remove();
      s.twitch = 0;
    },
  };
}

// the web in the top right corner of the window with the hanging spider and the egg sac, held by `corner` (the hero,
// or a layer over the top of a news page), the web of a band with the resting spider, the walking spiders, and their
// invitation to a poke
export function spiders(corner: HTMLElement | null, band: HTMLElement | null): Part[] {
  const parts: Part[] = [];
  // the kinds of spiders in the order they take turns to ask for a poke
  const kinds: Speakers[] = [];
  if (corner) {
    const web = createWeb(corner, "top-right", 320);
    // the web hangs in the top right corner of the window, below the header, whatever the width of the window
    const pin = () => {
      const r = corner.getBoundingClientRect();
      const header = document.querySelector<HTMLElement>(".header")?.offsetHeight ?? 0;
      web.svg.style.right = `${(r.right - document.documentElement.clientWidth).toFixed(0)}px`;
      web.svg.style.top = `${(header - r.top - scrollY).toFixed(0)}px`;
    };
    pin();
    new ResizeObserver(pin).observe(document.documentElement);
    const hanging = hangingSpider(web, [320, 0]);
    parts.push(hanging, eggSac(web));
    kinds.push(hanging.speakers);
  }
  if (band) {
    const resting = restingSpider(createWeb(band, "bottom-left", 230), [0, 230]);
    parts.push(resting);
    kinds.push(resting.speakers);
  }
  const walking = walkers();
  kinds.push(walking.speakers);
  parts.push(walking, invitations(kinds));
  return parts;
}
