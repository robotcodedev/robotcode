/* eslint-disable @typescript-eslint/no-unsafe-assignment */
/* eslint-disable @typescript-eslint/no-unsafe-member-access */
/* eslint-disable @typescript-eslint/no-unsafe-argument */
import { red, yellow } from "ansi-colors";
import * as vscode from "vscode";
import { DebugManager } from "./debugmanager";
import { ClientState, LanguageClientsManager, RobotTestItem, toVsCodeRange } from "./languageclientsmanger";
import { Mutex, sleep, WeakValueMap } from "./utils";

interface RobotExecutionAttributes {
  id: string | undefined;
  longname: string | undefined;
  originalname: string | undefined;
  template: string | undefined;
  status: string | undefined;
  message: string | undefined;
  elapsedtime: number | undefined;
  source: string | undefined;
  lineno: number | undefined;
  starttime: string | undefined;
  endtime: string | undefined;
  tags: string[] | undefined;
}

type RobotEventType = "suite" | "test" | "keyword" | string;

interface RobotExecutionEvent {
  type: RobotEventType;
  id: string;
  attributes: RobotExecutionAttributes | undefined;
  failedKeywords: RobotExecutionAttributes[] | undefined;
}

type RobotLogLevel = "FAIL" | "WARN" | "INFO" | "DEBUG" | "TRACE" | string;

interface RobotLogMessageEvent {
  itemId: string | undefined;
  source: string | undefined;
  lineno: number | undefined;
  column: number | undefined;

  message: string;
  level: RobotLogLevel;
  timestamp: string;
  html: string;
}

class DidChangeEntry {
  constructor(timerHandle: NodeJS.Timeout, tokenSource: vscode.CancellationTokenSource) {
    this.timer = timerHandle;
    this.tokenSource = tokenSource;
  }
  public readonly timer: NodeJS.Timeout;
  public readonly tokenSource: vscode.CancellationTokenSource;

  public cancel() {
    clearTimeout(this.timer);
    this.tokenSource.cancel();
  }
}

class WorkspaceFolderEntry {
  private _valid: boolean;
  public get valid(): boolean {
    return this._valid;
  }
  public set valid(v: boolean) {
    this._valid = v;
  }

  public constructor(valid: boolean, readonly items: RobotTestItem[] | undefined) {
    this._valid = valid;
  }
}

export class TestControllerManager {
  private _disposables: vscode.Disposable;
  public readonly testController: vscode.TestController;
  public readonly runProfile: vscode.TestRunProfile;
  public readonly debugProfile: vscode.TestRunProfile;
  public readonly dryRunProfile: vscode.TestRunProfile;
  public readonly dryRunDebugProfile: vscode.TestRunProfile;
  private readonly refreshMutex = new Mutex();
  private readonly debugSessions = new Set<vscode.DebugSession>();
  private readonly didChangedTimer = new Map<string, DidChangeEntry>();
  private fileChangeTimer: DidChangeEntry | undefined;

