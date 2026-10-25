import * as vscode from "vscode";
import { bookmarkLabel, DocumentationBookmark, DocumentationBookmarks } from "./documentationViewerBookmarks";

const BOOKMARK_ICON = new vscode.ThemeIcon("star-full");
// The tree's own mime type, under which VS Code keeps the dragged items of a drag within the tree.
const TREE_MIME_TYPE = "application/vnd.code.tree.robotcode.documentationbookmarksview";

// The group All Workspaces, whose bookmarks hold in all workspaces, or the group of a workspace folder. An empty group
// stays as a place to drop a bookmark on. VS Code takes the collapsible state of an item only when it first shows its
// id, so a group that gets its first bookmark comes with another id, and expanded.
class GroupItem extends vscode.TreeItem {
  constructor(
    readonly folder: vscode.WorkspaceFolder | undefined,
    empty: boolean,
  ) {
    super(
      folder?.name ?? "All Workspaces",
      empty ? vscode.TreeItemCollapsibleState.None : vscode.TreeItemCollapsibleState.Expanded,
    );
    this.id = `${folder?.uri.toString() ?? "allWorkspaces"}${empty ? "#empty" : ""}`;
    this.contextValue = "group";
  }
}

class BookmarkItem extends vscode.TreeItem {
  constructor(
    readonly bookmark: DocumentationBookmark,
    readonly folder: vscode.WorkspaceFolder | undefined,
  ) {
    super(bookmarkLabel(bookmark), vscode.TreeItemCollapsibleState.None);
    this.iconPath = BOOKMARK_ICON;
    this.contextValue = folder !== undefined ? "folderBookmark" : "allWorkspacesBookmark";
    this.command = {
      command: "robotcode.documentationBookmarks.open",
      title: "Open Bookmark",
      arguments: [bookmark, folder?.uri.toString()],
    };
  }
}

type Item = GroupItem | BookmarkItem;

// The view Documentation Bookmarks in the Explorer: while a bookmark exists, the group All Workspaces and a group for
// each workspace folder. A bookmark moves to another group by its context menu or by dragging it onto the group.
export class DocumentationBookmarksView
  implements vscode.TreeDataProvider<Item>, vscode.TreeDragAndDropController<Item>, vscode.Disposable
{
  readonly dragMimeTypes = [TREE_MIME_TYPE];
  readonly dropMimeTypes = [TREE_MIME_TYPE];
  private readonly _onDidChangeTreeData = new vscode.EventEmitter<void>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;
  private readonly _disposables: vscode.Disposable;

  constructor(private readonly bookmarks: DocumentationBookmarks) {
    this._disposables = vscode.Disposable.from(
      this._onDidChangeTreeData,
      vscode.window.createTreeView("robotcode.documentationBookmarksView", {
        treeDataProvider: this,
        dragAndDropController: this,
      }),
      bookmarks.onDidChange(() => this._onDidChangeTreeData.fire()),
      vscode.workspace.onDidChangeWorkspaceFolders(() => this._onDidChangeTreeData.fire()),
      vscode.commands.registerCommand("robotcode.documentationBookmarks.remove", (item: unknown) => {
        if (item instanceof BookmarkItem) return bookmarks.remove(item.folder?.uri.toString(), item.bookmark);
        return undefined;
      }),
      vscode.commands.registerCommand("robotcode.documentationBookmarks.moveToAllWorkspaces", (item: unknown) => {
        if (item instanceof BookmarkItem) return bookmarks.move(item.bookmark, item.folder?.uri.toString(), undefined);
        return undefined;
      }),
      vscode.commands.registerCommand("robotcode.documentationBookmarks.moveToFolder", (item: unknown) => {
        if (item instanceof BookmarkItem) return this.moveToFolder(item);
        return undefined;
      }),
      vscode.commands.registerCommand("robotcode.documentationBookmarks.reset", () => this.reset()),
    );
  }

  dispose(): void {
    this._disposables.dispose();
  }

  // eslint-disable-next-line class-methods-use-this
  getTreeItem(item: Item): vscode.TreeItem {
    return item;
  }

  getChildren(item?: Item): Item[] {
    if (item === undefined) {
      const groups = [undefined, ...(vscode.workspace.workspaceFolders ?? [])].map((folder) => ({
        folder,
        empty: this.bookmarks.group(folder?.uri.toString()).length === 0,
      }));
      // Without any bookmark, the view says how to add one.
      if (groups.every((group) => group.empty)) return [];
      return groups.map((group) => new GroupItem(group.folder, group.empty));
    }
    if (item instanceof GroupItem) {
      return this.bookmarks
        .group(item.folder?.uri.toString())
        .map((bookmark) => new BookmarkItem(bookmark, item.folder));
    }
    return [];
  }

  // eslint-disable-next-line class-methods-use-this
  handleDrag(source: readonly Item[], dataTransfer: vscode.DataTransfer): void {
    const items = source.filter((item) => item instanceof BookmarkItem);
    if (items.length > 0) dataTransfer.set(TREE_MIME_TYPE, new vscode.DataTransferItem(items));
  }

  // A drop on a group, or on a bookmark of a group, moves the dragged bookmarks into that group.
  async handleDrop(target: Item | undefined, dataTransfer: vscode.DataTransfer): Promise<void> {
    const items: unknown = dataTransfer.get(TREE_MIME_TYPE)?.value;
    if (target === undefined || !Array.isArray(items)) return;

    const to = target.folder?.uri.toString();
    for (const item of items) {
      if (item instanceof BookmarkItem) await this.bookmarks.move(item.bookmark, item.folder?.uri.toString(), to);
    }
  }

  // Into the one other workspace folder at once; among several, the user picks one.
  private async moveToFolder(item: BookmarkItem): Promise<void> {
    const folders = (vscode.workspace.workspaceFolders ?? []).filter(
      (folder) => folder.uri.toString() !== item.folder?.uri.toString(),
    );
    const folder =
      folders.length > 1
        ? (
            await vscode.window.showQuickPick(
              folders.map((f) => ({ label: f.name, folder: f })),
              { placeHolder: `Workspace folder for the bookmark ${bookmarkLabel(item.bookmark)}` },
            )
          )?.folder
        : folders[0];
    if (folder === undefined) return;

    await this.bookmarks.move(item.bookmark, item.folder?.uri.toString(), folder.uri.toString());
  }

  private async reset(): Promise<void> {
    const reset = "Reset";
    const choice = await vscode.window.showWarningMessage(
      "Reset the documentation bookmarks?",
      {
        modal: true,
        detail:
          "This removes the bookmarks of all workspaces and of the open workspace folders, and bookmarks the standard libraries of Robot Framework again.",
      },
      reset,
    );
    if (choice !== reset) return;

    await this.bookmarks.reset((vscode.workspace.workspaceFolders ?? []).map((folder) => folder.uri.toString()));
  }
}
