import { red, yellow, blue } from "ansi-colors";
import * as vscode from "vscode";
import { DebugManager } from "./debugmanager";
import * as fs from "fs";

import { ClientState, LanguageClientsManager, toVsCodeRange } from "./languageclientsmanger";
import { escapeRobotGlobPatterns, filterAsync, Mutex, truncateAndReplaceNewlines, WeakValueMap } from "./utils";
import { CONFIG_SECTION } from "./config";
import { Range, Diagnostic, DiagnosticSeverity } from "vscode-languageclient/node";

function arraysEqual<T>(a: T[] | undefined, b: T[] | undefined): boolean {
  if (a === b) return true;
  if (a === undefined || b === undefined) return false;
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return false;
  return true;
}

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

function robotItemsEqual(a: RobotTestItem | undefined, b: RobotTestItem | undefined): boolean {
  if (a === b) return true;
  if (a === undefined || b === undefined) return false;
  if (a.id !== b.id) return false;
  if (a.type !== b.type) return false;
  if (a.name !== b.name) return false;
  if (a.longname !== b.longname) return false;
  if (a.description !== b.description) return false;
  if (a.error !== b.error) return false;
  if (!arraysEqual(a.tags, b.tags)) return false;
  const aRange = a.range;
  const bRange = b.range;
  if ((aRange === undefined) !== (bRange === undefined)) return false;
  if (aRange && bRange) {
    if (
      aRange.start.line !== bRange.start.line ||
      aRange.start.character !== bRange.start.character ||
      aRange.end.line !== bRange.end.line ||
      aRange.end.character !== bRange.end.character
    ) {
      return false;
    }
  }
  return robotItemListsEqual(a.children, b.children);
}

function robotItemListsEqual(a: RobotTestItem[] | undefined, b: RobotTestItem[] | undefined): boolean {
  if (a === b) return true;
  if (a === undefined || b === undefined) return false;
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (!robotItemsEqual(a[i], b[i])) return false;
  }
  return true;
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
  public constructor(
    public valid: boolean,
    public readonly items: RobotTestItem[] | undefined,
  ) {}
}

class TestRunInfo {
  public constructor(
    public readonly run: vscode.TestRun,
    public readonly startedEvents: Map<string, RobotExecutionEvent> = new Map(),
  ) {}
}

export class TestControllerManager {
  private _disposables!: vscode.Disposable;
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
  private readonly profilesCache = new WeakMap<vscode.WorkspaceFolder, RobotCodeProfilesResult>();
  // O(1) lookup for RobotTestItem by id — derived from robotTestItems, not source of truth.
  private readonly robotItemIndex = new Map<string, RobotTestItem>();
  // O(1) lookup for vscode.TestItem by URI — derived from testItems, not source of truth.
  private readonly testItemByUri = new Map<string, vscode.TestItem>();
  // Cache of the last set tag IDs per TestItem ID. Used for tag diffing in addOrUpdateTestItem.
  private readonly lastSetTags = new Map<string, string[]>();
  // Deep snapshot of the last successfully processed children per TestItem ID
  // (key "__root__" for the workspace top level). Used in refreshItem for the result
  // compare — if the new children are structurally identical, no UI update is triggered.
  private readonly lastKnownChildren = new Map<string, RobotTestItem[] | undefined>();
  // CTS for the config-change refresh path. Cancelled on the next config change so an
  // in-flight refresh terminates before the next refreshWorkspace queues behind it on
  // refreshFromUriMutex. Direct-to-refresh() events don't need this — refresh()'s
  // single-inflight pattern already cancels predecessors.
  private configChangeCts: vscode.CancellationTokenSource | undefined;

