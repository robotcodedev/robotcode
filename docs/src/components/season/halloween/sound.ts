// The sounds of the Halloween decorations, made in the browser with the Web Audio API, so there are no audio files:
// thunder after a lightning bolt, a far rumble after a soft lightning, the patter and squeak of a clicked spider, the
// pop of the egg sac, the ghost's boo, the patter of walking spiders, and a music box. The sounds play while sound is on
// (`data-sound` on <html>, set by Halloween.astro), the music box while music is on as well (`data-music`), both only
// while Spooky mode is on and the tab is shown; browsers let them start only after a click or a key press on the page.
import { clamp, rand } from "./world";

const root = document.documentElement;
let ctx: AudioContext | null = null;
let out: GainNode | null = null;
const buffers: { brown?: AudioBuffer; white?: AudioBuffer } = {};

const spooky = () => root.dataset.spooky !== "off";
const effectsOn = () => root.dataset.sound === "on" && spooky();
const musicOn = () => root.dataset.music === "on" && spooky();

// creates or resumes the audio context; called on a click or a key press, as browsers require
function unlock() {
  if (!effectsOn() && !musicOn()) return;
  if (!ctx) {
    ctx = new AudioContext();
    out = ctx.createGain();
    out.gain.value = 0.5;
    out.connect(ctx.destination);
    ctx.addEventListener("statechange", waiting);
  }
  if (ctx.state === "suspended" && !document.hidden) void ctx.resume();
}

// while sound is on but the browser still holds it back until a click, Halloween.astro shows a hint
// (`data-sound-waiting`); once the sound has played, pauses of a hidden tab or a turned off switch are no reason for it
let played = false;
function waiting() {
  if (ctx?.state === "running") played = true;
  if ((effectsOn() || musicOn()) && !played) root.dataset.soundWaiting = "";
  else delete root.dataset.soundWaiting;
}

// falls silent at once when sound and music or Spooky mode are turned off or the tab is hidden; starts and stops the
// music box
function sync() {
  if (ctx) {
    if ((effectsOn() || musicOn()) && !document.hidden) void ctx.resume();
    else void ctx.suspend();
    if (musicOn()) startMusic();
    else stopMusic();
  }
  waiting();
}

// the first click, tap or key press starts the sound and the music; on touch screens only the end of a tap counts
for (const event of ["pointerdown", "pointerup", "touchend", "keydown"]) {
  addEventListener(
    event,
    () => {
      unlock();
      sync();
    },
    { capture: true, passive: true },
  );
}
for (const event of ["rc-sound", "rc-music"]) {
  document.addEventListener(event, () => {
    unlock();
    sync();
  });
}
document.addEventListener("rc-spooky", sync);
document.addEventListener("visibilitychange", sync);

// the context and the output while sounds may play now
function live(): [AudioContext, GainNode] | null {
  return effectsOn() && ctx?.state === "running" && out ? [ctx, out] : null;
}

// two seconds of noise: brown for thunder, white for the patter of legs
function noise(a: AudioContext, kind: "brown" | "white"): AudioBuffer {
  let buffer = buffers[kind];
  if (!buffer) {
    buffer = a.createBuffer(1, a.sampleRate * 2, a.sampleRate);
    const d = buffer.getChannelData(0);
    let last = 0;
    for (let i = 0; i < d.length; i++) {
      const white = Math.random() * 2 - 1;
      last = (last + 0.02 * white) / 1.02;
      d[i] = kind === "brown" ? last * 3.5 : white;
    }
    buffers[kind] = buffer;
  }
  return buffer;
}

