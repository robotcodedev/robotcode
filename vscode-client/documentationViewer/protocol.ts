// Messages between the page and the extension (`vscode-client/extension/documentationViewer.ts`).

// Where a history entry was left: the offset in a page of that width, and the heading at the top of the view for a
// page of another width.
export interface ScrollPosition {
  scrollTop: number;
  width: number;
  heading?: string;
}

export interface HistoryEntry {
  folder: string;
  text: string;
  anchor?: string;
  // The place of a `show`, until a page of the target resolves it to `anchor`: a keyword, a data type, or a
  // fragment as the page's own links name a place.
  keyword?: string;
  dataType?: string;
  fragment?: string;
  position?: ScrollPosition;
  // The file of the kept page the entry showed last, which the viewer shows until the folder's environment is usable.
  keptPage?: string;
}

export interface ViewerState {
  v: 1;
  // Identifies the viewer across reloads, for the pin.
  id: string;
  history: HistoryEntry[];
  index: number;
  filter: string;
  split?: string;
  // Missing in a new viewer and in the state of an older version, which start as the setting says.
  outlineHidden?: boolean;
  collapsed: string[];
  pinned: boolean;
}

export interface NamedAnchor {
  name: string;
  anchor: string;
}

export interface PageMeta {
  name: string;
  type: string;
  version?: string;
  scope?: string;
  source?: string;
  lineno?: number;
}

export interface PageMessage {
  type: "page";
  seq: number;
  folder: string;
  text: string;
  meta: PageMeta;
  keywords: NamedAnchor[];
  types: NamedAnchor[];
  html?: string;
  renderError?: string;
  markdown?: string;
  error?: string;
  busy: boolean;
  // The file of the kept page that the page was read from or written to.
  keptPage: string;
}

export interface StatusMessage {
  type: "status";
  seq: number;
  busy: boolean;
  error?: string;
  // The load waits for the folder's Python environment instead of generating, with its progress bar running; the
  // extension asks for a reload when the environment is usable.
  waiting?: string;
  // The folder's Python environment has been unusable for a while, or RobotCode is switched off for the folder. The
  // load still waits: the extension asks for a reload when the environment is usable.
  environmentError?: string;
}

// The folder's Python environment became usable, or its interpreter changed: the current entry is loaded again, as a
// refresh when the load that waited for the environment was one.
export interface ReloadMessage {
  type: "reload";
  refresh?: boolean;
}

export interface ShowMessage {
  type: "show";
  folder: string;
  text: string;
  keyword?: string;
  anchor?: string;
  dataType?: string;
  focusTarget?: boolean;
}

export interface PinMessage {
  type: "pin";
  pinned: boolean;
}

export interface FocusMessage {
  type: "focus";
}

export interface WorkspaceFolderInfo {
  uri: string;
  name: string;
}

// The workspace folders, after each `ready` and when they change.
export interface FoldersMessage {
  type: "folders";
  folders: WorkspaceFolderInfo[];
}

// The folder the user picked after a `pickFolder`.
export interface FolderMessage {
  type: "folder";
  folder: string;
}

// A completion of the text in the target field: `label` replaces the text from `start` on. `kind` is the name of its
// kind, `FOLDER` for a directory, and `detail` the text the editor's completion shows for it.
export interface TargetCompletion {
  label: string;
  kind: string;
  detail: string;
  start: number;
}

// The completion of the text of the `suggest` with the same `seq`.
export interface SuggestionsMessage {
  type: "suggestions";
  seq: number;
  completions: TargetCompletion[];
}

// A bookmarked place: the target as the target field shows it before its place, and the heading at the top of the view
// with the title the outline shows for it; both are missing for the top of the page.
export interface Bookmark {
  text: string;
  heading?: string;
  title?: string;
}

// The bookmarks that hold for the viewer's folder, sorted by label: after each `ready`, after each change, and when the
// viewer switches its folder.
export interface BookmarksMessage {
  type: "bookmarks";
  bookmarks: Bookmark[];
}

export type ExtensionMessage =
  | PageMessage
  | StatusMessage
  | ShowMessage
  | PinMessage
  | FocusMessage
  | FoldersMessage
  | FolderMessage
  | ReloadMessage
  | SuggestionsMessage
  | BookmarksMessage;

export type ViewerMessage =
  | { type: "ready"; state?: ViewerState }
  // `typed`: entered in the target field; only then does an absolute path switch to the folder it lies in.
  // `keptPage`: the kept page the entry showed last.
  | { type: "load"; seq: number; folder?: string; text: string; refresh: boolean; typed?: boolean; keptPage?: string }
  | PinMessage
  | { type: "pickFolder" }
  // The page of the load `seq`, as a Markdown document.
  | { type: "openMarkdown"; seq: number }
  // A new viewer on `BuiltIn`, in the folder of this viewer.
  | { type: "newViewer" }
  // The completion of the text in the target field.
  | { type: "suggest"; seq: number; folder?: string; text: string }
  // Adds the bookmark of a place to the folder of the viewer's page, or removes the place from that folder and from All
  // Workspaces.
  | ({ type: "bookmark"; folder?: string; add: boolean } & Bookmark);

const api = acquireVsCodeApi();

export function post(message: ViewerMessage): void {
  api.postMessage(message);
}

export function loadState(): ViewerState | undefined {
  const state = api.getState() as ViewerState | undefined;
  return state?.v === 1 ? state : undefined;
}

export function saveState(state: ViewerState): void {
  api.setState(state);
}
