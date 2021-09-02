import * as vscode from "vscode";
import { LanguageClientsManager, RobotTestItem } from "./languageclientsmanger";
import { Mutex } from "./utils";

export class TestControllerManager {
  private _disposables: vscode.Disposable;
  public readonly testController: vscode.TestController;
  public readonly runProfile: vscode.TestRunProfile;
  public readonly debugProfile: vscode.TestRunProfile;
  private readonly refreshMutex = new Mutex();

  constructor(
    public readonly extensionContext: vscode.ExtensionContext,
    public readonly languageClientsManager: LanguageClientsManager,
    public readonly outputChannel: vscode.OutputChannel
  ) {
    this.testController = vscode.tests.createTestController("robotCode.RobotFramework", "RobotFramework");

    this.runProfile = this.testController.createRunProfile(
      "Run Tests",
      vscode.TestRunProfileKind.Run,
      async (request, token) => {
        await this.runHandler(request, token);
      }
    );

    this.debugProfile = this.testController.createRunProfile(
      "Debug",
      vscode.TestRunProfileKind.Debug,
      async (request, token) => {
        await this.runHandler(request, token);
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

        await this.refresh(this.findTestItemFromDocument(document));
      }),
      vscode.workspace.onDidOpenTextDocument(async (document) => {
        if (document.languageId !== "robotframework") return;

        await this.refresh(this.findTestItemFromDocument(document));
      }),
      vscode.workspace.onDidChangeTextDocument(async (event) => {
        if (event.document.languageId !== "robotframework") return;

        await this.refresh(this.findTestItemFromDocument(event.document));
      }),
      vscode.workspace.onDidChangeWorkspaceFolders(async (event) => {
        for (const r of event.removed) {
          this.testItems.delete(r);
        }

        await this.refresh();
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

  public findTestItemFromDocument(document: vscode.TextDocument): vscode.TestItem | undefined {
    return this.findTestItem(document.uri.toString());
  }

  public findTestItem(documentUri: string, items?: vscode.TestItemCollection): vscode.TestItem | undefined {
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
        result = this.findTestItem(documentUri, i.children);
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

  public async runHandler(request: vscode.TestRunRequest, _token: vscode.CancellationToken): Promise<void> {
    let includedItems: vscode.TestItem[] = [];

    if (request.include) {
      includedItems = request.include;
    } else {
      this.testController.items.forEach((test) => includedItems.push(test));
    }

    const included = this.mapTestItemsToWorkspace(includedItems);
    const excluded = this.mapTestItemsToWorkspace(request.exclude ?? []);

    // const run = this.testController.createTestRun(request);
  }
}