  constructor(
    public readonly extensionContext: vscode.ExtensionContext,
    public readonly languageClientsManager: LanguageClientsManager,
    public readonly debugManager: DebugManager,
    public readonly outputChannel: vscode.OutputChannel
  ) {
    this.testController = vscode.tests.createTestController("robotCode.RobotFramework", "RobotFramework");

    this.runProfile = this.testController.createRunProfile(
      "Run",
      vscode.TestRunProfileKind.Run,
      async (request, token) => this.runTests(request, token),
      true
    );

    this.dryRunProfile = this.testController.createRunProfile(
      "Dry Run",
      vscode.TestRunProfileKind.Run,
      async (request, token) => this.runTests(request, token, true),
      false
    );

    this.debugProfile = this.testController.createRunProfile(
      "Debug",
      vscode.TestRunProfileKind.Debug,
      async (request, token) => this.runTests(request, token),
      true
    );

    this.dryRunDebugProfile = this.testController.createRunProfile(
      "Dry Debug",
      vscode.TestRunProfileKind.Debug,
      async (request, token) => this.runTests(request, token, true),
      false
    );

    this.testController.resolveHandler = async (item) => {
      await this.refresh(item);
    };

    const fileWatcher = vscode.workspace.createFileSystemWatcher("**/*.{robot,resource}");
    fileWatcher.onDidCreate((uri) => this.refreshUri(uri, "create"));
    fileWatcher.onDidDelete((uri) => this.refreshUri(uri, "delete"));
    fileWatcher.onDidChange((uri) => this.refreshUri(uri, "change"));

    this._disposables = vscode.Disposable.from(
      fileWatcher,
      this.languageClientsManager.onClientStateChanged((event) => {
        switch (event.state) {
          case ClientState.Running: {
            this.refresh().catch((_) => undefined);
            break;
          }
          case ClientState.Stopped: {
            const folder = vscode.workspace.getWorkspaceFolder(event.uri);
            if (folder) this.removeWorkspaceFolderItems(folder);

            break;
          }
        }
      }),
      vscode.workspace.onDidCloseTextDocument(async (document) => {
        if (document.languageId !== "robotframework") return;

        await this.refreshWorkspace(vscode.workspace.getWorkspaceFolder(document.uri));
      }),
      vscode.workspace.onDidSaveTextDocument((document) => {
        this.refreshDocument(document);
      }),
      vscode.workspace.onDidOpenTextDocument(async (document) => {
        if (document.languageId !== "robotframework") return;

        await this.refresh(this.findTestItemForDocument(document));
      }),
      vscode.workspace.onDidChangeTextDocument((event) => {
        this.refreshDocument(event.document);
      }),
      vscode.workspace.onDidChangeWorkspaceFolders(async (event) => {
        for (const r of event.removed) {
          this.removeWorkspaceFolderItems(r);
        }
        if (event.added.length > 0) await this.refresh();
      }),

      vscode.debug.onDidStartDebugSession((session) => {
        if (session.configuration.type === "robotcode" && session.configuration.runId !== undefined) {
          if (this.testRuns.has(session.configuration.runId)) {
            this.debugSessions.add(session);
          }
        }
      }),
      vscode.debug.onDidTerminateDebugSession((session) => {
        if (this.debugSessions.has(session)) {
          this.debugSessions.delete(session);

          if (session.configuration.runId !== undefined) {
            this.TestRunExited(session.configuration.runId);
          }
        }
      }),
      vscode.debug.onDidReceiveDebugSessionCustomEvent((event) => {
        if (event.session.configuration.type === "robotcode") {
          switch (event.event) {
            case "robotExited": {
              this.TestRunExited(event.session.configuration.runId);
              break;
            }

            case "robotStarted": {
              this.OnRobotStartedEvent(event.session.configuration.runId, event.body as RobotExecutionEvent);
              break;
            }
            case "robotEnded": {
              this.OnRobotEndedEvent(event.session.configuration.runId, event.body as RobotExecutionEvent);
              break;
            }
            case "robotEnqueued": {
              this.TestItemEnqueued(event.session.configuration.runId, event.body?.items);
              break;
            }
            case "robotLog": {
              this.OnRobotLogMessageEvent(event.session.configuration.runId, event.body as RobotLogMessageEvent);
              break;
            }
          }
        }
      }),
      vscode.commands.registerCommand("robotcode.runCurrentFile", async (...args) => {
        await vscode.commands.executeCommand("testing.runCurrentFile", ...args);
      }),
      vscode.commands.registerCommand("robotcode.debugCurrentFile", async (...args) => {
        await vscode.commands.executeCommand("testing.debugCurrentFile", ...args);
      })
    );
  }

  private removeWorkspaceFolderItems(folder: vscode.WorkspaceFolder) {
    if (this.robotTestItems.has(folder)) {
      const robotItems = this.robotTestItems.get(folder)?.items;

      this.robotTestItems.delete(folder);

      for (const id of robotItems?.map((i) => i.id) ?? []) {
        const deleteItem = (itemId: string) => {
          const item = this.testItems.get(itemId);
          this.testItems.delete(itemId);
          item?.children.forEach((v) => deleteItem(v.id));
        };

        deleteItem(id);
      }

      for (const item of robotItems || []) {
        this.testController.items.delete(item.id);
      }
    }
  }

  dispose(): void {
    this._disposables.dispose();
    this.testController.dispose();
  }

  public readonly robotTestItems = new WeakMap<vscode.WorkspaceFolder, WorkspaceFolderEntry | undefined>();

  public findRobotItem(item: vscode.TestItem): RobotTestItem | undefined {
    if (item.parent) {
      return this.findRobotItem(item.parent)?.children?.find((i) => i.id === item.id);
    } else {
      for (const workspace of vscode.workspace.workspaceFolders ?? []) {
        if (this.robotTestItems.has(workspace)) {
          const items = this.robotTestItems.get(workspace)?.items;
          if (items) {
            for (const i of items) {
              if (i.id === item.id) {
                return i;
              }
            }
          }
        }
      }
      return undefined;
    }
  }

