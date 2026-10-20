import * as assert from "assert";

import {
  FileEvent,
  fileDiscoveryArguments,
  fileEventAction,
  folderRun,
  RefreshJobs,
  RefreshQueue,
  RobotCodeDiscoverResult,
  RobotItemIndex,
  RobotItemType,
  RobotTestItem,
  suiteChildrenIn,
  TimerFunctions,
  walkRobotTree,
} from "../extension/testdiscovery";
import multipathFile from "./fixtures/discover/multipath-file.json";
import multipathFileWithoutName from "./fixtures/discover/multipath-file-without-name.json";
import multipathFolder from "./fixtures/discover/multipath-folder.json";
import rpaFile from "./fixtures/discover/rpa-file.json";

// A fresh copy of a recorded result of `robotcode discover`, so that a test may change it.
function recorded(result: unknown): RobotCodeDiscoverResult {
  return JSON.parse(JSON.stringify(result)) as RobotCodeDiscoverResult;
}

function find(items: RobotTestItem[] | undefined, id: string): RobotTestItem {
  let found: RobotTestItem | undefined;
  walkRobotTree(items, (item) => {
    if (item.id === id) found = item;
  });
  assert.ok(found, `no item ${id}`);
  return found;
}

const OPEN_VS_CODE = "/project/vscode/open_vs_code.robot;Electron & Vscode.Vscode.Open Vs Code";
const SETTINGS_PAGE = "/project/vscode/settings_page.robot;Electron & Vscode.Vscode.Settings Page";
const VSCODE_FOLDER = "/project/vscode;Electron & Vscode.Vscode";

suite("Reading a single suite file", () => {
  test("the children of the file's suite come from the result", () => {
    const children = suiteChildrenIn(recorded(multipathFile).items, OPEN_VS_CODE);

    assert.deepStrictEqual(
      children?.map((child) => child.name),
      ["Opens Editor", "Opens Terminal"],
    );
  });

  test("the tasks of a file with a Tasks section arrive", () => {
    const children = suiteChildrenIn(recorded(rpaFile).items, "/project/tasks/cleanup.robot;Tasks.Cleanup");

    assert.deepStrictEqual(
      children?.map((child) => [child.type, child.name]),
      [
        [RobotItemType.TASK, "Clean Up"],
        [RobotItemType.TASK, "Archive Files"],
      ],
    );
  });

  test("a result whose top-level suite has another name asks for a discovery of the folder", () => {
    // Without -N, Robot Framework names the top-level suite after the suites it keeps (RF #4289).
    assert.strictEqual(suiteChildrenIn(recorded(multipathFileWithoutName).items, OPEN_VS_CODE), undefined);
  });

  test("a suite without children asks for a discovery of the folder", () => {
    const result = recorded(multipathFile);
    find(result.items, OPEN_VS_CODE).children = [];

    assert.strictEqual(suiteChildrenIn(result.items, OPEN_VS_CODE), undefined);
  });

  test("a missing suite asks for a discovery of the folder", () => {
    assert.strictEqual(suiteChildrenIn(recorded(multipathFile).items, SETTINGS_PAGE), undefined);
  });
});

suite("The index of a folder's model", () => {
  test("replacing a suite's children keeps the sibling suites and their index entries", () => {
    const model = recorded(multipathFolder).items;
    const index = new RobotItemIndex();
    index.add(model);
    const suite = find(model, OPEN_VS_CODE);
    const oldChildren = suite.children ?? [];
    const sibling = find(model, SETTINGS_PAGE);
    const siblingChildren = sibling.children;

    const children = suiteChildrenIn(recorded(multipathFile).items, OPEN_VS_CODE) ?? [];
    const added = { ...children[0], id: `${OPEN_VS_CODE}.Opens Settings;8`, name: "Opens Settings" };
    index.replaceChildren(suite, [...children, added]);

    assert.strictEqual(suite.children?.length, 3);
    assert.strictEqual(index.get(added.id), added);
    for (const child of children) assert.strictEqual(index.get(child.id), child);
    for (const child of oldChildren) assert.notStrictEqual(index.get(child.id), child);

    assert.strictEqual(index.get(SETTINGS_PAGE), sibling);
    assert.strictEqual(sibling.children, siblingChildren);
    for (const child of siblingChildren ?? []) assert.strictEqual(index.get(child.id), child);
    assert.deepStrictEqual(
      find(model, VSCODE_FOLDER).children?.map((child) => child.name),
      ["Open Vs Code", "Settings Page"],
    );
    assert.strictEqual(index.get(VSCODE_FOLDER), find(model, VSCODE_FOLDER));
  });

  test("finds the suite of a file by its URI", () => {
    const model = recorded(multipathFolder).items;
    const index = new RobotItemIndex();
    index.add(model);

    assert.strictEqual(index.suiteOf("file:///project/vscode/open_vs_code.robot"), find(model, OPEN_VS_CODE));
    assert.strictEqual(index.suiteOf("file:///project/vscode/missing.robot"), undefined);
  });

  test("removing a model removes its entries", () => {
    const model = recorded(multipathFolder).items;
    const index = new RobotItemIndex();
    index.add(model);
    index.remove(model);

    assert.strictEqual(index.get(OPEN_VS_CODE), undefined);
    assert.strictEqual(index.suiteOf("file:///project/vscode/open_vs_code.robot"), undefined);
  });
});