// thunder `delay` seconds from now: a near one cracks dully, then rolls and dies away over seven to nine seconds; a far
// one only rumbles softly; both deep, with the lows lifted
export function thunder(near: boolean, delay: number): void {
  const audio = live();
  if (!audio) return;
  const [a, dest] = audio;
  const t = a.currentTime + delay, len = near ? rand(7, 9.5) : rand(3.5, 5), peak = near ? 1.3 : 0.4;
  const src = a.createBufferSource();
  src.buffer = noise(a, "brown");
  src.loop = true;
  const lp = a.createBiquadFilter();
  lp.type = "lowpass";
  lp.frequency.setValueAtTime(near ? 650 : 450, t);
  lp.frequency.exponentialRampToValueAtTime(near ? 80 : 90, t + len * 0.6);
  const lows = a.createBiquadFilter();
  lows.type = "lowshelf";
  lows.frequency.value = 110;
  lows.gain.value = 6;
  const g = a.createGain();
  g.gain.setValueAtTime(0.0001, t);
  g.gain.exponentialRampToValueAtTime(peak, t + (near ? 0.05 : 0.6));
  // the roll: a few swells over the first half, then a long tail
  let at = t + (near ? 0.3 : 0.9);
  for (; at < t + len * 0.5; at += rand(0.3, 0.7)) {
    g.gain.linearRampToValueAtTime(peak * Math.pow(1 - (at - t) / len, 1.2) * rand(0.4, 1), at);
  }
  g.gain.setTargetAtTime(0.0001, at, len * 0.12);
  duck(t, len, near ? 0.35 : 0.7);
  src.connect(lp).connect(lows).connect(g).connect(dest);
  src.start(t, rand(0, 1.5));
  src.stop(t + len + 0.05);
  if (near) {
    const crack = a.createBufferSource();
    crack.buffer = noise(a, "white");
    const hp = a.createBiquadFilter();
    hp.type = "highpass";
    hp.frequency.value = 250;
    const dull = a.createBiquadFilter();
    dull.type = "lowpass";
    dull.frequency.value = 1800;
    const cg = a.createGain();
    cg.gain.setValueAtTime(0.25, t);
    cg.gain.exponentialRampToValueAtTime(0.0001, t + 0.45);
    crack.connect(hp).connect(dull).connect(cg).connect(dest);
    crack.start(t, rand(0, 1));
    crack.stop(t + 0.5);
  }
}

// a clicked spider: its legs patter off in `steps` quick taps, and it squeaks
export function scurry(steps = 8): void {
  const audio = live();
  if (!audio) return;
  const [a, dest] = audio;
  const t0 = a.currentTime;
  const src = a.createBufferSource();
  src.buffer = noise(a, "white");
  const bp = a.createBiquadFilter();
  bp.type = "bandpass";
  bp.frequency.value = 3800;
  bp.Q.value = 1.2;
  const g = a.createGain();
  g.gain.value = 0;
  src.connect(bp).connect(g).connect(dest);
  let t = t0;
  for (let i = 0; i < steps; i++) {
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(rand(0.5, 0.9) * (1 - i / (steps + 2)), t + 0.003);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.018);
    t += rand(0.022, 0.04);
  }
  src.start(t0, rand(0, 1));
  src.stop(t + 0.05);
  const squeak = a.createOscillator();
  squeak.type = "triangle";
  squeak.frequency.setValueAtTime(2300, t0);
  squeak.frequency.exponentialRampToValueAtTime(3600, t0 + 0.07);
  squeak.frequency.exponentialRampToValueAtTime(2800, t0 + 0.12);
  const sg = a.createGain();
  sg.gain.setValueAtTime(0.0001, t0);
  sg.gain.exponentialRampToValueAtTime(0.14, t0 + 0.015);
  sg.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.14);
  squeak.connect(sg).connect(dest);
  squeak.start(t0);
  squeak.stop(t0 + 0.15);
}

// the feet of a walking spider set down: a faint tick, now and then a second one, from where it is (`at` from 0 at the
// left edge of the window to 1 at the right); a small spider ticks higher and softer
export function patter(at: number, small: boolean): void {
  const audio = live();
  if (!audio) return;
  const [a, dest] = audio;
  const pan = a.createStereoPanner();
  pan.pan.value = clamp(at * 2 - 1, -1, 1) * 0.8;
  pan.connect(dest);
  for (let i = 0; i < (Math.random() < 0.4 ? 2 : 1); i++) {
    const t = a.currentTime + (i ? rand(0.008, 0.018) : 0);
    const src = a.createBufferSource();
    src.buffer = noise(a, "white");
    const bp = a.createBiquadFilter();
    bp.type = "bandpass";
    bp.frequency.value = (small ? 6500 : 4200) * rand(0.8, 1.25);
    bp.Q.value = 2;
    const g = a.createGain();
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime((small ? 0.2 : 0.35) * rand(0.6, 1) * (i ? 0.7 : 1), t + 0.002);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.012);
    src.connect(bp).connect(g).connect(pan);
    src.start(t, rand(0, 1.9));
    src.stop(t + 0.015);
  }
}

