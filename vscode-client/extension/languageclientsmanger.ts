import * as net from "net";
import * as path from "path";
import * as vscode from "vscode";
import {
  CloseHandlerResult,
  ErrorAction,
  CloseAction,
  ErrorHandlerResult,
  LanguageClient,
  LanguageClientOptions,
  Message,
  ServerOptions,
  TransportKind,
  ResponseError,
  InitializeError,
  RevealOutputChannelOn,
  State,
  Position,
  Location,
  Range,
  ResolveCodeLensSignature,
} from "vscode-languageclient/node";
import { sleep, Mutex } from "./utils";
import { CONFIG_SECTION } from "./config";
import {
  PythonManager,
  PythonEnvironmentProblem,
  PythonVersion,
  ResolvedPythonEnvironment,
  formatPythonVersion,
  virtualEnvironmentDir,
} from "./pythonmanger";
import { getAvailablePort } from "./net_utils";

const LANGUAGE_SERVER_DEFAULT_TCP_PORT = 6610;
const LANGUAGE_SERVER_DEFAULT_HOST = "127.0.0.1";

// Language Server Configuration Constants
const CLIENT_DISPOSE_TIMEOUT = 5000;
const CLIENT_SLEEP_DURATION = 500;
const LANGUAGE_CLIENT_PREFIX = "$robotCode:";
const ROBOT_FRAMEWORK_POLL_INTERVAL = 5000;
const ROBOT_FRAMEWORK_POLL_SLOW_INTERVAL = 10000;
const ROBOT_FRAMEWORK_POLL_FAST_ATTEMPTS = 60;
const ENVIRONMENT_EVENT_DEBOUNCE = 500;
const SELECT_ENVIRONMENT = "Select Environment";
const CREATE_ENVIRONMENT = "Create Environment";
const RETRY = "Retry";
const OPEN_SETTINGS = "Open Settings";
const DISABLE_FOR_SESSION = "For this session";
const DISABLE_FOR_PROJECT = "For this project";
// The Python side's own selection arrives shortly after RobotCode's first check at startup; the message waits for it.
const ENVIRONMENT_NOTIFICATION_DELAY = 2500;
const ENVIRONMENT_ACTION_COMMAND = "robotcode.environmentAction";

type EnvironmentAction = "select" | "create" | "useVenv" | "retry" | "settings";

/** The environment message of a folder: a progress notification whose text is replaced and which code can close. */
interface EnvironmentNotification {
  message: string;
  report: (message: string) => void;
  close: () => void;
}

// the packages of Robot Framework and RobotCode, not the libraries and tools named after them
const ROBOT_PACKAGE = String.raw`(?:robotframework|robotcode)`;
// a requirement string such as `"robotframework>=7.0"`, or a Poetry style key such as `robotframework = "^7.0"`
const ROBOT_DEPENDENCY_IN_PYPROJECT = new RegExp(
  String.raw`["']\s*${ROBOT_PACKAGE}\s*(?:\[[^\]]*\])?\s*(?:[<>=!~;@]|["'])|^\s*["']?${ROBOT_PACKAGE}["']?\s*=`,
  "im",
);
const ROBOT_REQUIREMENT = new RegExp(String.raw`^\s*${ROBOT_PACKAGE}\s*(?:\[[^\]]*\])?\s*(?:[<>=!~;@#]|$)`, "im");
// what the search for Robot Framework files skips: like Robot Framework, names that start with `.` or `_` and `CVS`
// folders, and also folders of other tools that can be large
const ROBOT_FILES_SEARCH_EXCLUDE = "{**/.*,**/_*,**/CVS,**/node_modules,**/target,**/build,**/dist,**/venv}";
const ROBOT_FILES_SEARCH_TIMEOUT = 5000;

export function toVsCodeRange(range: Range): vscode.Range {
  return new vscode.Range(
    new vscode.Position(range.start.line, range.start.character),
    new vscode.Position(range.end.line, range.end.character),
  );
}

export const SUPPORTED_LANGUAGES = ["robotframework"];

export interface Keyword {
  name: string;
  id?: string;
  signature?: string;
  documentation?: string;
}

export interface LibraryDocumentation {
  name: string;
  documentation?: string;
  keywords?: Keyword[];
  initializers?: Keyword[];
}

export interface DocumentImport {
  name: string;
  alias?: string;
  id?: string;
  type?: string;
  documentation?: string;
  keywords?: Keyword[];
}

export interface DocumentationTarget {
  uri: string;
  name: string;
  args: string[];
  baseDir?: string;
  keyword?: string;
  // A place on the page as the page's own links name it, without the `#`.
  anchor?: string;
  // The name of the documentation of a data type.
  dataType?: string;
}

export interface EvaluatableExpression {
  range: Range;
  expression?: string;
}

export enum ClientState {
  Stopped,
  Starting,
  Running,
  Ready,
  Refreshed,
}

export interface ClientStateChangedEvent {
  uri: vscode.Uri;
  state: ClientState;
}

export interface ProjectInfo {
  robotVersionString?: string;
  robocopVersionString?: string;
  pythonVersionString?: string;
  pythonExecutable?: string;
  robotCodeVersionString?: string;
}

interface RobotCodeContributions {
  contributes?: {
    robotCode?: {
      fileExtensions?: string[];
      languageIds?: string[];
    };
  };
}

/** Why a workspace folder's Python environment cannot run Robot Framework. */
export type RobotEnvironmentProblem = PythonEnvironmentProblem | "pythonTooOld" | "robotMissing" | "robotTooOld";

/**
 * What RobotCode knows about the Python environment of a workspace folder: `unknown` until something asked for it,
 * `checking` while a check runs, then `usable` or `unusable` with the problem.
 */
export interface RobotEnvironmentState {
  readonly state: "unknown" | "checking" | "usable" | "unusable";
  readonly problem?: RobotEnvironmentProblem;
  readonly environment?: ResolvedPythonEnvironment;
  readonly executable?: string;
  readonly version?: PythonVersion;
  readonly sysPrefix?: string;
  /** The Robot Framework version the check found. */
  readonly robotVersion?: string;
  /** A virtual environment in the folder that is known to the Python extension but not selected. */
  readonly venvCandidate?: string;
}

export interface RobotEnvironmentStateChangedEvent {
  readonly folder: vscode.WorkspaceFolder;
  readonly state: RobotEnvironmentState;
}

const UNKNOWN_ENVIRONMENT: RobotEnvironmentState = { state: "unknown" };

export function isRobotFrameworkProblem(problem: RobotEnvironmentProblem | undefined): boolean {
  return problem === "robotMissing" || problem === "robotTooOld";
}

function useVirtualEnvironmentAction(executable: string): string {
  return `Use ${path.basename(virtualEnvironmentDir(executable))}`;
}

function environmentActionLink(folder: vscode.WorkspaceFolder, label: string, action: EnvironmentAction): string {
  const args = encodeURIComponent(JSON.stringify([folder.uri.toString(), action]));
  return `[${label}](command:${ENVIRONMENT_ACTION_COMMAND}?${args})`;
}

// What a cancelled message was about: the problem and the virtual environment it offered, if any.
function cancelKey(state: RobotEnvironmentState): string {
  return `${state.problem ?? ""}:${state.venvCandidate ?? ""}`;
}

function usableEnvironmentMessage(folder: vscode.WorkspaceFolder, state: RobotEnvironmentState): string {
  const where =
    state.environment?.name !== undefined && !isFromSetting(state) ? state.environment.name : state.executable;
  const python = state.version !== undefined ? `Python ${formatPythonVersion(state.version)}` : "Python";
  const robot = state.robotVersion !== undefined ? `Robot Framework ${state.robotVersion}` : "Robot Framework";
  return `Environment for '${folder.name}' found: ${where ?? ""} with ${python} and ${robot}. RobotCode is ready.`;
}

