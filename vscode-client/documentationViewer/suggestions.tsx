import { JSX, RefObject } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { TargetCompletion } from "./protocol";

const ICONS: Record<string, string> = {
  FOLDER: "folder",
  MODULE: "symbol-module",
  MODULE_INTERNAL: "symbol-module",
};

export interface SuggestionListProps {
  // Holds the list, for the target field's references to it.
  listRef: RefObject<HTMLDivElement | null>;
  // The target field the list lies under, and its text.
  field: HTMLElement;
  text: string;
  completions: TargetCompletion[];
  active: number;
  onChoose(index: number): void;
}

// The list of suggestions under the target field. It is placed by the field's box, so that the toolbar does not clip
// it, and a mouse down on it keeps the focus in the field, which closes the list when it loses the focus. Its classes
// are unlike those of a documentation's own HTML, which the page keeps.
export function SuggestionList({
  listRef,
  field,
  text,
  completions,
  active,
  onChoose,
}: SuggestionListProps): JSX.Element {
  const [, setLayout] = useState(0);
  const activeRow = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const resize = () => setLayout((v) => v + 1);
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, []);

  // The selected row comes into view, without scrollIntoView, which would scroll the frames around the page as well.
  useEffect(() => {
    const container = listRef.current;
    const element = activeRow.current;
    if (!container || !element) return;
    const top = element.getBoundingClientRect().top - container.getBoundingClientRect().top;
    if (top < 0) container.scrollTop += top;
    else if (top + element.offsetHeight > container.clientHeight)
      container.scrollTop += top + element.offsetHeight - container.clientHeight;
  }, [active, completions]);

  const box = field.getBoundingClientRect();
  return (
    <div
      ref={listRef}
      class="target-suggestions"
      role="listbox"
      aria-label="Suggestions"
      style={{ left: `${box.left}px`, top: `${box.bottom + 2}px`, width: `${box.width}px` }}
      onMouseDown={(event) => event.preventDefault()}
    >
      {completions.map((completion, index) => {
        // The part of the label that is typed already.
        const typed = Math.max(0, text.length - completion.start);
        return (
          <div
            key={`${completion.start}:${completion.kind}:${completion.label}`}
            ref={index === active ? activeRow : undefined}
            class={index === active ? "target-suggestion active" : "target-suggestion"}
            role="option"
            aria-selected={index === active}
            onClick={() => onChoose(index)}
          >
            <span class={`codicon codicon-${ICONS[completion.kind] ?? "file"}`} aria-hidden="true" />
            <span class="label">
              <b>{completion.label.slice(0, typed)}</b>
              {completion.label.slice(typed)}
            </span>
            <span class="detail">{completion.detail}</span>
          </div>
        );
      })}
    </div>
  );
}