// the hall of the sounds, shared, created with the first sound that needs it
let fxHall: ConvolverNode | null = null;
function hallSend(a: AudioContext, dest: AudioNode): AudioNode {
  if (!fxHall) {
    fxHall = a.createConvolver();
    fxHall.buffer = hall(a);
    const wet = a.createGain();
    wet.gain.value = 0.4;
    fxHall.connect(wet).connect(dest);
  }
  return fxHall;
}

// the ghost says "boooo": a hollow voice on the vowel u that rises a little and sinks, with breath, a soft b and a
// hall; louder when it is clicked than when it only peeks out
export function boo(loud: boolean): void {
  const audio = live();
  if (!audio) return;
  const [a, dest] = audio;
  const t = a.currentTime + 0.05, len = loud ? 1.6 : 1.3, level = loud ? 1 : 0.55;
  const voice = a.createGain();
  voice.gain.setValueAtTime(0.0001, t);
  voice.gain.exponentialRampToValueAtTime(level, t + 0.18);
  voice.gain.setValueAtTime(level, t + len * 0.55);
  voice.gain.exponentialRampToValueAtTime(0.0001, t + len);
  voice.connect(dest);
  voice.connect(hallSend(a, dest));
  // the formants of an u, side by side
  const f1 = a.createBiquadFilter();
  f1.type = "bandpass";
  f1.frequency.value = 330;
  f1.Q.value = 6;
  const f2 = a.createBiquadFilter();
  f2.type = "bandpass";
  f2.frequency.value = 780;
  f2.Q.value = 9;
  const f2g = a.createGain();
  f2g.gain.value = 0.5;
  f1.connect(voice);
  f2.connect(f2g).connect(voice);
  // the voice: two slightly detuned saws with a vibrato, rising a little and then sinking
  const vibrato = a.createOscillator();
  vibrato.frequency.value = 5.5;
  const depth = a.createGain();
  depth.gain.value = 18;
  vibrato.connect(depth);
  vibrato.start(t);
  vibrato.stop(t + len + 0.05);
  for (const detune of [-6, 6]) {
    const o = a.createOscillator();
    o.type = "sawtooth";
    o.frequency.setValueAtTime(190, t);
    o.frequency.linearRampToValueAtTime(215, t + 0.3);
    o.frequency.exponentialRampToValueAtTime(125, t + len);
    o.detune.value = detune;
    depth.connect(o.detune);
    o.connect(f1);
    o.connect(f2);
    o.start(t);
    o.stop(t + len + 0.05);
  }
  // breath
  const breath = a.createBufferSource();
  breath.buffer = noise(a, "white");
  const air = a.createBiquadFilter();
  air.type = "bandpass";
  air.frequency.value = 600;
  const ag = a.createGain();
  ag.gain.value = 0.06;
  breath.connect(air).connect(ag).connect(voice);
  breath.start(t, rand(0, 0.5));
  breath.stop(t + len + 0.05);
  // the b: a soft, low thump
  const b = a.createOscillator();
  b.frequency.setValueAtTime(110, t);
  b.frequency.exponentialRampToValueAtTime(60, t + 0.06);
  const bg = a.createGain();
  bg.gain.setValueAtTime(0.0001, t);
  bg.gain.exponentialRampToValueAtTime(level * 0.3, t + 0.01);
  bg.gain.exponentialRampToValueAtTime(0.0001, t + 0.09);
  b.connect(bg).connect(dest);
  b.start(t);
  b.stop(t + 0.1);
}

// the egg sac bursts with a soft pop, and the hatchlings patter off
export function pop(): void {
  const audio = live();
  if (!audio) return;
  const [a, dest] = audio;
  const t = a.currentTime;
  const o = a.createOscillator();
  o.type = "sine";
  o.frequency.setValueAtTime(240, t);
  o.frequency.exponentialRampToValueAtTime(70, t + 0.1);
  const g = a.createGain();
  g.gain.setValueAtTime(0.0001, t);
  g.gain.exponentialRampToValueAtTime(0.5, t + 0.008);
  g.gain.exponentialRampToValueAtTime(0.0001, t + 0.14);
  o.connect(g).connect(dest);
  o.start(t);
  o.stop(t + 0.15);
  scurry(16);
}