  constructor(
    public readonly extensionContext: vscode.ExtensionContext,
    public readonly languageClientsManager: LanguageClientsManager,
    public readonly debugManager: DebugManager,
    public readonly outputChannel: vscode.OutputChannel,
  ) {
    this.testController = vscode.tests.createTestController("robotCode.RobotFramework", "Robot Framework Tests/Tasks");

    this.testController.resolveHandler = async (item) => {
      // resolveHandler has no token parameter in the VS Code API — refresh() itself
      // takes care of cancelling older calls via the single-inflight pattern.
      await this.refresh(item);
    };

    this.testController.refreshHandler = async (token) => {
      await this.refreshWorkspace(undefined, token);
    };

    this.updateRunProfiles().then(
      (_) => undefined,
      (_) => undefined,
    );

    const fileWatcher = vscode.workspace.createFileSystemWatcher(
      `**/*.{${this.languageClientsManager.fileExtensions.join(",")}}`,
    );

    fileWatcher.onDidCreate(async (uri) => {
      await this.refreshUri(uri);
    });
    fileWatcher.onDidDelete(async (uri) => {
      await this.refreshUri(uri);
    });
    fileWatcher.onDidChange(async (uri) => {
      await this.refreshUri(uri);
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
        const folder = vscode.workspace.getWorkspaceFolder(event.uri);
        if (folder) {
          this.invalidateProfilesCache(folder);
        }
        switch (event.state) {
          case ClientState.Running: {
            // refresh()'s single-inflight handles cancellation of any predecessor.
            await this.refresh();
            break;
          }
          case ClientState.Stopped: {
            if (folder) this.removeWorkspaceFolderItems(folder);

            break;
          }
        }
        await this.updateRunProfiles();
      }),
      vscode.workspace.onDidChangeConfiguration(async (event) => {
        let testExplorerChanged = false;
        for (const ws of vscode.workspace.workspaceFolders ?? []) {
          if (event.affectsConfiguration("robotcode.testExplorer", ws)) {
            testExplorerChanged = true;
            break;
          }
        }

        if (testExplorerChanged) {
          this.configChangeCts?.cancel();
          this.configChangeCts = new vscode.CancellationTokenSource();
          await this.refreshWorkspace(undefined, this.configChangeCts.token);
          await this.updateRunProfiles();
        } else if (event.affectsConfiguration("launch.configurations")) {
          await this.updateRunProfiles();
        }
      }),
      vscode.workspace.onDidSaveTextDocument((document) => this.refreshDocument(document)),
      vscode.workspace.onDidChangeTextDocument((event) => {
        // Skip events without actual content changes (e.g. dirty marker updates).
        if (event.contentChanges.length === 0) return;
        this.refreshDocument(event.document);
      }),
      vscode.workspace.onDidChangeWorkspaceFolders(async (event) => {
        await this.updateRunProfiles();

        for (const r of event.removed) {
          this.removeWorkspaceFolderItems(r);
        }
        if (event.added.length > 0) {
          // refresh()'s single-inflight handles cancellation of any predecessor.
          await this.refresh();
        }
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

  public invalidateProfilesCache(folder?: vscode.WorkspaceFolder): void {
    if (folder) {
      this.profilesCache.delete(folder);
    } else {
      for (const ws of vscode.workspace.workspaceFolders ?? []) {
        this.profilesCache.delete(ws);
      }
    }
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

    // Use cache only when no specific profiles are requested
    if (profiles === undefined && this.profilesCache.has(folder)) {
      return this.profilesCache.get(folder)!;
    }

    const config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);
    const paths = config.get<string[] | undefined>("robot.paths", undefined);

    const result = (await this.languageClientsManager.pythonManager.executeRobotCode(
      folder,
      [...(paths?.length ? paths.flatMap((v) => ["-dp", v]) : ["-dp", "."]), "profiles", "list"],
      profiles,
      "json",
      true,
      true,
    )) as RobotCodeProfilesResult;

    // Cache the result only when no specific profiles were requested
    if (profiles === undefined) {
      this.profilesCache.set(folder, result);
    }

    return result;
  }

  public async selectConfigurationProfiles(folder?: vscode.WorkspaceFolder): Promise<void> {
    if (!folder) {
      if (vscode.workspace.workspaceFolders === undefined || vscode.workspace.workspaceFolders?.length === 0) return;

      const folders = await filterAsync(
        vscode.workspace.workspaceFolders,
        async (v) =>
          (
            await vscode.workspace.findFiles(
              new vscode.RelativePattern(v, `**/*.{${this.languageClientsManager.fileExtensions.join(",")}}`),
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

      // Index/cache cleanup for the entire subtree.
      this.unindexRobotTree(robotItems);

      for (const id of robotItems?.map((i) => i.id) ?? []) {
        const deleteItem = (itemId: string) => {
          const item = this.testItems.get(itemId);
          this.testItems.delete(itemId);
          if (item?.uri !== undefined) {
            const uriStr = item.uri.toString();
            if (this.testItemByUri.get(uriStr) === item) {
              this.testItemByUri.delete(uriStr);
            }
          }
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

    this.robotItemIndex.clear();
    this.testItemByUri.clear();
    this.lastSetTags.clear();
    this.lastKnownChildren.clear();

    this.currentRefreshCts?.cancel();
    this.currentRefreshCts?.dispose();
    this.currentRefreshCts = undefined;
    this.configChangeCts?.cancel();
    this.configChangeCts?.dispose();
    this.configChangeCts = undefined;

    this._disposables.dispose();
    this.testController.dispose();
  }

  public readonly robotTestItems = new WeakMap<vscode.WorkspaceFolder, WorkspaceFolderEntry | undefined>();

  public findRobotItem(item: vscode.TestItem): RobotTestItem | undefined {
    // The index is kept consistent with robotTestItems (populated in getTestsFromWorkspaceFolder /
    // getTestsFromDocument, cleaned in removeNotAddedTestItems / removeWorkspaceFolderItems).
    return this.robotItemIndex.get(item.id);
  }

  // Recursively walks a RobotTestItem subtree and calls cb for each item.
  private walkRobotTree(items: RobotTestItem[] | undefined, cb: (item: RobotTestItem) => void): void {
    if (!items) return;
    for (const item of items) {
      cb(item);
      this.walkRobotTree(item.children, cb);
    }
  }

  private indexRobotTree(items: RobotTestItem[] | undefined): void {
    this.walkRobotTree(items, (i) => this.robotItemIndex.set(i.id, i));
  }

  private unindexRobotTree(items: RobotTestItem[] | undefined): void {
    this.walkRobotTree(items, (i) => {
      this.robotItemIndex.delete(i.id);
      this.lastSetTags.delete(i.id);
      this.lastKnownChildren.delete(i.id);
    });
  }

  // Deep clone of the fields of a RobotTestItem subtree that are relevant for
  // robotItemsEqual. Stored as a snapshot in lastKnownChildren so the next refresh can
  // perform a structural comparison without relying on a live reference that may have
  // been mutated in the meantime.
  private snapshotChildren(items: RobotTestItem[] | undefined): RobotTestItem[] | undefined {
    if (!items) return undefined;
    return items.map(
      (i): RobotTestItem => ({
        id: i.id,
        type: i.type,
        name: i.name,
        longname: i.longname,
        description: i.description,
        error: i.error,
        tags: i.tags ? [...i.tags] : undefined,
        range: i.range ? { start: { ...i.range.start }, end: { ...i.range.end } } : undefined,
        children: this.snapshotChildren(i.children),
      }),
    );
  }

  // Threshold for burst coalescing: when this many per-file refreshes are pending at
  // once, we drop them and fire a single workspace refresh instead — which is no more
  // expensive than a per-file discover but covers all files.
  private static readonly BURST_THRESHOLD = 5;
  // Debounce window for batching rapid file/document changes before triggering discover.
  private static readonly DEBOUNCE_MS = 1000;

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
          // Remove the entry from the map immediately — it only represents *pending*
          // refreshes. Without this, didChangedTimer.size would grow monotonically and
          // burst coalescing would trigger false positives.
          this.didChangedTimer.delete(uri_str);

          // Burst coalescing: when many per-file timers fire close together (e.g. an
          // AI agent applies 10+ edits at once), drop the remaining per-file refreshes
          // and replace them with a single workspace refresh.
          // Using >=THRESHOLD because we just removed ourselves from the map.
          if (this.didChangedTimer.size >= TestControllerManager.BURST_THRESHOLD) {
            for (const [, entry] of this.didChangedTimer) entry.cancel();
            this.didChangedTimer.clear();
            this.refreshWorkspace(vscode.workspace.getWorkspaceFolder(document.uri), cancelationTokenSource.token).then(
              () => undefined,
              () => undefined,
            );
            return;
          }

          const item = this.findTestItemForDocument(document);
          if (item)
            this.refresh(item, cancelationTokenSource.token).then(
              () => {
                if (item?.canResolveChildren && item.children.size === 0) {
                  this.refreshWorkspace(
                    vscode.workspace.getWorkspaceFolder(document.uri),
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
            this.refreshWorkspace(vscode.workspace.getWorkspaceFolder(document.uri), cancelationTokenSource.token).then(
              () => undefined,
              () => undefined,
            );
          }
        }, TestControllerManager.DEBOUNCE_MS),
        cancelationTokenSource,
      ),
    );
  }

  public findTestItemForDocument(document: vscode.TextDocument): vscode.TestItem | undefined {
    return this.findTestItemByUri(document.uri.toString());
  }

  public findTestItemByUri(documentUri: string): vscode.TestItem | undefined {
    const indexed = this.testItemByUri.get(documentUri);
    if (indexed !== undefined) {
      return indexed;
    }
    // Fallback: linear scan over the WeakValueMap. Containers only (suite/workspace) —
    // tests share the URI with their suite and a refresh on a test does nothing useful.
    for (const item of this.testItems.values()) {
      if (item.uri?.toString() === documentUri && item.canResolveChildren) {
        this.testItemByUri.set(documentUri, item);
        return item;
      }
    }
    return undefined;
  }

  public findTestItemById(id: string): vscode.TestItem | undefined {
    return this.testItems.get(id);
  }

  // Tracks the currently active refresh token — single-inflight + latest-pending pattern.
  // Every new refresh() call cancels the running one so that the in-flight subprocess
  // gets killed immediately via the AbortController in pythonmanger.ts:executeRobotCode.
  // Earlier refreshes still waiting on the mutex abort right after acquiring it because
  // their CTS is already cancelled — effectively only the newest call really runs.
  private currentRefreshCts: vscode.CancellationTokenSource | undefined;

  public async refresh(item?: vscode.TestItem, externalToken?: vscode.CancellationToken): Promise<void> {
    // Cancel any in-flight predecessor.
    this.currentRefreshCts?.cancel();

    const cts = new vscode.CancellationTokenSource();
    this.currentRefreshCts = cts;

    // Bridge external cancellation (e.g. from VS Code's refreshHandler) onto our CTS.
    const externalSub = externalToken?.onCancellationRequested(() => cts.cancel());

    try {
      await this.refreshMutex.dispatch(async () => {
        if (cts.token.isCancellationRequested) return;
        await this.refreshItem(item, cts.token);
      });
    } finally {
      externalSub?.dispose();
      if (this.currentRefreshCts === cts) {
        this.currentRefreshCts = undefined;
      }
      cts.dispose();
    }
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
      // Index the freshly discovered subtree for O(1) findRobotItem lookups.
      this.indexRobotTree(result?.items);

      return result?.items;
    } catch (e) {
      if (e instanceof Error) {
        if (e.name === "AbortError") {
          if (this.lastDiscoverResults.has(folder)) {
            return this.lastDiscoverResults.get(folder)?.items;
          }
          // Abort without a cached result — return undefined so refreshItem skips this
          // folder and tries again on the next refresh. Do NOT build an error item into
          // the tree — otherwise the user sees "AbortError" as a workspace entry.
          return undefined;
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

      // Index the freshly discovered items.
      this.indexRobotTree(result?.items);

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
    if (vscode.workspace.getConfiguration(CONFIG_SECTION, workspace).get<boolean>("disableExtension")) {
      return false;
    }

    const result = vscode.workspace.getConfiguration(CONFIG_SECTION, workspace).get<boolean>("testExplorer.enabled");

    return result === undefined || result;
  }

  private async refreshItem(
    item?: vscode.TestItem,
    token?: vscode.CancellationToken,
    skipPerDocumentDiscover: boolean = false,
  ): Promise<void> {
    if (token?.isCancellationRequested) return;

    if (item) {
      item.busy = true;
      try {
        const robotItem = this.findRobotItem(item);

        let tests = robotItem?.children;

        // The per-document discover only runs when we refresh a specific TestItem
        // (resolveHandler, refreshDocument, refreshUri). When the workspace refresh
        // walks recursively, the workspace discover has already covered every file via
        // dirty-stdin — a per-document discover would be redundant.
        if (!skipPerDocumentDiscover && robotItem?.type === RobotItemType.SUITE && item.uri !== undefined) {
          if (robotItem.children === undefined) robotItem.children = [];

          const openDoc = vscode.workspace.textDocuments.find((d) => d.uri.toString() === item.uri?.toString());

          if (openDoc !== undefined) {
            const newTests = await this.getTestsFromDocument(openDoc, robotItem, token);
            // If newTests is undefined: discovery was aborted or failed. We can NOT be
            // sure that robotItem.children still reflects the current file state — so
            // return early without a result compare. Otherwise the compare against the
            // old snapshot would wrongly say "everything is the same" and the tree
            // would stay stale. The next refresh trigger will retry.
            if (newTests === undefined) return;
            tests = newTests;
            const freshIds = new Set(newTests.map((t) => t.id));
            for (const test of newTests) {
              const index = robotItem.children.findIndex((v) => v.id === test.id);
              if (index >= 0) {
                robotItem.children[index] = test;
              } else {
                robotItem.children.push(test);
              }
            }
            // Keep only items that exist in the fresh discover result, then sort by line.
            robotItem.children = robotItem.children
              .filter((v) => freshIds.has(v.id))
              .sort((a, b) => (a.range?.start.line || -1) - (b.range?.start.line || -1));

            // Update the index after the mutations.
            this.indexRobotTree(robotItem.children);
          }
        }

        if (token?.isCancellationRequested) return;

        if (robotItem) {
          // Result compare: if the current children structurally match the last seen
          // state, there is nothing to update in the tree. The comparison is against the
          // children that are currently in the TestController tree, represented by the
          // lastKnownChildren entry for the parent TestItem.
          const lastKnown = this.lastKnownChildren.get(item.id);
          if (robotItemListsEqual(lastKnown, tests)) return;

          const addedIds = new Set<string>();

          for (const test of tests ?? []) {
            addedIds.add(test.id);
          }

          for (const test of tests ?? []) {
            if (token?.isCancellationRequested) return;
            const newItem = this.addOrUpdateTestItem(item, test);
            await this.refreshItem(newItem, token, skipPerDocumentDiscover);
            // Don't keep container items that resolved to nothing (no children, no
            // error) — they'd just sit in the tree as confusing empty nodes.
            if (newItem.canResolveChildren && newItem.children.size === 0 && newItem.error === undefined) {
              addedIds.delete(newItem.id);
            }
          }

          this.removeNotAddedTestItems(item, addedIds);
          this.lastKnownChildren.set(item.id, this.snapshotChildren(tests));
        }
      } finally {
        item.busy = false;
      }
    } else {
      const rootKey = "__root__";

      // Phase 1: collect the new root children (re-discover if needed) without UI calls.
      const newRootChildren: RobotTestItem[] = [];
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
          for (const t of tests) newRootChildren.push(t);
        }
      }

      // Phase 2: result compare against the last snapshot — if identical, no UI update.
      const lastKnown = this.lastKnownChildren.get(rootKey);
      if (robotItemListsEqual(lastKnown, newRootChildren)) return;

      // Phase 3: actual UI updates.
      const addedIds = new Set<string>();
      for (const test of newRootChildren) {
        if (token?.isCancellationRequested) return;
        addedIds.add(test.id);
        const newItem = this.addOrUpdateTestItem(undefined, test);
        // Recursion path from the workspace refresh → skip the per-document discover.
        await this.refreshItem(newItem, token, true);
        if (newItem.canResolveChildren && newItem.children.size === 0 && newItem.error === undefined) {
          addedIds.delete(newItem.id);
        }
      }

      this.removeNotAddedTestItems(undefined, addedIds);
      this.lastKnownChildren.set(rootKey, this.snapshotChildren(newRootChildren));
    }
  }

  private addOrUpdateTestItem(parentTestItem: vscode.TestItem | undefined, robotTestItem: RobotTestItem) {
    const newCanResolveChildren =
      robotTestItem.type === RobotItemType.SUITE || robotTestItem.type === RobotItemType.WORKSPACE;

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
      // testItemByUri only for containers — tests share the URI with their suite and
      // would overwrite the suite entry. findTestItemForDocument is expected to return
      // the suite item, not an individual test.
      if (testItem.uri !== undefined && newCanResolveChildren) {
        this.testItemByUri.set(testItem.uri.toString(), testItem);
      }

      if (parentTestItem) {
        parentTestItem.children.add(testItem);
      } else {
        this.testController.items.add(testItem);
      }
    }

    if (testItem.canResolveChildren !== newCanResolveChildren) {
      testItem.canResolveChildren = newCanResolveChildren;
    }

    if (robotTestItem.range !== undefined) {
      const newRange = toVsCodeRange(robotTestItem.range);
      if (testItem.range === undefined || !testItem.range.isEqual(newRange)) {
        testItem.range = newRange;
      }
    }

    if (testItem.label !== robotTestItem.name) {
      testItem.label = robotTestItem.name;
    }

    const newDescription =
      robotTestItem.type == RobotItemType.TEST ||
      robotTestItem.type == RobotItemType.TASK ||
      robotTestItem.type == RobotItemType.SUITE
        ? `${robotTestItem.type} ${robotTestItem.description ? ` - ${robotTestItem.description}` : ""}`
        : robotTestItem.description;
    if (testItem.description !== newDescription) {
      testItem.description = newDescription;
    }

    if (robotTestItem.error !== undefined && testItem.error !== robotTestItem.error) {
      testItem.error = robotTestItem.error;
    }

    // Tag diff via cache of the last set tag IDs.
    const folderTag = this.getFolderTag(this.findWorkspaceFolderForItem(testItem));
    const newTagIds = [...(robotTestItem.tags ?? [])];
    if (folderTag !== undefined) newTagIds.push(folderTag.id);
    const previousTagIds = this.lastSetTags.get(robotTestItem.id);
    if (!arraysEqual(previousTagIds, newTagIds)) {
      const tags = this.convertTags(robotTestItem.tags) ?? [];
      if (folderTag !== undefined) tags.push(folderTag);
      testItem.tags = tags;
      this.lastSetTags.set(robotTestItem.id, newTagIds);
    }

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
      if (item?.uri !== undefined) {
        const uriStr = item.uri.toString();
        if (this.testItemByUri.get(uriStr) === item) {
          this.testItemByUri.delete(uriStr);
        }
      }
      this.lastSetTags.delete(i);
      this.robotItemIndex.delete(i);
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

  private async refreshWorkspace(workspace?: vscode.WorkspaceFolder, token?: vscode.CancellationToken): Promise<void> {
    return this.refreshFromUriMutex.dispatch(async () => {
      // Incremental re-discover: only reset `valid` so refreshItem re-fetches the tests.
      // removeWorkspaceFolderItems would be a wipe-and-recreate and would destroy the
      // tree expansion state in VS Code. The result compare in refreshItem instead
      // ensures that only actual differences are propagated.
      if (workspace) {
        const entry = this.robotTestItems.get(workspace);
        if (entry !== undefined) {
          entry.valid = false;
        }
        // Special case: never discovered → entry === undefined; refreshItem fetches fresh anyway.
      } else {
        for (const w of vscode.workspace.workspaceFolders ?? []) {
          const entry = this.robotTestItems.get(w);
          if (entry !== undefined) {
            entry.valid = false;
          }
        }
      }
      await this.refresh(undefined, token);
    });
  }

  private async refreshUri(uri?: vscode.Uri) {
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
          this.refreshWorkspace(workspace, cancelationTokenSource.token).then(
            () => undefined,
            () => undefined,
          );
        }, TestControllerManager.DEBOUNCE_MS),
        cancelationTokenSource,
      );
    } else {
      if (this.refreshWorkspaceChangeTimer) {
        this.refreshWorkspaceChangeTimer.cancel();
        this.refreshWorkspaceChangeTimer = undefined;
      }

      // refresh()'s single-inflight handles cancellation of any predecessor.
      this.refresh().then(
        (_) => undefined,
        (_) => undefined,
      );
    }
  }

  // eslint-disable-next-line class-methods-use-this
  private findWorkspaceFolderForItem(item: vscode.TestItem): vscode.WorkspaceFolder | undefined {
    // RobotTestItems always have a URI (workspace folder URI, suite file URI, or test
    // file URI). Resolving via the URI is O(1) and correct in all cases.
    return item.uri !== undefined ? vscode.workspace.getWorkspaceFolder(item.uri) : undefined;
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

  private static nextRunId(): string {
    return (this._runIdCounter++).toString();
  }

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

      const runId = TestControllerManager.nextRunId();
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
