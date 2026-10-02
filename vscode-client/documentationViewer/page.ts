import { NamedAnchor, PageMessage } from "./protocol";

export interface OutlineEntry {
  id: string;
  title: string;
  kind: "keyword" | "type" | "heading";
}

export interface OutlineSection {
  id: string;
  title: string;
  children: OutlineEntry[];
  // Entries without headings, from the JSON when the page could not be rendered; choosing one only selects it.
  static?: boolean;
}

const KEYWORDS = "Keywords";
const DATA_TYPES = "Data types";
// A click on an image map's area reaches neither our link handler nor VS Code's, which handle only `a`.
const REMOVED_ELEMENTS = "script, style, link, meta, base, iframe, frame, frameset, object, embed, area";

// No `<` or quote in tag and attribute names: crafted text with many unclosed tags would otherwise take quadratic time.
const TAG = /<[A-Za-z][^\s/<>"']*(?:\s+[^\s"'<>/=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'=<>`]+))?)*\s*\/?>/g;
const ATTRIBUTE = /(\s+)([^\s"'<>/=]+)(\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'=<>`]+))?/g;

function isBlocked(name: string): boolean {
  const lower = name.toLowerCase();
  return lower === "style" || lower.startsWith("on");
}

// Chromium checks `style` attributes against the content security policy while it parses HTML, also into an
// inert template, and inline event handlers when they fire, so both are removed from the text before it is parsed.
function removeBlockedAttributes(html: string): string {
  return html.replace(TAG, (tag) =>
    tag.replace(ATTRIBUTE, (attribute: string, _space: string, name: string) => (isBlocked(name) ? "" : attribute)),
  );
}

// Scrolls `container` so that `element` is at its top, without scrolling the frames around the page as
// `scrollIntoView` does.
export function scrollToTop(container: HTMLElement, element: HTMLElement): void {
  container.scrollTop += element.getBoundingClientRect().top - container.getBoundingClientRect().top;
}

function headingText(heading: Element): string {
  return (heading.textContent ?? "").trim();
}

// The h3 headings under `Keywords` and `Data types` get the anchors of the JSON, so that keyword and type
// links hold even where VS Code's heading ids differ. Only when the counts match.
function assignAnchors(root: DocumentFragment, keywords: NamedAnchor[], types: NamedAnchor[]): void {
  const sections = new Map<string, HTMLElement[]>();
  let current: HTMLElement[] | undefined;

  for (const heading of root.querySelectorAll<HTMLElement>("h2, h3")) {
    if (heading.tagName === "H2") {
      const title = headingText(heading);
      current = title === KEYWORDS || title === DATA_TYPES ? [] : undefined;
      if (current !== undefined) sections.set(title, current);
    } else {
      current?.push(heading);
    }
  }

  for (const [title, entries] of [
    [KEYWORDS, keywords],
    [DATA_TYPES, types],
  ] as const) {
    const headings = sections.get(title);
    if (headings === undefined || headings.length !== entries.length) continue;
    headings.forEach((heading, i) => {
      if (entries[i].anchor) heading.id = entries[i].anchor;
      heading.dataset.name = entries[i].name;
    });
  }
}

export function renderPage(main: HTMLElement, page: PageMessage): void {
  if (page.html === undefined) {
    const notice = document.createElement("div");
    notice.className = "notice";
    notice.textContent =
      'The page needs VS Code\'s built-in extension "Markdown Language Features". Enable it to see the formatted page.';
    const pre = document.createElement("pre");
    pre.className = "raw-markdown";
    pre.textContent = page.markdown ?? "";
    main.replaceChildren(notice, pre);
    return;
  }

  // Parsed inert: nothing in it runs or loads until it is moved into the page.
  const template = document.createElement("template");
  template.innerHTML = removeBlockedAttributes(page.html);
  const content = template.content;

  const mermaid = content.querySelector("span#markdown-mermaid");
  if (mermaid?.parentNode === content) mermaid.remove();
  // Documentation has no use for elements that load, style or navigate outside the page; a meta refresh would
  // navigate the viewer away.
  for (const element of content.querySelectorAll(REMOVED_ELEMENTS)) element.remove();
  // What the text pass missed, such as attributes after a `/` in a tag.
  for (const element of content.querySelectorAll("*")) {
    for (const name of element.getAttributeNames()) if (isBlocked(name)) element.removeAttribute(name);
  }
  assignAnchors(content, page.keywords, page.types);

  main.replaceChildren(content);
}

export function buildOutline(main: HTMLElement, page: PageMessage): OutlineSection[] {
  if (page.html === undefined) {
    return [
      {
        id: "keywords",
        title: KEYWORDS,
        static: true,
        children: page.keywords.map((k) => ({ id: k.anchor, title: k.name, kind: "keyword" as const })),
      },
      {
        id: "data-types",
        title: DATA_TYPES,
        static: true,
        children: page.types.map((t) => ({ id: t.anchor, title: t.name, kind: "type" as const })),
      },
    ].filter((s) => s.children.length > 0);
  }

  const sections: OutlineSection[] = [];
  let section: OutlineSection | undefined;

  for (const heading of main.querySelectorAll<HTMLElement>("h2, h3")) {
    if (heading.tagName === "H2") {
      // Headings without an id, such as raw HTML headings, are left out, together with their entries.
      section = heading.id ? { id: heading.id, title: headingText(heading), children: [] } : undefined;
      if (section !== undefined) sections.push(section);
    } else if (section !== undefined && heading.id) {
      const kind = section.title === KEYWORDS ? "keyword" : section.title === DATA_TYPES ? "type" : "heading";
      section.children.push({ id: heading.id, title: heading.dataset.name ?? headingText(heading), kind });
    }
  }
  return sections;
}

// Finds a heading by the id of a link, raw and then decoded.
export function findHeading(main: HTMLElement, id: string): HTMLElement | undefined {
  let decoded = id;
  try {
    decoded = decodeURIComponent(id);
  } catch {
    // keep the raw id
  }
  for (const candidate of [id, decoded]) {
    // Inside the page: the document has elements with ids of its own, such as `root`.
    const element = candidate ? main.querySelector<HTMLElement>(`#${CSS.escape(candidate)}`) : null;
    if (element !== null) return element;
  }
  return undefined;
}
