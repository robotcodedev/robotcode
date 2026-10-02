// The pattern rules of `robotcode doc keywords`: Robot Framework's
// `MultiMatcher([f"*{text}*"], ignore="_")`, which normalizes like
// `robot.utils.normalize` and translates the pattern like Python's `fnmatch.translate`.

const STAR = Symbol("*");
type Part = string | typeof STAR;

// Robot Framework normalizes with `str.casefold()`; upper- and then lower-casing comes close to it (`ß` is `ss`).
function normalize(text: string): string {
  return text.replace(/\s+/gu, "").toUpperCase().toLowerCase().replaceAll("_", "");
}

function escape(c: string): string {
  return c.replace(/[\\^$.*+?()[\]{}|/]/gu, "\\$&");
}

function indexOf(chars: string[], c: string, start: number, end: number): number {
  for (let i = start; i < end; i++) if (chars[i] === c) return i;
  return -1;
}

function translateParts(pattern: string): Part[] {
  const pat = Array.from(pattern);
  const n = pat.length;
  const slice = (a: number, b: number) => pat.slice(a, b).join("");
  const res: Part[] = [];

  let i = 0;
  while (i < n) {
    const c = pat[i];
    i++;
    if (c === "*") {
      if (res.length === 0 || res[res.length - 1] !== STAR) res.push(STAR);
    } else if (c === "?") {
      res.push(".");
    } else if (c === "[") {
      let j = i;
      if (j < n && pat[j] === "!") j++;
      if (j < n && pat[j] === "]") j++;
      while (j < n && pat[j] !== "]") j++;

      if (j >= n) {
        res.push("\\[");
        continue;
      }

      let stuff: string;
      if (indexOf(pat, "-", i, j) < 0) {
        stuff = slice(i, j).replaceAll("\\", "\\\\");
      } else {
        const chunks: string[] = [];
        let k = pat[i] === "!" ? i + 2 : i + 1;
        for (;;) {
          k = indexOf(pat, "-", k, j);
          if (k < 0) break;
          chunks.push(slice(i, k));
          i = k + 1;
          k = k + 3;
        }
        const chunk = slice(i, j);
        if (chunk) chunks.push(chunk);
        else chunks[chunks.length - 1] += "-";

        // Remove empty ranges, as fnmatch does.
        for (let m = chunks.length - 1; m > 0; m--) {
          const previous = Array.from(chunks[m - 1]);
          const next = Array.from(chunks[m]);
          if (previous.length === 0 || next.length === 0) throw new Error("invalid pattern");
          if ((previous[previous.length - 1].codePointAt(0) ?? 0) > (next[0].codePointAt(0) ?? 0)) {
            chunks[m - 1] = previous.slice(0, -1).join("") + next.slice(1).join("");
            chunks.splice(m, 1);
          }
        }
        stuff = chunks.map((s) => s.replaceAll("\\", "\\\\").replaceAll("-", "\\-")).join("-");
      }
      i = j + 1;
      // A `]` in the set is literal in Python's re, but ends the set in JavaScript.
      stuff = stuff.replaceAll("]", "\\]");

      if (!stuff) {
        res.push("(?!)");
      } else if (stuff === "!") {
        res.push(".");
      } else {
        if (stuff[0] === "!") stuff = "^" + stuff.slice(1);
        else if (stuff[0] === "^" || stuff[0] === "[") stuff = "\\" + stuff;
        res.push(`[${stuff}]`);
      }
    } else {
      res.push(escape(c));
    }
  }
  return res;
}

export function translate(pattern: string): string {
  const parts = translateParts(pattern);
  const n = parts.length;
  let res = "";
  let group = 0;
  let i = 0;
  while (i < n && parts[i] !== STAR) res += parts[i++] as string;
  while (i < n) {
    i++; // the star
    if (i === n) {
      res += ".*";
      break;
    }
    let fixed = "";
    while (i < n && parts[i] !== STAR) fixed += parts[i++] as string;
    // fnmatch puts an atomic group here, so that many stars cannot backtrack exponentially. JavaScript has none; a
    // lookahead is atomic, and the backreference consumes what it matched, as in Python 3.10's fnmatch.
    res += i === n ? `.*${fixed}` : `(?=(.*?${fixed}))\\${++group}`;
  }
  return `^(?:${res})$`;
}

// A matcher for the filter text; an invalid pattern matches nothing.
export function createMatcher(text: string): (title: string) => boolean {
  let regex: RegExp | undefined;
  try {
    regex = new RegExp(translate(normalize(`*${text}*`)), "su");
  } catch {
    regex = undefined;
  }
  return (title) => regex !== undefined && regex.test(normalize(title));
}
