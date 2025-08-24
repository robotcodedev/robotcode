import { red, yellow, blue } from "ansi-colors";
import * as vscode from "vscode";
import { DebugManager } from "./debugmanager";
import * as fs from "fs";

import { ClientState, LanguageClientsManager, toVsCodeRange } from "./languageclientsmanger";
import { escapeRobotGlobPatterns, filterAsync, Mutex, sleep, truncateAndReplaceNewlines, WeakValueMap } from "./utils";
import { CONFIG_SECTION } from "./config";
import { Range, Diagnostic, DiagnosticSeverity } from "vscode-languageclient/node";

function diagnosticsSeverityToVsCode(severity?: DiagnosticSeverity): vscode.DiagnosticSeverity | undefined {
  switch (severity) {
    case DiagnosticSeverity.Error:
      return vscode.DiagnosticSeverity.Error;
    case DiagnosticSeverity.Warning:
      return vscode.DiagnosticSeverity.Warning;
    case DiagnosticSeverity.Information:
      return vscode.DiagnosticSeverity.Information;
    case DiagnosticSeverity.Hint:
      return vscode.DiagnosticSeverity.Hint;
    default:
      return undefined;
  }
}

enum RobotItemType {
  WORKSPACE = "workspace",
  SUITE = "suite",
  TEST = "test",
  TASK = "task",
  ERROR = "error",
}

interface RobotTestItem {
  type: RobotItemType;
  id: string;
  uri?: string;
  relSource?: string;
  source?: string;
  needsParseInclude?: boolean;
  children: RobotTestItem[] | undefined;
  name: string;
  longname: string;
  description?: string;
  range?: Range;
  error?: string;
  tags?: string[];
  rpa?: boolean;
}

interface RobotCodeDiscoverResult {
  items?: RobotTestItem[];
  diagnostics?: { [Key: string]: Diagnostic[] };
}

interface RobotCodeProfileInfo {
  name: string;
  description: string;
  selected: boolean;
}

interface RobotCodeProfilesResult {
  profiles: RobotCodeProfileInfo[];
  messages: string[] | undefined;
}

interface RobotExecutionAttributes {
  id: string | undefined;
  longname: string | undefined;
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

type RobotEventType = "suite" | "test" | "keyword";

interface RobotExecutionEvent {
  type: RobotEventType;
  id: string;
  attributes: RobotExecutionAttributes | undefined;
  failedKeywords: RobotExecutionAttributes[] | undefined;
  source: string | undefined;
  lineno: number | undefined;
}

type RobotLogLevel = "FAIL" | "ERROR" | "WARN" | "INFO" | "DEBUG" | "TRACE";

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
    this.tokenSource.cancel();
    clearTimeout(this.timer);
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

  public constructor(
    valid: boolean,
    readonly items: RobotTestItem[] | undefined,
  ) {
    this._valid = valid;
  }
}

class TestRunInfo {
  public constructor(
    public readonly run: vscode.TestRun,
    public readonly startedEvents: Map<string, RobotExecutionEvent> = new Map(),
  ) {}
}

export class TestControllerManager {
  private _disposables: vscode.Disposable;
  public readonly testController: vscode.TestController;

  private readonly runProfilesMutex = new Mutex();
  public runProfiles: vscode.TestRunProfile[] = [];

  private readonly refreshMutex = new Mutex();
  private readonly updateEditorsMutex = new Mutex();
  private readonly debugSessions = new Set<vscode.DebugSession>();
  private readonly didChangedTimer = new Map<string, DidChangeEntry>();
  private refreshWorkspaceChangeTimer: DidChangeEntry | undefined;
  private diagnosticCollection = vscode.languages.createDiagnosticCollection("robotCode discovery");
  private activeStepDecorationType: vscode.TextEditorDecorationType;
  showEditorRunDecorations = false;

