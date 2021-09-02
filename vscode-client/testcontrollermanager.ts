import * as vscode from "vscode";
import { DebugManager } from "./debugmanager";
import { LanguageClientsManager, RobotTestItem } from "./languageclientsmanger";
import { Mutex } from "./utils";

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
      async (request, token) => {
        await this.runTests(request, token);
      }
    );

    this.debugProfile = this.testController.createRunProfile(
      "Debug",
      vscode.TestRunProfileKind.Debug,
      async (request, token) => {
        await this.runTests(request, token);
      }
    );

    this.testController.resolveHandler = async (item) => {
      await this.refresh(item);
    };

    const fileWatcher = vscode.workspace.createFileSystemWatcher("**/*");
    fileWatcher.onDidCreate((uri) => this.refreshFromUri(uri, "create"));
    fileWatcher.onDidDelete((uri) => this.refreshFromUri(uri, "delete"));
    fileWatcher.onDidChange((uri) => this.refreshFromUri(uri, "change"));

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
          this.testItems.delete(r);
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
      vscode.debug.onDidTerminateDebugSession((session) => {
        if (this.debugSessions.has(session)) {
          this.debugSessions.delete(session);
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
              this.TestItemStarted(event.session.configuration.runId, event.body?.longname);
              break;
            }
            case "robotEnded": {
              this.TestItemEnded(event.session.configuration.runId, event.body as RobotExecutionAttributes);
              break;
            }
            case "robotEnqueued": {
              this.TestItemEnqueued(event.session.configuration.runId, event.body?.items);
              break;
            }
          }
        }
      })
    );
  }

  async dispose(): Promise<void> {
    this._disposables.dispose();
    this.testController.dispose();
  }

  public readonly testItems = new WeakMap<vscode.WorkspaceFolder, RobotTestItem[] | undefined>();

  public findRobotItem(item: vscode.TestItem): RobotTestItem | undefined {
    if (item.parent) {
      return this.findRobotItem(item.parent)?.children?.find((i) => i.id === item.id);
    } else {
      for (const workspace of vscode.workspace.workspaceFolders ?? []) {
        if (this.testItems.has(workspace)) {
          const items = this.testItems.get(workspace);
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

  public findTestItemByUri(documentUri: string, items?: vscode.TestItemCollection): vscode.TestItem | undefined {
    let result: vscode.TestItem | undefined;

    if (items === undefined) items = this.testController.items;

    items.forEach((i) => {
      if (result === undefined && i.uri?.toString() === documentUri) {
        result = i;
      }
    });

    if (result !== undefined) return result;

    items.forEach((i) => {
      if (result === undefined) {
        result = this.findTestItemByUri(documentUri, i.children);
      }
    });

    return result;
  }

  public findTestItemById(id: string, items?: vscode.TestItemCollection): vscode.TestItem | undefined {
    let result: vscode.TestItem | undefined;

    if (items === undefined) items = this.testController.items;

    items.forEach((i) => {
      console.log(i.id);
      if (result === undefined && i.id === id) {
        result = i;
      }
    });

    if (result !== undefined) return result;

    items.forEach((i) => {
      if (result === undefined) {
        result = this.findTestItemById(id, i.children);
      }
    });

    return result;
  }

  public async refresh(item?: vscode.TestItem): Promise<void> {
    await this.refreshMutex.dispatch(async () => {
      await this.refreshItem(item);
    });
  }

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

              item.children.add(testItem);
            }

            testItem.canResolveChildren = ri.children !== undefined && ri.children.length > 0;
            if (ri.range !== undefined) {
              testItem.range = new vscode.Range(
                new vscode.Position(ri.range.start.line, ri.range.start.character),
                new vscode.Position(ri.range.start.line, ri.range.start.character)
              );
            }
            testItem.label = ri.label;
            testItem.error = ri.error;

            await this.refreshItem(testItem);
          }
          const itemsToRemove = new Set<string>();

          item.children.forEach((i) => {
            if (!addedIds.has(i.id)) {
              itemsToRemove.add(i.id);
            }
          });

          itemsToRemove.forEach((i) => item.children.delete(i));
        }
      } finally {
        item.busy = false;
      }
    } else {
      const addedIds = new Set<string>();

      for (const workspace of vscode.workspace.workspaceFolders ?? []) {
        if (!this.testItems.has(workspace) && this.testItems.get(workspace) === undefined) {
          this.testItems.set(workspace, await this.languageClientsManager.getTestsFromWorkspace(workspace, []));
        }

        const tests = this.testItems.get(workspace);

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
              testItem.error = ri.error;
              this.testController.items.add(testItem);
            }
            testItem.canResolveChildren = ri.children !== undefined && ri.children.length > 0;
            testItem.label = ri.label;

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
      itemsToRemove.forEach((i) => this.testController.items.delete(i));
    }
  }

  private readonly refreshFromUriMutex = new Mutex();

  private async refreshFromUri(uri: vscode.Uri, _reason?: string): Promise<void> {
    await this.refreshFromUriMutex.dispatch(async () => {
      const workspace = vscode.workspace.getWorkspaceFolder(uri);
      if (workspace !== undefined) {
        this.testItems.delete(workspace);

        await this.refresh();
      }
    });
  }

  private findWorkspaceForItem(item: vscode.TestItem): vscode.WorkspaceFolder | undefined {
    if (item.uri !== undefined) {
      return vscode.workspace.getWorkspaceFolder(item.uri);
    }

    for (const ws of vscode.workspace.workspaceFolders ?? []) {
      if (this.testItems.has(ws)) {
        if (this.testItems.get(ws)?.find((w) => w.id === item.id) !== undefined) {
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
    // TODO const excluded = this.mapTestItemsToWorkspace(request.exclude ?? []);

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

    for (const e of included) {
      const runId = TestControllerManager.runId.next().value;
      this.testRuns.set(runId, run);

      let options = {};
      if (request.profile !== undefined && request.profile.kind !== vscode.TestRunProfileKind.Debug) {
        options = {
          noDebug: true,
        };
      }

      await DebugManager.runTests(
        e[0],
        e[1].map((i) => i.id),
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

  private async TestItemStarted(runId: string | undefined, id: string | undefined) {
    if (runId === undefined || id === undefined) return;

    const run = this.testRuns.get(runId);

    if (run !== undefined) {
      const item = this.findTestItemById(id);
      if (item !== undefined) {
        run.started(item);
      }
    }
  }

  private async TestItemEnded(runId: string | undefined, attributes: RobotExecutionAttributes) {
    if (runId === undefined || attributes === undefined || attributes.longname === undefined) return;

    const run = this.testRuns.get(runId);

    if (run !== undefined) {
      const item = this.findTestItemById(attributes.longname);
      if (item !== undefined) {
        switch (attributes.status) {
          case "PASS":
            run.passed(item, attributes.elapsedtime);
            break;
          case "SKIP":
            run.skipped(item);
            break;
          case "FAIL":
            {
              let message: vscode.TestMessage | undefined;
              if (attributes.message) {
                message = new vscode.TestMessage(attributes.message ?? "unknown error");
                if (attributes.source !== undefined) {
                  message.location = new vscode.Location(
                    vscode.Uri.file(attributes.source),
                    new vscode.Position((attributes.lineno ?? 1) - 1, 0)
                  );
                }
              }
              run.failed(item, message ?? [], attributes.elapsedtime);
            }
            break;
          default:
            {
              const message = new vscode.TestMessage(attributes.message ?? "unknown error");
              if (attributes.source !== undefined) {
                message.location = new vscode.Location(
                  vscode.Uri.file(attributes.source),
                  new vscode.Position((attributes.lineno ?? 1) - 1, 0)
                );
              }
              run.errored(item, message, attributes.elapsedtime);
            }
            break;
        }
      }
    }
  }
}
