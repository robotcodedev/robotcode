import * as net from "net";
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
import { PythonManager } from "./pythonmanger";
import { getAvailablePort } from "./net_utils";

const LANGUAGE_SERVER_DEFAULT_TCP_PORT = 6610;
const LANGUAGE_SERVER_DEFAULT_HOST = "127.0.0.1";

// Language Server Configuration Constants
const CLIENT_DISPOSE_TIMEOUT = 5000;
const CLIENT_SLEEP_DURATION = 500;
const LANGUAGE_CLIENT_PREFIX = "$robotCode:";

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

export interface EvaluatableExpression {
  range: Range;
  expression?: string;
}

export interface InlineValueText {
  type: "text";
  readonly range: Range;
  readonly text: string;
}

export interface InlineValueVariableLookup {
  type: "variable";
  readonly range: Range;
  readonly variableName?: string;
  readonly caseSensitiveLookup: boolean;
}

export interface InlineValueEvaluatableExpression {
  type: "expression";
  readonly range: Range;
  readonly expression?: string;
}

export type InlineValue = InlineValueText | InlineValueVariableLookup | InlineValueEvaluatableExpression;

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

interface DiscoverInfoResult {
  robot_version_string?: string;
  python_version_string?: string;
  executable?: string;
  machine?: string;
  platform?: string;
  system?: string;
  system_version?: string;
  [key: string]: string | undefined;
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

export class LanguageClientsManager {
  private clientsMutex = new Mutex();
  private _pythonValidPythonAndRobotEnvMutex = new Mutex();

  public readonly clients: Map<string, LanguageClient> = new Map();
  public readonly outputChannels: Map<string, vscode.OutputChannel> = new Map();

  private _disposables: vscode.Disposable;
  public _pythonCanceledPythonAndRobotEnv = new WeakMap<vscode.WorkspaceFolder, boolean>();
  public _pythonValidPythonAndRobotEnv = new WeakMap<vscode.WorkspaceFolder, boolean>();
  private _workspaceFolderDiscoverInfo = new WeakMap<vscode.WorkspaceFolder, DiscoverInfoResult>();

  private readonly _onClientStateChangedEmitter = new vscode.EventEmitter<ClientStateChangedEvent>();

  public get onClientStateChanged(): vscode.Event<ClientStateChangedEvent> {
    return this._onClientStateChangedEmitter.event;
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
      `**/{pyproject.toml,robot.toml,.robot.toml,robocop.toml,.gitignore,.robotignore,robocop.toml}`,
    );
    fileWatcher1.onDidCreate((uri) => this.restart(vscode.workspace.getWorkspaceFolder(uri)?.uri));
    fileWatcher1.onDidDelete((uri) => this.restart(vscode.workspace.getWorkspaceFolder(uri)?.uri));
    fileWatcher1.onDidChange((uri) => this.restart(vscode.workspace.getWorkspaceFolder(uri)?.uri));

    // Listen for extension changes to invalidate caches
    const extensionChangeListener = vscode.extensions.onDidChange(() => {
      this.logger.debug("Extensions changed, invalidating caches");
      this.invalidateExtensionCaches();
    });

