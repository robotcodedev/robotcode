import { JSX, TargetedKeyboardEvent } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { PageFinder } from "./find";
import { Outline, OutlineRowKind } from "./outline";
import { buildOutline, findHeading, headingTitle, OutlineEntry, OutlineSection, renderPage, scrollToTop } from "./page";
import {
  Bookmark,
  ExtensionMessage,
  HistoryEntry,
  loadState,
  PageMessage,
  post,
  saveState,
  ShowMessage,
  TargetCompletion,
  ViewerState,
  WorkspaceFolderInfo,
} from "./protocol";
import { bookmarkLabel, SuggestionList } from "./suggestions";

const MAX_HISTORY = 50;
const IS_MAC = /Mac|iPhone|iPad/.test(navigator.platform);
// How long the target field waits after the last input before it asks for the completion.
const SUGGEST_DELAY = 100;

interface Target {
  folder: string;
  text: string;
}

function sameTarget(a: Target | undefined, b: Target | undefined): boolean {
  return a !== undefined && b !== undefined && a.folder === b.folder && a.text === b.text;
}

function samePlace(a: Bookmark, b: Bookmark): boolean {
  return a.text === b.text && a.heading === b.heading;
}

function hasEntry(entries: OutlineEntry[], id: string): boolean {
  return entries.some((entry) => entry.id === id || (entry.children !== undefined && hasEntry(entry.children, id)));
}

function normalizeName(name: string): string {
  return name.replace(/[\s_]/gu, "").toLowerCase();
}

function isWaiting(entry: HistoryEntry): boolean {
  return entry.keyword !== undefined || entry.dataType !== undefined || entry.fragment !== undefined;
}

function stopWaiting(entry: HistoryEntry): void {
  delete entry.keyword;
  delete entry.dataType;
  delete entry.fragment;
}

// The keys of the editor's Trigger Suggest: Ctrl+Space, and on macOS also Option+Escape, as macOS often takes
// Ctrl+Space for switching the input source.
function opensSuggestions(event: KeyboardEvent): boolean {
  if (event.shiftKey || event.metaKey) return false;
  if (event.ctrlKey && !event.altKey && (event.key === " " || event.code === "Space")) return true;
  return IS_MAC && event.altKey && !event.ctrlKey && event.key === "Escape";
}

// The text of the target field with a completion in place of the part it continues; a directory ends with `/`.
function completedText(text: string, completion: TargetCompletion): string {
  return text.slice(0, completion.start) + completion.label + (completion.kind === "FOLDER" ? "/" : "");
}

// The text of the target field for a target and the id of a place: the place after a `#`. Without a place, a target
// with a `#` of its own ends with a `#`, so that the text after the last `#` is always the place.
function targetFieldText(text: string, place: string | undefined): string {
  if (place !== undefined) return `${text}#${place}`;
  return text.includes("#") ? `${text}#` : text;
}

