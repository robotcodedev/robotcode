import * as assert from "assert";
import * as vscode from "vscode";

import {
  BOOKMARKS_KEY,
  bookmarkLabel,
  DEFAULT_BOOKMARKS,
  DEFAULT_BOOKMARKS_KEY,
  DocumentationBookmark,
  DocumentationBookmarks,
} from "../extension/documentationViewerBookmarks";

// A memento in memory, which keeps a copy of each value as VS Code's memento keeps it in its storage.
class MemoryMemento implements vscode.Memento {
  syncedKeys: readonly string[] = [];
  private readonly _values = new Map<string, unknown>();

  keys(): readonly string[] {
    return [...this._values.keys()];
  }

  get<T>(key: string): T | undefined;
  get<T>(key: string, defaultValue: T): T;
  get<T>(key: string, defaultValue?: T): T | undefined {
    return this._values.has(key) ? (this._values.get(key) as T) : defaultValue;
  }

  update(key: string, value: unknown): Thenable<void> {
    if (value === undefined) this._values.delete(key);
    else this._values.set(key, JSON.parse(JSON.stringify(value)));
    return Promise.resolve();
  }

  setKeysForSync(keys: readonly string[]): void {
    this.syncedKeys = keys;
  }
}

const TESTS = "file:///workspace/tests";
const SHARED = "file:///workspace/shared";
const ALL_WORKSPACES = undefined;
const GET_FROM_DICTIONARY: DocumentationBookmark = {
  text: "Collections",
  heading: "Get%20From%20Dictionary",
  title: "Get From Dictionary",
};

function labels(bookmarks: DocumentationBookmark[]): string[] {
  return bookmarks.map(bookmarkLabel);
}

suite("bookmarkLabel", () => {
  test("names the target and the title of the heading", () => {
    assert.strictEqual(bookmarkLabel(GET_FROM_DICTIONARY), "Collections › Get From Dictionary");
    assert.strictEqual(bookmarkLabel({ text: "XML" }), "XML");
  });
});

