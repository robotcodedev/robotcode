import { JSX } from "preact";
import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import { createMatcher } from "./matcher";
import { OutlineEntry, OutlineSection } from "./page";

interface Row {
  id: string;
  title: string;
  level: 1 | 2;
  icon: string;
  section: OutlineSection;
  expanded?: boolean;
}

const ICONS: Record<OutlineEntry["kind"], string> = {
  keyword: "symbol-method",
  type: "symbol-class",
  heading: "symbol-key",
};

// The visible rows: an h2 stays while it or one of its entries matches; branches are open while a filter is set.
function visibleRows(sections: OutlineSection[], filter: string, collapsed: Set<string>): Row[] {
  const match = filter ? createMatcher(filter) : undefined;
  const rows: Row[] = [];

  for (const section of sections) {
    const children = match ? section.children.filter((c) => match(c.title)) : section.children;
    if (match && children.length === 0 && !match(section.title)) continue;

    const expanded = match !== undefined || !collapsed.has(section.id);
    rows.push({
      id: section.id,
      title: section.title,
      level: 1,
      icon: "symbol-namespace",
      section,
      expanded: section.children.length > 0 ? expanded : undefined,
    });
    if (expanded) {
      for (const child of children) {
        rows.push({ id: child.id, title: child.title, level: 2, icon: ICONS[child.kind], section });
      }
    }
  }
  return rows;
}

export interface OutlineProps {
  sections: OutlineSection[];
  filter: string;
  collapsed: string[];
  selected: string | undefined;
  onChoose(id: string, section: OutlineSection): void;
  onToggle(id: string): void;
}

export function Outline({ sections, filter, collapsed, selected, onChoose, onToggle }: OutlineProps): JSX.Element {
  const rows = useMemo(() => visibleRows(sections, filter, new Set(collapsed)), [sections, filter, collapsed]);
  const [focused, setFocused] = useState<string | undefined>(undefined);
  const tree = useRef<HTMLDivElement>(null);
  const typed = useRef({ text: "", time: 0 });

  const focusedIndex = Math.max(
    0,
    rows.findIndex((r) => r.id === (focused ?? selected)),
  );

  useEffect(() => {
    if (tree.current?.contains(document.activeElement)) {
      tree.current.querySelector<HTMLElement>('[tabindex="0"]')?.focus();
    }
  }, [focusedIndex, rows]);

  const rowElement = (id: string) => tree.current?.querySelector<HTMLElement>(`[data-id="${CSS.escape(id)}"]`);

  // Without scrollIntoView, which would scroll the frames around the page as well.
  const reveal = (element: HTMLElement | null | undefined) => {
    const container = tree.current;
    if (!element || !container) return;
    const top = element.getBoundingClientRect().top - container.getBoundingClientRect().top;
    if (top < 0) container.scrollTop += top;
    else if (top + element.offsetHeight > container.clientHeight)
      container.scrollTop += top + element.offsetHeight - container.clientHeight;
  };

  // The page shows another heading, or a new page: its entry comes into view. Not on filter changes, which would jump.
  useEffect(() => {
    if (selected !== undefined) reveal(rowElement(selected));
  }, [selected, sections]);

  const moveTo = (index: number) => {
    const row = rows[Math.max(0, Math.min(rows.length - 1, index))];
    if (row === undefined) return;
    setFocused(row.id);
    const element = rowElement(row.id);
    element?.focus({ preventScroll: true });
    reveal(element);
  };

  const pageSize = () => {
    const item = tree.current?.querySelector<HTMLElement>(".row");
    return item && tree.current ? Math.max(1, Math.floor(tree.current.clientHeight / item.offsetHeight) - 1) : 10;
  };

  const onKeyDown = (event: KeyboardEvent) => {
    // Combinations with Alt, Ctrl or Cmd are left to the page and to VS Code.
    if (event.altKey || event.ctrlKey || event.metaKey || rows.length === 0) return;

    const row = rows[focusedIndex];
    switch (event.key) {
      case "ArrowDown":
        moveTo(focusedIndex + 1);
        break;
      case "ArrowUp":
        moveTo(focusedIndex - 1);
        break;
      case "ArrowRight":
        if (row.expanded === false) onToggle(row.id);
        else if (row.expanded === true) moveTo(focusedIndex + 1);
        break;
      case "ArrowLeft":
        if (row.expanded === true && !filter) onToggle(row.id);
        else if (row.level === 2) moveTo(rows.findIndex((r) => r.id === row.section.id));
        break;
      case "Home":
        moveTo(0);
        break;
      case "End":
        moveTo(rows.length - 1);
        break;
      case "PageDown":
        moveTo(focusedIndex + pageSize());
        break;
      case "PageUp":
        moveTo(focusedIndex - pageSize());
        break;
      case "Enter":
        onChoose(row.id, row.section);
        break;
      default: {
        if (event.key.length !== 1) return;
        // Typing moves to the next visible entry whose title starts with the typed text.
        const now = Date.now();
        typed.current = { text: (now - typed.current.time < 700 ? typed.current.text : "") + event.key, time: now };
        const text = typed.current.text.toLowerCase();
        const start = typed.current.text.length > 1 ? focusedIndex : focusedIndex + 1;
        for (let i = 0; i < rows.length; i++) {
          const index = (start + i) % rows.length;
          if (rows[index].title.toLowerCase().startsWith(text)) {
            moveTo(index);
            break;
          }
        }
      }
    }
    event.preventDefault();
  };

  return (
    <div class="outline" role="tree" aria-label="Outline" ref={tree} onKeyDown={onKeyDown}>
      {rows.map((row, index) => (
        <div
          key={row.id}
          data-id={row.id}
          class={`row level-${row.level}${row.id === selected ? " selected" : ""}`}
          role="treeitem"
          aria-level={row.level}
          aria-expanded={row.expanded}
          aria-selected={row.id === selected}
          tabIndex={index === focusedIndex ? 0 : -1}
          title={row.title}
          onClick={() => {
            setFocused(row.id);
            onChoose(row.id, row.section);
          }}
        >
          {row.level === 1 && (
            <span
              class={`twistie codicon ${row.expanded === undefined ? "" : row.expanded ? "codicon-chevron-down" : "codicon-chevron-right"}`}
              onClick={(event) => {
                event.stopPropagation();
                if (row.expanded !== undefined && !filter) onToggle(row.id);
              }}
            />
          )}
          <span class={`codicon codicon-${row.icon}`} />
          <span class="label">{row.title}</span>
        </div>
      ))}
    </div>
  );
}