    this._disposables = vscode.Disposable.from(
      fileWatcher1,
      extensionChangeListener,

      this.pythonManager.onActivePythonEnvironmentChanged(async (event) => {
        if (event.resource !== undefined) {
          this.inselectPythonEnvironment = true;

          this._workspaceFolderDiscoverInfo.delete(event.resource);
          this._pythonValidPythonAndRobotEnv.delete(event.resource);
          this._pythonCanceledPythonAndRobotEnv.delete(event.resource);
          this.selectPythonEnvironmentCancelTokenSource?.cancel();
          await this.refresh(event.resource.uri, true);
        } else {
          this._pythonValidPythonAndRobotEnv = new WeakMap<vscode.WorkspaceFolder, boolean>();
          this._pythonCanceledPythonAndRobotEnv = new WeakMap<vscode.WorkspaceFolder, boolean>();

          await this.restart();
        }
      }),

      vscode.workspace.onDidChangeWorkspaceFolders(async (_event) => this.refresh()),
      vscode.workspace.onDidOpenTextDocument(async (document) => this.getLanguageClientForDocument(document)),
      vscode.commands.registerCommand(
        "robotcode.restartLanguageServers",
        async (uri?: vscode.Uri) => await this.restart(uri),
      ),
      vscode.commands.registerCommand("robotcode.clearCacheRestartLanguageServers", async (uri?: vscode.Uri) => {
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

  private inselectPythonEnvironment = false;
  private selectPythonEnvironmentCancelTokenSource: vscode.CancellationTokenSource | undefined;

  public async selectPythonEnvironment(
    title: string,
    folder?: vscode.WorkspaceFolder,
    showRetry: boolean = true,
  ): Promise<void> {
    this.selectPythonEnvironmentCancelTokenSource?.cancel();

    if (folder !== undefined) {
      this._pythonCanceledPythonAndRobotEnv.set(folder, false);
    }

    this.inselectPythonEnvironment = false;
    this.selectPythonEnvironmentCancelTokenSource = new vscode.CancellationTokenSource();

    this.outputChannel.appendLine(`${title}`);

    const item = await vscode.window.showQuickPick(
      [
        {
          id: "select",
          label: "Select Python Interpreter...",
          detail:
            "Choose a Python interpreter version 3.8 or newer that has `robotframework` version 4.1 or higher installed",
        },
        {
          id: "create",
          label: "Create Virtual Environment...",
          detail: "Create a new virtual Python environment",
        },
        ...(showRetry
          ? [
              {
                id: "retry",
                label: "Retry",
                detail:
                  "Install `robotframework` version 4.1 or higher manually in the current environment, then restart the language server",
              },
              { id: "ignore", label: "Ignore", detail: "Ignore this at the moment" },
            ]
          : []),
      ],
      { title: title, placeHolder: "Choose an option...", ignoreFocusOut: true },
      this.selectPythonEnvironmentCancelTokenSource.token,
    );

    switch (item?.id) {
      case "create":
        await vscode.commands.executeCommand("python.createEnvironment");
        break;
      case "select":
        await vscode.commands.executeCommand("python.setInterpreter");
        break;
      case "retry":
        return;
      default:
        if (!showRetry) return;
    }

    if (folder !== undefined && !this.inselectPythonEnvironment) {
      this._pythonCanceledPythonAndRobotEnv.set(folder, true);

      throw new Error(`Select Python Interpreter for folder '${folder.name}' canceled.`);
    }
  }

  public async isValidRobotEnvironmentInFolder(
    folder: vscode.WorkspaceFolder,
    showDialogs?: boolean,
  ): Promise<boolean> {
    return this._pythonValidPythonAndRobotEnvMutex.dispatch(async () => {
      if (this._pythonCanceledPythonAndRobotEnv.has(folder)) {
        return false;
      }

      let result = false;
      while (!result) {
        result = await this._isValidRobotEnvironmentInFolder(folder, showDialogs);
        if (!showDialogs) break;
      }

      return result;
    });
  }

  public async _isValidRobotEnvironmentInFolder(
    folder: vscode.WorkspaceFolder,
    showDialogs?: boolean,
  ): Promise<boolean> {
    if (this._pythonValidPythonAndRobotEnv.has(folder)) {
      const r = this._pythonValidPythonAndRobotEnv.get(folder) ?? false;
      if (r || !showDialogs) {
        return r;
      }
    }

    const pythonCommand = await this.pythonManager.getPythonCommand(folder);
    if (!pythonCommand) {
      this._pythonValidPythonAndRobotEnv.set(folder, false);
      if (showDialogs) {
        await this.selectPythonEnvironment(
          `Can't find a valid python executable for workspace folder '${folder.name}'`,
          folder,
        );
      }

      return false;
    }

    if (!this.pythonManager.checkPythonVersion(pythonCommand)) {
      this._pythonValidPythonAndRobotEnv.set(folder, false);
      if (showDialogs) {
        await this.selectPythonEnvironment(`Invalid python version for workspace folder '${folder.name}'`, folder);
      }

      return false;
    }

    const robotCheck = this.pythonManager.checkRobotVersion(pythonCommand);
    if (robotCheck === undefined) {
      this._pythonValidPythonAndRobotEnv.set(folder, false);

      if (showDialogs) {
        await this.selectPythonEnvironment(
          `Robot Framework package not found in workspace folder '${folder.name}'.`,
          folder,
        );
      }

      return false;
    }

    if (robotCheck === false) {
      this._pythonValidPythonAndRobotEnv.set(folder, false);

      if (showDialogs) {
        await this.selectPythonEnvironment(
          `Robot Framework version in workspace folder '${folder.name}' not supported.`,
          folder,
        );
      }

      return false;
    }

    this._pythonValidPythonAndRobotEnv.set(folder, true);

    return true;
  }

  private async getServerOptions(folder: vscode.WorkspaceFolder, mode: string): Promise<ServerOptions | undefined> {
    const config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);

    try {
      if (!(await this.isValidRobotEnvironmentInFolder(folder, true))) return undefined;
    } catch {
      return undefined;
    }
    const pythonCommand = await this.pythonManager.getPythonCommand(folder);
    if (!pythonCommand) return undefined;

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
      const outputChannel = this.outputChannels.get(name) ?? vscode.window.createOutputChannel(name);
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
          isTrusted: true,
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
    this._pythonValidPythonAndRobotEnv = new WeakMap<vscode.WorkspaceFolder, boolean>();
    this._workspaceFolderDiscoverInfo = new WeakMap<vscode.WorkspaceFolder, DiscoverInfoResult>();
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
        const robotFiles = await vscode.workspace.findFiles(
          new vscode.RelativePattern(f, `**/*.{${this.fileExtensions.join(",")}}}`),
          undefined,
          1,
        );
        if (robotFiles.length > 0) {
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

  public async getInlineValues(
    document: vscode.TextDocument,
    viewPort: vscode.Range,
    context: vscode.InlineValueContext,
    token?: vscode.CancellationToken | undefined,
  ): Promise<InlineValue[]> {
    const client = await this.getLanguageClientForResource(document.uri);

    if (!client) return [];

    return (
      (await client.sendRequest<InlineValue[]>(
        "robot/debugging/getInlineValues",
        {
          textDocument: { uri: document.uri.toString() },
          viewPort: { start: viewPort.start, end: viewPort.end },
          context: {
            frameId: context.frameId,
            stoppedLocation: { start: context.stoppedLocation.start, end: context.stoppedLocation.end },
          },
        },
        token ?? new vscode.CancellationTokenSource().token,
      )) ?? []
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
}
