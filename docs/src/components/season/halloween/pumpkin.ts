// The pumpkin with the Robot Framework face carved in: it floats in one of the two lower corners of the window, the one
// that Halloween.astro chose at random on this page load (`data-pumpkin-corner`, shared with the Spooky mode switch),
// and glows like a candle inside. A click makes the flame flare up and leaves a treat
// above the pumpkin. A neon sign above it lights up while the pointer is on the pumpkin: typing "boo" sends bats.
import { rand, RF_FACE, treat, world, type Part } from "./world";

const PUMPKIN = `
  <ellipse class="rc-hw-pumpkin-shadow" cx="60" cy="105" rx="44" ry="5" fill="var(--hw-shadow)"/>
  <g class="rc-hw-pumpkin-float">
    <g class="rc-hw-pumpkin-body">
      <path d="M57 23 C56 15 59 9 65 5 C67 4 69 6 67 8 C63 11 62 16 63 23 Z" fill="var(--hw-stem)"/>
      <path d="M65 11 C72 4 83 7 82 14 C79 10 73 9 68 13" fill="none" stroke="var(--hw-stem)" stroke-width="2" stroke-linecap="round"/>
      <ellipse cx="33" cy="64" rx="26" ry="37" fill="url(#rc-hw-skin)" stroke="var(--hw-pumpkin-line)" stroke-width="1.2"/>
      <ellipse cx="87" cy="64" rx="26" ry="37" fill="url(#rc-hw-skin)" stroke="var(--hw-pumpkin-line)" stroke-width="1.2"/>
      <ellipse cx="46" cy="63" rx="26" ry="40" fill="url(#rc-hw-skin)" stroke="var(--hw-pumpkin-line)" stroke-width="1.2"/>
      <ellipse cx="74" cy="63" rx="26" ry="40" fill="url(#rc-hw-skin)" stroke="var(--hw-pumpkin-line)" stroke-width="1.2"/>
      <ellipse cx="60" cy="62" rx="27" ry="41" fill="url(#rc-hw-skin)" stroke="var(--hw-pumpkin-line)" stroke-width="1.2"/>
      <path d="M42 32 Q37 52 42 86" fill="none" stroke="rgb(255 255 255 / 28%)" stroke-width="2.2" stroke-linecap="round"/>
    </g>
    <ellipse class="rc-hw-inner-glow" cx="60" cy="62" rx="34" ry="36" fill="url(#rc-hw-inner)"/>
    <g class="rc-hw-carving" transform="translate(38 41) scale(1.85)">
      <path fill="var(--hw-pumpkin-cut)" stroke="var(--hw-pumpkin-cut)" stroke-width="0.5" stroke-linejoin="round" transform="translate(0.2 0.35)" d="${RF_FACE}"/>
      <path fill="url(#rc-hw-flame)" stroke="url(#rc-hw-flame)" stroke-width="0.55" stroke-linejoin="round" d="${RF_FACE}"/>
    </g>
  </g>`;

export function pumpkin(): Part {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  const right = document.documentElement.dataset.pumpkinCorner === "right";
  svg.setAttribute("class", `rc-halloween rc-hw-pumpkin${right ? " rc-hw-right" : ""}`);
  svg.setAttribute("viewBox", "0 0 120 112");
  svg.setAttribute("aria-hidden", "true");
  svg.innerHTML = PUMPKIN;
  document.body.appendChild(svg);
  const float = svg.querySelector<SVGGElement>(".rc-hw-pumpkin-float")!;
  const shadow = svg.querySelector<SVGEllipseElement>(".rc-hw-pumpkin-shadow")!;
  const carving = svg.querySelector<SVGGElement>(".rc-hw-carving")!;
  const glow = svg.querySelector<SVGEllipseElement>(".rc-hw-inner-glow")!;
  const flameGradient = document.getElementById("rc-hw-flame")!;

  const body = svg.querySelector(".rc-hw-pumpkin-body")!;
  const sign = document.createElement("div");
  sign.className = `rc-halloween rc-hw-neon${right ? " rc-hw-right" : ""}`;
  sign.setAttribute("aria-hidden", "true");
  sign.innerHTML = "type <span>boo</span>";
  document.body.appendChild(sign);
  body.addEventListener("pointerenter", () => sign.classList.add("rc-hw-on"));
  body.addEventListener("pointerleave", () => sign.classList.remove("rc-hw-on"));

  // a candle: the brightness moves slowly to a new level every few tenths of a second, now and then it dips as in a
  // draught, a gust of wind makes it flicker, and the flame sways a little
  const flame = { v: 0.85, target: 0.85, next: 0, flare: 0, t: 0 };
  // a candle and a slow bob need no more than about 20 pictures a second, and every picture paints the pumpkin anew
  let pending = 0;
  body.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    // the treat takes the place of the sign
    sign.classList.remove("rc-hw-on");
    flame.flare = 0.95;
    treat((e as PointerEvent).clientX, (e as PointerEvent).clientY, "Treat!", svg.getBoundingClientRect());
  });

  return {
    update(dt, now) {
      if (dt === 0) {
        carving.style.opacity = "";
        glow.style.opacity = "";
        flameGradient.setAttribute("cx", "0.5");
        flameGradient.setAttribute("cy", "0.6");
        float.setAttribute("transform", "translate(0 -5)");
        shadow.removeAttribute("transform");
        shadow.style.opacity = "";
        return;
      }
      pending += dt;
      if (pending < 0.05) return;
      dt = pending;
      pending = 0;
      if (now >= flame.next) {
        flame.target = Math.random() < 0.06 ? rand(0.5, 0.62) : rand(0.7, 0.96);
        flame.next = now + rand(220, 600);
      }
      if (world.wind.s > 0.4 && Math.random() < dt * 2.5) flame.target = rand(0.45, 0.68);
      flame.v += (flame.target - flame.v) * Math.min(1, dt * 3.2);
      flame.flare = Math.max(0, flame.flare - dt * 0.9);
      flame.t += dt;
      const v = flame.v + flame.flare;
      // the glow of the carving stays (halloween.css); the flame flickers in the opacity of the carving and the inner glow
      carving.style.opacity = (0.72 + 0.28 * Math.min(1, v)).toFixed(3);
      glow.style.opacity = Math.min(1, 0.3 + 0.45 * v).toFixed(3);
      flameGradient.setAttribute("cx", (0.5 + Math.sin(flame.t * 1.1) * 0.04 + (flame.v - 0.83) * 0.06).toFixed(3));
      flameGradient.setAttribute("cy", (0.6 + Math.sin(flame.t * 1.6) * 0.03).toFixed(3));
      // floating: up and down slowly with a slight sway; the shadow shrinks and fades as the pumpkin rises
      const lift = (Math.sin(flame.t * 1.25) + 1) / 2;
      float.setAttribute("transform", `translate(0 ${(-4 - 7 * lift).toFixed(2)}) rotate(${(Math.sin(flame.t * 0.8) * 2.5).toFixed(2)} 60 62)`);
      shadow.setAttribute("transform", `translate(60 105) scale(${(1 - 0.2 * lift).toFixed(3)} 1) translate(-60 -105)`);
      shadow.style.opacity = (1 - 0.4 * lift).toFixed(3);
    },
  };
}