  public refreshDocument(document: vscode.TextDocument): void {
    if (document.languageId !== "robotframework") return;

    const uri_str = document.uri.toString();
    if (this.didChangedTimer.has(uri_str)) {
      this.didChangedTimer.get(uri_str)?.cancel();
      this.didChangedTimer.delete(uri_str);
    }

    const token = new vscode.CancellationTokenSource();

    this.didChangedTimer.set(
      uri_str,
      new DidChangeEntry(
        setTimeout((_) => {
          const item = this.findTestItemForDocument(document);
          if (item)
            this.refresh(item).then(
              () => {
                if (item?.canResolveChildren && item.children.size === 0) {
                  this.refreshWorkspace(vscode.workspace.getWorkspaceFolder(document.uri)).then(
                    () => undefined,
                    () => undefined
                  );
                }
              },
              () => undefined
            );
          else {
            this.refreshWorkspace(vscode.workspace.getWorkspaceFolder(document.uri)).then(
              () => undefined,
              () => undefined
            );
          }
        }, 500),
        token
      )
    );
  }

  public findTestItemForDocument(document: vscode.TextDocument): vscode.TestItem | undefined {
    return this.findTestItemByUri(document.uri.toString());
  }

  public findTestItemByUri(documentUri: string): vscode.TestItem | undefined {
    for (const item of this.testItems.values()) {
      if (item.uri?.toString() === documentUri) return item;
    }
    return undefined;
  }

  public findTestItemById(id: string): vscode.TestItem | undefined {
    return this.testItems.get(id);
  }

  public async refresh(item?: vscode.TestItem): Promise<void> {
    await this.refreshMutex.dispatch(async () => {
      await this.refreshItem(item);
    });
  }

  private testItems = new WeakValueMap<string, vscode.TestItem>();

  private async refreshItem(item?: vscode.TestItem, token?: vscode.CancellationToken): Promise<void> {
    if (token?.isCancellationRequested) return;

    if (item) {
      item.busy = true;
      try {
        const robotItem = this.findRobotItem(item);

        let tests = robotItem?.children;

        if (robotItem?.type === "suite" && item.uri !== undefined) {
          if (robotItem.children === undefined) robotItem.children = [];

          const openDoc = vscode.workspace.textDocuments.find((d) => d.uri.toString() === item.uri?.toString());

          if (openDoc !== undefined) {
            tests = await this.languageClientsManager.getTestsFromDocument(openDoc, robotItem.longname, token);

            if (tests !== undefined) {
              for (const test of tests) {
                const index = robotItem.children.findIndex((v) => v.id === test.id);
                if (index >= 0 && robotItem.children) {
                  robotItem.children[index] = test;
                } else {
                  robotItem.children.push(test);
                }
              }

              const removed = robotItem.children.filter((v) => tests?.find((w) => w.id === v.id) === undefined);

              robotItem.children = robotItem.children.filter((v) => removed.find((w) => w.id == v.id) === undefined);
            } else {
              robotItem.children = [];
            }

            robotItem.children = robotItem.children.sort(
              (a, b) => (a.range?.start.line || -1) - (b.range?.start.line || -1)
            );
          }
        }

        if (token?.isCancellationRequested) return;

        if (robotItem) {
          const addedIds = new Set<string>();

          for (const test of tests ?? []) {
            addedIds.add(test.id);
          }

          for (const test of tests ?? []) {
            const newItem = this.addOrUpdateTestItem(item, test);
            await this.refreshItem(newItem, token);
            if (newItem.canResolveChildren && newItem.children.size === 0) {
              addedIds.delete(newItem.id);
            }
          }

          // TODO: we need a sleep after deletion here, it seem's there is a bug in vscode
          if (this.removeNotAddedTestItems(item, addedIds)) await sleep(5);
        }
      } finally {
        item.busy = false;
      }
    } else {
      const addedIds = new Set<string>();

      for (const folder of vscode.workspace.workspaceFolders ?? []) {
        if (token?.isCancellationRequested) return;

        if (this.robotTestItems.get(folder) === undefined || !this.robotTestItems.get(folder)?.valid) {
          this.robotTestItems.set(
            folder,
            new WorkspaceFolderEntry(
              true,
              await this.languageClientsManager.getTestsFromWorkspace(folder, undefined, undefined, token)
            )
          );
        }

        const tests = this.robotTestItems.get(folder)?.items;

        if (tests) {
          for (const test of tests) {
            addedIds.add(test.id);
            const newItem = this.addOrUpdateTestItem(undefined, test);
            await this.refreshItem(newItem, token);
            if (newItem.canResolveChildren && newItem.children.size === 0) {
              addedIds.delete(newItem.id);
            }
          }
        }
      }

      // TODO: we need a sleep after deletion here, it seem's there is a bug in vscode
      if (this.removeNotAddedTestItems(undefined, addedIds)) await sleep(5);
    }
  }

