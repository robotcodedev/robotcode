// Halloween weather: fog drifting along the bottom of the window, the moon behind the hero's gallery picture with clouds
// passing in front of it, gusts of wind that blow leaves across the page (the other parts read `world.wind`), far
// lightning behind the moon, at most two soft pulses with a far rumble, and now and then a lightning bolt with thunder.
import { thunder } from "./sound";
import { el, rand, windowLayer, world, type Part } from "./world";

// a soft, horizontally tileable fog texture from blurred blobs, used as a mask over the fog color
function fogTexture(w: number, h: number, blobs: number): string {
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const g = canvas.getContext("2d")!;
  for (let i = 0; i < blobs; i++) {
    const x = Math.random() * w, y = h * (0.3 + 0.7 * Math.random());
    const r = rand(h * 0.16, h * 0.42), a = rand(0.07, 0.2), sx = rand(1.6, 2.8);
    for (const dx of [-w, 0, w]) {
      g.save();
      g.translate(x + dx, y);
      g.scale(sx, 1);
      const grd = g.createRadialGradient(0, 0, 0, 0, 0, r);
      grd.addColorStop(0, `rgba(255,255,255,${a})`);
      grd.addColorStop(1, "rgba(255,255,255,0)");
      g.fillStyle = grd;
      g.beginPath();
      g.arc(0, 0, r, 0, Math.PI * 2);
      g.fill();
      g.restore();
    }
  }
  return `url(${canvas.toDataURL()})`;
}

// the fog of every decorated page: a faint layer over the lower part of the window and a thin one at its bottom edge;
// it drifts sideways and billows, every texture swelling and sinking, thickening and thinning slowly in its own time.
// All of it runs as CSS animations of transforms and opacity, which the compositor plays without the script and without
// painting the masked fog again; the script only sizes the textures.
export function fog(): Part {
  const layers: { box: HTMLElement; texture: HTMLElement; w: number; speed: number }[] = [];
  for (const [kind, textures] of [
    ["back", [[1500, 9], [1100, -5]]],
    ["front", [[900, 15]]],
  ] as const) {
    const container = document.createElement("div");
    container.className = `rc-halloween rc-hw-fog rc-hw-fog-${kind}`;
    container.setAttribute("aria-hidden", "true");
    for (const [w, speed] of textures) {
      const wave = document.createElement("div");
      wave.className = "rc-hw-fog-wave";
      wave.style.animationDuration = `${rand(22, 38).toFixed(1)}s, ${rand(15, 27).toFixed(1)}s`;
      wave.style.animationDelay = `-${rand(0, 38).toFixed(1)}s, -${rand(0, 27).toFixed(1)}s`;
      const texture = document.createElement("div");
      texture.className = "rc-hw-fog-texture";
      const url = fogTexture(w, 260, 48);
      texture.style.maskImage = url;
      texture.style.setProperty("-webkit-mask-image", url);
      wave.appendChild(texture);
      container.appendChild(wave);
      layers.push({ box: container, texture, w, speed });
    }
    document.body.appendChild(container);
  }
  // A texture is a tile wider than the window and slides by one tile and back (`--tile`); a tile is as wide as the
  // texture at the height of its layer, so the jump back does not show.
  function measure() {
    for (const f of layers) {
      const tile = Math.max(1, (f.w * f.box.clientHeight) / 260);
      f.texture.style.width = `${Math.ceil(innerWidth + tile)}px`;
      f.texture.style.setProperty("--tile", `${tile.toFixed(1)}px`);
      f.texture.style.animationDuration = `${(tile / Math.abs(f.speed)).toFixed(1)}s`;
      f.texture.style.animationDirection = f.speed > 0 ? "normal" : "reverse";
    }
  }
  measure();
  addEventListener("resize", measure);
  return { update() {} };
}