// The music box: an own little waltz in D minor, played on the tines of a music box that is slightly out of tune and
// wobbles a little, with some reverb. Each round slows down at its end; every third round the spring runs down, the
// tune sinks and stops, and the box is wound up again before it starts over.

// the chords of the accompaniment as MIDI notes: the bass on the first beat, the other two on the second and third
const DM = [62, 65, 69], A = [57, 61, 64], A7 = [57, 61, 67], GM = [55, 62, 70], BB = [58, 62, 65];
// the tune, bar by bar: [MIDI note or 0 for a rest, beats]
const BARS: { notes: [number, number][]; chord: number[] }[] = [
  { notes: [[81, 1], [86, 1], [89, 1]], chord: DM },
  { notes: [[88, 2], [86, 1]], chord: DM },
  { notes: [[85, 1], [88, 1], [81, 1]], chord: A },
  { notes: [[86, 3]], chord: DM },
  { notes: [[89, 1], [88, 1], [86, 1]], chord: DM },
  { notes: [[82, 2], [81, 1]], chord: GM },
  { notes: [[79, 1], [82, 1], [76, 1]], chord: A7 },
  { notes: [[81, 3]], chord: A },
  { notes: [[93, 1], [92, 1], [91, 1]], chord: DM },
  { notes: [[90, 1], [89, 1], [88, 1]], chord: DM },
  { notes: [[87, 1], [86, 1], [85, 1]], chord: A7 },
  { notes: [[86, 2], [0, 1]], chord: DM },
  { notes: [[82, 1], [86, 1], [91, 1]], chord: GM },
  { notes: [[89, 1.5], [88, 0.5], [86, 1]], chord: BB },
  { notes: [[85, 1], [81, 1], [88, 1]], chord: A7 },
  { notes: [[86, 3]], chord: DM },
];
const BEATS = BARS.length * 3, BEAT = 0.6, MUSIC = 0.4;

let bus: GainNode | null = null;
let wow: OscillatorNode | null = null;
let wowDepth: GainNode | null = null;
let timer = 0;
let pass = 0;
let passEnd = 0;
let queue: { at: number; play: () => void }[] = [];

// a soft hall: two and a half seconds of decaying noise
function hall(a: AudioContext): AudioBuffer {
  const len = Math.floor(a.sampleRate * 2.5), buffer = a.createBuffer(2, len, a.sampleRate);
  for (let c = 0; c < 2; c++) {
    const d = buffer.getChannelData(c);
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 3);
  }
  return buffer;
}

function startMusic() {
  if (bus || !ctx || !out) return;
  const a = ctx;
  bus = a.createGain();
  bus.gain.setValueAtTime(0.0001, a.currentTime);
  bus.gain.exponentialRampToValueAtTime(MUSIC, a.currentTime + 2.5);
  const verb = a.createConvolver();
  verb.buffer = hall(a);
  const wet = a.createGain();
  wet.gain.value = 0.5;
  bus.connect(out);
  bus.connect(verb).connect(wet).connect(out);
  // the wobble of an old mechanism: all tines drift a few cents up and down together
  wow = a.createOscillator();
  wow.frequency.value = 0.23;
  wowDepth = a.createGain();
  wowDepth.gain.value = 9;
  wow.connect(wowDepth);
  wow.start();
  pass = 0;
  queue = [];
  passEnd = a.currentTime + 0.3;
  timer = window.setInterval(tick, 100);
  tick();
}

function stopMusic() {
  if (!bus || !ctx) return;
  clearInterval(timer);
  queue = [];
  const fading = bus, lfo = wow;
  bus = null;
  fading.gain.cancelScheduledValues(ctx.currentTime);
  fading.gain.setTargetAtTime(0.0001, ctx.currentTime, 0.4);
  setTimeout(() => {
    fading.disconnect();
    lfo?.stop();
  }, 3000);
}

// the music goes quiet while thunder rolls and comes back as it fades
function duck(t: number, len: number, depth: number) {
  if (!bus) return;
  bus.gain.cancelScheduledValues(t);
  bus.gain.setTargetAtTime(MUSIC * depth, t, 0.1);
  bus.gain.setTargetAtTime(MUSIC, t + len * 0.45, len * 0.12);
}

// plays the notes of the next few tenths of a second, and plans the next round in time
function tick() {
  if (!ctx || !bus) return;
  const horizon = ctx.currentTime + 0.4;
  if (!queue.length && passEnd < horizon + 1) plan();
  while (queue.length && queue[0].at < horizon) queue.shift()!.play();
}