// The target of a text of the target field, and its place, the text after the last `#`; without one, or with an empty
// one, the top of the page.
function splitPlace(text: string): { target: string; place: string | undefined } {
  const at = text.lastIndexOf("#");
  if (at < 0) return { target: text, place: undefined };
  return { target: text.slice(0, at).trim(), place: text.slice(at + 1).trim() || undefined };
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

interface HeadingTop {
  id: string;
  top: number;
  element: HTMLElement;
}

export class Controller {
  state: ViewerState;
  // The page shown in `main`, and its outline.
  page: PageMessage | undefined;
  sections: OutlineSection[] = [];
  busy = false;
  error: string | undefined;
  // The load waits for the folder's Python environment: the note that says so, or the error when that takes long.
  waiting: string | undefined;
  environmentError: string | undefined;
  // Choosing an entry of an outline without headings only selects it.
  outlineSelection: string | undefined;
  findOpen = false;
  findText = "";
  // Bumped to ask the page to focus the target field or the find field.
  focusTarget = 0;
  focusFind = 0;
  folders: WorkspaceFolderInfo[] = [];
  // The bookmarks that hold for the viewer's folder, sorted by label.
  bookmarks: Bookmark[] = [];
  // The list under the target field while it is open: the bookmarks that match the field's text, then the completion
  // of the text. And the selected entry of both; as in the editor, the first is selected when the list opens.
  suggestedBookmarks: Bookmark[] = [];
  suggestions: TargetCompletion[] = [];
  activeSuggestion = -1;

  // Not from 0: a recreated page would reuse the numbers of its previous instance, and a load of that instance that
  // is still waiting in the extension would answer this page.
  private _seq = Date.now();
  // The entry whose place was not on its page and that was loaded again for it.
  private _placeRefresh: HistoryEntry | undefined;
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
  private _headings: HeadingTop[] | undefined;
  private _headingsWidth = -1;
  // The heading of the place that the star shows; the scroll listener renders again when the heading at the top of the
  // view is another one.
  private _placeHeading: string | undefined;
  // Whether the list under the target field is open, and the text that its bookmarks match.
  private _listOpen = false;
  private _listText = "";
  // The `suggest` asked last and its text, until its answer arrives; the answers of older ones are dropped. And the
  // text that the suggestions shown complete.
  private _suggestSeq = -1;
  private _suggestText = "";
  private _suggestionsText = "";
  private _suggestTimer: number | undefined;
  // The anchors of the page's keywords whose source the extension knows, for Go to Source in the outline's menu.
  private _sourceAnchors = new Set<string>();

  constructor() {
    this.state = loadState() ?? { v: 1, id: "", history: [], index: -1, filter: "", collapsed: [], pinned: false };
    if (!this.state.id) this.state.id = newId();
    // The setting decides only how a viewer starts; from then on the viewer keeps its own state.
    if (this.state.outlineHidden === undefined) {
      this.state.outlineHidden = document.getElementById("root")?.dataset.showOutline === "false";
      saveState(this.state);
    }
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
        // The star follows the heading at the top of the view.
        if (this.placeHeading()?.id !== this._placeHeading) this.changed();
      },
      { passive: true },
    );
    // An image that loads after the headings were measured moves the headings below it.
    main.addEventListener("load", () => (this._headings = undefined), true);
    window.addEventListener("message", (event: MessageEvent<ExtensionMessage>) => this.onMessage(event.data));
    window.addEventListener("click", this.onClick, true);
    window.addEventListener("keydown", this.onKeyDown, true);
    window.addEventListener("mousedown", this.onMouse, true);
    window.addEventListener("mouseup", this.onMouse, true);

    post({ type: "ready", state: this.state });
    const entry = this.entry;
    if (entry !== undefined) this.load(entry, false);
  }

  // Shows the text of the target field: its target at the place after its last `#`. For the target shown, the place
  // shown only refreshes it, and another place that the page has is a new entry without a load, as an outline entry is.
  submit(text: string): void {
    const { target, place } = splitPlace(text.trim());
    if (!target) return;

    const entry = this.entry;
    const page = this.page;
    if (entry !== undefined && entry.text === target && page !== undefined && sameTarget(entry, page)) {
      const anchor = place !== undefined ? this.placeOnPage(place, page) : undefined;
      if (place === undefined || anchor !== undefined) {
        if (anchor === this.placeHeading()?.id) this.load(entry, true);
        else this.showPlace(anchor);
        return;
      }
    }
    this.navigate(
      { folder: entry?.folder ?? "", text: target, ...(place !== undefined ? { fragment: place } : {}) },
      true,
    );
  }

  // The text the target field shows for the current entry while nothing is typed: the target, and the place at the top
  // of the view, or the place the entry goes to while its page is not shown.
  get fieldText(): string {
    const entry = this.entry;
    if (entry === undefined) return "";
    const place = sameTarget(entry, this.page) ? this.placeHeading()?.id : (entry.fragment ?? entry.anchor);
    return targetFieldText(entry.text, place);
  }

  refresh(): void {
    const entry = this.entry;
    if (entry !== undefined) this.load(entry, true);
  }

  openMarkdown(): void {
    // The toolbar button has no `disabled`: without a page, Enter or Space on it opens nothing.
    if (this.page !== undefined) post({ type: "openMarkdown", seq: this.page.seq });
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

  setOutlineHidden(hidden: boolean): void {
    this.state.outlineHidden = hidden;
    this.save();
    this.changed();
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

  get suggestionCount(): number {
    return this.suggestedBookmarks.length + this.suggestions.length;
  }

  get suggestionsOpen(): boolean {
    return this._listOpen && this.suggestionCount > 0;
  }

  // Whether a `suggest` waits for the pause after typing or for its answer.
  get suggestionsPending(): boolean {
    return this._suggestTimer !== undefined || this._suggestSeq !== -1;
  }

  // The place the star bookmarks: the target of the current entry, and the heading at the top of the view with the
  // title the outline shows for it. None without a page of the current entry.
  get place(): Bookmark | undefined {
    const entry = this.entry;
    if (entry === undefined || !sameTarget(entry, this.page)) return undefined;
    const heading = this.placeHeading();
    return heading !== undefined
      ? { text: entry.text, heading: heading.id, title: headingTitle(heading.element) }
      : { text: entry.text };
  }

  get bookmarked(): boolean {
    const place = this.place;
    return place !== undefined && this.bookmarks.some((b) => samePlace(b, place));
  }

  // The star: bookmarks the place, or removes the bookmark of a bookmarked place.
  toggleBookmark(): void {
    const place = this.place;
    if (place !== undefined) this.setBookmark(place, !this.bookmarked);
  }

  removeBookmark(bookmark: Bookmark): void {
    this.setBookmark(bookmark, false);
  }

  // The context of VS Code's menu for a row of the outline, as its `data-vscode-context`: the viewer and the entry,
  // whether the entry's place is bookmarked, and whether it is a keyword with a source. A static outline, whose entries
  // only select, keeps VS Code's menu.
  menuContext(id: string, title: string, kind: OutlineRowKind, section: OutlineSection): string | undefined {
    const entry = this.entry;
    if (section.static || entry === undefined || this.page === undefined) return undefined;
    return JSON.stringify({
      webviewSection: "outlineEntry",
      preventDefaultContextMenuItems: true,
      viewerId: this.state.id,
      anchor: id,
      title,
      entryBookmarked: this.bookmarks.some((b) => b.text === entry.text && b.heading === id),
      entryHasSource: kind === "keyword" && this._sourceAnchors.has(id),
    });
  }

  // Opens a bookmark at its place, as a link opens one.
  openBookmark(bookmark: Bookmark): void {
    this.navigate({
      folder: this.entry?.folder ?? "",
      text: bookmark.text,
      ...(bookmark.heading !== undefined ? { fragment: bookmark.heading } : {}),
    });
  }

  // Opens the list for the target field's text: the bookmarks that match it at once, and the completion of the text
  // after the pause after typing, or at once with `now`. An answer still on its way is for an older text and is
  // dropped; until the answer for this text, the list keeps the completions that still complete it. An empty text gets
  // all bookmarks and no completion.
  suggest(text: string, now: boolean): void {
    window.clearTimeout(this._suggestTimer);
    this._suggestTimer = undefined;
    this._suggestSeq = -1;
    this._listOpen = true;
    this._listText = text;
    this.matchBookmarks();
    if (text === "") this.suggestions = [];
    else this.keepCompleting(text);
    this.activeSuggestion = this.suggestionCount > 0 ? 0 : -1;
    // Without a bookmark, the list of an empty text stays closed, also when bookmarks arrive.
    if (text === "") this._listOpen = this.suggestionCount > 0;
    this.changed();
    if (text === "") return;

    const ask = () => {
      this._suggestTimer = undefined;
      this._suggestSeq = ++this._seq;
      this._suggestText = text;
      post({ type: "suggest", seq: this._suggestSeq, folder: this.entry?.folder || undefined, text });
    };
    if (now) ask();
    else this._suggestTimer = window.setTimeout(ask, SUGGEST_DELAY);
  }

  closeSuggestions(): void {
    if (this.dropSuggestions()) this.changed();
  }

  // Selects the next or the previous suggestion, from the last to the first and back.
  moveSuggestion(step: 1 | -1): void {
    const count = this.suggestionCount;
    if (count === 0) return;
    this.activeSuggestion = (this.activeSuggestion + step + count) % count;
    this.changed();
  }

  // The bookmarks whose label or text in the target field contains the list's text without regard to case; all of
  // them for an empty text.
  private matchBookmarks(): void {
    const text = this._listText.toLowerCase();
    this.suggestedBookmarks = this.bookmarks.filter(
      (b) =>
        bookmarkLabel(b).toLowerCase().includes(text) ||
        targetFieldText(b.text, b.heading).toLowerCase().includes(text),
    );
  }

  // Keeps the completions that still complete `text`: the text before their start is unchanged, and their label starts
  // with the part after it.
  private keepCompleting(text: string): void {
    const before = this._suggestionsText;
    this.suggestions = this.suggestions.filter(
      (s) =>
        text.slice(0, s.start) === before.slice(0, s.start) &&
        s.label.toLowerCase().startsWith(text.slice(s.start).toLowerCase()),
    );
  }

  // The bookmarks have changed while the list is open: the selection stays where it is, within the list.
  private bookmarksChanged(): void {
    if (!this._listOpen) return;
    this.matchBookmarks();
    const count = this.suggestionCount;
    this.activeSuggestion = count > 0 ? Math.min(Math.max(this.activeSuggestion, 0), count - 1) : -1;
  }

  // Until the extension sends the bookmarks again, the change is made here, so that the star and the list follow it at
  // once.
  private setBookmark(bookmark: Bookmark, add: boolean): void {
    post({ type: "bookmark", folder: this.entry?.folder || undefined, ...bookmark, add });
    const others = this.bookmarks.filter((b) => !samePlace(b, bookmark));
    this.bookmarks = add ? [...others, bookmark] : others;
    this.bookmarksChanged();
    this.changed();
  }

  // Closes the list without telling the listeners, and drops an answer that is still on its way. Returns whether the
  // list was open.
  private dropSuggestions(): boolean {
    window.clearTimeout(this._suggestTimer);
    this._suggestTimer = undefined;
    this._suggestSeq = -1;
    const open = this.suggestionsOpen;
    this._listOpen = false;
    this.suggestedBookmarks = [];
    this.suggestions = [];
    this.activeSuggestion = -1;
    return open;
  }

  // Tells the listeners, and remembers the heading of the place that the star shows then.
  private changed(): void {
    this._placeHeading = this.placeHeading()?.id;
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

  private headingTops(): HeadingTop[] {
    const width = this._main.clientWidth;
    if (this._headings === undefined || this._headingsWidth !== width) {
      const origin = this._main.getBoundingClientRect().top - this._main.scrollTop;
      this._headings = Array.from(
        this._main.querySelectorAll<HTMLElement>("h1[id], h2[id], h3[id], h4[id], h5[id], h6[id]"),
        (heading) => ({ id: heading.id, top: heading.getBoundingClientRect().top - origin, element: heading }),
      );
      this._headingsWidth = width;
    }
    return this._headings;
  }

  // The last heading whose top is at or above the top of the view.
  private headingAtTop(): HeadingTop | undefined {
    const scrollTop = this._main.scrollTop;
    const headings = this.headingTops();
    let heading: HeadingTop | undefined;
    let low = 0;
    let high = headings.length - 1;
    while (low <= high) {
      const middle = (low + high) >> 1;
      if (headings[middle].top <= scrollTop + 1) {
        heading = headings[middle];
        low = middle + 1;
      } else {
        high = middle - 1;
      }
    }
    return heading;
  }

  // The heading of the place at the top of the view; none at the top of the page, which begins with the `h1` that
  // names the target.
  private placeHeading(): HeadingTop | undefined {
    const heading = this.headingAtTop();
    return heading?.element.tagName === "H1" ? undefined : heading;
  }

  // Records where the current entry is: the offset, the width of the page and the heading at the top of the view.
  private recordPosition(): boolean {
    const entry = this.entry;
    if (entry === undefined || !sameTarget(entry, this.page)) return false;

    entry.position = {
      scrollTop: this._main.scrollTop,
      width: this._main.clientWidth,
      heading: this.headingAtTop()?.id,
    };
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

  // Before the viewer leaves the current entry: its position, no place that is still waiting for a page, and no list of
  // suggestions, as the target field then shows the text of the next entry.
  private leave(): void {
    this.recordPosition();
    const entry = this.entry;
    if (entry !== undefined) stopWaiting(entry);
    this.dropSuggestions();
  }

  private navigate(entry: HistoryEntry, typed = false): void {
    this.push(entry);
    this.load(entry, false, typed);
  }

  private showAnchor(id: string): void {
    const entry = this.entry;
    if (entry === undefined) return;
    // The heading the current entry shows is only shown again.
    if (entry.anchor !== id || isWaiting(entry)) {
      this.push({ folder: entry.folder, text: entry.text, anchor: id, keptPage: entry.keptPage });
    }
    this.reveal(id);
    this.changed();
  }

  // Another place of the target shown, typed in the target field: a new entry at that heading, or at the top of the
  // page without one.
  private showPlace(anchor: string | undefined): void {
    const entry = this.entry;
    if (entry === undefined) return;
    this.push({
      folder: entry.folder,
      text: entry.text,
      ...(anchor !== undefined ? { anchor } : {}),
      keptPage: entry.keptPage,
    });
    this.reveal(anchor);
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
    this.dropSuggestions();
    this._loading = ++this._seq;
    this.busy = true;
    this.error = undefined;
    this.waiting = undefined;
    this.environmentError = undefined;
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
      ...(entry.keptPage !== undefined ? { keptPage: entry.keptPage } : {}),
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
        this.waiting = message.waiting;
        this.environmentError = message.environmentError;
        // The load ended without a page that has the place of its show. A load that waits for the environment has
        // not ended: the extension asks for a reload when the environment is usable.
        const entry = this.entry;
        const waitsForEnvironment = message.waiting !== undefined || message.environmentError !== undefined;
        if (!message.busy && !waitsForEnvironment && entry !== undefined && isWaiting(entry)) {
          stopWaiting(entry);
          this.save();
        }
        this.changed();
        break;
      }
      case "reload": {
        const entry = this.entry;
        if (entry !== undefined) this.load(entry, message.refresh ?? false);
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
      case "suggestions":
        if (message.seq !== this._suggestSeq) return;
        this._suggestSeq = -1;
        this._suggestionsText = this._suggestText;
        this.suggestions = message.completions;
        // The bookmarks are shown before the answer and stay as they are, so a bookmark selected meanwhile stays
        // selected.
        if (this.activeSuggestion < 0 || this.activeSuggestion >= this.suggestedBookmarks.length) {
          this.activeSuggestion = this.suggestionCount > 0 ? 0 : -1;
        }
        this.changed();
        break;
      case "bookmarks":
        this.bookmarks = message.bookmarks;
        this.bookmarksChanged();
        this.changed();
        break;
      case "openEntry": {
        // Open in the context menu of an outline row: as a click on the row.
        const section = this.sections.find((s) => s.id === message.anchor || hasEntry(s.children, message.anchor));
        if (section !== undefined) this.choose(message.anchor, section);
        break;
      }
      case "focus":
        // The focus VS Code gives a webview while its page loads does not stick; the page takes it itself, unless
        // something in it has the focus already.
        if (document.activeElement === null || document.activeElement === document.body) this._main.focus();
        break;
    }
  }

  private onShow(show: ShowMessage): void {
    this.navigate({
      folder: show.folder,
      text: show.text,
      keyword: show.keyword,
      dataType: show.dataType,
      fragment: show.anchor,
    });
    if (show.focusTarget) this.focusTarget++;
    this.changed();
  }

  private onPage(page: PageMessage): void {
    if (page.seq !== this._loading) return;

    const entry = this.entry;
    // A typed absolute path inside another workspace folder switches the folder.
    if (entry !== undefined && entry.text === page.text) {
      entry.folder = page.folder;
      entry.keptPage = page.keptPage;
    }

    const first = this._pageSeq !== page.seq;
    const scrollTop = this._main.scrollTop;
    if (page.busy) this._generatedSeq = page.seq;

    this.page = page;
    this._sourceAnchors = new Set(page.keywords.filter((k) => k.source).map((k) => k.anchor));
    this._pageSeq = page.seq;
    this.busy = page.busy;
    this.error = page.error;
    this.outlineSelection = undefined;

    renderPage(this._main, page);
    this._headings = undefined;
    this.sections = buildOutline(this._main, page);

    let refresh = false;
    if (entry !== undefined) {
      if (isWaiting(entry)) {
        // The place of a `show` waits for a page that has it: a kept page may be older than the place. A kept page
        // that is not generated again, because that happened earlier in this session, is generated once more.
        const anchor = this.placeAnchor(entry, page);
        if (anchor !== undefined) {
          entry.anchor = anchor;
          stopWaiting(entry);
        } else if (!page.busy) {
          if (this._generatedSeq === page.seq || this._placeRefresh === entry) stopWaiting(entry);
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
      this._placeRefresh = entry;
      this.load(entry, true);
    }
  }

  // The anchor of the place an entry waits for, if the rendered page has it. The server cannot know the anchor of a
  // data type: the page numbers it when another heading has the same title.
  private placeAnchor(entry: HistoryEntry, page: PageMessage): string | undefined {
    if (entry.keyword !== undefined) {
      const keyword = normalizeName(entry.keyword);
      return page.keywords.find((k) => normalizeName(k.name) === keyword)?.anchor;
    }
    if (entry.dataType !== undefined) return page.types.find((t) => t.name === entry.dataType)?.anchor;
    if (entry.fragment !== undefined) return this.placeOnPage(entry.fragment, page);
    return undefined;
  }

  // The anchor of a place on the rendered page: the heading with that id, else the keyword or data type with that name,
  // compared as the keyword of a `show` is.
  private placeOnPage(place: string, page: PageMessage): string | undefined {
    const heading = findHeading(this._main, place);
    if (heading !== undefined) return heading.id;
    const name = normalizeName(place);
    return (
      page.keywords.find((k) => normalizeName(k.name) === name) ??
      page.types.find((t) => normalizeName(t.name) === name)
    )?.anchor;
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
  const suggestionList = useRef<HTMLDivElement>(null);
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
      if (controller.state.outlineHidden) return;
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

  // Typed text belongs to the history entry it was typed in; another entry shows its own target and place.
  const [edit, setEdit] = useState<{ index: number; text: string } | undefined>(undefined);
  const targetText = edit !== undefined && edit.index === controller.state.index ? edit.text : controller.fieldText;
  // Text that was typed but not entered is dropped when the viewer navigates.
  useEffect(() => setEdit(undefined), [controller.state.index, controller.state.history]);

  useFocus(targetField, controller.focusTarget);
  useFocus(findField, controller.focusFind);

  // The target field as a combobox of its suggestion list. Its input lies in the shadow root of `vscode-textfield`, so
  // the list and the selected option are linked as elements: an id would not reach out of the shadow root.
  useEffect(() => {
    const field = targetField.current;
    if (field === null) return;
    const link = () => {
      const input = field.wrappedElement;
      if (input === undefined || input === null) return;
      const list = suggestionList.current;
      input.setAttribute("role", "combobox");
      input.setAttribute("aria-autocomplete", "list");
      input.setAttribute("aria-expanded", String(list !== null));
      input.ariaControlsElements = list !== null ? [list] : null;
      input.ariaActiveDescendantElement = list?.querySelector<HTMLElement>(".target-suggestion.active") ?? null;
    };
    if (field.wrappedElement) link();
    else void field.updateComplete.then(link);
  });

  // Puts a suggestion into the target field. A directory gets its content listed next; any other suggestion is loaded
  // by Enter and a click, and only put in by Tab. A bookmark is opened at its place, and Tab puts its target and place
  // in.
  const choose = (index: number, load: boolean): void => {
    const bookmark = controller.suggestedBookmarks[index];
    if (bookmark !== undefined) {
      if (load) {
        controller.openBookmark(bookmark);
        setEdit(undefined);
      } else {
        setEdit({ index: controller.state.index, text: targetFieldText(bookmark.text, bookmark.heading) });
        controller.closeSuggestions();
      }
      return;
    }

    const completion = controller.suggestions[index - controller.suggestedBookmarks.length];
    const field = targetField.current;
    if (completion === undefined || field === null) return;

    const text = completedText(field.value, completion);
    if (completion.kind === "FOLDER") {
      setEdit({ index: controller.state.index, text });
      controller.suggest(text, true);
    } else if (load) {
      controller.closeSuggestions();
      controller.submit(text);
      setEdit(undefined);
    } else {
      setEdit({ index: controller.state.index, text });
      controller.closeSuggestions();
    }
  };

  const onTargetKeyDown = (event: TargetedKeyboardEvent<HTMLElement>): void => {
    // The keys of an IME composition belong to the IME.
    if (event.isComposing) return;
    const text = (event.currentTarget as TextField).value;
    const plain = !event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey;
    const active = controller.activeSuggestion;

    if (plain && event.key === "ArrowDown") {
      if (controller.suggestionsOpen) controller.moveSuggestion(1);
      else controller.suggest(text, true);
    } else if (plain && event.key === "ArrowUp" && controller.suggestionsOpen) {
      controller.moveSuggestion(-1);
    } else if (opensSuggestions(event)) {
      controller.suggest(text, true);
    } else if (plain && event.key === "Escape" && (controller.suggestionsOpen || controller.suggestionsPending)) {
      controller.closeSuggestions();
    } else if (plain && event.key === "Tab" && active >= 0) {
      choose(active, false);
    } else if (event.key === "Enter") {
      if (active >= 0) {
        choose(active, true);
      } else {
        controller.closeSuggestions();
        controller.submit(text);
        setEdit(undefined);
      }
    } else {
      return;
    }
    // stopPropagation keeps the key from VS Code's keybindings.
    event.preventDefault();
    event.stopPropagation();
  };

  const { page, error, waiting, environmentError, busy, state } = controller;
  const pinLabel = state.pinned
    ? "Unpin: actions use the viewer used last"
    : "Pin: actions from the editor use this viewer";
  const folderName = controller.folders.length > 1 ? controller.folderName : undefined;
  const outlineHidden = state.outlineHidden === true;
  const outlineLabel = outlineHidden ? "Show Outline" : "Hide Outline";
  const place = controller.place;
  const bookmarked = controller.bookmarked;
  const starLabel = bookmarked ? "Remove Bookmark" : "Add Bookmark";

  return (
    <>
      <vscode-toolbar-container class="toolbar">
        <vscode-toolbar-button
          icon={outlineHidden ? "layout-sidebar-left-off" : "layout-sidebar-left"}
          label={outlineLabel}
          title={outlineLabel}
          toggleable
          checked={!outlineHidden}
          onChange={(event) =>
            controller.setOutlineHidden(!(event.currentTarget as HTMLElement & { checked: boolean }).checked)
          }
        />
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
          onInput={(event) => {
            const text = (event.currentTarget as TextField).value;
            setEdit({ index: controller.state.index, text });
            controller.suggest(text, false);
          }}
          onKeyDown={onTargetKeyDown}
          onBlur={() => controller.closeSuggestions()}
        />
        <vscode-toolbar-button
          icon={bookmarked ? "star-full" : "star-empty"}
          label={starLabel}
          title={starLabel}
          toggleable
          checked={bookmarked}
          aria-disabled={place === undefined}
          onChange={(event) => {
            controller.toggleBookmark();
            // Without a page, Enter or Space on the button change nothing.
            (event.currentTarget as HTMLElement & { checked: boolean }).checked = controller.bookmarked;
          }}
        />
        <vscode-toolbar-button icon="refresh" label="Refresh" title="Refresh" onClick={() => controller.refresh()} />
        <vscode-toolbar-button
          icon="markdown"
          label="Open as Markdown"
          title="Open as Markdown"
          aria-disabled={page === undefined}
          onClick={() => controller.openMarkdown()}
        />
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
        <vscode-toolbar-button
          icon="new-file"
          label="New Documentation Viewer"
          title="New Documentation Viewer"
          onClick={() => post({ type: "newViewer" })}
        />
      </vscode-toolbar-container>
      {controller.suggestionsOpen && targetField.current !== null && (
        <SuggestionList
          listRef={suggestionList}
          field={targetField.current}
          text={targetText}
          bookmarks={controller.suggestedBookmarks}
          completions={controller.suggestions}
          active={controller.activeSuggestion}
          onChoose={(index) => choose(index, true)}
          onRemove={(bookmark) => controller.removeBookmark(bookmark)}
        />
      )}
      <div class="progress">
        {busy && <vscode-progress-bar indeterminate aria-label="Generating the documentation" />}
      </div>
      {/* A hidden outline collapses the start pane, so that the page stays in its element and keeps its position.
          The minimum comes before the position, which the split layout clamps to it. */}
      <vscode-split-layout
        class={`body${outlineHidden ? " outline-hidden" : ""}`}
        ref={split}
        split="vertical"
        initial-handle-position="280px"
        fixed-pane="start"
        min-start={outlineHidden ? "0px" : "160px"}
        handle-position={outlineHidden ? "0px" : (state.split ?? "280px")}
        handle-size={outlineHidden ? 0 : 4}
        min-end="30%"
      >
        {!outlineHidden && (
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
              menuContext={(id, title, kind, section) => controller.menuContext(id, title, kind, section)}
            />
          </div>
        )}
        <div slot="end" class="content">
          {waiting !== undefined && <div class="waiting">{waiting}</div>}
          {environmentError !== undefined && <div class="environment-error">{environmentError}</div>}
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