// the moon with clouds passing it, and the lightning in the sky around it, in a box at the start of `host`: around the
// hero's gallery picture (`hero`) or along the top of a page (`page`); `moon` gives the place of the moon's top left
// corner in the window. The sky spans the width of the window, so that nothing of it ends at an edge inside the page.
function sky(host: HTMLElement, kind: "hero" | "page", moonAt: () => { x: number; y: number } | null): Part {
  if (getComputedStyle(host).position === "static") host.style.position = "relative";
  const box = document.createElement("div");
  box.className = `rc-halloween rc-hw-sky rc-hw-sky-${kind}`;
  box.setAttribute("aria-hidden", "true");
  // a cloud for about every 480 pixels of the window, the first two near the moon as before
  const count = Math.max(2, Math.round(document.documentElement.clientWidth / 480));
  box.innerHTML =
    '<div class="rc-hw-flash"></div><div class="rc-hw-flash rc-hw-flash-strong"></div><div class="rc-hw-moon"></div>' +
    '<svg class="rc-hw-bolt"></svg>' +
    '<div class="rc-hw-cloud"></div>'.repeat(count);
  host.prepend(box);
  const moon = box.querySelector<HTMLElement>(".rc-hw-moon")!;
  const [flash, strong] = box.querySelectorAll<HTMLElement>(".rc-hw-flash");
  const bolt = box.querySelector<SVGSVGElement>(".rc-hw-bolt")!;
  const clouds = [...box.querySelectorAll<HTMLElement>(".rc-hw-cloud")].map((element, i) => ({
    element, y: i % 2 ? 0 : 26, speed: i % 2 ? 11 : 7, px: null as number | null,
  }));
  let next = performance.now() + rand(6000, 10000);
  let nextBolt = performance.now() + rand(20000, 30000);
  let cloudTime = 0;
  let moonX = 0;

  // the sky from the left to the right edge of the window, with the moon in its place and the lightning around it
  function place() {
    const h = host.getBoundingClientRect();
    box.style.left = `${(-h.left).toFixed(0)}px`;
    box.style.width = `${document.documentElement.clientWidth}px`;
    const m = moonAt(), b = box.getBoundingClientRect();
    if (!m) return;
    moonX = m.x - b.left;
    const moonY = m.y - b.top;
    moon.style.left = `${moonX.toFixed(0)}px`;
    moon.style.top = `${moonY.toFixed(0)}px`;
    for (const f of [flash, strong]) {
      f.style.left = `${(moonX + moon.offsetWidth / 2).toFixed(0)}px`;
      f.style.top = `${(moonY + moon.offsetWidth / 2).toFixed(0)}px`;
    }
  }
  place();
  new ResizeObserver(place).observe(document.documentElement);

  function moveClouds(dt: number) {
    const W = box.clientWidth;
    const span = W + 360;
    clouds.forEach((c, i) => {
      if (c.px === null) {
        const x = i === 1 ? moonX - 50 : moonX + 220 + (Math.max(0, i - 1) * span) / clouds.length;
        c.px = ((((x + 320) % span) + span) % span) - 320;
      }
      c.px += (-c.speed + world.wind.v * 45) * dt;
      if (c.px < -320) c.px = W + 40;
      if (c.px > W + 60) c.px = -300;
      c.element.style.transform = `translate(${c.px.toFixed(1)}px, ${c.y}px)`;
    });
  }
  moveClouds(0);

  // a jagged line from (x, y) down to `bottom`, drifting sideways by `drift` steps per step
  function zigzag(x: number, y: number, bottom: number, step: number, drift: number): [number, number][] {
    const points: [number, number][] = [[x, y]];
    while (y < bottom) {
      y += rand(step * 0.6, step * 1.4);
      x += (drift + rand(-0.9, 0.9)) * step;
      points.push([x, y]);
    }
    return points;
  }
  const path = (points: [number, number][]) => "M" + points.map(([x, y]) => `${x.toFixed(0)} ${y.toFixed(0)}`).join(" L");

  // a lightning bolt with a branch somewhere in the sky, with the strong flash and, a moment later, thunder; in the hero
  // it starts at the top of the hero, which on narrow screens lies far above the sky box around the picture, and it is
  // at least 420 pixels long, also below the shallow sky at the top of a page
  function strike() {
    const W = box.clientWidth, H = Math.max(box.clientHeight, 420), drift = rand(-0.3, 0.3);
    const hero = host.closest(".rc-hero")?.getBoundingClientRect();
    const top = Math.min(0, (hero?.top ?? 0) - box.getBoundingClientRect().top) + rand(0, 30);
    const main = zigzag(rand(0.12, 0.88) * W, top, rand(0.65, 0.9) * H, 22, drift);
    const [bx, by] = main[Math.floor(main.length * rand(0.3, 0.55))];
    const branch = zigzag(bx, by, by + rand(0.25, 0.4) * H, 16, drift + (Math.random() < 0.5 ? -0.8 : 0.8));
    bolt.innerHTML = `<path d="${path(main)}"/><path class="rc-hw-branch" d="${path(branch)}"/>`;
    const pulses = [{ opacity: 0 }, { opacity: 1, offset: 0.04 }, { opacity: 0.15, offset: 0.14 }, { opacity: 1, offset: 0.22 }, { opacity: 0 }];
    bolt.animate(pulses, { duration: 700, easing: "ease-out" });
    strong.animate(pulses, { duration: 1000, easing: "ease-out" });
    thunder(true, rand(1, 2.5));
  }

  return {
    update(dt, now) {
      if (dt === 0) return;
      if (now >= nextBolt) {
        strike();
        nextBolt = now + rand(45000, 90000);
        next = Math.max(next, now + 6000);
      } else if (now >= next) {
        flash.animate(
          [{ opacity: 0 }, { opacity: 1, offset: 0.06 }, { opacity: 0.12, offset: 0.2 }, { opacity: 0.75, offset: 0.3 }, { opacity: 0 }],
          { duration: 1100, easing: "ease-out" },
        );
        thunder(false, rand(2, 4));
        next = now + rand(15000, 30000);
      }
      // the clouds drift a few pixels a second, so ten steps a second are enough
      cloudTime += dt;
      if (cloudTime >= 0.1) {
        moveClouds(cloudTime);
        cloudTime = 0;
      }
    },
  };
}

