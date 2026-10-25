import * as vscode from "vscode";

// A bookmarked place of a Documentation Viewer: the target as the target field shows it before its place, and the
// heading at the top of the view with the title the outline shows for it; both are missing for the top of the page.
export interface DocumentationBookmark {
  text: string;
  heading?: string;
  title?: string;
}

// In `globalState` the group All Workspaces, whose bookmarks hold in all workspaces; in `workspaceState` the groups of
// the workspace folders, by the URI of the folder.
export const BOOKMARKS_KEY = "robotcode.documentationViewer.bookmarks";
// Set once the default bookmarks are created, so that a removed one does not come back. Settings Sync takes it along,
// so that another machine of the user does not create them again.
export const DEFAULT_BOOKMARKS_KEY = "robotcode.documentationViewer.defaultBookmarks";

// The standard libraries of Robot Framework: `robot.libraries.STDLIBS` of Robot Framework 7 without the easter egg
// `Easter`. Robot Framework 5 and 6 also list `Reserved`, whose keywords only report that their names are reserved.
export const DEFAULT_BOOKMARKS: readonly string[] = [
  "BuiltIn",
  "Collections",
  "DateTime",
  "Dialogs",
  "OperatingSystem",
  "Process",
  "Remote",
  "Screenshot",
  "String",
  "Telnet",
  "XML",
];

export function bookmarkLabel(bookmark: DocumentationBookmark): string {
  return bookmark.heading !== undefined ? `${bookmark.text} › ${bookmark.title ?? bookmark.heading}` : bookmark.text;
}

function samePlace(a: DocumentationBookmark, b: DocumentationBookmark): boolean {
  return a.text === b.text && a.heading === b.heading;
}

// By the label without regard to case, and by the label itself between labels that differ only in case.
function compareLabels(a: DocumentationBookmark, b: DocumentationBookmark): number {
  const labelA = bookmarkLabel(a);
  const labelB = bookmarkLabel(b);
  const lowerA = labelA.toLowerCase();
  const lowerB = labelB.toLowerCase();
  if (lowerA !== lowerB) return lowerA < lowerB ? -1 : 1;
  return labelA < labelB ? -1 : labelA > labelB ? 1 : 0;
}

// The bookmarks of a stored value or of a message, sorted by label. A group from Settings Sync may come from another
// version: anything that is not a bookmark is left out.
function bookmarksOf(value: unknown): DocumentationBookmark[] {
  if (!Array.isArray(value)) return [];

  const result: DocumentationBookmark[] = [];
  for (const item of value as unknown[]) {
    if (typeof item !== "object" || item === null) continue;
    const { text, heading, title } = item as Record<string, unknown>;
    if (typeof text !== "string" || text === "") continue;
    if (typeof heading === "string" && heading !== "") {
      result.push({ text, heading, ...(typeof title === "string" ? { title } : {}) });
    } else {
      result.push({ text });
    }
  }
  return result.sort(compareLabels);
}

function withBookmark(bookmarks: DocumentationBookmark[], bookmark: DocumentationBookmark): DocumentationBookmark[] {
  return [...bookmarks.filter((b) => !samePlace(b, bookmark)), bookmark].sort(compareLabels);
}

function withoutBookmark(bookmarks: DocumentationBookmark[], bookmark: DocumentationBookmark): DocumentationBookmark[] {
  return bookmarks.filter((b) => !samePlace(b, bookmark));
}

// The bookmarks of the Documentation Viewers, which the viewers, their stars and the view Documentation Bookmarks share.
// A group is All Workspaces for `undefined`, else the workspace folder with that URI. Each change fires `onDidChange`.
export class DocumentationBookmarks implements vscode.Disposable {
  private readonly _onDidChange = new vscode.EventEmitter<void>();
  readonly onDidChange = this._onDidChange.event;
  private readonly _disposables: vscode.Disposable;
  // All Workspaces as this window knows it, to notice the changes of other windows and of Settings Sync.
  private _knownAllWorkspaces: string;

  constructor(
    private readonly globalState: vscode.Memento & { setKeysForSync(keys: readonly string[]): void },
    private readonly workspaceState: vscode.Memento,
  ) {
    globalState.setKeysForSync([BOOKMARKS_KEY, DEFAULT_BOOKMARKS_KEY]);
    this._knownAllWorkspaces = JSON.stringify(this.group(undefined));
    this._disposables = vscode.Disposable.from(
      this._onDidChange,
      // Another window and Settings Sync change `globalState` without an event; a window that gets the focus looks.
      vscode.window.onDidChangeWindowState((state) => {
        if (state.focused) this.checkForChanges();
      }),
    );
  }