  constructor(
    public readonly extensionContext: vscode.ExtensionContext,
    public readonly languageClientsManager: LanguageClientsManager,
    public readonly debugManager: DebugManager,
    public readonly outputChannel: vscode.OutputChannel,
  ) {
    this.testController = vscode.tests.createTestController("robotCode.RobotFramework", "Robot Framework Tests/Tasks");

    this.testController.resolveHandler = async (item) => {
      await this.refresh(item);
    };

    this.testController.refreshHandler = async (token) => {
      await this.refreshWorkspace(undefined, undefined, token);
    };

    this.updateRunProfiles().then(
      (_) => undefined,
      (_) => undefined,
    );

    const fileWatcher = vscode.workspace.createFileSystemWatcher(
      `**/*.{${this.languageClientsManager.fileExtensions.join(",")}}`,
    );

    fileWatcher.onDidCreate(async (uri) => {
      await this.refreshUri(uri, "create");
    });
    fileWatcher.onDidDelete(async (uri) => {
      await this.refreshUri(uri, "delete");
    });
    fileWatcher.onDidChange(async (uri) => {
      await this.refreshUri(uri, "change");
    });

    this.activeStepDecorationType = vscode.window.createTextEditorDecorationType({
      isWholeLine: true,
      backgroundColor: { id: "editor.rangeHighlightBackground" },
      borderColor: { id: "editor.rangeHighlightBorder" },
      after: {
        color: { id: "editorCodeLens.foreground" },
        contentText: " \u231B",
      },
    });

    this._disposables = vscode.Disposable.from(
      this.diagnosticCollection,
      fileWatcher,
      this.activeStepDecorationType,
      this.languageClientsManager.onClientStateChanged(async (event) => {
        switch (event.state) {
          case ClientState.Running: {
            await this.refresh();
            break;
          }
          case ClientState.Stopped: {
            const folder = vscode.workspace.getWorkspaceFolder(event.uri);
            if (folder) this.removeWorkspaceFolderItems(folder);

            break;
          }
        }
        await this.updateRunProfiles();
      }),
      vscode.workspace.onDidChangeConfiguration(async (event) => {
        let refresh = false;

        for (const ws of vscode.workspace.workspaceFolders ?? []) {
          if (event.affectsConfiguration("robotcode.testExplorer", ws)) {
            refresh = true;
          }
        }

        if (refresh) {
          await this.refreshWorkspace();
          await this.updateRunProfiles();
        }
      }),
      vscode.workspace.onDidCloseTextDocument((document) => this.refreshDocument(document)),
      vscode.workspace.onDidSaveTextDocument((document) => this.refreshDocument(document)),
      vscode.workspace.onDidOpenTextDocument((document) => this.refreshDocument(document)),

      vscode.workspace.onDidChangeTextDocument((event) => {
        this.refreshDocument(event.document);
      }),
      vscode.workspace.onDidChangeWorkspaceFolders(async (event) => {
        await this.updateRunProfiles();

        for (const r of event.removed) {
          this.removeWorkspaceFolderItems(r);
        }
        if (event.added.length > 0) await this.refresh();
      }),

      vscode.debug.onDidStartDebugSession((session) => {
        if (session.configuration.type === "robotcode" && session.configuration.runId !== undefined) {
          if (this.testRunInfos.has(session.configuration.runId)) {
            this.debugSessions.add(session);
          }
        }
      }),
      vscode.debug.onDidTerminateDebugSession((session) => {
        if (this.debugSessions.has(session)) {
          this.debugSessions.delete(session);

          if (session.configuration.runId !== undefined) {
            this.testRunExited(session.configuration.runId);
          }
        }
      }),
      vscode.debug.onDidReceiveDebugSessionCustomEvent(async (event) => {
        if (event.session.configuration.type === "robotcode") {
          switch (event.event) {
            case "robotExited": {
              this.testRunExited(event.session.configuration.runId);
              break;
            }
            case "robotStarted": {
              await this.onRobotStartedEvent(event.session.configuration.runId, event.body as RobotExecutionEvent);
              break;
            }
            case "robotEnded": {
              await this.onRobotEndedEvent(event.session.configuration.runId, event.body as RobotExecutionEvent);
              break;
            }
            case "robotSetFailed": {
              this.onRobotSetFailed(event.session.configuration.runId, event.body as RobotExecutionEvent);
              break;
            }
            case "robotEnqueued": {
              this.testItemEnqueued(event.session.configuration.runId, event.body?.items);
              break;
            }
            case "robotLog": {
              this.onRobotLogMessageEvent(event.session.configuration.runId, event.body as RobotLogMessageEvent, false);
              break;
            }
            case "robotMessage": {
              this.onRobotLogMessageEvent(event.session.configuration.runId, event.body as RobotLogMessageEvent, true);
              break;
            }
          }
          if (event.body?.synced) {
            await event.session.customRequest("robot/sync");
          }
        }
      }),
      vscode.commands.registerCommand("robotcode.runCurrentFile", async (...args) => {
        await vscode.commands.executeCommand("testing.runCurrentFile", ...args);
      }),
      vscode.commands.registerCommand("robotcode.debugCurrentFile", async (...args) => {
        await vscode.commands.executeCommand("testing.debugCurrentFile", ...args);
      }),
      vscode.commands.registerCommand(
        "robotcode.selectConfigurationProfiles",
        async (folder?: vscode.WorkspaceFolder) => {
          await this.selectConfigurationProfiles(folder);
        },
      ),
      vscode.workspace.onDidChangeConfiguration(async (event) => {
        for (const s of ["launch.configurations"]) {
          if (event.affectsConfiguration(s)) {
            await this.updateRunProfiles();
          }
        }
      }),
    );
  }

  private getFolderTag(folder: vscode.WorkspaceFolder | undefined): vscode.TestTag | undefined {
    if (folder === undefined) return undefined;
    return this.createTag(`_robotFolder:${folder.uri.toString()}`);
  }