  private addOrUpdateTestItem(parentTestItem: vscode.TestItem | undefined, robotTestItem: RobotTestItem) {
    let testItem = parentTestItem
      ? parentTestItem.children.get(robotTestItem.id)
      : this.testController.items.get(robotTestItem.id);

    if (testItem === undefined) {
      testItem = this.testController.createTestItem(
        robotTestItem.id,
        robotTestItem.label,
        robotTestItem.uri ? vscode.Uri.parse(robotTestItem.uri) : undefined
      );

      this.testItems.set(robotTestItem.id, testItem);

      if (parentTestItem) {
        parentTestItem.children.add(testItem);
      } else {
        this.testController.items.add(testItem);
      }
    }

    testItem.canResolveChildren = robotTestItem.type === "suite" || robotTestItem.type === "workspace";

    if (robotTestItem.range !== undefined) {
      testItem.range = toVsCodeRange(robotTestItem.range);
    }
    testItem.label = robotTestItem.label;
    testItem.error = robotTestItem.error;

    const tags = this.convertTags(robotTestItem.tags);
    if (tags) testItem.tags = tags;
    return testItem;
  }

  private removeNotAddedTestItems(parentTestItem: vscode.TestItem | undefined, addedIds: Set<string>): boolean {
    const itemsToRemove = new Set<string>();

    const items = parentTestItem ? parentTestItem.children : this.testController.items;

    items.forEach((i) => {
      if (!addedIds.has(i.id)) {
        itemsToRemove.add(i.id);
      }
    });
    itemsToRemove.forEach((i) => {
      items.delete(i);
      this.testItems.delete(i);
    });

    return itemsToRemove.size > 0;
  }

  private testTags = new WeakValueMap<string, vscode.TestTag>();

  private convertTags(tags: string[] | undefined): vscode.TestTag[] | undefined {
    if (tags === undefined) return undefined;

    const result: vscode.TestTag[] = [];

    for (const tag of tags) {
      if (!this.testTags.has(tag)) {
        this.testTags.set(tag, new vscode.TestTag(tag));
      }
      const vstag = this.testTags.get(tag);
      if (vstag !== undefined) result.push(vstag);
    }

    return result;
  }

  private readonly refreshFromUriMutex = new Mutex();

  private async refreshWorkspace(workspace?: vscode.WorkspaceFolder, _reason?: string): Promise<void> {
    return this.refreshFromUriMutex.dispatch(async () => {
      if (workspace) {
        const entry = this.robotTestItems.get(workspace);
        if (entry !== undefined) {
          entry.valid = false;
        } else {
          this.removeWorkspaceFolderItems(workspace);
        }
      } else {
        for (const w of vscode.workspace.workspaceFolders ?? []) {
          this.removeWorkspaceFolderItems(w);
        }
      }
      await sleep(5);
      await this.refresh();
    });
  }

  private refreshUri(uri?: vscode.Uri, reason?: string) {
    if (uri) {
      this.outputChannel.appendLine(`refresh uri ${uri.toString()}`);

      const workspace = vscode.workspace.getWorkspaceFolder(uri);
      if (workspace === undefined) return;

      if (this.didChangedTimer.has(uri.toString())) return;

      if (this.fileChangeTimer) {
        this.fileChangeTimer.cancel();
        this.fileChangeTimer = undefined;
      }

      const token = new vscode.CancellationTokenSource();

      this.fileChangeTimer = new DidChangeEntry(
        setTimeout((_) => {
          this.refreshWorkspace(workspace, reason).then(
            () => undefined,
            () => undefined
          );
        }, 500),
        token
      );
    } else {
      if (this.fileChangeTimer) {
        this.fileChangeTimer.cancel();
        this.fileChangeTimer = undefined;
      }

      this.refresh().then(
        (_) => undefined,
        (_) => undefined
      );
    }
  }

