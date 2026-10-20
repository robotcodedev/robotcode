// The title of the home page is full of blood (custom.css colors the letters); here blood runs down from the bottom of
// the letters. A trickle starts where a letter stands on the baseline, runs down slowly, and drops form at its end and
// fall, one after another; when no more blood follows, the trace dries and darkens but stays. When every foot of the
// letters has a trace, fresh blood runs down an old one again. With reduced motion a few trickles hang still.
import { el, put, rand, world, type Part } from "./world";

interface Foot {
  x: number;
  width: number;
  drip: Drip | null;
}

interface Drip {
  foot: Foot;
  w: number;
  length: number;
  max: number;
  speed: number;
  // the bead at the end: its growth from 0 to 1, and how long until it is full
  bead: number;
  beadTime: number;
  drops: number;
  wet: number;
  dried: number;
  // the trace sways a little sideways on its way down
  bend: number;
  falling: { y: number; v: number; o: number; r: number } | null;
  path: SVGPathElement;
  dry: SVGPathElement;
  shine: SVGPathElement;
  gloss: SVGEllipseElement;
  drop: SVGPathElement;
  dropGloss: SVGEllipseElement;
}

export function bloodTitle(title: HTMLElement): Part {
  title.style.position = "relative";
  const svg = el("svg", { class: "rc-halloween rc-hw-blood", "aria-hidden": "true" });
  // the gradient of the letters (custom.css) over the height of the title, so that a drip has the color of the letter
  // where it leaves it; below the title it keeps the darkest red
  svg.innerHTML = `<defs><linearGradient id="rc-hw-blood" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ff4b4b"/><stop offset="0.4" stop-color="#c8001c"/><stop offset="0.72" stop-color="#8c0013"/>
    <stop offset="1" stop-color="#5a000b"/></linearGradient>
    <linearGradient id="rc-hw-blood-dry" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#190004" stop-opacity="0"/><stop offset="1" stop-color="#190004" stop-opacity="0.6"/></linearGradient></defs>`;
  const gradient = svg.querySelector<SVGLinearGradientElement>("#rc-hw-blood")!;
  // drying darkens a trace only below the letter, so that it still meets the letter in the letter's color
  const dryGradient = svg.querySelector<SVGLinearGradientElement>("#rc-hw-blood-dry")!;
  title.appendChild(svg);
  let feet: Foot[] = [];
  let baseline = 0, size = 0, room = 0, measured = "", clock = 0, next = 0;
  const drips: Drip[] = [];

  // The feet of the letters, from the rendered font: every character is drawn at its place in the title onto a canvas,
  // and the ink just above the baseline gives the stems, legs and round bottoms that blood can run down from. The
  // baseline is where an empty inline block in the title sits.
  function measure() {
    const text = title.firstChild;
    const box = title.getBoundingClientRect();
    if (measured === `${box.width}x${box.height}` || !text || text.nodeType !== Node.TEXT_NODE) return;
    const again = measured !== "";
    measured = `${box.width}x${box.height}`;
    for (const d of drips.splice(0)) [d.path, d.dry, d.shine, d.gloss, d.drop, d.dropGloss].forEach((e) => e.remove());
    const style = getComputedStyle(title);
    size = parseFloat(style.fontSize);
    const probe = document.createElement("span");
    probe.style.cssText = "display: inline-block; width: 0; height: 0; vertical-align: baseline";
    title.insertBefore(probe, text.nextSibling);
    baseline = probe.getBoundingClientRect().bottom - box.top;
    probe.remove();
    svg.setAttribute("width", String(Math.ceil(box.width)));
    svg.setAttribute("height", String(Math.ceil(box.height + size * 1.6)));
    gradient.setAttribute("y2", String(box.height));
    dryGradient.setAttribute("y1", String(baseline + size * 0.02));
    dryGradient.setAttribute("y2", String(baseline + size * 0.25));
    // the traces end above what follows the title, the tagline, so that they never cover it
    const below = title.nextElementSibling?.getBoundingClientRect().top ?? box.bottom + size;
    room = Math.max(size * 0.15, below - box.top - baseline - size * 0.16);

    const scale = 2;
    const canvas = document.createElement("canvas");
    canvas.width = Math.ceil(box.width * scale) + 2;
    canvas.height = Math.ceil((baseline + size * 0.2) * scale);
    const context = canvas.getContext("2d", { willReadFrequently: true })!;
    context.scale(scale, scale);
    context.font = `${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
    context.textBaseline = "alphabetic";
    const range = document.createRange();
    const chars = text.textContent ?? "";
    for (let i = 0; i < chars.length; i++) {
      range.setStart(text, i);
      range.setEnd(text, i + 1);
      context.fillText(chars[i], range.getBoundingClientRect().left - box.left, baseline);
    }
    const row = context.getImageData(0, Math.round((baseline - size * 0.04) * scale), canvas.width, 1).data;
    feet = [];
    for (let x = 0, start = -1; x <= canvas.width; x++) {
      const ink = x < canvas.width && row[x * 4 + 3] > 128;
      if (ink && start < 0) start = x;
      if (!ink && start >= 0) {
        const width = (x - start) / scale;
        if (width >= size * 0.05) feet.push({ x: (start + x) / 2 / scale, width, drip: null });
        start = -1;
      }
    }
    if (again && world.reduced()) still();
  }
  measure();
  new ResizeObserver(measure).observe(title);

  function create(foot: Foot, settled: boolean): Drip {
    const w = Math.min(size * rand(0.06, 0.1), foot.width * 0.7);
    const max = Math.min(size * rand(0.2, 0.5), room);
    const drip: Drip = {
      foot,
      w,
      length: settled ? max * rand(0.5, 1) : 0,
      max,
      speed: max / rand(5, 10),
      bead: settled ? rand(0.2, 0.9) : 0,
      beadTime: rand(2, 4),
      drops: Math.floor(rand(2, 5)),
      wet: 1,
      dried: 0,
      bend: rand(-0.4, 0.4),
      falling: null,
      path: el("path", { fill: "url(#rc-hw-blood)" }, svg),
      dry: el("path", { fill: "url(#rc-hw-blood-dry)" }, svg),
      shine: el("path", { fill: "none", stroke: "rgb(255 200 200 / 35%)", "stroke-linecap": "round" }, svg),
      gloss: el("ellipse", { fill: "rgb(255 230 230 / 55%)" }, svg),
      drop: el("path", { fill: "url(#rc-hw-blood)" }, svg),
      dropGloss: el("ellipse", { fill: "rgb(255 230 230 / 55%)" }, svg),
    };
    foot.drip = drip;
    drips.push(drip);
    return drip;
  }

  const freeFoot = () => {
    const free = feet.filter((f) => !f.drip);
    return free.length ? free[Math.floor(Math.random() * free.length)] : null;
  };

  // a new trickle at a free foot, or fresh blood down the trace that dried first
  function start() {
    const foot = freeFoot();
    if (foot) create(foot, false);
    else {
      const dry = drips.filter((d) => d.wet === 0).sort((a, b) => a.dried - b.dried)[0];
      if (dry) {
        dry.wet = 1;
        dry.drops = Math.floor(rand(2, 4));
        dry.max = Math.min(room, dry.max + size * rand(0.05, 0.15));
        dry.speed = (dry.max - dry.length) / rand(3, 6) + 1;
        dry.bead = 0;
      }
    }
    next = clock + rand(2, 5);
  }

  // reduced motion: a few trickles that hang still
  function still() {
    for (let i = 0; i < 4; i++) {
      const foot = freeFoot();
      if (foot) create(foot, true);
    }
    drips.forEach(draw);
  }

  const f = (n: number) => n.toFixed(1);

  // A trace: a lip where it leaves the letter, a thin stream that tapers and sways a little, and a bead at its end that
  // swells into a teardrop while a drop gathers; a falling drop is a teardrop that stretches as it falls. Drying
  // darkens the trace and takes its shine.
  function draw(d: Drip) {
    // slow changes in steps, so that a trace is painted again only now and then: its length in whole pixels, the bead
    // and the drying in steps too small to see
    const length = Math.round(d.length), bead = Math.round(d.bead * 12) / 12, wet = Math.round(d.wet * 20) / 20;
    const x = d.foot.x, top = baseline - size * 0.03, bottom = baseline + length;
    const sw = d.w * 0.4, lip = Math.min(d.w * 0.9, d.foot.width / 2), neck = Math.min(length * 0.5, d.w * 1.2);
    const r = sw * (1.4 + 1.7 * bead * wet);
    const cy = Math.max(top + neck + r * 0.8, bottom - r), join = cy - r * 0.95, mid = (top + neck + join) / 2;
    const bend = d.bend * sw;
    put(
      d.path,
      "d",
      `M${f(x - lip)} ${f(top)} C${f(x - lip * 0.55)} ${f(top + neck * 0.25)} ${f(x - sw * 1.1)} ${f(top + neck * 0.55)} ${f(x - sw)} ${f(top + neck)} ` +
        `Q${f(x - sw * 0.85 + bend)} ${f(mid)} ${f(x - sw * 0.65)} ${f(join)} ` +
        `C${f(x - sw * 0.65)} ${f(join + r * 0.35)} ${f(x - r)} ${f(cy - r * 0.55)} ${f(x - r)} ${f(cy)} ` +
        `A${f(r)} ${f(r)} 0 0 0 ${f(x + r)} ${f(cy)} ` +
        `C${f(x + r)} ${f(cy - r * 0.55)} ${f(x + sw * 0.65)} ${f(join + r * 0.35)} ${f(x + sw * 0.65)} ${f(join)} ` +
        `Q${f(x + sw * 0.85 + bend)} ${f(mid)} ${f(x + sw)} ${f(top + neck)} ` +
        `C${f(x + sw * 1.1)} ${f(top + neck * 0.55)} ${f(x + lip * 0.55)} ${f(top + neck * 0.25)} ${f(x + lip)} ${f(top)} Z`,
    );
    put(d.dry, "d", d.path.getAttribute("d")!);
    put(d.dry, "opacity", (1 - wet).toFixed(2));
    // the wet shine: a streak down the stream and a highlight on the bead
    put(d.shine, "stroke-width", f(Math.max(0.8, sw * 0.35)));
    put(d.shine, "d", join - top > neck + sw * 3 ? `M${f(x - sw * 0.35)} ${f(top + neck)} Q${f(x - sw * 0.3 + bend * 0.9)} ${f(mid)} ${f(x - sw * 0.3)} ${f(join - r * 0.2)}` : "");
    put(d.shine, "opacity", wet.toFixed(2));
    Object.entries({ cx: x - r * 0.35, cy: cy - r * 0.3, rx: r * 0.22, ry: r * 0.32 }).forEach(([k, v]) => put(d.gloss, k, f(v)));
    put(d.gloss, "opacity", wet.toFixed(2));
    if (d.falling) {
      const { y, r: rf } = d.falling, tip = rf * 2.1 * (1 + Math.min(0.8, d.falling.v / 1800));
      put(
        d.drop,
        "d",
        `M${f(x)} ${f(y - tip)} C${f(x + rf * 0.45)} ${f(y - tip * 0.65)} ${f(x + rf)} ${f(y - rf * 0.7)} ${f(x + rf)} ${f(y)} ` +
          `A${f(rf)} ${f(rf)} 0 0 1 ${f(x - rf)} ${f(y)} C${f(x - rf)} ${f(y - rf * 0.7)} ${f(x - rf * 0.45)} ${f(y - tip * 0.65)} ${f(x)} ${f(y - tip)} Z`,
      );
      Object.entries({ cx: x - rf * 0.35, cy: y - rf * 0.25, rx: rf * 0.22, ry: rf * 0.3 }).forEach(([k, v]) => put(d.dropGloss, k, f(v)));
      put(d.drop, "opacity", d.falling.o.toFixed(2));
      put(d.dropGloss, "opacity", d.falling.o.toFixed(2));
    } else {
      put(d.drop, "d", "");
      put(d.dropGloss, "rx", "0");
    }
  }

  return {
    update(dt) {
      if (dt === 0) {
        if (!drips.length) still();
        return;
      }
      clock += dt;
      const flowing = drips.filter((d) => d.wet > 0).length;
      if (flowing < (innerWidth < 600 ? 3 : 4) && clock >= next) start();
      for (const d of drips) {
        if (d.wet > 0 && d.length < d.max) {
          // slower as it gets longer, as the blood thins out
          d.length = Math.min(d.max, d.length + d.speed * dt * (1.2 - (0.8 * d.length) / d.max));
        } else if (d.wet > 0 && d.drops > 0) {
          // a drop gathers at the end and falls; the trace stays and runs on a little
          d.bead = Math.min(1, d.bead + dt / d.beadTime);
          if (d.bead >= 1 && !d.falling) {
            const r = d.w * 0.4 * 3.1;
            d.falling = { y: baseline + d.length - r, v: 0, o: 1, r };
            d.bead = 0;
            d.drops -= 1;
            d.beadTime = rand(2.5, 5);
            d.length = Math.min(room, d.length + size * 0.02);
          }
        } else if (d.wet > 0) {
          // nothing follows any more: the trace dries
          d.bead = Math.max(0, d.bead - dt);
          d.wet = Math.max(0, d.wet - dt / 12);
          if (d.wet === 0) d.dried = clock;
        }
        if (d.falling) {
          d.falling.v += 900 * dt;
          d.falling.y += d.falling.v * dt;
          // it falls away below the tagline
          if (d.falling.y > baseline + size * 1.4) d.falling.o = Math.max(0, d.falling.o - dt * 5);
          if (d.falling.o <= 0) d.falling = null;
        }
        draw(d);
      }
    },
  };
}