  private async updateRunProfiles(): Promise<void> {
    await this.runProfilesMutex.dispatch(async () => {
      for (const a of this.runProfiles) {
        a.dispose();
      }
      this.runProfiles = [];

      const multiFolders = (vscode.workspace.workspaceFolders?.length ?? 0) > 1;

      for (const folder of vscode.workspace.workspaceFolders ?? []) {
        if (!this.isTestExplorerEnabledForWorkspace(folder)) continue;

        const folderTag = this.getFolderTag(folder);

        const folderName = multiFolders ? ` [${folder.name}]` : "";

        const runProfile = this.testController.createRunProfile(
          "Run" + folderName,
          vscode.TestRunProfileKind.Run,
          async (request, token) => this.runTests(request, token, undefined),
          false,
          folderTag,
        );

        runProfile.configureHandler = () => {
          this.selectConfigurationProfiles(folder).then(
            (_) => undefined,
            (_) => undefined,
          );
        };

        this.runProfiles.push(runProfile);

        const debugProfile = this.testController.createRunProfile(
          "Debug" + folderName,
          vscode.TestRunProfileKind.Debug,
          async (request, token) => this.runTests(request, token, undefined),
          false,
          folderTag,
        );

        debugProfile.configureHandler = () => {
          this.selectConfigurationProfiles(folder).then(
            (_) => undefined,
            (_) => undefined,
          );
        };

        this.runProfiles.push(debugProfile);

        const configurations = vscode.workspace
          .getConfiguration("launch", folder)
          ?.get<{ [Key: string]: unknown }[]>("configurations");

        configurations?.forEach((config, index) => {
          if (config.type === "robotcode" && config.purpose == "test-profile") {
            const name =
              (config.name ? truncateAndReplaceNewlines((config.name as string).trim()) : `Profile ${index}`) +
              folderName;

            const runProfile = this.testController.createRunProfile(
              "Run " + name,
              vscode.TestRunProfileKind.Run,
              async (request, token) => this.runTests(request, token, undefined, config),
              false,
              folderTag,
            );

            this.runProfiles.push(runProfile);

            const debugProfile = this.testController.createRunProfile(
              "Debug " + name,
              vscode.TestRunProfileKind.Debug,
              async (request, token) => this.runTests(request, token, undefined, config),
              false,
              folderTag,
            );

            this.runProfiles.push(debugProfile);
          }
        });

        const profiles = await this.getRobotCodeProfiles(folder);

        profiles.profiles.forEach((profile, index) => {
          const name =
            (truncateAndReplaceNewlines(profile.name.trim()) || `Profile ${index}`) +
            (profile.description ? ` - ${truncateAndReplaceNewlines(profile.description.trim())} ` : "") +
            folderName;

          const runProfile = this.testController.createRunProfile(
            "Run " + name,
            vscode.TestRunProfileKind.Run,
            async (request, token) => this.runTests(request, token, [profile.name]),
            false,
            folderTag,
          );

          this.runProfiles.push(runProfile);

          const debugProfile = this.testController.createRunProfile(
            "Debug " + name,
            vscode.TestRunProfileKind.Debug,
            async (request, token) => this.runTests(request, token, [profile.name]),
            false,
            folderTag,
          );

          this.runProfiles.push(debugProfile);
        });
      }
    });
  }

  public async getRobotCodeProfiles(
    folder: vscode.WorkspaceFolder,
    profiles?: string[],
  ): Promise<RobotCodeProfilesResult> {
    if (!(await this.languageClientsManager.isValidRobotEnvironmentInFolder(folder))) {
      return {
        profiles: [],
        messages: [],
      } as RobotCodeProfilesResult;
    }
    const config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);
    const paths = config.get<string[] | undefined>("robot.paths", undefined);