suite("The arguments for reading a single suite file", () => {
  const suite = { relSource: "vscode/open_vs_code.robot", longname: "Electron & Vscode.Vscode.Open Vs Code" };

  test("pass -I, the top-level suite name with -N and the suite, in this order", () => {
    assert.deepStrictEqual(fileDiscoveryArguments(suite, "Electron & Vscode", true), [
      "-I",
      "vscode/open_vs_code.robot",
      "-N",
      "Electron & Vscode",
      "--suite",
      "Electron & Vscode.Vscode.Open Vs Code",
    ]);
  });

  test("pass no -N without a top-level suite name", () => {
    assert.deepStrictEqual(fileDiscoveryArguments(suite, undefined, true), [
      "-I",
      "vscode/open_vs_code.robot",
      "--suite",
      "Electron & Vscode.Vscode.Open Vs Code",
    ]);
  });

  test("pass no -I when Robot Framework does not support it", () => {
    assert.deepStrictEqual(fileDiscoveryArguments(suite, "Electron & Vscode", false), [
      "-N",
      "Electron & Vscode",
      "--suite",
      "Electron & Vscode.Vscode.Open Vs Code",
    ]);
  });

  test("escape the glob characters of -I and --suite, not of the name", () => {
    assert.deepStrictEqual(
      fileDiscoveryArguments({ relSource: "a*b.robot", longname: "Project.A*b [x]" }, "P*", true),
      ["-I", "a[*]b.robot", "-N", "P*", "--suite", "Project.A[*]b [[]x[]]"],
    );
  });
});

suite("What a file event leads to", () => {
  const event = (facts: Partial<FileEvent>): FileEvent => ({
    kind: "changed",
    isSuiteFile: false,
    isResourceFile: false,
    isRobotFile: false,
    isFolderWithRobotFiles: false,
    isAtOrAboveSuite: false,
    ...facts,
  });

  test("an edit of an open suite file reads the file", () => {
    assert.strictEqual(fileEventAction(event({ kind: "edited", isSuiteFile: true, isRobotFile: true })), "read");
  });

  test("a change on disk of a suite file, open or closed, reads the file", () => {
    assert.strictEqual(fileEventAction(event({ kind: "changed", isSuiteFile: true, isRobotFile: true })), "read");
  });

  test("a change on disk of a custom parser's suite file reads the file", () => {
    assert.strictEqual(fileEventAction(event({ kind: "changed", isSuiteFile: true })), "read");
  });

  test("a resource file starts nothing", () => {
    for (const kind of ["edited", "changed", "created", "deleted"] as const) {
      assert.strictEqual(fileEventAction(event({ kind, isResourceFile: true, isRobotFile: true })), "none", kind);
    }
  });

  test("an edit of __init__.robot or of a .robot file without tests discovers the folder", () => {
    assert.strictEqual(fileEventAction(event({ kind: "edited", isRobotFile: true })), "discover");
    assert.strictEqual(fileEventAction(event({ kind: "changed", isRobotFile: true })), "discover");
  });

  test("an edit of another file starts nothing", () => {
    assert.strictEqual(fileEventAction(event({ kind: "edited" })), "none");
    assert.strictEqual(fileEventAction(event({ kind: "changed" })), "none");
  });

  test("a created Robot Framework file or folder with such files discovers the folder", () => {
    assert.strictEqual(fileEventAction(event({ kind: "created", isRobotFile: true })), "discover");
    assert.strictEqual(fileEventAction(event({ kind: "created", isFolderWithRobotFiles: true })), "discover");
    assert.strictEqual(fileEventAction(event({ kind: "created" })), "none");
  });

  test("a deleted Robot Framework file, suite or folder above a suite discovers the folder", () => {
    assert.strictEqual(fileEventAction(event({ kind: "deleted", isRobotFile: true })), "discover");
    assert.strictEqual(fileEventAction(event({ kind: "deleted", isAtOrAboveSuite: true })), "discover");
    assert.strictEqual(fileEventAction(event({ kind: "deleted" })), "none");
  });
});

suite("Which workspace folders a run request runs", () => {
  test("a request without tests runs the profile's folder with its settings and another folder with its own", () => {
    assert.strictEqual(folderRun(true, false), "profile");
    assert.strictEqual(folderRun(false, false), "own");
  });

  test("a request that names its tests leaves the folders of other profiles out", () => {
    assert.strictEqual(folderRun(true, true), "profile");
    assert.strictEqual(folderRun(false, true), "none");
  });
});