suite("DocumentationBookmarks", () => {
  let globalState: MemoryMemento;
  let workspaceState: MemoryMemento;
  let bookmarks: DocumentationBookmarks;

  setup(() => {
    globalState = new MemoryMemento();
    workspaceState = new MemoryMemento();
    bookmarks = new DocumentationBookmarks(globalState, workspaceState);
  });

  teardown(() => bookmarks.dispose());

  test("syncs All Workspaces and the mark of the default bookmarks", () => {
    assert.deepStrictEqual(globalState.syncedKeys, [BOOKMARKS_KEY, DEFAULT_BOOKMARKS_KEY]);
  });

  test("keeps a bookmark in the group of its folder, whatever its target", async () => {
    await bookmarks.add(TESTS, { text: "XML" });
    await bookmarks.add(TESTS, { text: "resources/shop.resource" });

    assert.deepStrictEqual(labels(bookmarks.group(TESTS)), ["resources/shop.resource", "XML"]);
    assert.deepStrictEqual(bookmarks.group(ALL_WORKSPACES), []);
    assert.deepStrictEqual(bookmarks.forFolder(SHARED), []);
    assert.strictEqual(globalState.get(BOOKMARKS_KEY), undefined);
    assert.deepStrictEqual(workspaceState.get(BOOKMARKS_KEY), {
      [TESTS]: [{ text: "resources/shop.resource" }, { text: "XML" }],
    });
  });

  test("offers All Workspaces and the folder's group for a folder, each place once", async () => {
    await bookmarks.add(ALL_WORKSPACES, { text: "XML" });
    await bookmarks.add(ALL_WORKSPACES, GET_FROM_DICTIONARY);
    await bookmarks.add(TESTS, GET_FROM_DICTIONARY);
    await bookmarks.add(TESTS, { text: "Collections" });

    assert.deepStrictEqual(labels(bookmarks.forFolder(TESTS)), [
      "Collections",
      "Collections › Get From Dictionary",
      "XML",
    ]);
    assert.deepStrictEqual(labels(bookmarks.forFolder(SHARED)), ["Collections › Get From Dictionary", "XML"]);
  });

  test("keeps each place once in a group, sorted by label without regard to case", async () => {
    await bookmarks.add(TESTS, { text: "XML" });
    await bookmarks.add(TESTS, GET_FROM_DICTIONARY);
    await bookmarks.add(TESTS, { text: "dialogs" });
    await bookmarks.add(TESTS, { text: "Collections" });
    await bookmarks.add(TESTS, { ...GET_FROM_DICTIONARY, title: "Get from dictionary" });

    assert.deepStrictEqual(labels(bookmarks.group(TESTS)), [
      "Collections",
      "Collections › Get from dictionary",
      "dialogs",
      "XML",
    ]);
  });

  test("keeps only the place of a bookmark from a message", async () => {
    await bookmarks.add(TESTS, { type: "bookmark", add: true, ...GET_FROM_DICTIONARY } as DocumentationBookmark);

    assert.deepStrictEqual(bookmarks.group(TESTS), [GET_FROM_DICTIONARY]);
  });

  test("removes a bookmark from its group only", async () => {
    await bookmarks.add(ALL_WORKSPACES, { text: "XML" });
    await bookmarks.add(TESTS, { text: "XML" });

    await bookmarks.remove(TESTS, { text: "XML" });

    assert.deepStrictEqual(labels(bookmarks.group(ALL_WORKSPACES)), ["XML"]);
    assert.deepStrictEqual(bookmarks.group(TESTS), []);
    assert.strictEqual(workspaceState.get(BOOKMARKS_KEY), undefined);
  });

  test("removes a place from the folder and from All Workspaces", async () => {
    await bookmarks.add(ALL_WORKSPACES, GET_FROM_DICTIONARY);
    await bookmarks.add(TESTS, GET_FROM_DICTIONARY);
    await bookmarks.add(SHARED, GET_FROM_DICTIONARY);

    await bookmarks.removePlace(TESTS, GET_FROM_DICTIONARY);

    assert.deepStrictEqual(bookmarks.forFolder(TESTS), []);
    assert.deepStrictEqual(bookmarks.group(SHARED), [GET_FROM_DICTIONARY]);
  });

  test("moves a bookmark between the groups", async () => {
    await bookmarks.add(TESTS, GET_FROM_DICTIONARY);

    await bookmarks.move(GET_FROM_DICTIONARY, TESTS, ALL_WORKSPACES);
    assert.deepStrictEqual(bookmarks.group(TESTS), []);
    assert.deepStrictEqual(bookmarks.group(ALL_WORKSPACES), [GET_FROM_DICTIONARY]);

    await bookmarks.move(GET_FROM_DICTIONARY, ALL_WORKSPACES, SHARED);
    assert.deepStrictEqual(bookmarks.group(ALL_WORKSPACES), []);
    assert.deepStrictEqual(bookmarks.group(SHARED), [GET_FROM_DICTIONARY]);

    await bookmarks.move(GET_FROM_DICTIONARY, SHARED, TESTS);
    assert.deepStrictEqual(bookmarks.group(SHARED), []);
    assert.deepStrictEqual(bookmarks.group(TESTS), [GET_FROM_DICTIONARY]);
  });

  test("changes nothing for a move into the bookmark's own group", async () => {
    await bookmarks.add(TESTS, GET_FROM_DICTIONARY);
    let changes = 0;
    bookmarks.onDidChange(() => changes++);

    await bookmarks.move(GET_FROM_DICTIONARY, TESTS, TESTS);

    assert.deepStrictEqual(bookmarks.group(TESTS), [GET_FROM_DICTIONARY]);
    assert.strictEqual(changes, 0);
  });

  test("keeps a moved place once in the group it moves into", async () => {
    await bookmarks.add(ALL_WORKSPACES, GET_FROM_DICTIONARY);
    await bookmarks.add(TESTS, GET_FROM_DICTIONARY);

    await bookmarks.move(GET_FROM_DICTIONARY, TESTS, ALL_WORKSPACES);

    assert.deepStrictEqual(bookmarks.group(ALL_WORKSPACES), [GET_FROM_DICTIONARY]);
    assert.deepStrictEqual(bookmarks.group(TESTS), []);
  });

  test("creates the default bookmarks in All Workspaces once, so that a removed one does not come back", async () => {
    await bookmarks.createDefaults();
    assert.deepStrictEqual(labels(bookmarks.group(ALL_WORKSPACES)), [...DEFAULT_BOOKMARKS]);
    assert.strictEqual(globalState.get(DEFAULT_BOOKMARKS_KEY), true);

    await bookmarks.remove(ALL_WORKSPACES, { text: "Telnet" });
    await bookmarks.createDefaults();

    assert.deepStrictEqual(
      labels(bookmarks.group(ALL_WORKSPACES)),
      DEFAULT_BOOKMARKS.filter((text) => text !== "Telnet"),
    );
  });

  test("resets All Workspaces and the groups of the given folders to the default bookmarks", async () => {
    await bookmarks.createDefaults();
    await bookmarks.remove(ALL_WORKSPACES, { text: "Telnet" });
    await bookmarks.add(ALL_WORKSPACES, GET_FROM_DICTIONARY);
    await bookmarks.add(TESTS, { text: "resources/shop.resource" });
    await bookmarks.add(SHARED, { text: "common.resource" });

    await bookmarks.reset([TESTS]);

    assert.deepStrictEqual(labels(bookmarks.group(ALL_WORKSPACES)), [...DEFAULT_BOOKMARKS]);
    assert.deepStrictEqual(bookmarks.group(TESTS), []);
    assert.deepStrictEqual(labels(bookmarks.group(SHARED)), ["common.resource"]);
  });

  test("leaves out stored values that are not bookmarks", async () => {
    await globalState.update(BOOKMARKS_KEY, [{ text: 1 }, "XML", { text: "XML", heading: 3 }, { text: "" }]);
    await workspaceState.update(BOOKMARKS_KEY, { [TESTS]: "common.resource" });

    assert.deepStrictEqual(bookmarks.forFolder(TESTS), [{ text: "XML" }]);
  });

  test("tells of each change, and of a change by another window", async () => {
    let changes = 0;
    bookmarks.onDidChange(() => changes++);

    await bookmarks.add(TESTS, { text: "XML" });
    await bookmarks.move({ text: "XML" }, TESTS, ALL_WORKSPACES);
    await bookmarks.removePlace(TESTS, { text: "XML" });
    assert.strictEqual(changes, 3);

    bookmarks.checkForChanges();
    assert.strictEqual(changes, 3);

    await globalState.update(BOOKMARKS_KEY, [{ text: "String" }]);
    bookmarks.checkForChanges();
    bookmarks.checkForChanges();
    assert.strictEqual(changes, 4);
  });
});
