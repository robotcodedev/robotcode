// What the parts of the Halloween decorations share: the page kind, the pointer, the wind, the state of the season
// and of Spooky mode, small SVG helpers, and the treat bubble that clicked creatures leave.
import { TIPS } from "./treats";

export const SVG_NS = "http://www.w3.org/2000/svg";

// The Robot Framework face, 24 × 24 (icons/light/robot.svg of the RobotCode repository).
export const RF_FACE =
  "M6.53 10.621a2.645 2.645 0 012.64-2.643 2.645 2.645 0 012.644 2.643.96.959 0 01-.96.96.96.959 0 01-.958-.96.724.724 0 00-.725-.722.724.724 0 00-.724.722.959.959 0 11-1.917 0m10.942 4.441a.959.959 0 01-.959.96H7.618a.959.959 0 01-.959-.96.96.959 0 01.959-.96h8.895a.96.959 0 01.96.96m-4.158-3.903a.96.96 0 01.26-1.331l2.223-1.502a.956.956 0 011.332.255.96.96 0 01-.26 1.332l-2.223 1.502a.943.943 0 01-.535.167.965.964 0 01-.797-.423m6.09 5.905a.685.685 0 01-.2.484l-1.653 1.653a.685.685 0 01-.485.2H6.934a.685.685 0 01-.484-.2l-1.652-1.653a.685.685 0 01-.201-.484V6.937c0-.182.072-.355.2-.484L6.45 4.8a.685.685 0 01.484-.2h10.134c.181 0 .355.072.484.2l1.652 1.653a.684.684 0 01.201.484zM20.81 5.348L18.653 3.19a1.744 1.743 0 00-1.232-.51H6.579a1.743 1.743 0 00-1.233.51L3.189 5.348a1.744 1.744 0 00-.51 1.233v10.84c0 .462.184.906.51 1.232l2.159 2.158a1.743 1.743 0 001.233.51h10.84c.462 0 .906-.183 1.232-.51l2.158-2.158a1.744 1.743 0 00.511-1.233V6.581a1.744 1.743 0 00-.51-1.233";

export type Page = "home" | "news";

// A part of the decorations: `update` is called once per frame while motion is allowed, and once with `dt = 0` when
// it is not, so that the part can show its still state.
export interface Part {
  update(dt: number, now: number): void;
  // takes away what only exists while things move (flying bats, blown leaves, a peeking ghost)
  calm?(): void;
}

const motionQuery = matchMedia("(prefers-reduced-motion: reduce)");

export const world = {
  page: "home" as Page,
  pointer: null as { x: number; y: number } | null,
  // the wind of a gust: `s` its strength from 0 to 1, `v` the signed push (positive blows to the right)
  wind: { s: 0, v: 0 },
  reduced: () => motionQuery.matches,
  motionQuery,
};

addEventListener("pointermove", (e) => (world.pointer = { x: e.clientX, y: e.clientY }), { passive: true });
document.addEventListener("pointerleave", () => (world.pointer = null));

export const rand = (a: number, b: number) => a + Math.random() * (b - a);

// Sets an attribute, or the opacity, only when its value changes, so that parts at rest cause no work: a change to the
// SVG of a decoration makes the browser paint that part again.
const written = new WeakMap<Element, Record<string, string>>();
export function put(target: Element, name: string, value: string): void {
  let values = written.get(target);
  if (!values) written.set(target, (values = {}));
  if (values[name] === value) return;
  values[name] = value;
  if (name === "opacity") (target as SVGElement).style.opacity = value;
  else target.setAttribute(name, value);
}
export const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));

export function el<K extends keyof SVGElementTagNameMap>(
  tag: K,
  attrs: Record<string, string | number> = {},
  parent?: Element,
): SVGElementTagNameMap[K] {
  const n = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, String(v));
  if (parent) parent.appendChild(n);
  return n;
}

// a fixed layer over the whole window that only its clickable creatures react to
export function windowLayer(className: string): SVGSVGElement {
  const svg = el("svg", { class: `rc-halloween ${className}`, "aria-hidden": "true" });
  document.body.appendChild(svg);
  return svg;
}

let tipAt = Math.floor(Math.random() * TIPS.length);

// A tip as a treat near the click, above it, or above the whole `anchor` box so that it does not cover what was
// clicked; it fades after a few seconds.
export function treat(x: number, y: number, title = "Treat!", anchor?: DOMRect): void {
  tipAt = (tipAt + 1) % TIPS.length;
  const bubble = document.createElement("div");
  bubble.className = "rc-halloween rc-hw-treat";
  bubble.setAttribute("role", "status");
  const heading = document.createElement("strong");
  heading.textContent = title;
  bubble.append(heading, " ", ...renderTip(TIPS[tipAt]));
  document.body.appendChild(bubble);
  const w = bubble.offsetWidth, h = bubble.offsetHeight;
  let top = anchor ? anchor.top - h - 12 : y - h - 22;
  if (top < 70) top = anchor ? anchor.bottom + 12 : y + 26;
  const left = anchor ? anchor.left : x - w / 2;
  bubble.style.left = `${clamp(left, 16, innerWidth - w - 16)}px`;
  bubble.style.top = `${clamp(top, 16, innerHeight - h - 16)}px`;
  setTimeout(() => bubble.classList.add("rc-hw-out"), 3400);
  setTimeout(() => bubble.remove(), 3900);
}

// `code` in backticks becomes <code>
function renderTip(tip: string): Node[] {
  return tip.split("`").map((part, i) => {
    if (i % 2 === 0) return document.createTextNode(part);
    const code = document.createElement("code");
    code.textContent = part;
    return code;
  });
}