function describeRobotEnvironmentState(state: RobotEnvironmentState): string {
  const version = state.version !== undefined ? ` Python ${formatPythonVersion(state.version)}` : "";
  const executable = state.executable !== undefined ? ` ${state.executable}` : "";
  return `${state.state}${state.problem !== undefined ? ` (${state.problem})` : ""}${executable}${version}`;
}

function isFromSetting(state: RobotEnvironmentState): boolean {
  return state.environment?.source === "setting";
}

function robotEnvironmentProblemMessage(folder: vscode.WorkspaceFolder, state: RobotEnvironmentState): string {
  const found = `Found a Robot Framework project in '${folder.name}', but `;
  const executable = state.executable !== undefined ? ` '${state.executable}'` : "";
  const version = state.version !== undefined ? ` ${formatPythonVersion(state.version)}` : "";
  const robotVersion = state.robotVersion !== undefined ? ` ${state.robotVersion}` : "";
  // the setting robotcode.python wins over the Python side, so the message names it
  const fromSetting = isFromSetting(state);
  const name = fromSetting ? undefined : state.environment?.name;
  const environment = fromSetting
    ? `the Python environment of the setting robotcode.python (${state.executable ?? ""})`
    : name !== undefined
      ? `the selected Python environment '${name}'`
      : "the selected Python environment";
  switch (state.problem) {
    case "noInterpreter":
      return `${found}no Python interpreter is selected for it.`;
    case "interpreterMissing":
      return fromSetting
        ? `${found}the interpreter${executable} of the setting robotcode.python no longer exists or cannot be started.`
        : `${found}its Python interpreter${executable} no longer exists or cannot be started.`;
    case "pythonTooOld":
      return fromSetting
        ? `${found}the Python${version} of the setting robotcode.python (${state.executable ?? ""}) is older than 3.10, which RobotCode needs.`
        : `${found}its Python${version} is older than 3.10, which RobotCode needs.`;
    case "robotTooOld":
      return `${found}the Robot Framework${robotVersion} in ${environment} is older than 5.0, which RobotCode needs. Update it.`;
    default:
      return `${found}${environment} has no Robot Framework. Install it into that environment.`;
  }
}

export class LanguageClientsManager {
  private clientsMutex = new Mutex();

  public readonly clients: Map<string, LanguageClient> = new Map();
  public readonly outputChannels: Map<string, vscode.LogOutputChannel> = new Map();

  private _disposables: vscode.Disposable;

  // The environment state per workspace folder (key: folder URI), the running check, the Robot Framework polling and
  // the pending looks after environment events.
  private readonly _environmentStates = new Map<string, RobotEnvironmentState>();
  private readonly _environmentChecks = new Map<string, Promise<RobotEnvironmentState>>();
  // Bumped by a reset: a check that started before does not publish its result.
  private readonly _environmentGenerations = new Map<string, number>();
  private readonly _environmentPollers = new Map<string, NodeJS.Timeout>();
  private readonly _environmentReconsiderTimers = new Map<string, NodeJS.Timeout>();
  private readonly _environmentReconsiders = new Map<string, Promise<void>>();
  private readonly _environmentReconsiderAgain = new Set<string>();
  // Folders whose callers want the environment message; the open message per folder, the pending request to show
  // it, the problem the user cancelled it for, when the user asked for a new check, and the folders switched off
  // for this session.
  private readonly _environmentNotifyWanted = new Set<string>();
  private readonly _environmentNotifications = new Map<string, EnvironmentNotification>();
  private readonly _environmentNotificationTimers = new Map<string, NodeJS.Timeout>();
  private readonly _environmentNotificationsCancelled = new Map<string, string>();
  private readonly _environmentRetriedAt = new Map<string, string>();
  // Folders whose message was shown: when they become usable, a short information message says so.
  private readonly _environmentMessageShown = new Set<string>();
  private readonly _foldersDisabledForSession = new Set<string>();

  private readonly _onClientStateChangedEmitter = new vscode.EventEmitter<ClientStateChangedEvent>();

  public get onClientStateChanged(): vscode.Event<ClientStateChangedEvent> {
    return this._onClientStateChangedEmitter.event;
  }

  private readonly _onRobotEnvironmentStateChangedEmitter =
    new vscode.EventEmitter<RobotEnvironmentStateChangedEvent>();

  /** Fires when a folder's environment check ends, with the usable or unusable state. */
  public get onRobotEnvironmentStateChanged(): vscode.Event<RobotEnvironmentStateChangedEvent> {
    return this._onRobotEnvironmentStateChangedEmitter.event;
  }

  private _supportedLanguages?: string[];
  private _fileExtensions?: string[];

  /**
   * Invalidate cached extension data when extensions change
   */
  private invalidateExtensionCaches(): void {
    this._supportedLanguages = undefined;
    this._fileExtensions = undefined;
  }

  /**
   * Helper method to collect extension contributions from all VS Code extensions
   */
  private static collectExtensionContributions(
    propertyPath: "languageIds" | "fileExtensions",
    defaultValues: string[],
  ): string[] {
    const result: string[] = [...defaultValues];

    vscode.extensions.all.forEach((extension) => {
      if (extension.packageJSON) {
        const ext = (extension.packageJSON as RobotCodeContributions)?.contributes?.robotCode?.[propertyPath];
        if (ext !== undefined) {
          result.push(...ext);
        }
      }
    });

    return result;
  }

  public get supportedLanguages(): string[] {
    if (this._supportedLanguages === undefined) {
      this._supportedLanguages = LanguageClientsManager.collectExtensionContributions("languageIds", [
        "robotframework",
      ]);
    }
    return this._supportedLanguages;
  }

  public get fileExtensions(): string[] {
    if (this._fileExtensions === undefined) {
      this._fileExtensions = LanguageClientsManager.collectExtensionContributions("fileExtensions", [
        "robot",
        "resource",
      ]);
    }
    return this._fileExtensions;
  }

  constructor(
    public readonly extensionContext: vscode.ExtensionContext,
    public readonly pythonManager: PythonManager,
    public readonly outputChannel: vscode.OutputChannel,
  ) {
    const fileWatcher1 = vscode.workspace.createFileSystemWatcher(
      `**/{pyproject.toml,robot.toml,.robot.toml,robocop.toml,.gitignore,.robotignore}`,
    );
    fileWatcher1.onDidCreate((uri) => this.restart(vscode.workspace.getWorkspaceFolder(uri)?.uri));
    fileWatcher1.onDidDelete((uri) => this.restart(vscode.workspace.getWorkspaceFolder(uri)?.uri));
    fileWatcher1.onDidChange((uri) => this.restart(vscode.workspace.getWorkspaceFolder(uri)?.uri));

    // Listen for extension changes to invalidate caches
    const extensionChangeListener = vscode.extensions.onDidChange(() => {
      this.logger.debug("Extensions changed, invalidating caches");
      this.invalidateExtensionCaches();
    });

    const virtualEnvironmentWatcher = vscode.workspace.createFileSystemWatcher("**/pyvenv.cfg", false, true, true);

    this._disposables = vscode.Disposable.from(
      fileWatcher1,
      extensionChangeListener,
      virtualEnvironmentWatcher,
      virtualEnvironmentWatcher.onDidCreate((uri) => {
        this.onVirtualEnvironmentCreated(uri).catch((error) => this.logger.error(`${error}`));
      }),
      this.pythonManager.onDidChangeEnvironment((event) => this.scheduleEnvironmentReconsider(event.folder)),
      this._onRobotEnvironmentStateChangedEmitter,

      vscode.workspace.onDidChangeWorkspaceFolders(async (event) => {
        for (const folder of event.removed) this.forgetFolder(folder);
        await this.refresh();
      }),
      vscode.workspace.onDidOpenTextDocument(async (document) => this.getLanguageClientForDocument(document)),
      vscode.commands.registerCommand(
        ENVIRONMENT_ACTION_COMMAND,
        async (folderUri: string, action: EnvironmentAction) => {
          const folder = vscode.workspace.getWorkspaceFolder(vscode.Uri.parse(folderUri));
          if (folder !== undefined) await this.runEnvironmentAction(folder, action);
        },
      ),
      vscode.commands.registerCommand("robotcode.restartLanguageServers", async (uri?: vscode.Uri) => {
        this.enableFoldersForSession(uri);
        await this.restart(uri);
      }),
      vscode.commands.registerCommand("robotcode.clearCacheRestartLanguageServers", async (uri?: vscode.Uri) => {
        this.enableFoldersForSession(uri);
        await this.clearCaches(uri);
        await this.restart(uri);
      }),
    );
  }

