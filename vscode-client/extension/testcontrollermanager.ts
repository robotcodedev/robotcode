import { red, yellow, blue } from "ansi-colors";
import * as vscode from "vscode";
import { DebugManager } from "./debugmanager";
import * as fs from "fs";
import * as path from "path";

import { ClientState, LanguageClientsManager, toVsCodeRange } from "./languageclientsmanger";
import { filterAsync, Mutex, truncateAndReplaceNewlines, WeakValueMap } from "./utils";
import { CONFIG_SECTION } from "./config";
import { Diagnostic, DiagnosticSeverity } from "vscode-languageclient/node";
import {
  FILE_DISCOVERY_COMMAND,
  FileEventKind,
  fileDiscoveryArguments,
  fileEventAction,
  folderRun,
  RefreshQueue,
  RobotCodeDiscoverResult,
  RobotItemIndex,
  RobotItemType,
  RobotTestItem,
  suiteChildrenIn,
} from "./testdiscovery";
import { folderUriOf, TestTreeBuilder } from "./testtree";

// Why the Testing view is empty; the manifest's viewsWelcome entries pick their hint by this key.
const CONTEXT_TEST_EXPLORER_STATE = "robotcode.testExplorer.state";

function setTestExplorerState(state: "noTests" | "noEnvironment" | "disabled" | "hasTests" | undefined): void {
  void vscode.commands.executeCommand("setContext", CONTEXT_TEST_EXPLORER_STATE, state);
}

// A cancellation token source that follows an AbortSignal of the refresh queue, for the processes of discoveries.
function tokenSourceOf(signal: AbortSignal): vscode.CancellationTokenSource {
  const source = new vscode.CancellationTokenSource();
  if (signal.aborted) source.cancel();
  else signal.addEventListener("abort", () => source.cancel(), { once: true });
  return source;
}

function signalOf(token: vscode.CancellationToken | undefined): AbortSignal | undefined {
  if (token === undefined) return undefined;
  const controller = new AbortController();
  if (token.isCancellationRequested) controller.abort();
  else token.onCancellationRequested(() => controller.abort());
  return controller.signal;
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
  kwname: string | undefined;
  libname: string | undefined;
  caught: boolean | undefined;
}

type RobotEventType = "suite" | "test" | "keyword";

interface RobotFailure {
  // indices into failedKeywords: the failed keyword whose message and caught mark are the failure's, and the failed
  // keywords from the innermost call out to the test
  keyword: number;
  calls: number[];
}

