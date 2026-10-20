// The part of the Test Explorer that needs no VS Code API: the items of a discovery, the arguments for reading a single
// suite file again, what a file event leads to, and the queue of reads and discoveries. It imports nothing from the
// `vscode` module, so that its tests need no running extension, as RobotCodeFileDiscovery.kt for PyCharm.
import type { Diagnostic, Range } from "vscode-languageclient/node";

import { escapeRobotGlobPatterns } from "./utils";

export enum RobotItemType {
  WORKSPACE = "workspace",
  SUITE = "suite",
  TEST = "test",
  TASK = "task",
  ERROR = "error",
}

export interface RobotTestItem {
  type: RobotItemType;
  id: string;
  uri?: string;
  relSource?: string;
  source?: string;
  children: RobotTestItem[] | undefined;
  name: string;
  longname: string;
  description?: string;
  range?: Range;
  error?: string;
  tags?: string[];
  rpa?: boolean;
}

export interface RobotCodeDiscoverResult {
  items?: RobotTestItem[];
  diagnostics?: { [Key: string]: Diagnostic[] };
  // True when the folder's Robot Framework version supports `--parseinclude` (RF >= 6.1).
  // A per-folder environment fact, not a property of any single test item.
  supportsParseInclude?: boolean;
}

export function walkRobotTree(items: RobotTestItem[] | undefined, cb: (item: RobotTestItem) => void): void {
  if (!items) return;
  for (const item of items) {
    cb(item);
    walkRobotTree(item.children, cb);
  }
}

// `discover all` returns tests and tasks alike, so the same command reads a test suite, a task suite and a project
// with `rpa = true`; `discover tests` would leave the tasks out.
export const FILE_DISCOVERY_COMMAND = ["discover", "--read-from-stdin", "all"];

/**
 * The arguments for reading a single suite file again, after the discover command: `-I` with the file when Robot
 * Framework supports it, `-N` with the top-level suite name of the folder's last discovery, as the runs pass it, and
 * `--suite` with the file's suite. With several test paths, Robot Framework names the top-level suite after the
 * suites it keeps unless `-N` sets it, and the tests of the file would get other IDs (RF #4289).
 */
export function fileDiscoveryArguments(
  suite: Pick<RobotTestItem, "relSource" | "longname">,
  topLevelSuite: string | undefined,
  supportsParseInclude: boolean,
): string[] {
  return [
    ...(supportsParseInclude && suite.relSource ? ["-I", escapeRobotGlobPatterns(suite.relSource)] : []),
    ...(topLevelSuite !== undefined ? ["-N", topLevelSuite] : []),
    "--suite",
    escapeRobotGlobPatterns(suite.longname),
  ];
}

/**
 * The children of the suite with `suiteId` in the result of reading a single file, or undefined when the result has
 * no such suite or the suite has no children; the folder is then discovered instead. The result also holds the
 * workspace item and the folder suites above the file, each with only the path to the file as children, so only the
 * children of the file's suite may replace those in the model.
 */
export function suiteChildrenIn(items: RobotTestItem[] | undefined, suiteId: string): RobotTestItem[] | undefined {
  for (const item of items ?? []) {
    if (item.id === suiteId) return item.children?.length ? item.children : undefined;
    const children = suiteChildrenIn(item.children, suiteId);
    if (children !== undefined) return children;
  }
  return undefined;
}

/**
 * The items of the folders' models by ID, and their suites by URI. Replacing the children of a suite with those of
 * a single file's read changes only that suite and its index entries; the other suites keep theirs.
 */
export class RobotItemIndex {
  private readonly byId = new Map<string, RobotTestItem>();
  private readonly suitesByUri = new Map<string, RobotTestItem>();

  // `normalizeUri` gives the form of a URI that file events use, so that the suites can be looked up by it.
  constructor(private readonly normalizeUri: (uri: string) => string = (uri) => uri) {}

  public get(id: string): RobotTestItem | undefined {
    return this.byId.get(id);
  }

  public suiteOf(uri: string): RobotTestItem | undefined {
    return this.suitesByUri.get(uri);
  }

  public add(items: RobotTestItem[] | undefined): void {
    walkRobotTree(items, (item) => {
      this.byId.set(item.id, item);
      if (item.type === RobotItemType.SUITE && item.uri !== undefined) {
        this.suitesByUri.set(this.normalizeUri(item.uri), item);
      }
    });
  }