// Timers that a test fires by hand, one after another, as long as some are pending.
class ManualTimers implements TimerFunctions {
  private next = 1;
  private readonly pending = new Map<number, () => void>();

  public setTimeout(callback: () => void): unknown {
    const handle = this.next++;
    this.pending.set(handle, callback);
    return handle;
  }

  public clearTimeout(handle: unknown): void {
    this.pending.delete(handle as number);
  }

  public get size(): number {
    return this.pending.size;
  }

  public fireAll(): void {
    for (let entry = this.pending.entries().next(); !entry.done; entry = this.pending.entries().next()) {
      const [handle, callback] = entry.value;
      this.pending.delete(handle);
      callback();
    }
  }
}

// Jobs that record what ran, and that can be held until a test lets them go on.
class RecordingJobs implements RefreshJobs {
  public readonly calls: string[] = [];
  public hold: Promise<void> | undefined;

  public async readFile(folder: string, uri: string, signal: AbortSignal): Promise<void> {
    this.calls.push(`read ${uri}`);
    await this.hold;
    if (signal.aborted) this.calls.push(`aborted ${uri}`);
  }

  public async discoverFolder(folder: string, signal: AbortSignal): Promise<void> {
    this.calls.push(`discover ${folder}`);
    await this.hold;
    if (signal.aborted) this.calls.push(`aborted ${folder}`);
  }
}

const flush = async () => {
  for (let i = 0; i < 5; i++) await new Promise((resolve) => setTimeout(resolve, 0));
};

suite("The queue of reads and discoveries", () => {
  let timers: ManualTimers;
  let jobs: RecordingJobs;
  let queue: RefreshQueue;

  setup(() => {
    timers = new ManualTimers();
    jobs = new RecordingJobs();
    queue = new RefreshQueue(jobs, timers);
  });

  teardown(() => queue.dispose());

  test("two files changed together are both read", async () => {
    queue.requestFile("f", "a.robot");
    queue.requestFile("f", "b.robot");
    timers.fireAll();
    await flush();

    assert.deepStrictEqual(jobs.calls, ["read a.robot", "read b.robot"]);
  });

  test("a second request for the same file replaces the first", async () => {
    queue.requestFile("f", "a.robot");
    queue.requestFile("f", "a.robot");
    assert.strictEqual(timers.size, 1);
    timers.fireAll();
    await flush();

    assert.deepStrictEqual(jobs.calls, ["read a.robot"]);
  });

  test("a new request for a file cancels its running read", async () => {
    let release: () => void = () => undefined;
    jobs.hold = new Promise((resolve) => (release = resolve));
    queue.requestFile("f", "a.robot");
    timers.fireAll();
    await flush();
    queue.requestFile("f", "a.robot");
    release();
    await flush();

    assert.deepStrictEqual(jobs.calls, ["read a.robot", "aborted a.robot"]);
  });

  test("a discovery of a folder drops that folder's reads and not another folder's", async () => {
    queue.requestFile("f1", "a.robot");
    queue.requestFile("f2", "b.robot");
    await queue.discoverFolder("f1");
    timers.fireAll();
    await flush();

    assert.deepStrictEqual(jobs.calls, ["discover f1", "read b.robot"]);
  });

  test("reads wait behind a running discovery instead of cancelling it", async () => {
    let release: () => void = () => undefined;
    jobs.hold = new Promise((resolve) => (release = resolve));
    const discovery = queue.discoverFolder("f");
    await flush();
    queue.requestFile("f", "a.robot");
    timers.fireAll();
    await flush();
    release();
    await discovery;
    await flush();

    assert.deepStrictEqual(jobs.calls, ["discover f", "read a.robot"]);
  });

  test("six files of one folder lead to one discovery of that folder", async () => {
    for (let i = 1; i <= 6; i++) queue.requestFile("f", `${i}.robot`);
    timers.fireAll();
    await flush();

    assert.deepStrictEqual(jobs.calls, ["discover f"]);
  });

  test("the six files of one folder leave the read of another folder's file", async () => {
    for (let i = 1; i <= 6; i++) queue.requestFile("f1", `${i}.robot`);
    queue.requestFile("f2", "other.robot");
    timers.fireAll();
    await flush();

    assert.deepStrictEqual(jobs.calls, ["discover f1", "read other.robot"]);
  });

  test("five files of one folder are read one by one", async () => {
    for (let i = 1; i <= 5; i++) queue.requestFile("f", `${i}.robot`);
    timers.fireAll();
    await flush();

    assert.deepStrictEqual(jobs.calls, [
      "read 1.robot",
      "read 2.robot",
      "read 3.robot",
      "read 4.robot",
      "read 5.robot",
    ]);
  });

  test("requests for a folder within the debounce time lead to one discovery", async () => {
    queue.requestFolder("f");
    queue.requestFolder("f");
    timers.fireAll();
    await flush();

    assert.deepStrictEqual(jobs.calls, ["discover f"]);
  });
});
