import { red, yellow } from "ansi-colors";
import * as vscode from "vscode";
import { DebugManager } from "./debugmanager";
import { LanguageClientsManager, RobotTestItem } from "./languageclientsmanger";
import { Mutex, WeakValueMap } from "./utils";

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

export class TestControllerManager {
  private _disposables: vscode.Disposable;
  public readonly testController: vscode.TestController;
  public readonly runProfile: vscode.TestRunProfile;
  public readonly debugProfile: vscode.TestRunProfile;
  private readonly refreshMutex = new Mutex();
  private readonly debugSessions = new Set<vscode.DebugSession>();

  constructor(
    public readonly extensionContext: vscode.ExtensionContext,
    public readonly languageClientsManager: LanguageClientsManager,
    public readonly debugManager: DebugManager,
    public readonly outputChannel: vscode.OutputChannel
  ) {
    this.testController = vscode.tests.createTestController("robotCode.RobotFramework", "RobotFramework");

    this.runProfile = this.testController.createRunProfile(
      "Run Tests",
      vscode.TestRunProfileKind.Run,
      async (request, token) => await this.runTests(request, token)
    );

    this.debugProfile = this.testController.createRunProfile(
      "Debug",
      vscode.TestRunProfileKind.Debug,
      async (request, token) => await this.runTests(request, token)
    );

    this.testController.resolveHandler = async (item) => await this.refresh(item);

    const fileWatcher = vscode.workspace.createFileSystemWatcher("**/*");
    fileWatcher.onDidCreate(async (uri) => await this.refreshFromUri(uri, "create"));
    fileWatcher.onDidDelete(async (uri) => await this.refreshFromUri(uri, "delete"));
    fileWatcher.onDidChange(async (uri) => await this.refreshFromUri(uri, "change"));

    this._disposables = vscode.Disposable.from(
      fileWatcher,
      vscode.workspace.onDidSaveTextDocument(async (document) => {
        if (document.languageId !== "robotframework") return;

        await this.refresh(this.findTestItemForDocument(document));
      }),
      vscode.workspace.onDidOpenTextDocument(async (document) => {
        if (document.languageId !== "robotframework") return;

        await this.refresh(this.findTestItemForDocument(document));
      }),
      vscode.workspace.onDidChangeTextDocument(async (event) => {
        if (event.document.languageId !== "robotframework") return;

        await this.refresh(this.findTestItemForDocument(event.document));
      }),
      vscode.workspace.onDidChangeWorkspaceFolders(async (event) => {
        for (const r of event.removed) {
          this.removeWorkspaceFolderItems(r, true);
        }

        await this.refresh();
      }),

      vscode.debug.onDidStartDebugSession((session) => {
        if (session.configuration.type === "robotcode" && session.configuration.runId !== undefined) {
          if (this.testRuns.has(session.configuration.runId)) {
            this.debugSessions.add(session);
          }
        }
      }),
      vscode.debug.onDidTerminateDebugSession(async (session) => {
        if (this.debugSessions.has(session)) {
          this.debugSessions.delete(session);

          if (session.configuration.runId !== undefined) {
            await this.TestRunExited(session.configuration.runId);
          }
        }
      }),

      vscode.debug.onDidReceiveDebugSessionCustomEvent(async (event) => {
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
      vscode.commands.registerCommand("robotcode.runCurrentFile", (...args) => {
        vscode.commands.executeCommand("testing.runCurrentFile", ...args);
      }),
      vscode.commands.registerCommand("robotcode.debugCurrentFile", (...args) => {
        vscode.commands.executeCommand("testing.debugCurrentFile", ...args);
      })
    );
  }

  private removeWorkspaceFolderItems(folder: vscode.WorkspaceFolder, deleteTestItems: boolean) {
    if (this.robotTestItems.has(folder)) {
      const robotItems = this.robotTestItems.get(folder);

      this.robotTestItems.delete(folder);

      if (deleteTestItems) {
        for (const id of robotItems?.map((i) => i.id) ?? []) {
          const deleteItem = (itemId: string) => {
            const item = this.testItems.get(itemId);
            this.testItems.delete(itemId);
            item?.children.forEach((v) => deleteItem(v.id));
          };

          deleteItem(id);
        }
      }
    }
  }

  async dispose(): Promise<void> {
    this._disposables.dispose();
    this.testController.dispose();
  }

  public readonly robotTestItems = new WeakMap<vscode.WorkspaceFolder, RobotTestItem[] | undefined>();

  public findRobotItem(item: vscode.TestItem): RobotTestItem | undefined {
    if (item.parent) {
      return this.findRobotItem(item.parent)?.children?.find((i) => i.id === item.id);
    } else {
      for (const workspace of vscode.workspace.workspaceFolders ?? []) {
        if (this.robotTestItems.has(workspace)) {
          const items = this.robotTestItems.get(workspace);
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

  private async refreshItem(item?: vscode.TestItem): Promise<void> {
    if (item) {
      item.busy = true;
      try {
        const robotItem = this.findRobotItem(item);

        let children = robotItem?.children;

        if (robotItem?.type === "suite" && item.uri !== undefined) {
          const openDoc = vscode.workspace.textDocuments.find((d) => d.uri.toString() === item.uri?.toString());

          if (openDoc !== undefined) {
            children = await this.languageClientsManager.getTestsFromDocument(openDoc, robotItem.id);
          }
        }

        if (robotItem) {
          const addedIds = new Set<string>();
          for (const ri of children ?? []) {
            addedIds.add(ri.id);

            let testItem = item.children.get(ri.id);
            if (testItem === undefined) {
              testItem = this.testController.createTestItem(
                ri.id,
                ri.label,
                ri.uri ? vscode.Uri.parse(ri.uri) : undefined
              );
              this.testItems.set(ri.id, testItem);

              item.children.add(testItem);
            }

            testItem.canResolveChildren = ri.children !== undefined && ri.children.length > 0;
            if (ri.range !== undefined) {
              testItem.range = new vscode.Range(
                new vscode.Position(ri.range.start.line, ri.range.start.character),
                new vscode.Position(ri.range.end.line, ri.range.end.character)
              );
            }
            testItem.label = ri.label;
            testItem.error = ri.error;

            const tags = this.convertTags(ri.tags);
            if (tags) testItem.tags = tags;

            await this.refreshItem(testItem);
          }
          const itemsToRemove = new Set<string>();

          item.children.forEach((i) => {
            if (!addedIds.has(i.id)) {
              itemsToRemove.add(i.id);
            }
          });

          itemsToRemove.forEach((i) => {
            item.children.delete(i);
            this.testItems.delete(i);
          });
        }
      } finally {
        item.busy = false;
      }
    } else {
      const addedIds = new Set<string>();

      for (const workspace of vscode.workspace.workspaceFolders ?? []) {
        if (!this.robotTestItems.has(workspace) && this.robotTestItems.get(workspace) === undefined) {
          this.robotTestItems.set(workspace, await this.languageClientsManager.getTestsFromWorkspace(workspace, []));
        }

        const tests = this.robotTestItems.get(workspace);

        if (tests) {
          for (const ri of tests) {
            addedIds.add(ri.id);
            let testItem = this.testController.items.get(ri.id);
            if (testItem === undefined) {
              testItem = this.testController.createTestItem(
                ri.id,
                ri.label,
                ri.uri ? vscode.Uri.parse(ri.uri) : undefined
              );
              this.testItems.set(ri.id, testItem);

              this.testController.items.add(testItem);
            }
            testItem.canResolveChildren = ri.children !== undefined && ri.children.length > 0;
            testItem.label = ri.label;
            testItem.error = ri.error;

            const tags = this.convertTags(ri.tags);
            if (tags) testItem.tags = tags;

            await this.refreshItem(testItem);
          }
        }
      }

      const itemsToRemove = new Set<string>();

      this.testController.items.forEach((i) => {
        if (!addedIds.has(i.id)) {
          itemsToRemove.add(i.id);
        }
      });
      itemsToRemove.forEach((i) => {
        this.testController.items.delete(i);
        this.testItems.delete(i);
      });
    }
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

  private async refreshFromUri(uri: vscode.Uri, _reason?: string): Promise<void> {
    await this.refreshFromUriMutex.dispatch(async () => {
      const workspace = vscode.workspace.getWorkspaceFolder(uri);
      if (workspace !== undefined) {
        this.removeWorkspaceFolderItems(workspace, false);

        await this.refresh();
      }
    });
  }

  private findWorkspaceForItem(item: vscode.TestItem): vscode.WorkspaceFolder | undefined {
    if (item.uri !== undefined) {
      return vscode.workspace.getWorkspaceFolder(item.uri);
    }

    for (const ws of vscode.workspace.workspaceFolders ?? []) {
      if (this.robotTestItems.has(ws)) {
        if (this.robotTestItems.get(ws)?.find((w) => w.id === item.id) !== undefined) {
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

  public async runTests(request: vscode.TestRunRequest, token: vscode.CancellationToken): Promise<void> {
    let includedItems: vscode.TestItem[] = [];

    if (request.include) {
      includedItems = request.include;
    } else {
      this.testController.items.forEach((test) => includedItems.push(test));
    }

    const included = this.mapTestItemsToWorkspace(includedItems);
    const excluded = this.mapTestItemsToWorkspace(request.exclude ?? []);

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

    for (const [workspace, id] of included) {
      const runId = TestControllerManager.runId.next().value;
      this.testRuns.set(runId, run);

      let options = {};
      if (request.profile !== undefined && request.profile.kind !== vscode.TestRunProfileKind.Debug) {
        options = {
          noDebug: true,
        };
      }

      await DebugManager.runTests(
        workspace,
        id.map((i) => i.id),
        excluded.get(workspace)?.map((i) => i.id) ?? [],
        runId,
        options
      );
    }
  }

  private async TestRunExited(runId: string | undefined) {
    if (runId === undefined) return;

    const run = this.testRuns.get(runId);
    this.testRuns.delete(runId);
    if (run !== undefined) {
      if (Array.from(this.testRuns.values()).indexOf(run) === -1) {
        run.end();
      }
    }
  }

  private async TestItemEnqueued(runId: string | undefined, items: string[] | undefined) {
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

  private async OnRobotStartedEvent(runId: string | undefined, event: RobotExecutionEvent) {
    switch (event.type) {
      case "suite":
      case "test":
        await this.TestItemStarted(runId, event);
        break;
      default:
        // do nothing
        break;
    }
  }

  private async TestItemStarted(runId: string | undefined, event: RobotExecutionEvent) {
    if (runId === undefined || event.attributes?.longname === undefined) return;

    const run = this.testRuns.get(runId);

    if (run !== undefined) {
      const item = this.findTestItemById(event.attributes.longname);
      if (item !== undefined) {
        run.started(item);
      }
    }
  }

  private async OnRobotEndedEvent(runId: string | undefined, event: RobotExecutionEvent) {
    switch (event.type) {
      case "suite":
      case "test":
        await this.TestItemEnded(runId, event);
        break;
      default:
        // do nothing
        break;
    }
  }

  private async TestItemEnded(runId: string | undefined, event: RobotExecutionEvent) {
    if (runId === undefined || event.attributes?.longname === undefined) return;

    const run = this.testRuns.get(runId);

    if (run !== undefined) {
      const item = this.findTestItemById(event.attributes.longname);
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

  private async OnRobotLogMessageEvent(runId: string | undefined, event: RobotLogMessageEvent): Promise<void> {
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