  public remove(items: RobotTestItem[] | undefined): void {
    walkRobotTree(items, (item) => {
      if (this.byId.get(item.id) === item) this.byId.delete(item.id);
      if (item.type === RobotItemType.SUITE && item.uri !== undefined) {
        const uri = this.normalizeUri(item.uri);
        if (this.suitesByUri.get(uri) === item) this.suitesByUri.delete(uri);
      }
    });
  }

  /** Puts `children` in place of the children of `suite`, in the model and in the index. */
  public replaceChildren(suite: RobotTestItem, children: RobotTestItem[]): void {
    this.remove(suite.children);
    suite.children = children;
    this.add(children);
  }

  public clear(): void {
    this.byId.clear();
    this.suitesByUri.clear();
  }
}

// "edited": an edit or a save in the editor; the others come from the file watcher.
export type FileEventKind = "edited" | "changed" | "created" | "deleted";

export type FileEventAction = "read" | "discover" | "none";

export interface FileEvent {
  kind: FileEventKind;
  // the folder's model shows the file as a suite
  isSuiteFile: boolean;
  // a file with the extension of resource files; Robot Framework never builds a suite from one
  isResourceFile: boolean;
  // a file with one of the extensions of Robot Framework files
  isRobotFile: boolean;
  // a created folder that holds Robot Framework files
  isFolderWithRobotFiles: boolean;
  // a deleted path that is the source of a discovered suite, or lies above one
  isAtOrAboveSuite: boolean;
}

/**
 * What a file event leads to: reading the file again, a discovery of its workspace folder, or nothing. A content
 * change of a suite file reads that file, in the editor or on disk, open or closed. Any other event of a Robot
 * Framework file, such as an `__init__.robot` or a file without tests so far, or of a folder discovers the folder.
 */
export function fileEventAction(event: FileEvent): FileEventAction {
  if (event.isResourceFile) return "none";
  switch (event.kind) {
    case "edited":
    case "changed":
      if (event.isSuiteFile) return "read";
      return event.isRobotFile ? "discover" : "none";
    case "created":
      return event.isRobotFile || event.isFolderWithRobotFiles ? "discover" : "none";
    case "deleted":
      return event.isRobotFile || event.isAtOrAboveSuite ? "discover" : "none";
  }
}

// How a run request runs a workspace folder: with the settings of the request's profile, with the folder's own
// settings, or not at all.
export type FolderRun = "profile" | "own" | "none";

/**
 * How a run request runs a workspace folder, from whether the request's profile belongs to the folder and whether the
 * request names its tests. A request without tests asks for all tests (VS Code's `TestRunRequest.include`); **Run
 * Tests** sends it with the profile of one folder, so the other folders run as their own profile runs them: the
 * `robot.toml` profiles and launch configurations of one folder mean nothing in another. A request that names its tests
 * runs only the folders of its profile; VS Code offers an item only the profiles of its folder.
 */
export function folderRun(isProfileFolder: boolean, namesTests: boolean): FolderRun {
  if (isProfileFolder) return "profile";
  return namesTests ? "none" : "own";
}

export interface TimerFunctions {
  setTimeout(callback: () => void, ms: number): unknown;
  clearTimeout(handle: unknown): void;
}

export interface RefreshJobs {
  readFile(folder: string, uri: string, signal: AbortSignal): Promise<void>;
  discoverFolder(folder: string, signal: AbortSignal): Promise<void>;
}

/**
 * The queue of the reads of single files and the discoveries of workspace folders, both keyed by URI string. All jobs
 * run one after another. A newer request for a file replaces an older read of the same file, a discovery of a folder
 * replaces the folder's reads and its older discovery, and reads never cancel each other or a running discovery.
 * When many files of one folder change together, one discovery of that folder covers them.
 */
export class RefreshQueue {
  static readonly DEBOUNCE_MS = 1000;
  // When a file's timer fires and at least this many other files of its folder are pending, the folder is discovered.
  static readonly BURST_THRESHOLD = 5;

  private readonly fileTimers = new Map<string, { folder: string; handle: unknown }>();
  private readonly fileJobs = new Map<string, { folder: string; controller: AbortController }>();
  private readonly folderTimers = new Map<string, unknown>();
  private readonly folderJobs = new Map<string, AbortController>();
  private chain: Promise<void> = Promise.resolve();