  private readonly logger = {
    info: (message: string) => this.outputChannel.appendLine(`[INFO] ${message}`),
    warn: (message: string) => this.outputChannel.appendLine(`[WARN] ${message}`),
    error: (message: string) => this.outputChannel.appendLine(`[ERROR] ${message}`),
    debug: (message: string) => this.outputChannel.appendLine(`[DEBUG] ${message}`),
  };

  public async clearCaches(uri?: vscode.Uri): Promise<void> {
    this.logger.info("Clearing language server caches...");

    if (uri !== undefined) {
      const client = await this.getLanguageClientForResource(uri);
      if (client) {
        try {
          await client.sendRequest("robot/cache/clear");
          this.logger.info(`Cache cleared for ${uri.toString()}`);
        } catch (error) {
          this.logger.error(`Failed to clear cache for ${uri.toString()}: ${error}`);
        }
      }
    } else {
      const clearPromises = Array.from(this.clients.values()).map(async (client) => {
        try {
          await client.sendRequest("robot/cache/clear");
        } catch (error) {
          this.logger.error(`Failed to clear cache for client: ${error}`);
        }
      });

      await Promise.allSettled(clearPromises);
      this.logger.info("Cache clearing completed for all clients");
    }
  }

  public async stopAllClients(): Promise<boolean> {
    const promises: Promise<void>[] = [];

    const clients = [...this.clients.values()];
    this.clients.clear();

    for (const client of clients) {
      promises.push(client.dispose(CLIENT_DISPOSE_TIMEOUT));
    }
    await sleep(CLIENT_SLEEP_DURATION);

    return Promise.all(promises).then(
      (r) => {
        return r.length > 0;
      },
      (reason) => {
        this.outputChannel.appendLine(`can't stop client ${reason}`);
        return true;
      },
    );
  }

  dispose(): void {
    this.stopAllClients().then(
      (_) => undefined,
      (error) => this.logger.error(`Error during dispose: ${error}`),
    );
    for (const timer of this._environmentPollers.values()) clearTimeout(timer);
    for (const timer of this._environmentReconsiderTimers.values()) clearTimeout(timer);
    for (const timer of this._environmentNotificationTimers.values()) clearTimeout(timer);
    for (const notification of this._environmentNotifications.values()) notification.close();
    this._disposables.dispose();
  }

