import * as assert from "assert";
import * as vscode from "vscode";

import { RobotTestItem, walkRobotTree } from "../extension/testdiscovery";
import { folderUriOf, TestTreeBuilder } from "../extension/testtree";
import multipathFolder from "./fixtures/discover/multipath-folder.json";
import rpaFolder from "./fixtures/discover/rpa-folder.json";

// A fresh copy of the items of a recorded result of `robotcode discover`, so that a test may change it.
function recorded(result: unknown): RobotTestItem[] {
  return (JSON.parse(JSON.stringify(result)) as { items: RobotTestItem[] }).items;
}

function find(items: RobotTestItem[], id: string): RobotTestItem {
  let found: RobotTestItem | undefined;
  walkRobotTree(items, (item) => {
    if (item.id === id) found = item;
  });
  assert.ok(found, `no item ${id}`);
  return found;
}

// Every item of the tree by ID, in the order of the tree.
function seen(
  items: vscode.TestItemCollection,
  result = new Map<string, vscode.TestItem>(),
): Map<string, vscode.TestItem> {
  items.forEach((item) => {
    result.set(item.id, item);
    seen(item.children, result);
  });
  return result;
}

// A controller whose items count every property set on them. Items of a real controller give no sign whether a
// property was set to an equal value again.
class CountingController {
  public writes = 0;
  public readonly items = new CountingCollection();

  public createTestItem(id: string, label: string, uri?: vscode.Uri): vscode.TestItem {
    const values: Record<string, unknown> = { label, tags: [], canResolveChildren: false, busy: false };
    const item = { id, uri, children: new CountingCollection() } as unknown as vscode.TestItem;
    for (const name of ["label", "description", "range", "error", "tags", "canResolveChildren", "busy"]) {
      Object.defineProperty(item, name, {
        get: () => values[name],
        set: (value) => {
          this.writes++;
          values[name] = value;
        },
      });
    }
    return item;
  }
}

class CountingCollection {
  private readonly items = new Map<string, vscode.TestItem>();

  public get size(): number {
    return this.items.size;
  }

  public get(id: string): vscode.TestItem | undefined {
    return this.items.get(id);
  }

  public add(item: vscode.TestItem): void {
    this.items.set(item.id, item);
  }

  public delete(id: string): void {
    this.items.delete(id);
  }

  public forEach(callback: (item: vscode.TestItem) => void): void {
    this.items.forEach((item) => callback(item));
  }
}

// The top-level suite that Robot Framework creates for the paths "electron" and "vscode"; it has no source.
const TOP_LEVEL = ";Electron & Vscode";
const OPEN_VS_CODE = "/project/vscode/open_vs_code.robot;Electron & Vscode.Vscode.Open Vs Code";
const OPENS_TERMINAL = `${OPEN_VS_CODE}.Opens Terminal;5`;
const SETTINGS_PAGE = "/project/vscode/settings_page.robot;Electron & Vscode.Vscode.Settings Page";

