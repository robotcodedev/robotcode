import { JSX } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { PageFinder } from "./find";
import { Outline } from "./outline";
import { buildOutline, findHeading, OutlineSection, renderPage, scrollToTop } from "./page";
import {
  ExtensionMessage,
  HistoryEntry,
  loadState,
  PageMessage,
  post,
  saveState,
  ShowMessage,
  ViewerState,
  WorkspaceFolderInfo,
} from "./protocol";

const MAX_HISTORY = 50;
const IS_MAC = /Mac|iPhone|iPad/.test(navigator.platform);

interface Target {
  folder: string;
  text: string;
}

function sameTarget(a: Target | undefined, b: Target | undefined): boolean {
  return a !== undefined && b !== undefined && a.folder === b.folder && a.text === b.text;
}

function normalizeName(name: string): string {
  return name.replace(/[\s_]/gu, "").toLowerCase();
}

function newId(): string {
  return typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

interface TextField extends HTMLElement {
  value: string;
  updateComplete: Promise<boolean>;
  wrappedElement: HTMLInputElement;
}

export class Controller {
  state: ViewerState;
  // The page shown in `main`, and its outline.
  page: PageMessage | undefined;
  sections: OutlineSection[] = [];
  busy = false;
  error: string | undefined;
  // Choosing an entry of an outline without headings only selects it.
  outlineSelection: string | undefined;
  findOpen = false;
  findText = "";
  // Bumped to ask the page to focus the target field or the find field.
  focusTarget = 0;
  focusFind = 0;
  folders: WorkspaceFolderInfo[] = [];

  // Not from 0: a recreated page would reuse the numbers of its previous instance, and a load of that instance that
  // is still waiting in the extension would answer this page.
  private _seq = Date.now();
  // The entry whose keyword was not on its page and that was loaded again for it.
  private _keywordRefresh: HistoryEntry | undefined;
  // The load for which a generation ran: its page without `busy` is the generated one.
  private _generatedSeq = -1;
  private _loading = -1;
  private _pageSeq = -1;
  private _main!: HTMLElement;
  private _finder!: PageFinder;
  private readonly _listeners = new Set<() => void>();
  private _saveTimer: number | undefined;
  private _lastSave = 0;
  // The headings of the page with their offsets, for the width they were measured at.
  private _headings: { id: string; top: number }[] | undefined;
  private _headingsWidth = -1;

  constructor() {
    this.state = loadState() ?? { v: 1, id: "", history: [], index: -1, filter: "", collapsed: [], pinned: false };
    if (!this.state.id) this.state.id = newId();
  }

  get entry(): HistoryEntry | undefined {
    return this.state.history[this.state.index];
  }

  get canGoBack(): boolean {
    return this.state.index > 0;
  }

  get canGoForward(): boolean {
    return this.state.index < this.state.history.length - 1;
  }

  get findCount(): number {
    return this._finder?.count ?? 0;
  }

  get findCurrent(): number {
    return this._finder?.current ?? -1;
  }

  get selected(): string | undefined {
    return this.outlineSelection ?? this.entry?.anchor;
  }

  // The name of the current entry's workspace folder; a folder that is gone from the workspace by its URI.
  get folderName(): string | undefined {
    const folder = this.entry?.folder;
    if (!folder) return undefined;
    const known = this.folders.find((f) => f.uri === folder);
    if (known !== undefined) return known.name;
    const segment = folder.replace(/\/+$/u, "").split("/").pop() ?? folder;
    try {
      return decodeURIComponent(segment);
    } catch {
      return segment;
    }
  }

  subscribe(listener: () => void): () => void {
    this._listeners.add(listener);
    return () => this._listeners.delete(listener);
  }

  start(main: HTMLElement): void {
    this._main = main;
    this._finder = new PageFinder(main);

    main.addEventListener(
      "scroll",
      () => {
        if (this.recordPosition()) this.save(true);
      },
      { passive: true },
    );
    window.addEventListener("message", (event: MessageEvent<ExtensionMessage>) => this.onMessage(event.data));
    window.addEventListener("click", this.onClick, true);
    window.addEventListener("keydown", this.onKeyDown, true);
    window.addEventListener("mousedown", this.onMouse, true);
    window.addEventListener("mouseup", this.onMouse, true);

    post({ type: "ready", state: this.state });
    const entry = this.entry;
    if (entry !== undefined) this.load(entry, false);
  }

  submit(text: string): void {
    text = text.trim();
    if (!text) return;

    const entry = this.entry;
    // Entering the target that is shown only refreshes it.
    if (entry !== undefined && entry.text === text) {
      this.load(entry, true);
      return;
    }
    this.navigate({ folder: entry?.folder ?? "", text }, true);
  }

  refresh(): void {
    const entry = this.entry;
    if (entry !== undefined) this.load(entry, true);
  }

  back(): void {
    this.go(-1);
  }

  forward(): void {
    this.go(1);
  }

  choose(id: string, section: OutlineSection): void {
    if (section.static) {
      this.outlineSelection = id;
      this.changed();
      return;
    }
    this.showAnchor(id);
  }

  setFilter(filter: string): void {
    this.state.filter = filter;
    this.save(true);
    this.changed();
  }

  toggle(id: string): void {
    const collapsed = new Set(this.state.collapsed);
    if (!collapsed.delete(id)) collapsed.add(id);
    this.state.collapsed = [...collapsed];
    this.save();
    this.changed();
  }

  setSplit(position: string): void {
    this.state.split = position;
    this.save(true);
  }

  setPinned(pinned: boolean): void {
    this.state.pinned = pinned;
    post({ type: "pin", pinned });
    this.save();
    this.changed();
  }

  openFind(): void {
    const selection = window.getSelection();
    if (selection !== null && !selection.isCollapsed && this._main.contains(selection.anchorNode)) {
      this.findText = selection.toString().split("\n")[0];
    }
    this.findOpen = true;
    this.focusFind++;
    this._finder.search(this.findText);
    this.changed();
  }

  find(text: string): void {
    this.findText = text;
    this._finder.search(text);
    this.changed();
  }

  findNext(): void {
    this._finder.next();
    this.changed();
  }

  findPrevious(): void {
    this._finder.previous();
    this.changed();
  }

  closeFind(): void {
    this.findOpen = false;
    this._finder.clear();
    this._main.focus();
    this.changed();
  }

  private changed(): void {
    for (const listener of this._listeners) listener();
  }

  // `later` throttles the saves of a scrolling page: the first one at once, then one every 100 ms. A hidden page is
  // gone at once, and a save from its pagehide no longer reaches VS Code.
  private save(later = false): void {
    if (later && performance.now() - this._lastSave < 100) {
      this._saveTimer ??= window.setTimeout(() => this.save(), 100);
      return;
    }
    if (this._saveTimer !== undefined) {
      window.clearTimeout(this._saveTimer);
      this._saveTimer = undefined;
    }
    this._lastSave = performance.now();
    saveState(this.state);
  }

  private headingTops(): { id: string; top: number }[] {
    const width = this._main.clientWidth;
    if (this._headings === undefined || this._headingsWidth !== width) {
      const origin = this._main.getBoundingClientRect().top - this._main.scrollTop;
      this._headings = Array.from(
        this._main.querySelectorAll<HTMLElement>("h1[id], h2[id], h3[id], h4[id], h5[id], h6[id]"),
        (heading) => ({ id: heading.id, top: heading.getBoundingClientRect().top - origin }),
      );
      this._headingsWidth = width;
    }
    return this._headings;
  }

  // Records where the current entry is: the offset, the width of the page and the heading at the top of the view.
  private recordPosition(): boolean {
    const entry = this.entry;
    if (entry === undefined || !sameTarget(entry, this.page)) return false;

    const scrollTop = this._main.scrollTop;
    const headings = this.headingTops();
    let heading: string | undefined;
    let low = 0;
    let high = headings.length - 1;
    while (low <= high) {
      const middle = (low + high) >> 1;
      if (headings[middle].top <= scrollTop + 1) {
        heading = headings[middle].id;
        low = middle + 1;
      } else {
        high = middle - 1;
      }
    }
    entry.position = { scrollTop, width: this._main.clientWidth, heading };
    return true;
  }

  // Adds a history entry and drops the forward entries.
  private push(entry: HistoryEntry): void {
    this.leave();
    const history = this.state.history.slice(0, this.state.index + 1);
    history.push(entry);
    while (history.length > MAX_HISTORY) history.shift();
    this.state.history = history;
    this.state.index = history.length - 1;
    this.save();
  }

  // Before the viewer leaves the current entry: its position, and no keyword that is still waiting for a page.
  private leave(): void {
    this.recordPosition();
    const entry = this.entry;
    if (entry?.keyword !== undefined) delete entry.keyword;
  }

  private navigate(entry: HistoryEntry, typed = false): void {
    this.push(entry);
    this.load(entry, false, typed);
  }

  private showAnchor(id: string): void {
    const entry = this.entry;
    if (entry === undefined) return;
    // The heading the current entry shows is only shown again.
    if (entry.anchor !== id || entry.keyword !== undefined)
      this.push({ folder: entry.folder, text: entry.text, anchor: id });
    this.reveal(id);
    this.changed();
  }

  private changeFolder(folder: string): void {
    const entry = this.entry;
    if (entry === undefined || entry.folder === folder) return;
    this.navigate({ folder, text: entry.text, anchor: entry.anchor });
  }

  private go(step: number): void {
    const index = this.state.index + step;
    if (index < 0 || index >= this.state.history.length) return;

    this.leave();
    this.state.index = index;
    this.save();

    const entry = this.state.history[index];
    if (sameTarget(entry, this.page)) {
      this.position(entry);
      this.changed();
    } else {
      this.load(entry, false);
    }
  }

  private position(entry: HistoryEntry): void {
    const position = entry.position;
    if (position === undefined) this.reveal(entry.anchor);
    else if (position.width === this._main.clientWidth) this._main.scrollTop = position.scrollTop;
    // In a page of another width, the offset points elsewhere; the heading that was at the top does not.
    else this.reveal(position.heading);
  }

  private reveal(anchor: string | undefined): void {
    const heading = anchor !== undefined ? findHeading(this._main, anchor) : undefined;
    if (heading !== undefined) scrollToTop(this._main, heading);
    else this._main.scrollTop = 0;
  }

  private load(entry: HistoryEntry, refresh: boolean, typed = false): void {
    this._loading = ++this._seq;
    this.busy = true;
    this.error = undefined;
    if (!sameTarget(entry, this.page)) {
      this.page = undefined;
      this._pageSeq = -1;
      this.sections = [];
      this.outlineSelection = undefined;
      this._main.replaceChildren();
      this._main.scrollTop = 0;
      this._headings = undefined;
      this._finder.search("");
    }
    post({
      type: "load",
      seq: this._loading,
      folder: entry.folder || undefined,
      text: entry.text,
      refresh,
      ...(typed ? { typed } : {}),
    });
    this.changed();
  }

  private onMessage(message: ExtensionMessage): void {
    switch (message.type) {
      case "page":
        this.onPage(message);
        break;
      case "status": {
        if (message.seq !== this._loading) return;
        if (message.busy) this._generatedSeq = message.seq;
        this.busy = message.busy;
        this.error = message.error;
        // The load ended without a page that has the keyword of its show.
        const entry = this.entry;
        if (!message.busy && entry?.keyword !== undefined) {
          delete entry.keyword;
          this.save();
        }
        this.changed();
        break;
      }
      case "show":
        this.onShow(message);
        break;
      case "pin":
        this.state.pinned = message.pinned;
        this.save();
        this.changed();
        break;
      case "folders":
        this.folders = message.folders;
        this.changed();
        break;
      case "folder":
        this.changeFolder(message.folder);
        break;
      case "focus":
        // The focus VS Code gives a webview while its page loads does not stick; the page takes it itself, unless
        // something in it has the focus already.
        if (document.activeElement === null || document.activeElement === document.body) this._main.focus();
        break;
    }
  }

  private onShow(show: ShowMessage): void {
    this.navigate({ folder: show.folder, text: show.text, keyword: show.keyword });
    if (show.focusTarget) this.focusTarget++;
    this.changed();
  }

  private onPage(page: PageMessage): void {
    if (page.seq !== this._loading) return;

    const entry = this.entry;
    // A typed absolute path inside another workspace folder switches the folder.
    if (entry !== undefined && entry.text === page.text) entry.folder = page.folder;

    const first = this._pageSeq !== page.seq;
    const scrollTop = this._main.scrollTop;
    if (page.busy) this._generatedSeq = page.seq;

    this.page = page;
    this._pageSeq = page.seq;
    this.busy = page.busy;
    this.error = page.error;
    this.outlineSelection = undefined;

    renderPage(this._main, page);
    this._headings = undefined;
    this.sections = buildOutline(this._main, page);

    let refresh = false;
    if (entry !== undefined) {
      if (entry.keyword !== undefined) {
        // The keyword of a `show` waits for a page that has it: a kept page may be older than the keyword. A kept
        // page that is not generated again, because that happened earlier in this session, is generated once more.
        const keyword = normalizeName(entry.keyword);
        const anchor = page.keywords.find((k) => normalizeName(k.name) === keyword)?.anchor;
        if (anchor !== undefined) {
          entry.anchor = anchor;
          delete entry.keyword;
        } else if (!page.busy) {
          if (this._generatedSeq === page.seq || this._keywordRefresh === entry) delete entry.keyword;
          else refresh = true;
        }
        this.reveal(anchor);
      } else if (first) {
        this.position(entry);
      } else if (entry.anchor !== undefined) {
        // The page was generated again with other content.
        this.reveal(entry.anchor);
      } else {
        this._main.scrollTop = scrollTop;
      }
    }

    // The page is positioned already; the search does not move it.
    if (this.findOpen) this._finder.search(this.findText, false);
    this.save();
    this.changed();

    if (refresh && entry !== undefined) {
      this._keywordRefresh = entry;
      this.load(entry, true);
    }
  }

  private readonly onClick = (event: MouseEvent): void => {
    const link = event.target instanceof Element ? event.target.closest("a[href^='#']") : null;
    if (link === null || !this._main.contains(link)) return;

    // Without stopPropagation, the host would scroll as well.
    event.preventDefault();
    event.stopPropagation();

    const heading = findHeading(this._main, (link.getAttribute("href") ?? "#").slice(1));
    if (heading !== undefined) this.showAnchor(heading.id);
  };

  private readonly onKeyDown = (event: KeyboardEvent): void => {
    const back = IS_MAC
      ? event.metaKey && !event.ctrlKey && !event.shiftKey && (event.key === "[" || event.code === "BracketLeft")
      : event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey && event.key === "ArrowLeft";
    const forward = IS_MAC
      ? event.metaKey && !event.ctrlKey && !event.shiftKey && (event.key === "]" || event.code === "BracketRight")
      : event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey && event.key === "ArrowRight";
    const command = IS_MAC ? event.metaKey && !event.ctrlKey : event.ctrlKey && !event.metaKey;

    if (back) this.back();
    else if (forward) this.forward();
    // By the typed letter on Latin layouts such as Dvorak, by the physical key on layouts without Latin letters.
    else if (
      command &&
      !event.altKey &&
      !event.shiftKey &&
      (/^[a-z]$/iu.test(event.key) ? event.key.toLowerCase() === "f" : event.code === "KeyF")
    )
      this.openFind();
    else if (event.key === "F3" && this.findOpen && !event.altKey && !event.ctrlKey && !event.metaKey) {
      if (event.shiftKey) this.findPrevious();
      else this.findNext();
    } else return;

    // stopPropagation keeps the key from VS Code's keybindings.
    event.preventDefault();
    event.stopPropagation();
  };

  private readonly onMouse = (event: MouseEvent): void => {
    if (event.button !== 3 && event.button !== 4) return;

    event.preventDefault();
    event.stopPropagation();
    if (event.type === "mouseup") {
      if (event.button === 3) this.back();
      else this.forward();
    }
  };
}

function useFocus(field: { current: TextField | null }, request: number): void {
  useEffect(() => {
    const element = field.current;
    if (request === 0 || element === null) return;
    void element.updateComplete.then(() => {
      element.focus();
      element.wrappedElement?.select();
    });
  }, [request]);
}

export function App({ controller }: { controller: Controller }): JSX.Element {
  const [, setVersion] = useState(0);
  const main = useRef<HTMLElement>(null);
  const split = useRef<HTMLElement>(null);
  const targetField = useRef<TextField>(null);
  const findField = useRef<TextField>(null);

  useEffect(() => controller.subscribe(() => setVersion((v) => v + 1)), [controller]);
  useEffect(() => {
    if (main.current !== null) controller.start(main.current);
  }, [controller]);
  useEffect(() => {
    const element = split.current;
    if (element === null) return undefined;
    const listener = (event: Event) => {
      const detail = (event as CustomEvent<{ position: number }>).detail;
      controller.setSplit(`${Math.round(detail.position)}px`);
    };
    // A drag of the split handle released outside the webview gets no mouseup; the first move without a button ends it.
    let dragging = false;
    const down = (event: MouseEvent) => {
      dragging = event.target === element;
    };
    const move = (event: MouseEvent) => {
      if (!dragging || event.buttons !== 0) return;
      dragging = false;
      window.dispatchEvent(new MouseEvent("mouseup", { clientX: event.clientX, clientY: event.clientY }));
    };
    const up = () => {
      dragging = false;
    };
    // The split layout clamps the outline while the viewer is narrow; a wider viewer gets the saved width back.
    const resize = () => {
      (element as HTMLElement & { handlePosition: string }).handlePosition = controller.state.split ?? "280px";
    };
    element.addEventListener("vsc-split-layout-change", listener);
    window.addEventListener("mousedown", down, true);
    window.addEventListener("mousemove", move, true);
    window.addEventListener("mouseup", up, true);
    window.addEventListener("resize", resize);
    return () => {
      element.removeEventListener("vsc-split-layout-change", listener);
      window.removeEventListener("mousedown", down, true);
      window.removeEventListener("mousemove", move, true);
      window.removeEventListener("mouseup", up, true);
      window.removeEventListener("resize", resize);
    };
  }, [controller]);

  const entry = controller.entry;
  // Typed text belongs to the history entry it was typed in; another entry shows its own target.
  const [edit, setEdit] = useState<{ index: number; text: string } | undefined>(undefined);
  const targetText = edit !== undefined && edit.index === controller.state.index ? edit.text : (entry?.text ?? "");
  // Text that was typed but not entered is dropped when the viewer navigates.
  useEffect(() => setEdit(undefined), [controller.state.index, controller.state.history]);

  useFocus(targetField, controller.focusTarget);
  useFocus(findField, controller.focusFind);

  const { page, error, busy, state } = controller;
  const pinLabel = state.pinned
    ? "Unpin: actions use the viewer used last"
    : "Pin: actions from the editor use this viewer";
  const folderName = controller.folders.length > 1 ? controller.folderName : undefined;

  return (
    <>
      <vscode-toolbar-container class="toolbar">
        <vscode-toolbar-button
          icon="arrow-left"
          label="Back"
          title="Back"
          aria-disabled={!controller.canGoBack}
          onClick={() => controller.back()}
        />
        <vscode-toolbar-button
          icon="arrow-right"
          label="Forward"
          title="Forward"
          aria-disabled={!controller.canGoForward}
          onClick={() => controller.forward()}
        />
        <vscode-textfield
          class="target"
          ref={targetField}
          value={targetText}
          placeholder="Library, resource or suite file, as Name::arg1::arg2 or path"
          aria-label="Target"
          onInput={(event) =>
            setEdit({ index: controller.state.index, text: (event.currentTarget as TextField).value })
          }
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              controller.submit((event.currentTarget as TextField).value);
              setEdit(undefined);
            }
          }}
        />
        <vscode-toolbar-button icon="refresh" label="Refresh" title="Refresh" onClick={() => controller.refresh()} />
        {folderName !== undefined && (
          <vscode-toolbar-button
            class="folder"
            icon="root-folder"
            label={`Workspace folder: ${folderName}`}
            title={`Workspace folder: ${folderName}`}
            onClick={() => post({ type: "pickFolder" })}
          >
            <span class="folder-name">{folderName}</span>
          </vscode-toolbar-button>
        )}
        <vscode-toolbar-button
          icon={state.pinned ? "pinned" : "pin"}
          label={pinLabel}
          title={pinLabel}
          toggleable
          checked={state.pinned}
          onChange={(event) =>
            controller.setPinned((event.currentTarget as HTMLElement & { checked: boolean }).checked)
          }
        />
      </vscode-toolbar-container>
      <div class="progress">
        {busy && <vscode-progress-bar indeterminate aria-label="Generating the documentation" />}
      </div>
      <vscode-split-layout
        class="body"
        ref={split}
        split="vertical"
        initial-handle-position="280px"
        fixed-pane="start"
        handle-position={state.split}
        min-start="160px"
        min-end="30%"
      >
        <div slot="start" class="side">
          <vscode-textfield
            class="filter"
            value={state.filter}
            placeholder="Filter"
            aria-label="Filter the outline"
            onInput={(event) => controller.setFilter((event.currentTarget as TextField).value)}
          />
          <Outline
            sections={controller.sections}
            filter={state.filter}
            collapsed={state.collapsed}
            selected={controller.selected}
            onChoose={(id, section) => controller.choose(id, section)}
            onToggle={(id) => controller.toggle(id)}
          />
        </div>
        <div slot="end" class="content">
          {error !== undefined && page !== undefined && <pre class="error">{error}</pre>}
          {error !== undefined && page === undefined && (
            <div class="failure">
              <pre class="error">{error}</pre>
              <button type="button" class="retry" onClick={() => controller.refresh()}>
                Retry
              </button>
            </div>
          )}
          <main class="markdown-body" tabIndex={0} ref={main} />
          {controller.findOpen && (
            <div class="find" role="search">
              <vscode-textfield
                ref={findField}
                value={controller.findText}
                placeholder="Find"
                aria-label="Find in the page"
                onInput={(event) => controller.find((event.currentTarget as TextField).value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    if (event.shiftKey) controller.findPrevious();
                    else controller.findNext();
                  } else if (event.key === "Escape") {
                    event.preventDefault();
                    controller.closeFind();
                  }
                }}
              />
              <span class="count" aria-live="polite">
                {controller.findCount > 0
                  ? `${controller.findCurrent + 1} of ${controller.findCount}`
                  : controller.findText
                    ? "No results"
                    : ""}
              </span>
              <vscode-toolbar-button
                icon="arrow-up"
                label="Previous Match"
                title="Previous Match"
                onClick={() => controller.findPrevious()}
              />
              <vscode-toolbar-button
                icon="arrow-down"
                label="Next Match"
                title="Next Match"
                onClick={() => controller.findNext()}
              />
              <vscode-toolbar-button icon="close" label="Close" title="Close" onClick={() => controller.closeFind()} />
            </div>
          )}
        </div>
      </vscode-split-layout>
    </>
  );
}