  dispose(): void {
    this._disposables.dispose();
  }

  group(folder: string | undefined): DocumentationBookmark[] {
    return bookmarksOf(folder === undefined ? this.globalState.get(BOOKMARKS_KEY) : this.folderRecord()[folder]);
  }

  // The bookmarks that hold for a workspace folder, sorted by label: those of All Workspaces and of the folder, each
  // place once.
  forFolder(folder: string | undefined): DocumentationBookmark[] {
    let bookmarks = this.group(undefined);
    if (folder !== undefined) for (const bookmark of this.group(folder)) bookmarks = withBookmark(bookmarks, bookmark);
    return bookmarks;
  }

  async add(folder: string | undefined, bookmark: DocumentationBookmark): Promise<void> {
    const place = bookmarksOf([bookmark])[0];
    if (place === undefined) return;

    await this.write(folder, withBookmark(this.group(folder), place));
    this._onDidChange.fire();
  }

  async remove(folder: string | undefined, bookmark: DocumentationBookmark): Promise<void> {
    await this.write(folder, withoutBookmark(this.group(folder), bookmark));
    this._onDidChange.fire();
  }

  // Removes a place from the bookmarks that hold for a workspace folder: from the folder and from All Workspaces.
  async removePlace(folder: string | undefined, bookmark: DocumentationBookmark): Promise<void> {
    if (folder !== undefined) await this.write(folder, withoutBookmark(this.group(folder), bookmark));
    await this.write(undefined, withoutBookmark(this.group(undefined), bookmark));
    this._onDidChange.fire();
  }

  async move(bookmark: DocumentationBookmark, from: string | undefined, to: string | undefined): Promise<void> {
    const place = bookmarksOf([bookmark])[0];
    if (place === undefined || from === to) return;

    await this.write(from, withoutBookmark(this.group(from), place));
    await this.write(to, withBookmark(this.group(to), place));
    this._onDidChange.fire();
  }

  // At the first start of RobotCode, bookmarks the standard libraries in All Workspaces.
  async createDefaults(): Promise<void> {
    if (this.globalState.get(DEFAULT_BOOKMARKS_KEY) === true) return;

    let bookmarks = this.group(undefined);
    for (const text of DEFAULT_BOOKMARKS) bookmarks = withBookmark(bookmarks, { text });
    // The mark after the bookmarks: a start that ends in between creates them again.
    await this.write(undefined, bookmarks);
    await this.globalState.update(DEFAULT_BOOKMARKS_KEY, true);
    this._onDidChange.fire();
  }

  // The default bookmarks in place of All Workspaces and of the groups of the given workspace folders. The folders of
  // other workspaces are not reachable from this window.
  async reset(folders: readonly string[]): Promise<void> {
    const record = this.folderRecord();
    for (const folder of folders) delete record[folder];
    await this.workspaceState.update(BOOKMARKS_KEY, Object.keys(record).length > 0 ? record : undefined);
    await this.globalState.update(DEFAULT_BOOKMARKS_KEY, true);
    await this.write(undefined, bookmarksOf(DEFAULT_BOOKMARKS.map((text) => ({ text }))));
    this._onDidChange.fire();
  }

  // Fires `onDidChange` when another window or Settings Sync has changed All Workspaces.
  checkForChanges(): void {
    const bookmarks = JSON.stringify(this.group(undefined));
    if (bookmarks === this._knownAllWorkspaces) return;

    this._knownAllWorkspaces = bookmarks;
    this._onDidChange.fire();
  }

  // A copy: the memento's value must not change before its `update`.
  private folderRecord(): Record<string, unknown> {
    const value = this.workspaceState.get(BOOKMARKS_KEY);
    return typeof value === "object" && value !== null && !Array.isArray(value)
      ? { ...(value as Record<string, unknown>) }
      : {};
  }

  private async write(folder: string | undefined, bookmarks: DocumentationBookmark[]): Promise<void> {
    if (folder === undefined) {
      await this.globalState.update(BOOKMARKS_KEY, bookmarks);
      this._knownAllWorkspaces = JSON.stringify(bookmarks);
      return;
    }

    const record = this.folderRecord();
    if (bookmarks.length > 0) record[folder] = bookmarks;
    else delete record[folder];
    await this.workspaceState.update(BOOKMARKS_KEY, Object.keys(record).length > 0 ? record : undefined);
  }
}