    return (await this.languageClientsManager.pythonManager.executeRobotCode(
      folder,
      [...(paths?.length ? paths.flatMap((v) => ["-dp", v]) : ["-dp", "."]), "profiles", "list"],
      profiles,
      "json",
      true,
      true,
    )) as RobotCodeProfilesResult;
  }

  public async selectConfigurationProfiles(folder?: vscode.WorkspaceFolder): Promise<void> {
    if (!folder) {
      if (vscode.workspace.workspaceFolders === undefined || vscode.workspace.workspaceFolders?.length === 0) return;

      const folders = await filterAsync(
        vscode.workspace.workspaceFolders,
        async (v) =>
          (
            await vscode.workspace.findFiles(
              new vscode.RelativePattern(v, `**/*.{${this.languageClientsManager.fileExtensions.join(",")}}}`),
              null,
              1,
            )
          ).length > 0,
      );

      if (folders.length === 0) {
        await vscode.window.showWarningMessage("No workspaces with Robot Framework files found.");
        return;
      }

      folder =
        folders.length > 1
          ? (
              await vscode.window.showQuickPick(
                folders.map((v) => {
                  return {
                    label: v.name,
                    description: v.uri.fsPath.toString(),
                    value: v,
                  };
                }),
                { title: "Select Workspace Folder" },
              )
            )?.value
          : folders[0];

      if (!folder) return;
    }
    try {
      const config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);
      const result = await this.getRobotCodeProfiles(folder, config.get("profiles", undefined));

      if (result.profiles.length === 0 && result.messages) {
        await vscode.window.showWarningMessage(result.messages.join("\n"));
        return;
      }

      const options = result.profiles.map((p) => {
        return {
          label: truncateAndReplaceNewlines(p.name.trim()),
          description: truncateAndReplaceNewlines(p.description.trim()),
          picked: p.selected,
        };
      });

      const profiles = await vscode.window.showQuickPick([...options], {
        title: `Select Configuration Profiles for folder "${folder.name}"`,
        canPickMany: true,
      });
      if (profiles === undefined) return;

      await config.update(
        "profiles",
        profiles.map((p) => p.label),
        vscode.ConfigurationTarget.WorkspaceFolder,
      );
    } catch (e) {
      await vscode.window.showErrorMessage("Error while getting profiles, is this a robot project?", {
        modal: true,
        detail: (e as Error).toString(),
      });
    }
  }

  private removeWorkspaceFolderItems(folder: vscode.WorkspaceFolder) {
    this.diagnosticCollection.forEach((uri, _diagnostics, collection) => {
      if (vscode.workspace.getWorkspaceFolder(uri) === folder) {
        collection.delete(uri);
      }
    });

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
    this.didChangedTimer.forEach((entry) => entry.cancel());
    this.didChangedTimer.clear();

    if (this.refreshWorkspaceChangeTimer) {
      this.refreshWorkspaceChangeTimer.cancel();
      this.refreshWorkspaceChangeTimer = undefined;
    }

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
    if (!this.languageClientsManager.supportedLanguages.includes(document.languageId)) return;
    if (!this.languageClientsManager.fileExtensions.some((ext) => document.uri.path.toLowerCase().endsWith(`.${ext}`)))
      return;
    if (document.uri.path.toLowerCase().endsWith("__init__.robot")) return;

    const uri_str = document.uri.toString();
    if (this.didChangedTimer.has(uri_str)) {
      this.didChangedTimer.get(uri_str)?.cancel();
      this.didChangedTimer.delete(uri_str);
    }

    const cancelationTokenSource = new vscode.CancellationTokenSource();

    this.didChangedTimer.set(
      uri_str,
      new DidChangeEntry(
        setTimeout(() => {
          const item = this.findTestItemForDocument(document);
          if (item)
            this.refresh(item).then(
              () => {
                if (item?.canResolveChildren && item.children.size === 0) {
                  this.refreshWorkspace(
                    vscode.workspace.getWorkspaceFolder(document.uri),
                    undefined,
                    cancelationTokenSource.token,
                  ).then(
                    () => undefined,
                    () => undefined,
                  );
                }
              },
              () => undefined,
            );
          else {
            this.refreshWorkspace(
              vscode.workspace.getWorkspaceFolder(document.uri),
              undefined,
              cancelationTokenSource.token,
            ).then(
              () => undefined,
              () => undefined,
            );
          }
        }, 1000),
        cancelationTokenSource,
      ),
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

  public async refresh(item?: vscode.TestItem, token?: vscode.CancellationToken): Promise<void> {
    await this.refreshMutex.dispatch(async () => {
      await this.refreshItem(item, token);
    });
  }

  private testItems = new WeakValueMap<string, vscode.TestItem>();

  private async discoverTests(
    folder: vscode.WorkspaceFolder,
    discoverArgs: string[],
    extraArgs: string[],
    stdioData?: string,
    prune?: boolean,
    token?: vscode.CancellationToken,
  ): Promise<RobotCodeDiscoverResult> {
    if (!(await this.languageClientsManager.isValidRobotEnvironmentInFolder(folder))) {
      return {};
    }

    const config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);
    const profiles = config.get<string[]>("profiles", []);
    const pythonPath = config.get<string[]>("robot.pythonPath", []);
    const paths = config.get<string[] | undefined>("robot.paths", undefined);
    const languages = config.get<string[]>("robot.languages", []);
    const robotArgs = config.get<string[]>("robot.args", []);

    const mode = config.get<string>("robot.mode", "default");
    const mode_args: string[] = [];
    switch (mode) {
      case "default":
        break;
      case "norpa":
        mode_args.push("--norpa");
        break;
      case "rpa":
        mode_args.push("--rpa");
        break;
    }
    const result = (await this.languageClientsManager.pythonManager.executeRobotCode(
      folder,
      [
        ...(paths?.length ? paths.flatMap((v) => ["-dp", v]) : ["-dp", "."]),
        ...discoverArgs,
        ...mode_args,
        ...pythonPath.flatMap((v) => ["-P", v]),
        ...languages.flatMap((v) => ["--language", v]),
        ...robotArgs,
        ...extraArgs,
      ],
      profiles,
      "json",
      true,
      true,
      stdioData,
      token,
    )) as RobotCodeDiscoverResult;

    const added_uris = new Set<string>();

    if (result?.diagnostics) {
      for (const key of Object.keys(result?.diagnostics ?? {})) {
        const diagnostics = result.diagnostics[key];

        const uri = vscode.Uri.parse(key);
        added_uris.add(uri.toString());

        this.diagnosticCollection.set(
          uri,
          diagnostics.map((v) => {
            const r = new vscode.Diagnostic(toVsCodeRange(v.range), v.message, diagnosticsSeverityToVsCode(v.severity));
            r.source = v.source;
            r.code = v.code;
            return r;
          }),
        );
      }
    }

    if (prune) {
      this.diagnosticCollection.forEach((uri, _diagnostics, collection) => {
        if (vscode.workspace.getWorkspaceFolder(uri) === folder) {
          if (!added_uris.has(uri.toString())) collection.delete(uri);
        }
      });
    }

    return result;
  }

  private readonly lastDiscoverResults = new WeakMap<vscode.WorkspaceFolder, RobotCodeDiscoverResult>();

  public async getTestsFromWorkspaceFolder(
    folder: vscode.WorkspaceFolder,
    token?: vscode.CancellationToken,
  ): Promise<RobotTestItem[] | undefined> {
    const robotFiles = await vscode.workspace.findFiles(
      new vscode.RelativePattern(folder, `**/*.{${this.languageClientsManager.fileExtensions.join(",")}}`),
      undefined,
      1,
      token,
    );

    if (robotFiles.length === 0) {
      return undefined;
    }

    try {
      const o: { [key: string]: string } = {};

      for (const document of vscode.workspace.textDocuments) {
        if (
          this.languageClientsManager.supportedLanguages.includes(document.languageId) &&
          vscode.workspace.getWorkspaceFolder(document.uri) === folder
        ) {
          o[document.uri.toString()] = document.getText();
        }
      }

      const result = await this.discoverTests(
        folder,
        ["discover", "--read-from-stdin", "all"],
        [],
        JSON.stringify(o),
        true,
        token,
      );

      this.lastDiscoverResults.set(folder, result);

      return result?.items;
    } catch (e) {
      if (e instanceof Error) {
        if (e.name === "AbortError") {
          if (this.lastDiscoverResults.has(folder)) {
            return this.lastDiscoverResults.get(folder)?.items;
          }
        }
      }

      return [
        {
          name: folder.name,
          type: RobotItemType.WORKSPACE,
          id: folder.uri.fsPath,
          uri: folder.uri.toString(),
          longname: folder.name,
          error: e?.toString() || "Unknown Error",
          children: [],
        },
      ];
    }
  }

  public async getTestsFromDocument(
    document: vscode.TextDocument,
    testItem: RobotTestItem,
    token?: vscode.CancellationToken,
  ): Promise<RobotTestItem[] | undefined> {
    const folder = vscode.workspace.getWorkspaceFolder(document.uri);

    if (!folder) return undefined;

    const workspaceItem = this.findTestItemByUri(folder.uri.toString());
    const robotWorkspaceItem = workspaceItem ? this.findRobotItem(workspaceItem) : undefined;

    try {
      const o: { [key: string]: string } = {};
      for (const document of vscode.workspace.textDocuments) {
        if (
          this.languageClientsManager.supportedLanguages.includes(document.languageId) &&
          vscode.workspace.getWorkspaceFolder(document.uri) === folder
        ) {
          o[document.uri.toString()] = document.getText();
        }
      }

      if (this.diagnosticCollection.has(document.uri)) {
        this.diagnosticCollection.delete(document.uri);
      }

      const result = await this.discoverTests(
        folder,
        ["discover", "--read-from-stdin", "tests"],
        [
          ...(robotWorkspaceItem?.needsParseInclude && testItem.relSource
            ? ["-I", escapeRobotGlobPatterns(testItem.relSource)]
            : []),
          "--suite",
          escapeRobotGlobPatterns(testItem.longname),
        ],
        JSON.stringify(o),
        false,
        token,
      );

      return result?.items;
    } catch (e) {
      if (e instanceof Error) {
        if (e.name === "AbortError") return undefined;
      }
      this.outputChannel.appendLine(`Error while getting tests from document: ${e?.toString() || "Unknown Error"}`);

      return undefined;
    }
  }

  // eslint-disable-next-line class-methods-use-this
  private isTestExplorerEnabledForWorkspace(workspace: vscode.WorkspaceFolder): boolean {
    const result = vscode.workspace.getConfiguration(CONFIG_SECTION, workspace).get<boolean>("testExplorer.enabled");
    return result === undefined || result;
  }

  private async refreshItem(item?: vscode.TestItem, token?: vscode.CancellationToken): Promise<void> {
    if (token?.isCancellationRequested) return;

    if (item) {
      item.busy = true;
      try {
        const robotItem = this.findRobotItem(item);

        let tests = robotItem?.children;

        if (robotItem?.type === RobotItemType.SUITE && item.uri !== undefined) {
          if (robotItem.children === undefined) robotItem.children = [];

          const openDoc = vscode.workspace.textDocuments.find((d) => d.uri.toString() === item.uri?.toString());

          if (openDoc !== undefined) {
            tests = await this.getTestsFromDocument(openDoc, robotItem, token);
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
              (a, b) => (a.range?.start.line || -1) - (b.range?.start.line || -1),
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

        if (!this.isTestExplorerEnabledForWorkspace(folder)) continue;

        if (this.robotTestItems.get(folder) === undefined || !this.robotTestItems.get(folder)?.valid) {
          const items = await this.getTestsFromWorkspaceFolder(folder, token);
          if (items === undefined) continue;
          this.robotTestItems.set(folder, new WorkspaceFolderEntry(true, items));
        }

        const tests = this.robotTestItems.get(folder)?.items;

        if (tests) {
          for (const test of tests) {
            addedIds.add(test.id);
            const newItem = this.addOrUpdateTestItem(undefined, test);
            await this.refreshItem(newItem, token);
            if (newItem.canResolveChildren && newItem.children.size === 0 && newItem.error === undefined) {
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
        robotTestItem.name,
        robotTestItem.uri ? vscode.Uri.parse(robotTestItem.uri) : undefined,
      );

      this.testItems.set(robotTestItem.id, testItem);

      if (parentTestItem) {
        parentTestItem.children.add(testItem);
      } else {
        this.testController.items.add(testItem);
      }
    }

    testItem.canResolveChildren =
      robotTestItem.type === RobotItemType.SUITE || robotTestItem.type === RobotItemType.WORKSPACE;

    if (robotTestItem.range !== undefined) {
      testItem.range = toVsCodeRange(robotTestItem.range);
    }

    testItem.label = robotTestItem.name;
    if (
      robotTestItem.type == RobotItemType.TEST ||
      robotTestItem.type == RobotItemType.TASK ||
      robotTestItem.type == RobotItemType.SUITE
    ) {
      testItem.description = `${robotTestItem.type} ${robotTestItem.description ? ` - ${robotTestItem.description}` : ""}`;
    } else {
      testItem.description = robotTestItem.description;
    }

    if (robotTestItem.error !== undefined) {
      testItem.error = robotTestItem.error;
    }

    const tags = this.convertTags(robotTestItem.tags) ?? [];

    const folderTag = this.getFolderTag(this.findWorkspaceFolderForItem(testItem));
    if (folderTag !== undefined) tags?.push(folderTag);
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
      const item = this.testItems.get(i);
      if (item !== undefined && item.canResolveChildren) {
        this.removeNotAddedTestItems(item, new Set<string>());
      }
      items.delete(i);
      this.testItems.delete(i);
    });

    return itemsToRemove.size > 0;
  }

  private testTags = new WeakValueMap<string, vscode.TestTag>();

  private createTag(tag: string): vscode.TestTag | undefined {
    if (!this.testTags.has(tag)) {
      this.testTags.set(tag, new vscode.TestTag(tag));
    }
    const vstag = this.testTags.get(tag);

    return vstag;
  }

  private convertTags(tags: string[] | undefined): vscode.TestTag[] | undefined {
    if (tags === undefined) return undefined;

    const result: vscode.TestTag[] = [];

    for (const tag of tags) {
      const vstag = this.createTag(tag);
      if (vstag !== undefined) result.push(vstag);
    }

    return result;
  }

  private readonly refreshFromUriMutex = new Mutex();

  private async refreshWorkspace(
    workspace?: vscode.WorkspaceFolder,
    _reason?: string,
    token?: vscode.CancellationToken,
  ): Promise<void> {
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
      await this.refresh(undefined, token);
    });
  }

  private async refreshUri(uri?: vscode.Uri, reason?: string) {
    if (uri) {
      if (uri?.scheme !== "file") return;

      const exists = fs.existsSync(uri.fsPath);
      const isFileAndExists = exists && fs.statSync(uri.fsPath).isFile();

      if (
        isFileAndExists &&
        !this.languageClientsManager.fileExtensions.some((ext) => uri?.path.toLowerCase().endsWith(`.${ext}`))
      )
        return;

      if (isFileAndExists && vscode.workspace.textDocuments.find((d) => d.uri.toString() === uri?.toString())) return;

      if (exists) {
        const testItem = this.findTestItemByUri(uri.toString());
        if (testItem) {
          await this.refresh(testItem);
          return;
        }
      }

      const workspace = vscode.workspace.getWorkspaceFolder(uri);
      if (workspace === undefined) return;

      if (this.didChangedTimer.has(uri.toString())) return;

      if (this.refreshWorkspaceChangeTimer) {
        this.refreshWorkspaceChangeTimer.cancel();
        this.refreshWorkspaceChangeTimer = undefined;
      }

      const cancelationTokenSource = new vscode.CancellationTokenSource();

      this.refreshWorkspaceChangeTimer = new DidChangeEntry(
        setTimeout(() => {
          this.refreshWorkspace(workspace, reason, cancelationTokenSource.token).then(
            () => undefined,
            () => undefined,
          );
        }, 1000),
        cancelationTokenSource,
      );
    } else {
      if (this.refreshWorkspaceChangeTimer) {
        this.refreshWorkspaceChangeTimer.cancel();
        this.refreshWorkspaceChangeTimer = undefined;
      }

      this.refresh().then(
        (_) => undefined,
        (_) => undefined,
      );
    }
  }

  private findWorkspaceFolderForItem(item: vscode.TestItem): vscode.WorkspaceFolder | undefined {
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

  private readonly testRunInfos = new Map<string, TestRunInfo>();

  private mapTestItemsToWorkspaceFolder(items: vscode.TestItem[]): Map<vscode.WorkspaceFolder, vscode.TestItem[]> {
    const folders = new Map<vscode.WorkspaceFolder, vscode.TestItem[]>();
    for (const i of items) {
      const ws = this.findWorkspaceFolderForItem(i);
      if (ws !== undefined) {
        if (!folders.has(ws)) {
          folders.set(ws, []);
        }
        const ritem = this.findRobotItem(i);
        if (ritem?.type == RobotItemType.WORKSPACE) {
          i.children.forEach((c) => {
            folders.get(ws)?.push(c);
          });
        } else {
          folders.get(ws)?.push(i);
        }
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
    profiles?: string[],
    testConfiguration?: { [Key: string]: unknown },
  ): Promise<void> {
    const includedItems: vscode.TestItem[] = [];

    if (request.include) {
      request.include.forEach((v) => {
        const robotTest = this.findRobotItem(v);
        if (robotTest?.type === RobotItemType.WORKSPACE) {
          v.children.forEach((v) => includedItems.push(v));
        } else {
          includedItems.push(v);
        }
      });
    } else {
      this.testController.items.forEach((test) => {
        const robotTest = this.findRobotItem(test);
        if (robotTest?.type === RobotItemType.ERROR) {
          return;
        } else if (robotTest?.type === RobotItemType.WORKSPACE) {
          test.children.forEach((v) => includedItems.push(v));
        } else {
          includedItems.push(test);
        }
      });
    }

    const included = this.mapTestItemsToWorkspaceFolder(includedItems);
    const excluded = this.mapTestItemsToWorkspaceFolder(request.exclude ? Array.from(request.exclude) : []);

    if (included.size === 0) return;

    const testRun = this.testController.createTestRun(request, undefined);
    let run_started = false;

    token.onCancellationRequested(async (_) => {
      for (const e of this.testRunInfos.keys()) {
        for (const session of this.debugSessions) {
          if (session.configuration.runId === e) {
            await vscode.debug.stopDebugging(session);
          }
        }
      }
    });

    for (const [folder, testItems] of included) {
      if (
        request.profile !== undefined &&
        request.profile.tag !== undefined &&
        request.profile.tag !== this.getFolderTag(folder)
      )
        continue;

      const runId = TestControllerManager.runId.next().value;
      this.testRunInfos.set(runId, new TestRunInfo(testRun));

      const options: vscode.DebugSessionOptions = {
        testRun: testRun,
      };
      if (request.profile !== undefined && request.profile.kind !== vscode.TestRunProfileKind.Debug) {
        options.noDebug = true;
      }

      let workspaceItem = this.findTestItemByUri(folder.uri.toString());
      const workspaceRobotItem = workspaceItem ? this.findRobotItem(workspaceItem) : undefined;

      if (workspaceRobotItem?.type == RobotItemType.WORKSPACE && workspaceRobotItem.children?.length) {
        workspaceItem = workspaceItem?.children.get(workspaceRobotItem.children[0].id);
      }

      if (testItems.length === 1 && testItems[0] === workspaceItem && excluded.size === 0) {
        const started = await DebugManager.runTests(
          folder,
          [],
          [],
          workspaceRobotItem?.needsParseInclude ?? false,
          [],
          [],
          runId,
          options,
          undefined,
          profiles,
          testConfiguration,
        );
        run_started = run_started || started;
      } else {
        const includedInWs = testItems
          .map((i) => {
            const ritem = this.findRobotItem(i);
            if (ritem?.type == RobotItemType.WORKSPACE && ritem.children?.length) {
              return ritem.children[0].longname;
            }
            return ritem?.longname;
          })
          .filter((i) => i !== undefined) as string[];
        const excludedInWs =
          (excluded
            .get(folder)
            ?.map((i) => {
              const ritem = this.findRobotItem(i);
              if (ritem?.type == RobotItemType.WORKSPACE && ritem.children?.length) {
                return ritem.children[0].longname;
              }
              return ritem?.longname;
            })
            .filter((i) => i !== undefined) as string[]) ?? [];

        const suites = new Set<string>();
        const rel_sources = new Set<string>();

        for (const testItem of [...testItems, ...(excluded.get(folder) || [])]) {
          if (!testItem?.canResolveChildren) {
            if (testItem?.parent) {
              const ritem = this.findRobotItem(testItem?.parent);
              const longname = ritem?.longname;

              if (longname) {
                suites.add(longname);
                if (ritem?.relSource) rel_sources.add(ritem?.relSource);
              }
            }
          } else {
            const ritem = this.findRobotItem(testItem);
            let longname = ritem?.longname;
            if (ritem?.type == RobotItemType.WORKSPACE && ritem.children?.length) {
              longname = ritem.children[0].longname;
            }
            if (longname) {
              suites.add(longname);
              if (ritem?.relSource) rel_sources.add(ritem?.relSource);
            }
          }
        }

        let suiteName: string | undefined = undefined;

        if (workspaceRobotItem?.type == RobotItemType.WORKSPACE && workspaceRobotItem.children?.length) {
          suiteName = workspaceRobotItem.children[0].longname;
        }

        const started = await DebugManager.runTests(
          folder,
          Array.from(suites),
          Array.from(rel_sources),
          workspaceRobotItem?.needsParseInclude ?? false,
          includedInWs,
          excludedInWs,
          runId,
          options,
          suiteName,
          profiles,
          testConfiguration,
        );

        run_started = run_started || started;
      }
    }

    if (!run_started) {
      testRun.end();
    }
  }

  private testRunExited(runId: string | undefined) {
    if (runId === undefined) return;

    const run = this.testRunInfos.get(runId)?.run;
    this.testRunInfos.delete(runId);
    if (run !== undefined) {
      if (Array.from(this.testRunInfos.values()).findIndex((info) => info.run === run) === -1) {
        run.end();
      }
    }
  }

  private testItemEnqueued(runId: string | undefined, items: string[] | undefined) {
    if (runId === undefined || items === undefined) return;

    const run = this.testRunInfos.get(runId)?.run;

    if (run !== undefined) {
      for (const id of items) {
        const item = this.findTestItemById(id);
        if (item !== undefined && item.canResolveChildren === false) {
          run.enqueued(item);
        }
      }
    }
  }

  private async updateEditorDecorations(event: RobotExecutionEvent | undefined = undefined) {
    if (!this.showEditorRunDecorations) return;

    await this.updateEditorsMutex.dispatch(() => {
      // Early exit if no test runs
      if (this.testRunInfos.size === 0) return;

      // Filter editors based on event
      const editors =
        event !== undefined
          ? vscode.window.visibleTextEditors.filter((editor) => editor.document.uri.fsPath === event.source)
          : vscode.window.visibleTextEditors;

      if (editors.length === 0) return;

      // Build a map of source paths to line numbers for efficient lookup
      const sourceToLines = new Map<string, Set<number>>();

      for (const info of this.testRunInfos.values()) {
        for (const startedEvent of info.startedEvents.values()) {
          if (startedEvent.source && startedEvent.lineno && startedEvent.lineno > 0) {
            if (!sourceToLines.has(startedEvent.source)) {
              sourceToLines.set(startedEvent.source, new Set());
            }
            sourceToLines.get(startedEvent.source)!.add(startedEvent.lineno);
          }
        }
      }

      // Apply decorations to editors
      for (const editor of editors) {
        const editorPath = editor.document.uri.fsPath;
        const lineNumbers = sourceToLines.get(editorPath);

        const decorations: vscode.DecorationOptions[] = [];
        if (lineNumbers) {
          for (const lineno of lineNumbers) {
            decorations.push({
              range: new vscode.Range(new vscode.Position(lineno - 1, 0), new vscode.Position(lineno - 1, 0)),
            });
          }
        }

        editor.setDecorations(this.activeStepDecorationType, decorations);
      }
    });
  }

  private async onRobotStartedEvent(runId: string | undefined, event: RobotExecutionEvent) {
    if (runId) {
      if (event.source !== undefined && event.lineno !== undefined && event.lineno > 0) {
        // try {
        //   const editor = await vscode.window.showTextDocument(vscode.Uri.file(event.source));

        //   editor.revealRange(
        //     new vscode.Range(new vscode.Position(event.lineno - 1, 0), new vscode.Position(event.lineno - 1, 0)),
        //     vscode.TextEditorRevealType.Default,
        //   );
        // } catch {
        //   // ignore
        // }
        await this.updateEditorsMutex.dispatch(() => {
          const infos = this.testRunInfos.get(runId);
          if (infos !== undefined) {
            infos.startedEvents.set(event.id, event);
          }
        });
        await this.updateEditorDecorations(event);
      }
    }

    switch (event.type) {
      case "suite":
        break;
      case "test":
        this.testItemStarted(runId, event);
        break;
      case "keyword":
        break;
      default:
        // do nothing
        break;
    }
  }

  private testItemStarted(runId: string | undefined, event: RobotExecutionEvent) {
    if (runId === undefined || event.attributes?.longname === undefined) return;

    const run = this.testRunInfos.get(runId)?.run;

    if (run !== undefined) {
      const item = this.findTestItemById(event.id);
      if (item !== undefined) {
        run.started(item);
      }
    }
  }

  private async onRobotEndedEvent(runId: string | undefined, event: RobotExecutionEvent) {
    if (runId) {
      await this.updateEditorsMutex.dispatch(() => {
        const infos = this.testRunInfos.get(runId);
        if (infos !== undefined) {
          infos.startedEvents.delete(event.id);
        }
      });

      this.updateEditorDecorations(event);
    }
    switch (event.type) {
      case "suite":
        break;
      case "test":
        this.testItemEnded(runId, event);
        break;
      case "keyword":
        break;
      default:
        // do nothing
        break;
    }
  }

  private onRobotSetFailed(runId: string | undefined, event: RobotExecutionEvent) {
    switch (event.type) {
      case "suite":
      case "test":
        this.testItemSetFailed(runId, event);
        break;
      default:
        // do nothing
        break;
    }
  }

  private testItemSetFailed(runId: string | undefined, event: RobotExecutionEvent) {
    if (runId === undefined || event.attributes?.longname === undefined) return;

    const run = this.testRunInfos.get(runId)?.run;

    if (run !== undefined) {
      const item = this.findTestItemById(event.id);
      if (item) {
        const message = new vscode.TestMessage((event.attributes?.message ?? "").replaceAll("\n", "\r\n"));

        if (event.attributes.source) {
          message.location = new vscode.Location(
            vscode.Uri.file(event.attributes.source),
            new vscode.Range(
              new vscode.Position((event.attributes.lineno ?? 1) - 1, 0),
              new vscode.Position(event.attributes.lineno ?? 1, 0),
            ),
          );
        }

        if (event.attributes.status === "SKIP") {
          run.skipped(item);
        } else if (event.attributes.status === "FAIL") {
          run.failed(item, message, event.attributes.elapsedtime);
        } else if (event.attributes.status === "ERROR") {
          run.errored(item, message, event.attributes.elapsedtime);
        }
      }
    }
  }

  private testItemEnded(runId: string | undefined, event: RobotExecutionEvent) {
    if (runId === undefined || event.attributes?.longname === undefined) return;

    const run = this.testRunInfos.get(runId)?.run;

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

              if (
                !event.attributes?.message ||
                !event.failedKeywords?.find((v) => v.message === event.attributes?.message)
              ) {
                const message = new vscode.TestMessage((event.attributes.message ?? "").replaceAll("\n", "\r\n"));

                if (event.attributes.source) {
                  message.location = new vscode.Location(
                    vscode.Uri.file(event.attributes.source),
                    new vscode.Range(
                      new vscode.Position((event.attributes.lineno ?? 1) - 1, 0),
                      new vscode.Position(event.attributes.lineno ?? 1, 0),
                    ),
                  );
                }
                messages.push(message);
              }

              if (event.failedKeywords) {
                for (const keyword of event.failedKeywords.reverse()) {
                  const message = new vscode.TestMessage((keyword.message ?? "").replaceAll("\n", "\r\n"));

                  if (keyword.source) {
                    message.location = new vscode.Location(
                      vscode.Uri.file(keyword.source),
                      new vscode.Range(
                        new vscode.Position((keyword.lineno ?? 1) - 1, 0),
                        new vscode.Position(keyword.lineno ?? 1, 0),
                      ),
                    );
                  }

                  messages.push(message);
                }
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

  private onRobotLogMessageEvent(runId: string | undefined, event: RobotLogMessageEvent, isMessage: boolean): void {
    if (runId === undefined) return;

    const run = this.testRunInfos.get(runId)?.run;

    let location: vscode.Location | undefined = undefined;

    if (run !== undefined) {
      location = event.source
        ? new vscode.Location(
            vscode.Uri.file(event.source),
            new vscode.Range(
              new vscode.Position((event.lineno ?? 1) - 1, event.column ?? 0),
              new vscode.Position(event.lineno ?? 1, event.column ?? 0),
            ),
          )
        : undefined;

      let style = (s: string) => s;
      switch (event.level) {
        case "WARN":
          style = yellow;
          break;
        case "ERROR":
          style = red;
          break;
        case "FAIL":
          style = red;
          break;
      }

      const messageStyle = isMessage ? blue : (s: string) => s;

      run.appendOutput(
        `[ ${style(event.level)} ] ${messageStyle(event.message.replaceAll("\n", "\r\n"))}` + "\r\n",
        location,
        event.itemId !== undefined ? this.findTestItemById(event.itemId) : undefined,
      );
    }
  }
}