  private findWorkspaceForItem(item: vscode.TestItem): vscode.WorkspaceFolder | undefined {
    if (item.uri !== undefined) {
      return vscode.workspace.getWorkspaceFolder(item.uri);
    }

    let parent: vscode.TestItem | undefined = item;
    while (parent?.parent !== undefined) {
      parent = parent.parent;
    }

    if (parent) item = parent;

    for (const ws of vscode.workspace.workspaceFolders ?? []) {
      if (this.robotTestItems.has(ws)) {
        if (this.robotTestItems.get(ws)?.items?.find((w) => w.id === item.id) !== undefined) {
          return ws;
        }
      }
    }
    return undefined;
  }

  private readonly testRuns = new Map<string, vscode.TestRun>();

  private mapTestItemsToWorkspace(items: vscode.TestItem[]): Map<vscode.WorkspaceFolder, vscode.TestItem[]> {
    const folders = new Map<vscode.WorkspaceFolder, vscode.TestItem[]>();
    for (const i of items) {
      const ws = this.findWorkspaceForItem(i);
      if (ws !== undefined) {
        if (!folders.has(ws)) {
          folders.set(ws, []);
        }
        folders.get(ws)?.push(i);
      }
    }
    return folders;
  }

  private static _runIdCounter = 0;

  private static *runIdGenerator(): Iterator<string> {
    while (true) {
      yield (this._runIdCounter++).toString();
    }
  }

  private static readonly runId = TestControllerManager.runIdGenerator();

  public async runTests(
    request: vscode.TestRunRequest,
    token: vscode.CancellationToken,
    dryRun?: boolean
  ): Promise<void> {
    let includedItems: vscode.TestItem[] = [];

    if (request.include) {
      includedItems = Array.from(request.include);
    } else {
      this.testController.items.forEach((test) => {
        const robotTest = this.findRobotItem(test);
        if (robotTest?.type === "error") {
          return;
        } else if (robotTest?.type === "workspace") {
          test.children.forEach((v) => includedItems.push(v));
        } else {
          includedItems.push(test);
        }
      });
    }

    const included = this.mapTestItemsToWorkspace(includedItems);
    const excluded = this.mapTestItemsToWorkspace(request.exclude ? Array.from(request.exclude) : []);

    if (included.size === 0) return;

    const run = this.testController.createTestRun(request);

    token.onCancellationRequested(async (_) => {
      for (const e of this.testRuns.keys()) {
        for (const session of this.debugSessions) {
          if (session.configuration.runId === e) {
            await vscode.debug.stopDebugging(session);
          }
        }
      }
    });

    for (const [workspace, testItems] of included) {
      const runId = TestControllerManager.runId.next().value;
      this.testRuns.set(runId, run);

      let options = {};
      if (request.profile !== undefined && request.profile.kind !== vscode.TestRunProfileKind.Debug) {
        options = {
          noDebug: true,
        };
      }

      let workspaceItem = this.findTestItemByUri(workspace.uri.toString());
      const workspaceRobotItem = workspaceItem ? this.findRobotItem(workspaceItem) : undefined;

      if (workspaceRobotItem?.type == "workspace" && workspaceRobotItem.children?.length) {
        workspaceItem = workspaceItem?.children.get(workspaceRobotItem.children[0].id);
      }

      if (includedItems.length === 1 && includedItems[0] === workspaceItem && excluded.size === 0) {
        await DebugManager.runTests(workspace, [], [], [], runId, options, dryRun);
      } else {
        const includedInWs = testItems
          .map((i) => this.findRobotItem(i)?.longname)
          .filter((i) => i !== undefined) as string[];
        const excludedInWs =
          (excluded
            .get(workspace)
            ?.map((i) => this.findRobotItem(i)?.longname)
            .filter((i) => i !== undefined) as string[]) ?? [];

        const suites = new Set<string>();

        for (const testItem of [...testItems, ...(excluded.get(workspace) || [])]) {
          if (!testItem?.canResolveChildren) {
            if (testItem?.parent) {
              const longname = this.findRobotItem(testItem?.parent)?.longname;
              if (longname) suites.add(longname);
            }
          } else {
            const longname = this.findRobotItem(testItem)?.longname;
            if (longname) suites.add(longname);
          }
        }

        let suiteName: string | undefined = undefined;

        if (workspaceRobotItem?.type == "workspace" && workspaceRobotItem.children?.length) {
          suiteName = workspaceRobotItem.children[0].longname;
        }

        await DebugManager.runTests(
          workspace,
          Array.from(suites),
          includedInWs,
          excludedInWs,
          runId,
          options,
          dryRun,
          suiteName
        );
      }
    }
  }

