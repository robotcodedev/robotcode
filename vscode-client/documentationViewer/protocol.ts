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
  // The keyword of a `show`, until a page of the target resolves it to `anchor`.
  keyword?: string;
  position?: ScrollPosition;
}

export interface ViewerState {
  v: 1;
  // Identifies the viewer across reloads, for the pin.
  id: string;
  history: HistoryEntry[];
  index: number;
  filter: string;
  split?: string;
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
}

export interface StatusMessage {
  type: "status";
  seq: number;
  busy: boolean;
  error?: string;
}

export interface ShowMessage {
  type: "show";
  folder: string;
  text: string;
  keyword?: string;
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

export type ExtensionMessage =
  PageMessage | StatusMessage | ShowMessage | PinMessage | FocusMessage | FoldersMessage | FolderMessage;

export type ViewerMessage =
  | { type: "ready"; state?: ViewerState }
  // `typed`: entered in the target field; only then does an absolute path switch to the folder it lies in.
  | { type: "load"; seq: number; folder?: string; text: string; refresh: boolean; typed?: boolean }
  | PinMessage
  | { type: "pickFolder" };

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