suite("Building the tree from the model", () => {
  let controller: vscode.TestController;
  let builder: TestTreeBuilder;

  const build = (items: RobotTestItem[]) => {
    for (const item of items) builder.build(undefined, item);
  };

  setup(() => {
    controller = vscode.tests.createTestController(`robotcode.test.${Date.now()}`, "RobotCode tests of the tree");
    builder = new TestTreeBuilder(controller, {
      tagsOf: (names) => (names ?? []).map((name) => new vscode.TestTag(name)),
      folderTagOf: () => undefined,
    });
  });

  teardown(() => {
    controller.dispose();
  });

  test("builds the items of a folder with their names and lines", () => {
    build(recorded(multipathFolder));

    const terminal = builder.get(OPENS_TERMINAL);
    assert.strictEqual(terminal?.label, "Opens Terminal");
    assert.strictEqual(terminal?.range?.start.line, 4);
    assert.strictEqual(terminal?.parent?.id, OPEN_VS_CODE);
    assert.deepStrictEqual(
      [...seen(controller.items).values()].map((item) => item.label),
      [
        "multipath",
        "Electron & Vscode",
        "Electron",
        "App",
        "App Starts",
        "Vscode",
        "Open Vs Code",
        "Opens Editor",
        "Opens Terminal",
        "Settings Page",
        "Shows Settings",
      ],
    );
  });

  test("building again from an equal model changes no item", () => {
    const counting = new CountingController();
    const countingBuilder = new TestTreeBuilder(counting as unknown as vscode.TestController, {
      tagsOf: (names) => (names ?? []).map((name) => new vscode.TestTag(name)),
      folderTagOf: () => undefined,
    });
    for (const item of recorded(multipathFolder)) countingBuilder.build(undefined, item);
    const items = seen(counting.items as unknown as vscode.TestItemCollection);
    assert.ok(counting.writes > 0);
    counting.writes = 0;

    for (const item of recorded(multipathFolder)) countingBuilder.build(undefined, item);

    assert.strictEqual(counting.writes, 0, "properties were set again");
    const again = seen(counting.items as unknown as vscode.TestItemCollection);
    assert.deepStrictEqual([...again.keys()], [...items.keys()]);
    for (const [id, item] of items) assert.strictEqual(again.get(id), item, `${id} was replaced`);
  });

  test("a new model adds, updates and removes exactly the items that differ", () => {
    build(recorded(multipathFolder));
    const before = seen(controller.items);

    const model = recorded(multipathFolder);
    find(model, OPENS_TERMINAL).name = "Opens The Terminal";
    const suite = find(model, OPEN_VS_CODE);
    suite.children?.push({
      ...find(model, OPENS_TERMINAL),
      id: `${OPEN_VS_CODE}.Opens Settings;8`,
      name: "Opens Settings",
    });
    const folder = find(model, "/project/vscode;Electron & Vscode.Vscode");
    folder.children = folder.children?.filter((child) => child.id !== SETTINGS_PAGE);
    build(model);
    const after = seen(controller.items);

    assert.strictEqual(after.get(OPENS_TERMINAL), before.get(OPENS_TERMINAL));
    assert.strictEqual(after.get(OPENS_TERMINAL)?.label, "Opens The Terminal");
    assert.strictEqual(after.get(`${OPEN_VS_CODE}.Opens Settings;8`)?.label, "Opens Settings");
    assert.strictEqual(after.has(SETTINGS_PAGE), false);
    assert.strictEqual(builder.get(SETTINGS_PAGE), undefined);
    for (const [id, item] of before) {
      if (id.startsWith(SETTINGS_PAGE)) continue;
      assert.strictEqual(after.get(id), item, `${id} was replaced`);
    }
  });

  test("a suite left without children is removed", () => {
    build(recorded(multipathFolder));

    const model = recorded(multipathFolder);
    find(model, SETTINGS_PAGE).children = [];
    build(model);

    assert.strictEqual(builder.get(SETTINGS_PAGE), undefined);
    assert.ok(builder.get(OPEN_VS_CODE));
  });

  test("the top-level suite of several paths gets the tag of its workspace folder", () => {
    const folderTag = new vscode.TestTag("folder");
    builder = new TestTreeBuilder(controller, {
      tagsOf: (names) => (names ?? []).map((name) => new vscode.TestTag(name)),
      folderTagOf: (item) => (folderUriOf(item)?.toString() === "file:///project" ? folderTag : undefined),
    });
    build(recorded(multipathFolder));

    const topLevel = builder.get(TOP_LEVEL);
    assert.strictEqual(topLevel?.uri, undefined);
    // the builder asks for the tag once the item has its parent
    assert.ok(topLevel?.tags.includes(folderTag));
    // an item with a URI keeps its own
    const suite = builder.get(OPEN_VS_CODE);
    assert.ok(suite);
    assert.strictEqual(folderUriOf(suite)?.toString(), "file:///project/vscode/open_vs_code.robot");
  });

  test("keeps the tasks of a file with a Tasks section", () => {
    build(recorded(rpaFolder));

    const cleanup = builder.get("/project/tasks/cleanup.robot;Tasks.Cleanup");
    const tasks: string[] = [];
    cleanup?.children.forEach((child) => {
      tasks.push(child.label);
    });
    assert.deepStrictEqual(tasks, ["Clean Up", "Archive Files"]);
    assert.strictEqual(
      cleanup?.children.get("/project/tasks/cleanup.robot;Tasks.Cleanup.Clean Up;2")?.description,
      "task ",
    );
  });
});