interface RobotExecutionEvent {
  type: RobotEventType;
  id: string;
  attributes: RobotExecutionAttributes | undefined;
  failedKeywords: RobotExecutionAttributes[] | undefined;
  // in the order their keywords ended
  failures: RobotFailure[] | undefined;
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

function lineLocation(source: string, lineno: number | undefined): vscode.Location {
  return new vscode.Location(
    vscode.Uri.file(source),
    new vscode.Range(new vscode.Position((lineno ?? 1) - 1, 0), new vscode.Position(lineno ?? 1, 0)),
  );
}

function failureText(keyword: RobotExecutionAttributes): string {
  return ((keyword.caught ? "Caught: " : "") + (keyword.message ?? "")).replaceAll("\n", "\r\n");
}

// A failure, given by its calls innermost first, sits at the outermost one, the call in the test, and lists the others
// as Python does, from the outside in, so the call that failed comes last; VS Code would show the outermost one again
// in the list. A call on the line of the call it ran in, as a keyword that a Run Keyword variant runs, is left out, so
// that the list does not show the same code twice.
function failureMessage(keyword: RobotExecutionAttributes, calls: RobotExecutionAttributes[]): vscode.TestMessage {
  const message = new vscode.TestMessage(failureText(keyword));
  const outermost = calls[calls.length - 1];
  if (outermost.source) {
    message.location = lineLocation(outermost.source, outermost.lineno);
  }
  const listed = calls
    .slice(0, -1)
    .filter((call, i) => call.source !== calls[i + 1].source || call.lineno !== calls[i + 1].lineno)
    .reverse();
  if (listed.length > 0) {
    message.stackTrace = listed.map(
      (call) =>
        new vscode.TestMessageStackFrame(
          [call.libname, call.kwname].filter((name) => name).join("."),
          call.source ? vscode.Uri.file(call.source) : undefined,
          new vscode.Position((call.lineno ?? 1) - 1, 0),
        ),
    );
  }
  return message;
}

// VS Code marks the message of a failure once in each file: at its location, and in every other file at the first
// frame of its stack trace there, the outermost call. These are the other lines of its calls, once each.
function unmarkedCallLocations(calls: RobotExecutionAttributes[]): vscode.Location[] {
  const locations = calls.flatMap((call) => (call.source ? [lineLocation(call.source, call.lineno)] : []));
  if (locations.length === 0) return [];

  const lineOf = (location: vscode.Location) => `${location.uri.toString()}:${location.range.start.line}`;
  const outermost = locations[locations.length - 1];
  const markedFiles = new Set([outermost.uri.toString()]);
  const seenLines = new Set([lineOf(outermost)]);
  const result: vscode.Location[] = [];

  for (const location of locations.slice(0, -1).reverse()) {
    const file = location.uri.toString();
    if (!markedFiles.has(file)) {
      markedFiles.add(file);
      seenLines.add(lineOf(location));
    } else if (!seenLines.has(lineOf(location))) {
      seenLines.add(lineOf(location));
      result.push(location);
    }
  }
  return result;
}

// The model of a workspace folder: the items of its last discovery, with the read single files put in.
class WorkspaceFolderEntry {
  public constructor(
    public readonly items: RobotTestItem[],
    public readonly supportsParseInclude: boolean = false,
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

  private readonly updateEditorsMutex = new Mutex();
  private readonly debugSessions = new Set<vscode.DebugSession>();
  private diagnosticCollection = vscode.languages.createDiagnosticCollection("robotCode discovery");
  private activeStepDecorationType: vscode.TextEditorDecorationType;
  showEditorRunDecorations = false;
  private readonly profilesCache = new WeakMap<vscode.WorkspaceFolder, RobotCodeProfilesResult>();
  // The items of the folders' models by ID, and their suites by URI; derived from robotTestItems.
  private readonly itemIndex = new RobotItemIndex((uri) => vscode.Uri.parse(uri).toString());
  // The one way from the models to the items of the controller.
  private readonly treeBuilder: TestTreeBuilder;
  // The reads of single files and the discoveries of folders, keyed by URI string.
  private readonly refreshQueue: RefreshQueue;

  constructor(
    public readonly extensionContext: vscode.ExtensionContext,
    public readonly languageClientsManager: LanguageClientsManager,
    public readonly debugManager: DebugManager,
    public readonly outputChannel: vscode.OutputChannel,
  ) {
    this.testController = vscode.tests.createTestController("robotCode.RobotFramework", "Robot Framework Tests/Tasks");

    this.treeBuilder = new TestTreeBuilder(this.testController, {
      tagsOf: (names) => this.convertTags(names) ?? [],
      folderTagOf: (item) => this.getFolderTag(this.findWorkspaceFolderForItem(item)),
    });
    this.refreshQueue = new RefreshQueue({
      readFile: (folder, uri, signal) => this.readFile(folder, uri, signal),
      discoverFolder: (folder, signal) => this.discoverFolder(folder, signal),
    });

    this.testController.resolveHandler = async (item) => {
      if (item === undefined) {
        // At start: the folders without a model yet are discovered.
        await this.discoverFolders(
          (vscode.workspace.workspaceFolders ?? []).filter((folder) => this.robotTestItems.get(folder) === undefined),
        );
        return;
      }
      // An expanded item gets its children from the model; no file is read.
      const robotItem = this.findRobotItem(item);
      if (robotItem?.children !== undefined) this.treeBuilder.buildChildren(item, robotItem.children);
    };

    this.testController.refreshHandler = async (token) => {
      await this.discoverFolders(vscode.workspace.workspaceFolders ?? [], token);
    };

    this.updateRunProfiles().then(
      (_) => undefined,
      (_) => undefined,
    );

    // Watches everything: VS Code reports an operation on a whole folder as one event for the folder,
    // without events for the files in it.
    const fileWatcher = vscode.workspace.createFileSystemWatcher("**");

    fileWatcher.onDidCreate((uri) => this.onFileEvent("created", uri));
    fileWatcher.onDidDelete((uri) => this.onFileEvent("deleted", uri));
    fileWatcher.onDidChange((uri) => this.onFileEvent("changed", uri));

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
      this.languageClientsManager.onRobotEnvironmentStateChanged(async (event) => {
        // A folder that became usable gets its tests when its language server starts; a folder that lost its
        // environment, or was switched off, shows the hint instead of its tests.
        if (event.state.state === "unusable" || this.languageClientsManager.isDisabledForFolder(event.folder)) {
          await this.discoverFolders([event.folder]);
        }
      }),
      this.languageClientsManager.onClientStateChanged(async (event) => {
        const folder = vscode.workspace.getWorkspaceFolder(event.uri);
        switch (event.state) {
          case ClientState.Running: {
            if (folder) await this.discoverFolders([folder]);
            break;
          }
          case ClientState.Refreshed: {
            if (folder && !this.languageClientsManager.clients.has(folder.uri.toString())) {
              await this.discoverFolders([folder]);
            }
            if (folder) this.invalidateProfilesCache(folder);
            await this.updateRunProfiles();
            break;
          }
        }
      }),
      vscode.workspace.onDidChangeConfiguration(async (event) => {
        const changedFolders = (vscode.workspace.workspaceFolders ?? []).filter((folder) =>
          event.affectsConfiguration("robotcode.testExplorer", folder),
        );

        if (changedFolders.length > 0) {
          await this.discoverFolders(vscode.workspace.workspaceFolders ?? []);
          await this.updateRunProfiles();
        } else if (event.affectsConfiguration("launch.configurations")) {
          await this.updateRunProfiles();
        }
      }),
      vscode.workspace.onDidSaveTextDocument((document) => this.onFileEvent("edited", document.uri)),
      vscode.workspace.onDidChangeTextDocument((event) => {
        // Skip events without actual content changes (e.g. dirty marker updates).
        if (event.contentChanges.length === 0) return;
        void this.onFileEvent("edited", event.document.uri);
      }),
      vscode.workspace.onDidChangeWorkspaceFolders(async (event) => {
        await this.updateRunProfiles();

        for (const r of event.removed) {
          this.removeWorkspaceFolderItems(r);
        }
        if (event.added.length > 0) {
          await this.discoverFolders(event.added);
        }
        this.updateTestExplorerState();
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
      const selectedProfiles = config.get<string[]>("profiles", []);
      const result = await this.getRobotCodeProfiles(folder, selectedProfiles.length ? selectedProfiles : undefined);

      // Drop configured profiles that are no longer defined in the configuration so they don't
      // linger as an unselectable, active selection. Skip this when the available profiles could
      // not be determined (e.g. invalid environment) to avoid clearing a still-valid selection.
      const couldNotDetermine = result.profiles.length === 0 && !result.messages?.length;
      const availableNames = new Set(result.profiles.map((p) => p.name));
      const removedProfiles = couldNotDetermine ? [] : selectedProfiles.filter((name) => !availableNames.has(name));
      if (removedProfiles.length > 0) {
        await config.update(
          "profiles",
          selectedProfiles.filter((name) => availableNames.has(name)),
          vscode.ConfigurationTarget.WorkspaceFolder,
        );
      }

      const removedMessage =
        removedProfiles.length === 0
          ? undefined
          : removedProfiles.length === 1
            ? `The selected profile "${removedProfiles[0]}" was removed because it is no longer defined in the configuration.`
            : `The selected profiles ${removedProfiles
                .map((p) => `"${p}"`)
                .join(", ")} were removed because they are no longer defined in the configuration.`;

      const options = result.profiles.map((p) => {
        return {
          label: truncateAndReplaceNewlines(p.name.trim()),
          description: truncateAndReplaceNewlines(p.description.trim()),
          picked: p.selected,
        };
      });

      if (options.length === 0) {
        const baseMessage = result.messages?.length
          ? result.messages.join("\n")
          : "No configuration profiles available.";
        await vscode.window.showWarningMessage(removedMessage ? `${removedMessage}\n${baseMessage}` : baseMessage);
        return;
      }

      if (removedMessage) {
        vscode.window.showWarningMessage(removedMessage);
      }

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

    this.removeFolderModel(folder);
  }

  dispose(): void {
    this.refreshQueue.dispose();

    this.itemIndex.clear();

    this._disposables.dispose();
    this.testController.dispose();
  }

  public readonly robotTestItems = new WeakMap<vscode.WorkspaceFolder, WorkspaceFolderEntry | undefined>();

  public findRobotItem(item: vscode.TestItem): RobotTestItem | undefined {
    // The index follows the models in robotTestItems (setFolderModel, readFile).
    return this.itemIndex.get(item.id);
  }

  // Resolves the discover `workspace` RobotTestItem for a folder directly from the per-folder
  // discovery result. Do NOT go via the URI of an item here: the workspace item and its root suite
  // share the folder URI, so a lookup by URI cannot distinguish them (see #624 — a wrong resolution
  // dropped `-I`/`-N` from the run command).
  public findWorkspaceRobotItem(folder: vscode.WorkspaceFolder): RobotTestItem | undefined {
    return this.robotTestItems.get(folder)?.items?.find((i) => i.type === RobotItemType.WORKSPACE);
  }

  public findTestItemById(id: string): vscode.TestItem | undefined {
    return this.treeBuilder.get(id);
  }

  private static folderKey(folder: vscode.WorkspaceFolder): string {
    return folder.uri.toString();
  }

  private static folderOf(key: string): vscode.WorkspaceFolder | undefined {
    return vscode.workspace.workspaceFolders?.find((folder) => folder.uri.toString() === key);
  }

  // A file event reads the file again, discovers its folder, or does nothing, see fileEventAction.
  private async onFileEvent(kind: FileEventKind, uri: vscode.Uri): Promise<void> {
    if (uri.scheme !== "file") return;
    const folder = vscode.workspace.getWorkspaceFolder(uri);
    if (folder === undefined || !this.isTestExplorerEnabledForWorkspace(folder)) return;

    const isRobotFile = this.hasRobotFileExtension(uri.path);
    const action = fileEventAction({
      kind,
      isSuiteFile: this.itemIndex.suiteOf(uri.toString()) !== undefined,
      isResourceFile: uri.path.toLowerCase().endsWith(".resource"),
      isRobotFile,
      isFolderWithRobotFiles: kind === "created" && !isRobotFile && (await this.containsRobotFile(uri)),
      isAtOrAboveSuite: kind === "deleted" && this.isDiscoveredSuiteOrAbove(uri),
    });
    if (action === "read") this.refreshQueue.requestFile(TestControllerManager.folderKey(folder), uri.toString());
    else if (action === "discover") this.refreshQueue.requestFolder(TestControllerManager.folderKey(folder));
  }

  // Discovers the folders now, one after another in the refresh queue.
  private async discoverFolders(
    folders: readonly vscode.WorkspaceFolder[],
    token?: vscode.CancellationToken,
  ): Promise<void> {
    const signal = signalOf(token);
    await Promise.all(
      folders.map((folder) => this.refreshQueue.discoverFolder(TestControllerManager.folderKey(folder), signal)),
    );
  }

  // A job of the refresh queue: reads a suite file again and puts the children of its suite into the folder's model.
  private async readFile(folderKey: string, uri: string, signal: AbortSignal): Promise<void> {
    const folder = TestControllerManager.folderOf(folderKey);
    if (folder === undefined) return;
    const suite = this.itemIndex.suiteOf(uri);
    if (suite === undefined) {
      // queued behind this job; awaiting it here would wait for this job
      void this.refreshQueue.discoverFolder(folderKey);
      return;
    }

    const item = this.treeBuilder.get(suite.id);
    if (item !== undefined) item.busy = true;
    const tokenSource = tokenSourceOf(signal);
    try {
      const result = await this.getTestsFromFile(folder, vscode.Uri.parse(uri), suite, tokenSource.token);
      if (result === undefined || signal.aborted) return;

      const children = suiteChildrenIn(result.items, suite.id);
      if (children === undefined) {
        void this.refreshQueue.discoverFolder(folderKey);
        return;
      }
      this.itemIndex.replaceChildren(suite, children);

      const suiteItem = this.treeBuilder.get(suite.id);
      if (suiteItem !== undefined) this.treeBuilder.buildChildren(suiteItem, children);
      else this.buildFolder(folder, []);
    } finally {
      tokenSource.dispose();
      if (item !== undefined) item.busy = false;
    }
  }

  // A job of the refresh queue: discovers a workspace folder and builds its tree from the new model.
  private async discoverFolder(folderKey: string, signal: AbortSignal): Promise<void> {
    const folder = TestControllerManager.folderOf(folderKey);
    if (folder === undefined) return;

    if (
      !this.isTestExplorerEnabledForWorkspace(folder) ||
      this.languageClientsManager.isRobotEnvironmentKnownInvalid(folder)
    ) {
      // No discovery can run without a valid environment. The cached answer is used so that this does not wait for
      // the environment dialog; the language client start discovers again once an environment is valid.
      this.removeFolderModel(folder);
      this.updateTestExplorerState();
      return;
    }

    const workspaceRobotItem = this.findWorkspaceRobotItem(folder);
    const workspaceItem = workspaceRobotItem ? this.treeBuilder.get(workspaceRobotItem.id) : undefined;
    if (workspaceItem !== undefined) workspaceItem.busy = true;
    const tokenSource = tokenSourceOf(signal);
    try {
      const result = await this.getTestsFromWorkspaceFolder(folder, tokenSource.token);
      // An aborted discovery leaves the model as it is; the discovery that replaced it builds the tree.
      if (result === undefined || signal.aborted) return;

      const oldRootIds = (this.robotTestItems.get(folder)?.items ?? []).map((i) => i.id);
      this.setFolderModel(folder, result);
      this.buildFolder(folder, oldRootIds);
    } finally {
      tokenSource.dispose();
      if (workspaceItem !== undefined) workspaceItem.busy = false;
      this.updateTestExplorerState();
    }
  }

  private setFolderModel(folder: vscode.WorkspaceFolder, result: RobotCodeDiscoverResult): void {
    this.itemIndex.remove(this.robotTestItems.get(folder)?.items);
    const entry = new WorkspaceFolderEntry(result.items ?? [], result.supportsParseInclude ?? false);
    this.robotTestItems.set(folder, entry);
    this.itemIndex.add(entry.items);
  }

  private removeFolderModel(folder: vscode.WorkspaceFolder): void {
    const items = this.robotTestItems.get(folder)?.items;
    this.itemIndex.remove(items);
    this.robotTestItems.delete(folder);
    for (const item of items ?? []) this.treeBuilder.remove(undefined, item.id);
  }

  // Builds the root items of a folder from its model and removes the old root items that it no longer has.
  private buildFolder(folder: vscode.WorkspaceFolder, oldRootIds: string[]): void {
    const kept = new Set<string>();
    for (const robotItem of this.robotTestItems.get(folder)?.items ?? []) {
      const item = this.treeBuilder.build(undefined, robotItem);
      if (item !== undefined) kept.add(item.id);
    }
    for (const id of oldRootIds) if (!kept.has(id)) this.treeBuilder.remove(undefined, id);
  }

  // The Testing view shows welcome content only while the tree is empty; the context key says why it is
  // empty, so the manifest's viewsWelcome entries can pick the right hint. While an enabled folder has no
  // model yet, its discovery has not ended, and the state stays until it has.
  private updateTestExplorerState(): void {
    const folders = vscode.workspace.workspaceFolders ?? [];
    const enabled = folders.filter((folder) => this.isTestExplorerEnabledForWorkspace(folder));
    if (folders.length === 0) {
      setTestExplorerState(undefined);
    } else if (enabled.length === 0) {
      setTestExplorerState("disabled");
    } else if (this.testController.items.size > 0) {
      setTestExplorerState("hasTests");
    } else if (enabled.some((folder) => this.languageClientsManager.isRobotEnvironmentKnownInvalid(folder))) {
      setTestExplorerState("noEnvironment");
    } else if (enabled.every((folder) => this.robotTestItems.get(folder) !== undefined)) {
      setTestExplorerState("noTests");
    }
  }

  private async discoverTests(
    folder: vscode.WorkspaceFolder,
    discoverArgs: string[],
    extraArgs: string[],
    stdioData?: string,
    prune?: boolean,
    token?: vscode.CancellationToken,
  ): Promise<RobotCodeDiscoverResult> {
    if (!(await this.languageClientsManager.isValidRobotEnvironmentInFolder(folder, true))) {
      if (prune) {
        this.diagnosticCollection.forEach((uri, _diagnostics, collection) => {
          if (vscode.workspace.getWorkspaceFolder(uri) === folder) collection.delete(uri);
        });
      }
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
            const r = new vscode.Diagnostic(
              toVsCodeRange(v.range),
              Diagnostic.getMessageString(v),
              diagnosticsSeverityToVsCode(v.severity),
            );
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

  // The text of the folder's open Robot Framework documents, for the stdin of the discover command.
  private openDocumentsOf(folder: vscode.WorkspaceFolder): { [key: string]: string } {
    const documents: { [key: string]: string } = {};
    for (const document of vscode.workspace.textDocuments) {
      if (
        this.languageClientsManager.supportedLanguages.includes(document.languageId) &&
        vscode.workspace.getWorkspaceFolder(document.uri) === folder
      ) {
        documents[document.uri.toString()] = document.getText();
      }
    }
    return documents;
  }

  // The discovery of a folder, or undefined when it was aborted or could not run. A failed discovery gives the
  // folder's error item, so that it replaces the suites of the last result.
  public async getTestsFromWorkspaceFolder(
    folder: vscode.WorkspaceFolder,
    token?: vscode.CancellationToken,
  ): Promise<RobotCodeDiscoverResult | undefined> {
    const robotFiles = await vscode.workspace.findFiles(
      new vscode.RelativePattern(folder, `**/*.{${this.languageClientsManager.fileExtensions.join(",")}}`),
      undefined,
      1,
      token,
    );
    // A cancelled search finds nothing; that is no folder without files.
    if (token?.isCancellationRequested) return undefined;

    if (robotFiles.length === 0) {
      // A folder without Robot Framework files is a completed discovery without tests, not an aborted
      // one (`undefined`); a file created later reaches the tree through the watcher.
      return { items: [] };
    }

    try {
      const result = await this.discoverTests(
        folder,
        ["discover", "--read-from-stdin", "all"],
        [],
        JSON.stringify(this.openDocumentsOf(folder)),
        true,
        token,
      );
      return result.items !== undefined ? result : undefined;
    } catch (e) {
      if (e instanceof Error && e.name === "AbortError") return undefined;

      return {
        items: [
          {
            name: folder.name,
            type: RobotItemType.WORKSPACE,
            id: folder.uri.fsPath,
            uri: folder.uri.toString(),
            longname: folder.name,
            error: e?.toString() || "Unknown Error",
            children: [],
          },
        ],
      };
    }
  }

  // Reads a single suite file again, or undefined when the read was aborted or failed.
  public async getTestsFromFile(
    folder: vscode.WorkspaceFolder,
    uri: vscode.Uri,
    suite: RobotTestItem,
    token?: vscode.CancellationToken,
  ): Promise<RobotCodeDiscoverResult | undefined> {
    // Whether to pass `-I` is a per-folder environment fact, taken from the last discovery of the folder.
    const supportsParseInclude = this.robotTestItems.get(folder)?.supportsParseInclude ?? false;
    // The name of the top-level suite, as the runs pass it with -N.
    const topLevelSuite = this.findWorkspaceRobotItem(folder)?.children?.[0]?.longname;

    try {
      if (this.diagnosticCollection.has(uri)) {
        this.diagnosticCollection.delete(uri);
      }

      const result = await this.discoverTests(
        folder,
        FILE_DISCOVERY_COMMAND,
        fileDiscoveryArguments(suite, topLevelSuite, supportsParseInclude),
        JSON.stringify(this.openDocumentsOf(folder)),
        false,
        token,
      );
      return result.items !== undefined ? result : undefined;
    } catch (e) {
      if (e instanceof Error && e.name === "AbortError") return undefined;
      this.outputChannel.appendLine(`Error while getting tests from document: ${e?.toString() || "Unknown Error"}`);

      return undefined;
    }
  }

  private isTestExplorerEnabledForWorkspace(workspace: vscode.WorkspaceFolder): boolean {
    if (this.languageClientsManager.isDisabledForFolder(workspace)) {
      return false;
    }

    const result = vscode.workspace.getConfiguration(CONFIG_SECTION, workspace).get<boolean>("testExplorer.enabled");

    return result === undefined || result;
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

  private hasRobotFileExtension(name: string): boolean {
    const lowerName = name.toLowerCase();
    return this.languageClientsManager.fileExtensions.some((ext) => lowerName.endsWith(`.${ext}`));
  }

  // Whether a deleted path is the source of a suite in the folder's discovery result, or lies above one.
  // relSource is relative to the project root that discovery changes into, the source of the workspace
  // item. That path has symbolic links resolved, so for a workspace folder opened through one, the paths
  // VS Code reports are taken relative to the workspace folder instead.
  private isDiscoveredSuiteOrAbove(uri: vscode.Uri): boolean {
    const folder = vscode.workspace.getWorkspaceFolder(uri);
    if (uri.scheme !== "file" || folder === undefined) return false;

    const items = this.robotTestItems.get(folder)?.items;
    if (items === undefined) return false;

    const root = this.findWorkspaceRobotItem(folder)?.source;
    const fromRoot = root !== undefined ? path.relative(root, uri.fsPath) : undefined;
    const relativePath =
      fromRoot !== undefined && fromRoot !== ".." && !fromRoot.startsWith(`..${path.sep}`) && !path.isAbsolute(fromRoot)
        ? fromRoot
        : path.relative(folder.uri.fsPath, uri.fsPath);

    // Like VS Code's own glob matching, case-insensitive on Windows and macOS.
    const ignoreCase = process.platform === "win32" || process.platform === "darwin";
    const normalize = (p: string) => (ignoreCase ? p.toLowerCase() : p);
    const deleted = normalize(relativePath.split(path.sep).join("/"));

    const matches = (list: RobotTestItem[] | undefined): boolean =>
      list?.some((item) => {
        if (item.type === RobotItemType.SUITE && item.relSource !== undefined) {
          const source = normalize(item.relSource);
          if (source === deleted || source.startsWith(`${deleted}/`)) return true;
        }
        return matches(item.children);
      }) ?? false;

    return matches(items);
  }

  // Whether a created directory contains a Robot Framework file. The walk does not follow symbolic links
  // and skips what files.watcherExclude excludes, so it looks at what the watcher would report.
  private async containsRobotFile(uri: vscode.Uri): Promise<boolean> {
    const folder = vscode.workspace.getWorkspaceFolder(uri);
    if (uri.scheme !== "file" || folder === undefined) return false;

    try {
      if (!(await fs.promises.stat(uri.fsPath)).isDirectory()) return false;
    } catch {
      return false;
    }

    // Like VS Code, relative patterns apply to the workspace folder, and a trailing "/**" also excludes
    // the folder itself, which path.matchesGlob alone does not.
    const resolve = (pattern: string) =>
      pattern.startsWith("**") || path.isAbsolute(pattern) ? pattern : path.join(folder.uri.fsPath, pattern);
    const excludes = Object.entries(
      vscode.workspace.getConfiguration("files", folder).get<Record<string, boolean>>("watcherExclude", {}),
    )
      .filter(([, enabled]) => enabled)
      .map(([pattern]) => ({
        pattern: resolve(pattern),
        folderPattern: pattern.endsWith("/**") ? resolve(pattern.slice(0, -3)) : undefined,
      }));
    const isExcluded = (p: string, isDirectory: boolean) =>
      excludes.some(
        ({ pattern, folderPattern }) =>
          path.matchesGlob(p, pattern) ||
          (isDirectory && folderPattern !== undefined && path.matchesGlob(p, folderPattern)),
      );

    const walk = async (dir: string): Promise<boolean> => {
      let entries: fs.Dirent[];
      try {
        entries = await fs.promises.readdir(dir, { withFileTypes: true });
      } catch {
        return false;
      }
      for (const entry of entries) {
        const entryPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          if (!isExcluded(entryPath, true) && (await walk(entryPath))) return true;
        } else if (this.hasRobotFileExtension(entry.name) && !isExcluded(entryPath, false)) {
          return true;
        }
      }
      return false;
    };

    return walk(uri.fsPath);
  }

  // eslint-disable-next-line class-methods-use-this
  private findWorkspaceFolderForItem(item: vscode.TestItem): vscode.WorkspaceFolder | undefined {
    // The top-level suite of several paths has no URI; without its folder it would get no run profile and no run.
    const uri = folderUriOf(item);
    return uri !== undefined ? vscode.workspace.getWorkspaceFolder(uri) : undefined;
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

    const myRunIds = new Set<string>();
    let cancelled = false;
    const stopMyRunSessions = async () => {
      for (const session of this.debugSessions) {
        if (myRunIds.has(session.configuration.runId)) {
          await vscode.debug.stopDebugging(session);
        }
      }
    };

    token.onCancellationRequested(async (_) => {
      cancelled = true;
      await stopMyRunSessions();
    });

    for (const [folder, testItems] of included) {
      if (cancelled) break;
      const run = folderRun(
        request.profile?.tag === undefined || request.profile.tag === this.getFolderTag(folder),
        request.include !== undefined,
      );
      if (run === "none") continue;
      const folderProfiles = run === "profile" ? profiles : undefined;
      const folderTestConfiguration = run === "profile" ? testConfiguration : undefined;

      const runId = TestControllerManager.nextRunId();
      myRunIds.add(runId);
      this.testRunInfos.set(runId, new TestRunInfo(testRun));

      const options: vscode.DebugSessionOptions = {
        testRun: testRun,
      };
      if (request.profile !== undefined && request.profile.kind !== vscode.TestRunProfileKind.Debug) {
        options.noDebug = true;
      }

      const workspaceRobotItem = this.findWorkspaceRobotItem(folder);
      let workspaceItem = workspaceRobotItem ? this.findTestItemById(workspaceRobotItem.id) : undefined;

      if (workspaceRobotItem?.type == RobotItemType.WORKSPACE && workspaceRobotItem.children?.length) {
        workspaceItem = workspaceItem?.children.get(workspaceRobotItem.children[0].id);
      }

      const supportsParseInclude = this.robotTestItems.get(folder)?.supportsParseInclude ?? false;

      if (testItems.length === 1 && testItems[0] === workspaceItem && excluded.size === 0) {
        const started = await DebugManager.runTests(
          folder,
          [],
          [],
          supportsParseInclude,
          [],
          [],
          runId,
          options,
          undefined,
          folderProfiles,
          folderTestConfiguration,
        );
        if (!started) this.testRunInfos.delete(runId);
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
          supportsParseInclude,
          includedInWs,
          excludedInWs,
          runId,
          options,
          suiteName,
          folderProfiles,
          folderTestConfiguration,
        );

        if (!started) this.testRunInfos.delete(runId);
        run_started = run_started || started;
      }

      if (cancelled) {
        await stopMyRunSessions();
        break;
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
              const keywords = event.failedKeywords ?? [];
              const failures = (event.failures ?? []).map((failure) => ({
                keyword: keywords[failure.keyword],
                calls: failure.calls.map((index) => keywords[index]),
              }));
              // the failures that made the test fail first, then the caught ones
              const ordered = [
                ...failures.filter((failure) => !failure.keyword.caught),
                ...failures.filter((failure) => failure.keyword.caught),
              ];

              const messages: vscode.TestMessage[] = [];

              // without a failure in one of its keywords, the test's own message tells why it failed
              if (ordered.length === 0 || ordered[0].keyword.caught) {
                const message = new vscode.TestMessage((event.attributes.message ?? "").replaceAll("\n", "\r\n"));

                if (event.attributes.source) {
                  message.location = lineLocation(event.attributes.source, event.attributes.lineno);
                }
                messages.push(message);
              }

              for (const failure of ordered) {
                messages.push(failureMessage(failure.keyword, failure.calls));

                // the calls without a marker show the failure as inline output
                for (const location of unmarkedCallLocations(failure.calls)) {
                  run.appendOutput(`${failureText(failure.keyword)}\r\n`, location, item);
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