  private TestRunExited(runId: string | undefined) {
    if (runId === undefined) return;

    const run = this.testRuns.get(runId);
    this.testRuns.delete(runId);
    if (run !== undefined) {
      if (Array.from(this.testRuns.values()).indexOf(run) === -1) {
        run.end();
      }
    }
  }

  private TestItemEnqueued(runId: string | undefined, items: string[] | undefined) {
    if (runId === undefined || items === undefined) return;

    const run = this.testRuns.get(runId);

    if (run !== undefined) {
      for (const id of items) {
        const item = this.findTestItemById(id);
        if (item !== undefined) {
          run.enqueued(item);
        }
      }
    }
  }

  private OnRobotStartedEvent(runId: string | undefined, event: RobotExecutionEvent) {
    switch (event.type) {
      case "suite":
      case "test":
        this.TestItemStarted(runId, event);
        break;
      default:
        // do nothing
        break;
    }
  }

  private TestItemStarted(runId: string | undefined, event: RobotExecutionEvent) {
    if (runId === undefined || event.attributes?.longname === undefined) return;

    const run = this.testRuns.get(runId);

    if (run !== undefined) {
      const item = this.findTestItemById(event.id);
      if (item !== undefined) {
        run.started(item);
      }
    }
  }

  private OnRobotEndedEvent(runId: string | undefined, event: RobotExecutionEvent) {
    switch (event.type) {
      case "suite":
      case "test":
        this.TestItemEnded(runId, event);
        break;
      default:
        // do nothing
        break;
    }
  }

  private TestItemEnded(runId: string | undefined, event: RobotExecutionEvent) {
    if (runId === undefined || event.attributes?.longname === undefined) return;

    const run = this.testRuns.get(runId);

    if (run !== undefined) {
      const item = this.findTestItemById(event.id);
      if (item !== undefined) {
        switch (event.attributes.status) {
          case "PASS":
            run.passed(item, event.attributes.elapsedtime);
            break;
          case "SKIP":
            run.skipped(item);
            break;
          default:
            {
              const messages: vscode.TestMessage[] = [];

              if (event.failedKeywords) {
                for (const keyword of event.failedKeywords) {
                  const message = new vscode.TestMessage(keyword.message ?? "");

                  if (keyword.source) {
                    message.location = new vscode.Location(
                      vscode.Uri.file(keyword.source),
                      new vscode.Range(
                        new vscode.Position((keyword.lineno ?? 1) - 1, 0),
                        new vscode.Position(keyword.lineno ?? 1, 0)
                      )
                    );
                  }

                  messages.push(message);
                }
              }
              if (
                !event.attributes?.message ||
                !event.failedKeywords?.find((v) => v.message === event.attributes?.message)
              ) {
                const message = new vscode.TestMessage(event.attributes.message ?? "");

                if (event.attributes.source) {
                  message.location = new vscode.Location(
                    vscode.Uri.file(event.attributes.source),
                    new vscode.Range(
                      new vscode.Position((event.attributes.lineno ?? 1) - 1, 0),
                      new vscode.Position(event.attributes.lineno ?? 1, 0)
                    )
                  );
                }
                messages.push(message);
              }

              if (event.attributes.status === "FAIL") {
                run.failed(item, messages, event.attributes.elapsedtime);
              } else {
                run.errored(item, messages, event.attributes.elapsedtime);
              }
            }
            break;
        }
      }
    }
  }

  private OnRobotLogMessageEvent(runId: string | undefined, event: RobotLogMessageEvent): void {
    if (runId === undefined) return;

    const run = this.testRuns.get(runId);

    if (run !== undefined) {
      // TODO add location to appendOutput, VSCode testextension is buggy at this time
      // const location =
      //   event.source !== undefined
      //     ? new vscode.Location(
      //         vscode.Uri.file(event.source),
      //         new vscode.Range(
      //           new vscode.Position((event.lineno ?? 1) - 1, event.column ?? 0),
      //           new vscode.Position(event.lineno ?? 1, event.column ?? 0)
      //         )
      //       )
      //     : undefined;

      let style = (s: string) => s;
      switch (event.level) {
        case "WARN":
          style = yellow;
          break;
        case "ERROR":
          style = red;
          break;
      }

      run.appendOutput(
        style(`${event.level}: ${event.message.replaceAll("\n", "\r\n")}` + "\r\n"),
        undefined,
        event.itemId !== undefined ? this.findTestItemById(event.itemId) : undefined
      );
    }
  }
}