// one round of the tune from `passEnd` on
function plan() {
  const start = passEnd, windDown = pass % 3 === 2;
  pass++;
  // the start of every beat: the last two bars slow down, much more when the spring runs down
  const at = [0];
  for (let i = 0; i < BEATS; i++) {
    const late = Math.max(0, (i - (BEATS - 7)) / 6);
    at.push(at[i] + BEAT * (1 + late * (windDown ? 1.6 : 0.4)));
  }
  const time = (beat: number) => {
    const i = Math.floor(beat);
    return start + at[i] + (at[i + 1] - at[i]) * (beat - i);
  };
  // when the spring runs down the tune sinks over the last three bars
  const sink = (beat: number) => (windDown ? -45 * Math.max(0, (beat - (BEATS - 9)) / 9) : 0);
  const notes: { at: number; play: () => void }[] = [];
  const note = (beat: number, midi: number, level: number) =>
    notes.push({ at: time(beat), play: () => tine(time(beat), midi, level, sink(beat)) });
  BARS.forEach(({ notes: melody, chord }, bar) => {
    let beat = bar * 3;
    for (const [midi, beats] of melody) {
      if (midi) note(beat, midi, 0.5);
      beat += beats;
    }
    note(bar * 3, chord[0], 0.26);
    for (const b of [1, 2]) for (const m of chord.slice(1)) note(bar * 3 + b, m, 0.13);
  });
  passEnd = start + at[BEATS] + BEAT;
  if (windDown) {
    const wind = passEnd + 2.5;
    notes.push({ at: wind, play: () => ratchet(wind) });
    passEnd = wind + 2;
  }
  queue = notes.sort((x, y) => x.at - y.at);
}

// a tine of the music box: a sine with a bright, quickly fading partial and the click of the pin
function tine(t: number, midi: number, level: number, cents: number) {
  if (!ctx || !bus) return;
  const a = ctx, f = 440 * Math.pow(2, (midi - 69) / 12), tau = clamp(1.1 - (midi - 62) * 0.025, 0.25, 1.1);
  const detune = cents + rand(-7, 7);
  for (const [ratio, part, length] of [[1, 1, 1], [4.02, 0.22, 0.15]]) {
    const o = a.createOscillator();
    o.frequency.value = f * ratio;
    o.detune.value = detune;
    if (wowDepth) wowDepth.connect(o.detune);
    const g = a.createGain();
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(level * part, t + 0.004);
    g.gain.setTargetAtTime(0, t + 0.004, tau * length);
    o.connect(g).connect(bus);
    o.start(t);
    o.stop(t + 0.01 + tau * length * 7);
  }
  const pin = a.createBufferSource();
  pin.buffer = noise(a, "white");
  const hp = a.createBiquadFilter();
  hp.type = "highpass";
  hp.frequency.value = 3000;
  const pg = a.createGain();
  pg.gain.setValueAtTime(level * 0.12, t);
  pg.gain.exponentialRampToValueAtTime(0.0001, t + 0.006);
  pin.connect(hp).connect(pg).connect(bus);
  pin.start(t, rand(0, 1.5));
  pin.stop(t + 0.01);
}

// the box is wound up again: a ratchet of a dozen clicks
function ratchet(t: number) {
  if (!ctx || !bus) return;
  const a = ctx, src = a.createBufferSource();
  src.buffer = noise(a, "white");
  const bp = a.createBiquadFilter();
  bp.type = "bandpass";
  bp.frequency.value = 2500;
  bp.Q.value = 4;
  const g = a.createGain();
  g.gain.value = 0;
  src.connect(bp).connect(g).connect(bus);
  let at = t;
  for (let i = 0; i < 12; i++) {
    g.gain.setValueAtTime(0, at);
    g.gain.linearRampToValueAtTime(1.2, at + 0.002);
    g.gain.exponentialRampToValueAtTime(0.0001, at + 0.03);
    at += rand(0.09, 0.13);
  }
  src.start(t, rand(0, 0.5));
  src.stop(at + 0.05);
}

// at the end, once everything above is set up: coming from a click on another page of the site, the browser may
// already allow sound (Chromium carries the click over); then it starts at once, without waiting for another click
if (navigator.userActivation?.hasBeenActive) unlock();
sync();