  // eslint-disable-next-line class-methods-use-this
  private getServerOptionsTCP(folder: vscode.WorkspaceFolder) {
    const config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);
    let port = config.get<number>("languageServer.tcpPort", LANGUAGE_SERVER_DEFAULT_TCP_PORT);
    if (port === 0) {
      port = LANGUAGE_SERVER_DEFAULT_TCP_PORT;
    }
    const serverOptions: ServerOptions = function () {
      return new Promise((resolve, reject) => {
        const client = new net.Socket();
        client.on("error", (err) => {
          reject(err);
        });
        const host = LANGUAGE_SERVER_DEFAULT_HOST;
        client.connect(port, host, () => {
          resolve({
            reader: client,
            writer: client,
          });
        });
      });
    };
    return serverOptions;
  }

  /** The environment state of a workspace folder; `unknown` until something asked for it. */
  public getRobotEnvironmentState(folder: vscode.WorkspaceFolder): RobotEnvironmentState {
    return this._environmentStates.get(folder.uri.toString()) ?? UNKNOWN_ENVIRONMENT;
  }

  /**
   * Whether the last environment check of the folder found a problem. This never waits: a check that is running
   * keeps the problem it started with.
   */
  public isRobotEnvironmentKnownInvalid(folder: vscode.WorkspaceFolder): boolean {
    const state = this.getRobotEnvironmentState(folder);
    return state.state === "unusable" || (state.state === "checking" && state.problem !== undefined);
  }

  /**
   * Whether the folder's Python environment can run Robot Framework. The first call checks the environment, later
   * calls answer from the state until it is reset or the environment changes. With `notify`, a folder with a problem
   * gets its notification; callers that know the folder has Robot Framework files pass it.
   */
  public async isValidRobotEnvironmentInFolder(folder: vscode.WorkspaceFolder, notify = false): Promise<boolean> {
    if (this.isDisabledForFolder(folder)) return false;

    const key = folder.uri.toString();
    if (notify) this._environmentNotifyWanted.add(key);

    let state = this.getRobotEnvironmentState(folder);
    if (state.state === "unknown" || state.state === "checking") {
      state = await this.checkRobotEnvironment(folder);
    }

    if (state.state === "unusable" && notify) this.requestEnvironmentNotification(folder);

    return state.state === "usable";
  }

  // Runs the environment check of a folder, one at a time per folder; a second caller gets the running check.
  private checkRobotEnvironment(folder: vscode.WorkspaceFolder): Promise<RobotEnvironmentState> {
    const key = folder.uri.toString();
    let check = this._environmentChecks.get(key);
    if (check === undefined) {
      const started = this.doCheckRobotEnvironment(folder);
      check = started.finally(() => {
        if (this._environmentChecks.get(key) === check) this._environmentChecks.delete(key);
      });
      this._environmentChecks.set(key, check);
    }
    return check;
  }

  private async doCheckRobotEnvironment(folder: vscode.WorkspaceFolder): Promise<RobotEnvironmentState> {
    const key = folder.uri.toString();
    const generation = this._environmentGenerations.get(key) ?? 0;
    const previous = this.getRobotEnvironmentState(folder);
    this.setRobotEnvironmentState(folder, { ...previous, state: "checking" });

    let result: RobotEnvironmentState;
    try {
      result = await this.determineRobotEnvironment(folder);
    } catch (error) {
      this.logger.error(`checking the Python environment of folder '${folder.name}' failed: ${error}`);
      result = { state: "unusable", problem: "interpreterMissing" };
    }

    if ((this._environmentGenerations.get(key) ?? 0) !== generation) {
      this.logger.info(`Python environment of folder '${folder.name}': check superseded by a reset`);
      return result;
    }

    this.logger.info(`Python environment of folder '${folder.name}': ${describeRobotEnvironmentState(result)}`);
    this.setRobotEnvironmentState(folder, result);
    this.updateRobotFrameworkPolling(folder, result);
    return result;
  }

  private async determineRobotEnvironment(folder: vscode.WorkspaceFolder): Promise<RobotEnvironmentState> {
    const environment = await this.pythonManager.resolveEnvironment(folder);
    let result: RobotEnvironmentState;

    if (environment.problem !== undefined || environment.executable === undefined) {
      result = {
        state: "unusable",
        problem: environment.problem ?? "noInterpreter",
        environment,
        executable: environment.executable,
      };
    } else {
      const executable = environment.executable;
      let version = environment.version;
      let sysPrefix = environment.sysPrefix;
      if (version === undefined || sysPrefix === undefined) {
        const info = await this.pythonManager.queryInterpreter(executable);
        version ??= info?.version;
        sysPrefix ??= info?.sysPrefix;
      }

      if (version === undefined) {
        result = { state: "unusable", problem: "interpreterMissing", environment, executable, sysPrefix };
      } else if (version.major < 3 || (version.major === 3 && version.minor < 10)) {
        result = { state: "unusable", problem: "pythonTooOld", environment, executable, version, sysPrefix };
      } else {
        const robot = await this.pythonManager.checkRobotVersion(executable);
        if (robot.kind === "ok") {
          result = { state: "usable", environment, executable, version, sysPrefix, robotVersion: robot.version };
        } else if (robot.kind === "failed") {
          result = { state: "unusable", problem: "interpreterMissing", environment, executable, version, sysPrefix };
        } else {
          result = {
            state: "unusable",
            problem: robot.kind === "missing" ? "robotMissing" : "robotTooOld",
            environment,
            executable,
            version,
            sysPrefix,
            robotVersion: robot.version,
          };
        }
      }
    }

    if (result.state === "unusable" && !isFromSetting(result)) {
      result = {
        ...result,
        venvCandidate: await this.pythonManager.findVirtualEnvironmentCandidate(folder, result.executable),
      };
    }
    return result;
  }

  private setRobotEnvironmentState(folder: vscode.WorkspaceFolder, state: RobotEnvironmentState): void {
    this._environmentStates.set(folder.uri.toString(), state);
    if (state.state === "usable") {
      this._onRobotEnvironmentStateChangedEmitter.fire({ folder, state });
      this.closeEnvironmentNotification(folder);
      if (this._environmentMessageShown.delete(folder.uri.toString())) {
        void vscode.window.showInformationMessage(usableEnvironmentMessage(folder, state));
      }
    } else if (state.state === "unusable") {
      this._onRobotEnvironmentStateChangedEmitter.fire({ folder, state });
      this.requestEnvironmentNotification(folder);
    }
  }

  /** Forgets the environment state of a folder, or of all folders, so that the next use checks again. */
  private resetRobotEnvironmentState(folder?: vscode.WorkspaceFolder): void {
    this.pythonManager.forgetInterpreters();
    for (const f of folder !== undefined ? [folder] : (vscode.workspace.workspaceFolders ?? [])) {
      const key = f.uri.toString();
      this.stopRobotFrameworkPolling(f);
      this._environmentStates.delete(key);
      this._environmentChecks.delete(key);
      this._environmentRetriedAt.delete(key);
      this._environmentGenerations.set(key, (this._environmentGenerations.get(key) ?? 0) + 1);
    }
  }

  private forgetFolder(folder: vscode.WorkspaceFolder): void {
    const key = folder.uri.toString();
    this.stopRobotFrameworkPolling(folder);
    this.closeEnvironmentNotification(folder);
    clearTimeout(this._environmentReconsiderTimers.get(key));
    this._environmentReconsiderTimers.delete(key);
    this._environmentStates.delete(key);
    this._environmentNotifyWanted.delete(key);
    this._environmentNotificationsCancelled.delete(key);
    this._environmentRetriedAt.delete(key);
    this._environmentGenerations.delete(key);
    this._environmentMessageShown.delete(key);
    this._foldersDisabledForSession.delete(key);
  }

  /** Whether RobotCode is switched off for the folder, by `robotcode.disableExtension` or for this session. */
  public isDisabledForFolder(folder: vscode.WorkspaceFolder): boolean {
    return (
      this._foldersDisabledForSession.has(folder.uri.toString()) ||
      (vscode.workspace.getConfiguration(CONFIG_SECTION, folder).get<boolean>("disableExtension") ?? false)
    );
  }

  // Off for the session: until the window is reloaded or the restart commands run.
  private disableFolderForSession(folder: vscode.WorkspaceFolder): void {
    this._foldersDisabledForSession.add(folder.uri.toString());
    this.logger.info(`RobotCode switched off for folder '${folder.name}' for this session`);
    this.stopRobotFrameworkPolling(folder);
    this.closeEnvironmentNotification(folder);
    this._onRobotEnvironmentStateChangedEmitter.fire({ folder, state: this.getRobotEnvironmentState(folder) });
    // the Test Explorer drops the folder's run profiles on this event, as after a restart
    this._onClientStateChangedEmitter.fire({ uri: folder.uri, state: ClientState.Refreshed });
  }

  private enableFoldersForSession(uri?: vscode.Uri): void {
    const folder = uri !== undefined ? vscode.workspace.getWorkspaceFolder(uri) : undefined;
    for (const f of folder !== undefined ? [folder] : (vscode.workspace.workspaceFolders ?? [])) {
      this._foldersDisabledForSession.delete(f.uri.toString());
      this._environmentNotificationsCancelled.delete(f.uri.toString());
    }
  }

  // While Robot Framework is missing or too old, runs the check script every few seconds: it finds the package as
  // Python itself does (site-packages, user site, PYTHONPATH, .pth files), where a file watcher does not report files
  // deep inside a directory created while the window is open. Slower after five minutes, so that a folder left alone
  // costs little.
  private updateRobotFrameworkPolling(folder: vscode.WorkspaceFolder, state: RobotEnvironmentState): void {
    this.stopRobotFrameworkPolling(folder);
    const executable = state.executable;
    if (state.state !== "unusable" || !isRobotFrameworkProblem(state.problem) || executable === undefined) return;

    const key = folder.uri.toString();
    let attempts = 0;
    const schedule = (): void => {
      const timer = setTimeout(
        () => {
          attempts++;
          this.pythonManager
            .checkRobotVersion(executable)
            .then(async (robot) => {
              if (this._environmentPollers.get(key) !== timer) return;
              if (robot.kind !== "ok") {
                schedule();
                return;
              }
              this.logger.info(`Robot Framework ${robot.version ?? ""} appeared for '${executable}'`);
              this._environmentPollers.delete(key);
              await this.reconsiderFolder(folder);
            })
            .catch((error) => {
              this.logger.error(`checking Robot Framework for '${executable}' failed: ${error}`);
              if (this._environmentPollers.get(key) === timer) schedule();
            });
        },
        attempts < ROBOT_FRAMEWORK_POLL_FAST_ATTEMPTS
          ? ROBOT_FRAMEWORK_POLL_INTERVAL
          : ROBOT_FRAMEWORK_POLL_SLOW_INTERVAL,
      );
      this._environmentPollers.set(key, timer);
    };
    schedule();
  }

  private stopRobotFrameworkPolling(folder: vscode.WorkspaceFolder): void {
    const key = folder.uri.toString();
    const timer = this._environmentPollers.get(key);
    if (timer !== undefined) {
      clearTimeout(timer);
      this._environmentPollers.delete(key);
    }
  }

  // Environment events come in bursts; one look per folder after they settle is enough.
  private scheduleEnvironmentReconsider(folder: vscode.WorkspaceFolder | undefined): void {
    for (const f of folder !== undefined ? [folder] : (vscode.workspace.workspaceFolders ?? [])) {
      const key = f.uri.toString();
      if (!this._environmentStates.has(key) || this.isDisabledForFolder(f)) continue;

      clearTimeout(this._environmentReconsiderTimers.get(key));
      this._environmentReconsiderTimers.set(
        key,
        setTimeout(() => {
          this._environmentReconsiderTimers.delete(key);
          this.reconsiderFolder(f).catch((error) =>
            this.logger.error(`looking at the environment of '${f.name}' again failed: ${error}`),
          );
        }, ENVIRONMENT_EVENT_DEBOUNCE),
      );
    }
  }

  /**
   * Looks at a folder's environment again after something changed: a usable folder whose interpreter changed
   * restarts its language server, an unusable folder is checked again and gets its language server when it is
   * usable now.
   */
  private async reconsiderFolder(folder: vscode.WorkspaceFolder): Promise<void> {
    const key = folder.uri.toString();
    const running = this._environmentReconsiders.get(key);
    if (running !== undefined) {
      this._environmentReconsiderAgain.add(key);
      return running;
    }

    const run = (async () => {
      await this._environmentChecks.get(key);
      const previous = this._environmentStates.get(key);
      if (previous === undefined || previous.state === "unknown") return;
      if (this.isDisabledForFolder(folder)) return;

      if (previous.state === "usable") {
        const environment = await this.pythonManager.resolveEnvironment(folder);
        if (environment.problem === undefined && environment.executable === previous.executable) return;

        this.logger.info(`Python environment of folder '${folder.name}' changed, restarting its language server`);
        await this.restart(folder.uri);
        return;
      }

      const result = await this.checkRobotEnvironment(folder);
      if (result.state === "usable") await this.refresh(folder.uri, true);
    })().finally(() => this._environmentReconsiders.delete(key));
    this._environmentReconsiders.set(key, run);
    await run;

    if (this._environmentReconsiderAgain.delete(key)) await this.reconsiderFolder(folder);
  }

  private async onVirtualEnvironmentCreated(uri: vscode.Uri): Promise<void> {
    const folder = vscode.workspace.getWorkspaceFolder(uri);
    if (folder === undefined) return;

    this.logger.info(`virtual environment appeared: ${uri.fsPath}`);
    this.pythonManager.rememberVirtualEnvironment(uri);
    await this.pythonManager.refreshEnvironments(folder);
    await this.reconsiderFolder(folder);
  }

  private requestEnvironmentNotification(folder: vscode.WorkspaceFolder): void {
    const key = folder.uri.toString();
    clearTimeout(this._environmentNotificationTimers.get(key));
    this._environmentNotificationTimers.set(
      key,
      setTimeout(() => {
        this._environmentNotificationTimers.delete(key);
        this.updateEnvironmentNotification(folder);
      }, ENVIRONMENT_NOTIFICATION_DELAY),
    );
  }

  // Shows, replaces or closes the folder's environment message according to its state: one progress notification per
  // folder, which stays until the folder is usable or the user cancels it. Its actions are links, because a progress
  // notification is the only one code can close. No install action: which tool and which version a project wants (uv
  // sync, uv add, pip, poetry, conda, a pin in pyproject.toml or a lock file) is not ours to guess; the polling picks
  // up what the user installs.
  private updateEnvironmentNotification(folder: vscode.WorkspaceFolder): void {
    const key = folder.uri.toString();
    const state = this.getRobotEnvironmentState(folder);
    const open = this._environmentNotifications.get(key);
    if (
      state.state !== "unusable" ||
      !this._environmentNotifyWanted.has(key) ||
      this.isDisabledForFolder(folder) ||
      this._environmentNotificationsCancelled.get(key) === cancelKey(state)
    ) {
      open?.close();
      return;
    }

    const message = this.environmentNotificationMessage(folder, state);
    if (open !== undefined) {
      if (open.message !== message) open.report(message);
      return;
    }

    this.logger.warn(`environment message for folder '${folder.name}': ${describeRobotEnvironmentState(state)}`);
    this._environmentMessageShown.add(key);
    const notification: EnvironmentNotification = {
      message,
      report: (text) => {
        notification.message = text;
      },
      close: () => undefined,
    };
    this._environmentNotifications.set(key, notification);
    vscode.window
      .withProgress(
        { location: vscode.ProgressLocation.Notification, title: "RobotCode", cancellable: true },
        (progress, token) =>
          new Promise<void>((resolve) => {
            notification.report = (text) => {
              notification.message = text;
              progress.report({ message: text });
            };
            notification.close = resolve;
            progress.report({ message: notification.message });
            token.onCancellationRequested(() => {
              resolve();
              this.onEnvironmentNotificationCancelled(folder);
            });
          }),
      )
      .then(
        () => {
          if (this._environmentNotifications.get(key) === notification) this._environmentNotifications.delete(key);
        },
        (error) => this.logger.error(`environment message failed: ${error}`),
      );
  }

  private closeEnvironmentNotification(folder: vscode.WorkspaceFolder): void {
    const key = folder.uri.toString();
    clearTimeout(this._environmentNotificationTimers.get(key));
    this._environmentNotificationTimers.delete(key);
    this._environmentNotifications.get(key)?.close();
  }

  private environmentNotificationMessage(folder: vscode.WorkspaceFolder, state: RobotEnvironmentState): string {
    const links: string[] = [];
    if (isFromSetting(state)) {
      // selecting or creating an environment changes nothing while the setting wins
      links.push(environmentActionLink(folder, OPEN_SETTINGS, "settings"));
    } else {
      if (state.venvCandidate !== undefined) {
        links.push(environmentActionLink(folder, useVirtualEnvironmentAction(state.venvCandidate), "useVenv"));
      }
      links.push(
        environmentActionLink(folder, SELECT_ENVIRONMENT, "select"),
        environmentActionLink(folder, CREATE_ENVIRONMENT, "create"),
      );
    }
    links.push(environmentActionLink(folder, RETRY, "retry"));
    const retried = this._environmentRetriedAt.get(folder.uri.toString());
    const checked = retried !== undefined ? ` Checked again at ${retried}.` : "";
    return `${robotEnvironmentProblemMessage(folder, state)}${checked} ${links.join(" · ")}`;
  }

  // Cancel in the message: it stays closed for this problem (a virtual environment that appears afterwards opens it
  // again, because its Use .venv is new), and the user is asked whether to switch RobotCode off.
  private onEnvironmentNotificationCancelled(folder: vscode.WorkspaceFolder): void {
    const state = this.getRobotEnvironmentState(folder);
    if (state.problem !== undefined)
      this._environmentNotificationsCancelled.set(folder.uri.toString(), cancelKey(state));
    this.askToDisableFolder(folder).catch((error) => this.logger.error(`${error}`));
  }

  private async askToDisableFolder(folder: vscode.WorkspaceFolder): Promise<void> {
    if (!this.isRobotEnvironmentKnownInvalid(folder)) return;

    const choice = await vscode.window.showWarningMessage(
      `Switch RobotCode off for the folder '${folder.name}'? For this session: until the window is reloaded or the language servers are restarted. For this project: with the folder setting robotcode.disableExtension, until you remove it.`,
      DISABLE_FOR_SESSION,
      DISABLE_FOR_PROJECT,
    );
    if (choice === DISABLE_FOR_SESSION) {
      this.disableFolderForSession(folder);
    } else if (choice === DISABLE_FOR_PROJECT) {
      this.stopRobotFrameworkPolling(folder);
      this.closeEnvironmentNotification(folder);
      await vscode.workspace
        .getConfiguration(CONFIG_SECTION, folder)
        .update("disableExtension", true, vscode.ConfigurationTarget.WorkspaceFolder);
    }
  }

  private async runEnvironmentAction(folder: vscode.WorkspaceFolder, action: EnvironmentAction): Promise<void> {
    try {
      switch (action) {
        case "select":
          await this.selectPythonEnvironment(folder);
          break;
        case "create":
          await vscode.commands.executeCommand("python.createEnvironment", { workspaceFolder: folder });
          break;
        case "useVenv": {
          const state = this.getRobotEnvironmentState(folder);
          if (state.state !== "usable" && state.venvCandidate !== undefined) {
            await this.pythonManager.useVirtualEnvironment(folder, state.venvCandidate);
          }
          break;
        }
        case "retry":
          await this.retryEnvironment(folder);
          break;
        case "settings":
          await vscode.commands.executeCommand("workbench.action.openSettings", "robotcode.python");
          break;
      }
    } catch (error) {
      const label = {
        select: SELECT_ENVIRONMENT,
        create: CREATE_ENVIRONMENT,
        useVenv: "Use the virtual environment",
        retry: RETRY,
        settings: OPEN_SETTINGS,
      }[action];
      this.logger.error(`${label} failed: ${error}`);
      void vscode.window.showErrorMessage(`${label} failed: ${error}`);
    }
  }

  /** Checks the folder's environment again on the user's request, after asking the Python side to look for environments. */
  private async retryEnvironment(folder: vscode.WorkspaceFolder): Promise<void> {
    const key = folder.uri.toString();
    this._environmentNotificationsCancelled.delete(key);
    this._environmentNotifications.get(key)?.report("Checking the Python environment again…");
    await this.pythonManager.refreshEnvironments(folder);
    await this.restart(folder.uri);
    this._environmentRetriedAt.set(key, new Date().toLocaleTimeString());
    clearTimeout(this._environmentNotificationTimers.get(key));
    this._environmentNotificationTimers.delete(key);
    this.updateEnvironmentNotification(folder);
  }

  /** Opens the environment picker of the Python side for the folder; a selection comes back through its events. */
  public async selectPythonEnvironment(folder?: vscode.WorkspaceFolder): Promise<void> {
    if ((await this.pythonManager.getPythonEnvironmentsApi()) !== undefined) {
      try {
        await vscode.commands.executeCommand("python-envs.set", folder?.uri);
        return;
      } catch (error) {
        this.logger.warn(`python-envs.set failed, using python.setInterpreter: ${error}`);
      }
    }
    await vscode.commands.executeCommand("python.setInterpreter");
  }

  private async getServerOptions(folder: vscode.WorkspaceFolder, mode: string): Promise<ServerOptions | undefined> {
    const config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);

    if (!(await this.isValidRobotEnvironmentInFolder(folder, true))) return undefined;
    const pythonCommand = this.getRobotEnvironmentState(folder).executable;
    if (pythonCommand === undefined) return undefined;

    const robotCodeExtraArgs = config.get<string[]>("languageServer.extraArgs", []);

    const args: string[] = ["-u", "-X", "utf8", this.pythonManager.robotCodeMain];
    const serverArgs: string[] = [...robotCodeExtraArgs, "language-server"];

    const debug_args: string[] = ["--log"];

    const transport = { stdio: TransportKind.stdio, pipe: TransportKind.pipe, socket: TransportKind.socket }[mode];

    const getPort = async () => {
      return getAvailablePort(["127.0.0.1"]);
    };

    const profiles = config.get<string[]>("profiles", []).flatMap((v) => ["-p", v]);

    return {
      run: {
        command: pythonCommand,
        args: [...args, ...profiles, ...serverArgs],
        options: {
          cwd: folder.uri.fsPath,
        },

        transport:
          transport !== TransportKind.socket
            ? transport
            : { kind: TransportKind.socket, port: (await getPort()) ?? -1 },
      },
      debug: {
        command: pythonCommand,
        args: [...args, ...debug_args, ...profiles, ...serverArgs],
        options: {
          cwd: folder.uri.fsPath,
        },
        transport:
          transport !== TransportKind.socket
            ? transport
            : { kind: TransportKind.socket, port: (await getPort()) ?? -1 },
      },
    };
  }

  public async getLanguageClientForDocument(document: vscode.TextDocument): Promise<LanguageClient | undefined> {
    if (!this.supportedLanguages.includes(document.languageId)) return;

    return this.getLanguageClientForResource(document.uri);
  }

  public hasClientForResource(resource: string | vscode.Uri): boolean {
    const uri = resource instanceof vscode.Uri ? resource : vscode.Uri.parse(resource);
    const workspaceFolder = vscode.workspace.getWorkspaceFolder(uri);
    if (!workspaceFolder) return false;
    return this.clients.has(workspaceFolder.uri.toString());
  }

  public async getLanguageClientForResource(resource: string | vscode.Uri): Promise<LanguageClient | undefined> {
    return this.clientsMutex.dispatch(async () => {
      const uri = resource instanceof vscode.Uri ? resource : vscode.Uri.parse(resource);
      let workspaceFolder = vscode.workspace.getWorkspaceFolder(uri);

      if (!workspaceFolder) {
        if (vscode.workspace.workspaceFolders?.length === 1) {
          workspaceFolder = vscode.workspace.workspaceFolders[0];
        } else if (vscode.workspace.workspaceFolders?.length == 0) {
          workspaceFolder = undefined;
        } else {
          workspaceFolder = undefined;
        }
      }

      if (!workspaceFolder) return undefined;

      if (this.isDisabledForFolder(workspaceFolder)) {
        return undefined;
      }

      let result = this.clients.get(workspaceFolder.uri.toString());

      if (result) return result;

      const config = vscode.workspace.getConfiguration(CONFIG_SECTION, uri);

      const mode = config.get<string>("languageServer.mode", "pipe");

      const serverOptions: ServerOptions | undefined =
        mode === "tcp" ? this.getServerOptionsTCP(workspaceFolder) : await this.getServerOptions(workspaceFolder, mode);

      if (serverOptions === undefined) {
        return undefined;
      }

      const name = `RobotCode Language Server for folder ${workspaceFolder.name}`;
      const outputChannel = this.outputChannels.get(name) ?? vscode.window.createOutputChannel(name, { log: true });
      this.outputChannels.set(name, outputChannel);

      let closeHandlerAction = CloseAction.DoNotRestart;

      const clientOptions: LanguageClientOptions = {
        documentSelector:
          vscode.workspace.workspaceFolders?.length === 1
            ? this.supportedLanguages.flatMap((lang) => [
                { scheme: "file", language: lang },
                { scheme: "untitled", language: lang },
              ])
            : this.supportedLanguages.flatMap((lang) => [
                { scheme: "file", language: lang, pattern: `${workspaceFolder.uri.fsPath}/**/*` },
                { scheme: "untitled", language: lang, pattern: `${workspaceFolder.uri.fsPath}/**/*` },
              ]),
        synchronize: {
          configurationSection: [CONFIG_SECTION],
        },
        initializationOptions: {
          storageUri: this.extensionContext?.storageUri?.toString(),
          globalStorageUri: this.extensionContext?.globalStorageUri?.toString(),
          pythonPath: config.get<string[]>("robot.pythonPath", []),
          env: config.get<object>("robot.env", []),
          documentationViewerLinks: true,
          settings: { robotcode: config },
        },
        initializationFailedHandler: (error: ResponseError<InitializeError> | Error | undefined) => {
          if (error)
            void vscode.window // NOSONAR
              .showErrorMessage(error.message, { title: "Retry", id: "retry" })
              .then(async (item) => {
                if (item && item.id === "retry") {
                  await this.refresh();
                }
              });

          return false;
        },
        errorHandler: {
          error(error: Error, message: Message | undefined, _count: number | undefined): ErrorHandlerResult {
            outputChannel.appendLine(`language server error: ${error} (${message})`);
            return {
              action: ErrorAction.Continue,
              handled: true,
            };
          },

          closed(): CloseHandlerResult {
            return {
              action: closeHandlerAction,
            };
          },
        },
        // TODO: how we can start a language client on workspace level, not on folder level
        workspaceFolder,
        revealOutputChannelOn: RevealOutputChannelOn.Error, // TODO: should we make this configurable?
        outputChannel,
        outputChannelName: name,
        markdown: {
          // Only the links to the Documentation Viewer run; a command link of a library's documentation does not.
          isTrusted: { enabledCommands: ["robotcode.showInDocumentationViewer"] },
          supportHtml: true,
        },
        progressOnInitialization: true,
        middleware: {
          resolveCodeLens(
            this: void, // NOSONAR
            codeLens: vscode.CodeLens,
            token: vscode.CancellationToken,
            next: ResolveCodeLensSignature,
          ): vscode.ProviderResult<vscode.CodeLens> {
            const resolvedCodeLens = next(codeLens, token);

            const resolveFunc = (codeLensToFix: vscode.CodeLens): vscode.CodeLens => {
              if (codeLensToFix.command?.command === "editor.action.showReferences") {
                const args = codeLensToFix.command.arguments as [string, Position, Location[]];

                codeLensToFix.command.arguments = [
                  vscode.Uri.parse(args[0]),
                  new vscode.Position(args[1].line, args[1].character),
                  args[2].map((position) => {
                    return new vscode.Location(
                      vscode.Uri.parse(position.uri),
                      new vscode.Range(
                        position.range.start.line,
                        position.range.start.character,
                        position.range.end.line,
                        position.range.end.character,
                      ),
                    );
                  }),
                ];
              }

              return codeLensToFix;
            };

            if ((resolvedCodeLens as Thenable<vscode.CodeLens>).then) {
              return (resolvedCodeLens as Thenable<vscode.CodeLens>).then(resolveFunc);
            } else if (resolvedCodeLens as vscode.CodeLens) {
              return resolveFunc(resolvedCodeLens as vscode.CodeLens);
            }

            return resolvedCodeLens;
          },
        },
      };

      this.outputChannel.appendLine(`create Language client: ${name}`);
      result = new LanguageClient(
        `${LANGUAGE_CLIENT_PREFIX}${workspaceFolder.uri.toString()}`,
        name,
        serverOptions,
        clientOptions,
      );

      this.outputChannel.appendLine(`trying to start Language client: ${name}`);

      result.onDidChangeState((e) => {
        if (e.newState == State.Starting) {
          result?.diagnostics?.clear();

          this.outputChannel.appendLine(
            `client for ${result?.clientOptions.workspaceFolder?.uri ?? "unknown"} starting.`,
          );
        } else if (e.newState == State.Running) {
          this.outputChannel.appendLine(
            `client for ${result?.clientOptions.workspaceFolder?.uri ?? "unknown"} running.`,
          );
          closeHandlerAction = CloseAction.Restart;
        } else if (e.newState == State.Stopped) {
          this.outputChannel.appendLine(
            `client for ${result?.clientOptions.workspaceFolder?.uri ?? "unknown"} stopped.`,
          );
          if (workspaceFolder && this.clients.get(workspaceFolder.uri.toString()) !== result)
            closeHandlerAction = CloseAction.DoNotRestart;
        }

        this._onClientStateChangedEmitter.fire({
          uri: uri,
          state:
            e.newState === State.Starting
              ? ClientState.Starting
              : e.newState === State.Stopped
                ? ClientState.Stopped
                : ClientState.Running,
        });
      });

      const started = await result.start().then(
        (_) => {
          this.outputChannel.appendLine(
            `client for ${result?.clientOptions.workspaceFolder?.uri ?? "unknown"} started.`,
          );
          return true;
        },
        (reason) => {
          this.outputChannel.appendLine(
            `client  ${result?.clientOptions.workspaceFolder?.uri ?? "unknown"} error: ${reason}`,
          );
          return false;
        },
      );

      if (started) {
        this.clients.set(workspaceFolder.uri.toString(), result);
        this._onClientStateChangedEmitter.fire({
          uri: uri,
          state: ClientState.Ready,
        });
        return result;
      }

      return undefined;
    });
  }

  public async restart(uri?: vscode.Uri): Promise<void> {
    const folder = uri !== undefined ? vscode.workspace.getWorkspaceFolder(uri) : undefined;
    if (uri !== undefined && folder === undefined) return;

    this.resetRobotEnvironmentState(folder);
    await this.refresh(uri, true);
  }

  public async refresh(uri?: vscode.Uri, restart?: boolean): Promise<void> {
    await this.clientsMutex.dispatch(async () => {
      if (uri) {
        const workspaceFolder = vscode.workspace.getWorkspaceFolder(uri);

        if (!workspaceFolder) return;

        const client = this.clients.get(workspaceFolder.uri.toString());
        this.clients.delete(workspaceFolder.uri.toString());

        if (client) {
          await client.dispose(CLIENT_DISPOSE_TIMEOUT);
          await sleep(CLIENT_SLEEP_DURATION);
        }
      } else {
        if (await this.stopAllClients()) {
          await sleep(CLIENT_SLEEP_DURATION);
        }
      }
    });

    const folders = new Set<vscode.WorkspaceFolder>();

    if (uri !== undefined && restart) {
      const workspaceFolder = vscode.workspace.getWorkspaceFolder(uri);
      if (workspaceFolder) {
        folders.add(workspaceFolder);
      }
    }

    for (const document of vscode.workspace.textDocuments) {
      if (this.supportedLanguages.includes(document.languageId)) {
        const workspaceFolder = vscode.workspace.getWorkspaceFolder(document.uri);
        if (workspaceFolder) {
          folders.add(workspaceFolder);
        } else if (vscode.workspace.workspaceFolders?.length === 1) {
          folders.add(vscode.workspace.workspaceFolders[0]);
        }
      }
    }

    if (uri === undefined) {
      for (const f of vscode.workspace.workspaceFolders || []) {
        // a folder with an open Robot Framework document gets its client anyway
        if (!folders.has(f) && (await this.isRobotProject(f).catch(() => false))) {
          folders.add(f);
        }
      }
    }

    for (const folder of folders) {
      try {
        await this.getLanguageClientForResource(folder.uri.toString()).catch((_) => undefined);
        this._onClientStateChangedEmitter.fire({
          uri: folder.uri,
          state: ClientState.Refreshed,
        });
      } catch {
        // do noting
      }
    }
  }

  /**
   * Whether a workspace folder is a Robot Framework project: it has a `robot.toml` or `.robot.toml`, a
   * `pyproject.toml` or `requirements.txt` that depends on Robot Framework or RobotCode, or Robot Framework files
   * outside the folders that the search skips. A search that takes too long counts as no files; the client then
   * starts with the first opened Robot Framework document.
   */
  private async isRobotProject(folder: vscode.WorkspaceFolder): Promise<boolean> {
    const read = async (name: string): Promise<string> => {
      try {
        return new TextDecoder().decode(await vscode.workspace.fs.readFile(vscode.Uri.joinPath(folder.uri, name)));
      } catch {
        return "";
      }
    };

    const names = new Set((await vscode.workspace.fs.readDirectory(folder.uri)).map(([name]) => name));
    if (names.has("robot.toml") || names.has(".robot.toml")) return true;
    const pyproject = names.has("pyproject.toml") ? await read("pyproject.toml") : "";
    if (ROBOT_DEPENDENCY_IN_PYPROJECT.test(pyproject.replace(/^\s*#.*$/gm, ""))) return true;
    const requirements = names.has("requirements.txt") ? await read("requirements.txt") : "";
    if (ROBOT_REQUIREMENT.test(requirements)) return true;

    const cancellation = new vscode.CancellationTokenSource();
    const timeout = setTimeout(() => cancellation.cancel(), ROBOT_FILES_SEARCH_TIMEOUT);
    let files: vscode.Uri[] = [];
    let timedOut = false;
    try {
      files = await vscode.workspace.findFiles(
        new vscode.RelativePattern(folder, `**/*.{${this.fileExtensions.join(",")}}`),
        new vscode.RelativePattern(folder, ROBOT_FILES_SEARCH_EXCLUDE),
        1,
        cancellation.token,
      );
    } catch (error) {
      if (!cancellation.token.isCancellationRequested) throw error;
    } finally {
      timedOut = cancellation.token.isCancellationRequested;
      clearTimeout(timeout);
      cancellation.dispose();
    }
    if (timedOut) {
      this.outputChannel.appendLine(
        `Searching Robot Framework files in workspace folder '${folder.name}' took too long, ` +
          "its language server starts with the first opened Robot Framework document.",
      );
      return false;
    }

    return files.length > 0;
  }

  public async openUriInDocumentationView(uri: vscode.Uri): Promise<void> {
    const doc_uri = await this.convertToDocumentationUri(uri);
    if (doc_uri) {
      await vscode.commands.executeCommand("robotcode.showDocumentation", doc_uri.toString(true));
    } else {
      vscode.env.openExternal(uri).then(
        () => undefined,
        () => undefined,
      );
    }
  }

  public async openOutputFile(file: vscode.Uri): Promise<void> {
    const workspace = vscode.workspace.getWorkspaceFolder(file);
    const result = vscode.workspace.getConfiguration(CONFIG_SECTION, workspace).get<string>("run.openOutputTarget");

    switch (result) {
      case "simpleBrowser":
        await this.openUriInDocumentationView(file);
        break;
      case "externalHttp":
        await vscode.env.openExternal(
          await vscode.env.asExternalUri((await this.convertToDocumentationUri(file)) ?? file),
        );
        break;
      case "externalFile":
        await vscode.env.openExternal(file);
        break;
    }
  }

  public async convertToDocumentationUri(
    uri: vscode.Uri,
    token?: vscode.CancellationToken | undefined,
  ): Promise<vscode.Uri | undefined> {
    const client = await this.getLanguageClientForResource(uri);

    if (!client) return;

    return (
      vscode.Uri.parse(
        await client.sendRequest<string>(
          "robot/documentationServer/convertUri",
          {
            uri: uri.toString(),
          },
          token ?? new vscode.CancellationTokenSource().token,
        ),
      ) ?? undefined
    );
  }

  public async getEvaluatableExpression(
    document: vscode.TextDocument,
    position: Position,
    token?: vscode.CancellationToken | undefined,
  ): Promise<EvaluatableExpression | undefined> {
    const client = await this.getLanguageClientForResource(document.uri);

    if (!client) return;

    return (
      (await client.sendRequest<EvaluatableExpression | undefined>(
        "robot/debugging/getEvaluatableExpression",
        {
          textDocument: { uri: document.uri.toString() },
          position,
        },
        token ?? new vscode.CancellationTokenSource().token,
      )) ?? undefined
    );
  }

  public async getDocumentImports(
    document_or_uri: vscode.TextDocument | vscode.Uri | string,
    noDocumentation?: boolean | undefined,
    token?: vscode.CancellationToken | undefined,
  ): Promise<DocumentImport[]> {
    const uri =
      document_or_uri instanceof vscode.Uri
        ? document_or_uri
        : typeof document_or_uri === "string"
          ? vscode.Uri.parse(document_or_uri)
          : document_or_uri.uri;

    const client = await this.getLanguageClientForResource(uri);

    if (!client) return [];

    return (
      (await client.sendRequest<DocumentImport[]>(
        "robot/keywordsview/getDocumentImports",
        {
          textDocument: { uri: uri.toString() },
          noDocumentation: noDocumentation,
        },
        token ?? new vscode.CancellationTokenSource().token,
      )) ?? []
    );
  }

  public async getLibraryDocumentation(
    workspace_folder: vscode.WorkspaceFolder,
    libraryName: string,
    token?: vscode.CancellationToken | undefined,
  ): Promise<LibraryDocumentation | undefined> {
    const client = await this.getLanguageClientForResource(workspace_folder.uri);

    if (!client) return undefined;

    return (
      (await client.sendRequest<LibraryDocumentation>(
        "robot/keywordsview/getLibraryDocumentation",
        {
          workspaceFolderUri: workspace_folder.uri.toString(),
          libraryName: libraryName,
        },
        token ?? new vscode.CancellationTokenSource().token,
      )) ?? undefined
    );
  }

  public async getKeywordDocumentation(
    workspace_folder: vscode.WorkspaceFolder,
    libraryName: string,
    keywordName: string,
    token?: vscode.CancellationToken | undefined,
  ): Promise<Keyword | undefined> {
    const client = await this.getLanguageClientForResource(workspace_folder.uri);

    if (!client) return undefined;

    return (
      (await client.sendRequest<Keyword>(
        "robot/keywordsview/getKeywordDocumentation",
        {
          workspaceFolderUri: workspace_folder.uri.toString(),
          libraryName: libraryName,
          keywordName: keywordName,
        },
        token ?? new vscode.CancellationTokenSource().token,
      )) ?? undefined
    );
  }

  public async getDocumentKeywords(
    document: vscode.TextDocument,
    token?: vscode.CancellationToken | undefined,
  ): Promise<Keyword[]> {
    const client = await this.getLanguageClientForResource(document.uri);

    if (!client) return [];

    return (
      (await client.sendRequest<Keyword[]>(
        "robot/keywordsview/getDocumentKeywords",
        {
          textDocument: { uri: document.uri.toString() },
        },
        token ?? new vscode.CancellationTokenSource().token,
      )) ?? []
    );
  }

  public async getProjectInfo(
    workspaceFolder: vscode.WorkspaceFolder,
    token?: vscode.CancellationToken | undefined,
  ): Promise<ProjectInfo | undefined> {
    if (!this.hasClientForResource(workspaceFolder.uri)) return undefined;

    const client = await this.getLanguageClientForResource(workspaceFolder.uri);

    if (client === undefined) return undefined;

    return (
      (await client.sendRequest<ProjectInfo>(
        "robot/projectInfo",
        {},
        token ?? new vscode.CancellationTokenSource().token,
      )) ?? []
    );
  }

  public async getDocumentionUrl(
    document: vscode.TextDocument,
    importId?: string | undefined,
    keywordId?: string | undefined,
    token?: vscode.CancellationToken | undefined,
  ): Promise<string | undefined> {
    const client = await this.getLanguageClientForResource(document.uri);

    if (!client) return undefined;

    return (
      (await client.sendRequest<string | undefined>(
        "robot/keywordsview/getDocumentationUrl",
        {
          textDocument: { uri: document.uri.toString() },
          importId: importId,
          keywordId: keywordId,
        },
        token ?? new vscode.CancellationTokenSource().token,
      )) ?? undefined
    );
  }

  public async getDocumentationTarget(
    document: vscode.TextDocument,
    importId?: string | undefined,
    keywordId?: string | undefined,
    token?: vscode.CancellationToken | undefined,
  ): Promise<DocumentationTarget | undefined> {
    const client = await this.getLanguageClientForResource(document.uri);

    if (!client) return undefined;

    return (
      (await client.sendRequest<DocumentationTarget | undefined>(
        "robot/keywordsview/getDocumentationTarget",
        {
          textDocument: { uri: document.uri.toString() },
          importId: importId,
          keywordId: keywordId,
        },
        token ?? new vscode.CancellationTokenSource().token,
      )) ?? undefined
    );
  }
}