  constructor(
    private readonly jobs: RefreshJobs,
    private readonly timers: TimerFunctions = {
      setTimeout: (callback, ms) => setTimeout(callback, ms),
      clearTimeout: (handle) => clearTimeout(handle as NodeJS.Timeout),
    },
  ) {}

  /** Reads the file again after the debounce time, unless the folder is discovered first. */
  public requestFile(folder: string, uri: string): void {
    this.cancelFile(uri);
    const handle = this.timers.setTimeout(() => {
      this.fileTimers.delete(uri);
      const pendingOfFolder = [...this.fileTimers.values()].filter((timer) => timer.folder === folder).length;
      if (pendingOfFolder >= RefreshQueue.BURST_THRESHOLD) {
        void this.discoverFolder(folder);
      } else {
        void this.readFile(folder, uri);
      }
    }, RefreshQueue.DEBOUNCE_MS);
    this.fileTimers.set(uri, { folder, handle });
  }

  /** Discovers the folder after the debounce time; requests within that time lead to one discovery. */
  public requestFolder(folder: string): void {
    this.clearFolderTimer(folder);
    this.folderTimers.set(
      folder,
      this.timers.setTimeout(() => {
        this.folderTimers.delete(folder);
        void this.discoverFolder(folder);
      }, RefreshQueue.DEBOUNCE_MS),
    );
  }

  /** Discovers the folder now, in the queue's order, and cancels the folder's reads and its older discovery. */
  public discoverFolder(folder: string, signal?: AbortSignal): Promise<void> {
    this.clearFolderTimer(folder);
    for (const [uri, timer] of [...this.fileTimers]) {
      if (timer.folder === folder) {
        this.timers.clearTimeout(timer.handle);
        this.fileTimers.delete(uri);
      }
    }
    for (const [uri, job] of [...this.fileJobs]) {
      if (job.folder === folder) {
        job.controller.abort();
        this.fileJobs.delete(uri);
      }
    }
    this.folderJobs.get(folder)?.abort();

    const controller = new AbortController();
    if (signal?.aborted) controller.abort();
    signal?.addEventListener("abort", () => controller.abort(), { once: true });
    this.folderJobs.set(folder, controller);

    return this.enqueue(async () => {
      try {
        if (!controller.signal.aborted) await this.jobs.discoverFolder(folder, controller.signal);
      } finally {
        if (this.folderJobs.get(folder) === controller) this.folderJobs.delete(folder);
      }
    });
  }

  public dispose(): void {
    for (const timer of this.fileTimers.values()) this.timers.clearTimeout(timer.handle);
    for (const handle of this.folderTimers.values()) this.timers.clearTimeout(handle);
    for (const job of this.fileJobs.values()) job.controller.abort();
    for (const controller of this.folderJobs.values()) controller.abort();
    this.fileTimers.clear();
    this.folderTimers.clear();
    this.fileJobs.clear();
    this.folderJobs.clear();
  }

  private readFile(folder: string, uri: string): Promise<void> {
    this.fileJobs.get(uri)?.controller.abort();
    const controller = new AbortController();
    this.fileJobs.set(uri, { folder, controller });

    return this.enqueue(async () => {
      try {
        if (!controller.signal.aborted) await this.jobs.readFile(folder, uri, controller.signal);
      } finally {
        if (this.fileJobs.get(uri)?.controller === controller) this.fileJobs.delete(uri);
      }
    });
  }

  private cancelFile(uri: string): void {
    const timer = this.fileTimers.get(uri);
    if (timer !== undefined) {
      this.timers.clearTimeout(timer.handle);
      this.fileTimers.delete(uri);
    }
    this.fileJobs.get(uri)?.controller.abort();
    this.fileJobs.delete(uri);
  }

  private clearFolderTimer(folder: string): void {
    const handle = this.folderTimers.get(folder);
    if (handle !== undefined) {
      this.timers.clearTimeout(handle);
      this.folderTimers.delete(folder);
    }
  }

  private enqueue(job: () => Promise<void>): Promise<void> {
    const run = this.chain.then(job);
    this.chain = run.catch(() => undefined);
    return run;
  }
}
