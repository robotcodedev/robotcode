// The find bar's search: matches in the text of the page, across inline elements, marked with the
// CSS Custom Highlight API.

const MATCHES = "documentation-find";
const CURRENT = "documentation-find-current";

// The text of different blocks is kept apart, so that a match does not run from a heading into the next paragraph.
const BLOCKS =
  "address, blockquote, dd, details, div, dl, dt, figcaption, figure, h1, h2, h3, h4, h5, h6, hr, li, main, ol, " +
  "p, pre, section, summary, table, tbody, td, tfoot, th, thead, tr, ul";
const BLOCK_BREAK = "\u0000";

// Whitespace in the search text matches any whitespace: the Markdown keeps the line breaks of the documentation,
// which the page shows as spaces.
function pattern(text: string): RegExp {
  return new RegExp(
    text
      .split(/\s+/u)
      .map((part) => part.replace(/[\\^$.*+?()[\]{}|/]/gu, "\\$&"))
      .join("\\s+"),
    "giu",
  );
}

export class PageFinder {
  private _ranges: Range[] = [];
  private _current = -1;

  constructor(private readonly main: HTMLElement) {}

  get count(): number {
    return this._ranges.length;
  }

  get current(): number {
    return this._current;
  }

  // `reveal` scrolls to the first match. Without it, as for a new page that is already positioned, the first match
  // in view becomes the current one and the page stays where it is.
  search(text: string, reveal = true): void {
    this._ranges = [];
    this._current = -1;

    if (text) {
      const nodes: Text[] = [];
      const starts: number[] = [];
      let haystack = "";
      let block: Element | null = null;
      const walker = document.createTreeWalker(this.main, NodeFilter.SHOW_TEXT);
      for (let node = walker.nextNode(); node !== null; node = walker.nextNode()) {
        const nodeBlock = node.parentElement?.closest(BLOCKS) ?? null;
        if (nodes.length > 0 && nodeBlock !== block) haystack += BLOCK_BREAK;
        block = nodeBlock;
        nodes.push(node as Text);
        starts.push(haystack.length);
        haystack += (node as Text).data;
      }

      const locate = (offset: number, end: boolean): [Text, number] => {
        let low = 0;
        let high = nodes.length - 1;
        while (low < high) {
          const middle = Math.ceil((low + high) / 2);
          if (starts[middle] < offset || (!end && starts[middle] === offset)) low = middle;
          else high = middle - 1;
        }
        return [nodes[low], offset - starts[low]];
      };

      for (const match of haystack.matchAll(pattern(text))) {
        if (match[0].length === 0) continue;
        const range = document.createRange();
        range.setStart(...locate(match.index, false));
        range.setEnd(...locate(match.index + match[0].length, true));
        this._ranges.push(range);
      }
      if (this._ranges.length > 0) this._current = reveal ? 0 : this.firstInView();
    }
    this.paint(reveal);
  }

  next(): void {
    this.move(1);
  }

  previous(): void {
    this.move(-1);
  }

  clear(): void {
    this._ranges = [];
    this._current = -1;
    CSS.highlights.delete(MATCHES);
    CSS.highlights.delete(CURRENT);
  }

  private firstInView(): number {
    const top = this.main.getBoundingClientRect().top;
    const index = this._ranges.findIndex((range) => range.getBoundingClientRect().bottom > top);
    return index >= 0 ? index : 0;
  }

  private move(step: number): void {
    if (this._ranges.length === 0) return;
    this._current = (this._current + step + this._ranges.length) % this._ranges.length;
    this.paint(true);
  }

  private paint(reveal: boolean): void {
    CSS.highlights.set(MATCHES, new Highlight(...this._ranges));
    if (this._current < 0) {
      CSS.highlights.delete(CURRENT);
      return;
    }
    const range = this._ranges[this._current];
    CSS.highlights.set(CURRENT, new Highlight(range));
    if (!reveal) return;

    const rect = range.getBoundingClientRect();
    const view = this.main.getBoundingClientRect();
    if (rect.top < view.top || rect.bottom > view.bottom) {
      this.main.scrollTop += rect.top - view.top - this.main.clientHeight / 3;
    }
  }
}