const LEAF = "M0 -9 C5 -7 7 -1 5 4 C3 7 1 8 0 10 C-1 8 -3 7 -5 4 C-7 -1 -5 -7 0 -9 Z";
const LEAF_COLORS = ["#d9541e", "#e8892b", "#b5381c", "#c9a227", "#8a4b2a"];

// gusts of wind every 20 to 30 seconds, with leaves tumbling across the window
function wind(): Part {
  const layer = windowLayer("rc-hw-layer");
  const leaves: {
    g: SVGGElement; t: number; x: number; y: number; vx: number; vy: number; rot: number; vr: number;
    ph: number; flip: number; size: number;
  }[] = [];
  const gust = { target: 0, dir: 1, until: 0, next: performance.now() + rand(9000, 14000) };

  function spawnLeaf() {
    if (leaves.length >= 16) return;
    const W = innerWidth, H = innerHeight;
    const g = el("g", {}, layer);
    el("path", { d: LEAF, fill: LEAF_COLORS[Math.floor(Math.random() * LEAF_COLORS.length)] }, g);
    el("path", { d: "M0 -7 L0 12", fill: "none", stroke: "rgb(0 0 0 / 28%)", "stroke-width": 0.8 }, g);
    leaves.push({
      g, t: 0, x: gust.dir > 0 ? -20 : W + 20, y: rand(70, H * 0.75),
      vx: gust.dir * rand(150, 260), vy: rand(-15, 25), rot: rand(0, 360), vr: rand(-280, 280),
      ph: rand(0, 6), flip: rand(4, 9), size: rand(0.9, 1.5),
    });
  }

  return {
    update(dt, now) {
      if (dt === 0) return;
      if (now >= gust.next) {
        gust.dir = Math.random() < 0.5 ? 1 : -1;
        gust.target = 1;
        gust.until = now + rand(2600, 4200);
        gust.next = now + rand(18000, 32000);
      }
      if (now > gust.until) gust.target = 0;
      const w = world.wind;
      w.s += (gust.target - w.s) * Math.min(1, dt * (gust.target > w.s ? 2.2 : 0.8));
      w.v = w.s * (0.65 + 0.35 * Math.sin(now / 170) * Math.sin(now / 430)) * gust.dir;
      if (w.s > 0.3 && Math.random() < dt * 5) spawnLeaf();
      const W = innerWidth, H = innerHeight;
      for (let i = leaves.length - 1; i >= 0; i--) {
        const l = leaves[i];
        l.t += dt;
        l.x += l.vx * (0.3 + 0.7 * w.s) * dt;
        l.vy += 22 * dt;
        l.y += (l.vy + Math.sin(l.t * 2.2 + l.ph) * 30) * dt;
        l.rot += l.vr * dt;
        const sx = Math.cos(l.t * l.flip) * l.size;
        l.g.setAttribute("transform", `translate(${l.x.toFixed(1)} ${l.y.toFixed(1)}) rotate(${l.rot.toFixed(1)}) scale(${sx.toFixed(3)} ${l.size.toFixed(2)})`);
        if (l.x < -40 || l.x > W + 40 || l.y > H + 30) {
          l.g.remove();
          leaves.splice(i, 1);
        }
      }
    },
    calm() {
      for (const l of leaves.splice(0)) l.g.remove();
      gust.target = 0;
      world.wind.s = 0;
      world.wind.v = 0;
    },
  };
}

// the weather of the home page
export function homeWeather(gallery: HTMLElement | null): Part[] {
  const parts = [wind(), fog()];
  const picture = gallery?.querySelector<HTMLElement>(".rc-picture");
  // the moon rises behind the upper left corner of the picture
  if (gallery)
    parts.push(
      sky(gallery, "hero", () => {
        const p = picture?.getBoundingClientRect();
        return p?.width ? { x: p.left - 50, y: p.top - 46 } : null;
      }),
    );
  return parts;
}

// the weather of a news page: a smaller moon stands at the top, right of the title and above the line under it, on
// narrow screens half out of the window
export function pageWeather(main: HTMLElement | null): Part[] {
  const parts = [wind(), fog()];
  const column = main?.querySelector<HTMLElement>(".sl-markdown-content") ?? main;
  if (main && column)
    parts.push(
      sky(main, "page", () => {
        const c = column.getBoundingClientRect(), m = main.getBoundingClientRect();
        return { x: innerWidth < 800 ? innerWidth - 50 : c.right - 120, y: m.top + 14 };
      }),
    );
  return parts;
}
