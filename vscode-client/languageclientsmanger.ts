/* eslint-disable @typescript-eslint/restrict-template-expressions */
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

export function toVsCodeRange(range: Range): vscode.Range {
  return new vscode.Range(
    new vscode.Position(range.start.line, range.start.character),
    new vscode.Position(range.end.line, range.end.character)
  );
}

export interface RobotTestItem {
  type: string;
  id: string;
  uri?: string;
  children: RobotTestItem[] | undefined;
  label: string;
  longname: string;
  description?: string;
  range?: Range;
  error?: string;
  tags?: string[];
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
}

export interface ClientStateChangedEvent {
  uri: vscode.Uri;
  state: ClientState;
}

export class LanguageClientsManager {
  private clientsMutex = new Mutex();

  public readonly clients: Map<string, LanguageClient> = new Map();
  public readonly outputChannels: Map<string, vscode.OutputChannel> = new Map();

  private _disposables: vscode.Disposable;
  private _pythonValidPythonAndRobotEnv = new WeakMap<vscode.WorkspaceFolder, boolean>();

  private readonly _onClientStateChangedEmitter = new vscode.EventEmitter<ClientStateChangedEvent>();

  public get onClientStateChanged(): vscode.Event<ClientStateChangedEvent> {
    return this._onClientStateChangedEmitter.event;
  }

  constructor(
    public readonly extensionContext: vscode.ExtensionContext,
    public readonly pythonManager: PythonManager,
    public readonly outputChannel: vscode.OutputChannel
  ) {
    this._disposables = vscode.Disposable.from(
      this.pythonManager.pythonExtension?.exports.settings.onDidChangeExecutionDetails(async (uri) => {
        if (uri !== undefined) {
          const folder = vscode.workspace.getWorkspaceFolder(uri);
          let needsRestart = false;
          if (folder !== undefined) {
            needsRestart = this._pythonValidPythonAndRobotEnv.has(folder);
            if (needsRestart) this._pythonValidPythonAndRobotEnv.delete(folder);
          }
          await this.refresh(uri, needsRestart);
        } else {
          await this.restart();
        }
      }) ?? {
        dispose() {
          //empty
        },
      },
      vscode.workspace.onDidChangeWorkspaceFolders(async (_event) => this.refresh()),
      vscode.workspace.onDidOpenTextDocument(async (document) => this.getLanguageClientForDocument(document))
    );
  }

  public async stopAllClients(): Promise<boolean> {
    const promises: Promise<void>[] = [];

    const clients = [...this.clients.values()];
    this.clients.clear();

    for (const client of clients) {
      promises.push(client.stop(5000));
    }

    return Promise.all(promises).then(
      (r) => {
        return r.length > 0;
      },
      (reason) => {
        this.outputChannel.appendLine(`can't stop client ${reason}`);
        return true;
      }
    );
  }

  dispose(): void {
    this.stopAllClients().then(
      (_) => undefined,
      (_) => undefined
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

  private showErrorWithSelectPythonInterpreter(msg: string) {
    this.outputChannel.appendLine(msg);
    void vscode.window.showErrorMessage(msg, { title: "Select Python Interpreter", id: "select" }).then((item) => {
      if (item && item.id === "select") {
        void vscode.commands.executeCommand("python.setInterpreter");
      }
    });
  }

  private async getServerOptions(folder: vscode.WorkspaceFolder, mode: string): Promise<ServerOptions | undefined> {
    const config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);

    const pythonCommand = this.pythonManager.getPythonCommand(folder);

    const envOk = this._pythonValidPythonAndRobotEnv.get(folder);
    if (envOk === false) return undefined;

    if (!pythonCommand) {
      this._pythonValidPythonAndRobotEnv.set(folder, false);

      this.showErrorWithSelectPythonInterpreter(
        `Can't find a valid python executable for workspace folder '${folder.name}'. ` +
          "Check if python and the python extension is installed."
      );

      return undefined;
    }

    if (!this.pythonManager.checkPythonVersion(pythonCommand)) {
      this._pythonValidPythonAndRobotEnv.set(folder, false);

      this.showErrorWithSelectPythonInterpreter(
        `Invalid python version for workspace folder '${folder.name}'. Only python version >= 3.8 supported. ` +
          "Please update to a newer python version or select a valid python environment."
      );

      return undefined;
    }

    const robotCheck = this.pythonManager.checkRobotVersion(pythonCommand);
    if (robotCheck === undefined) {
      this._pythonValidPythonAndRobotEnv.set(folder, false);

      this.showErrorWithSelectPythonInterpreter(
        `Robot Framework package not found in workspace folder '${folder.name}'. ` +
          "Please install Robot Framework >= Version 4.0 to the current python environment or select a valid python environment."
      );

      return undefined;
    }

    if (robotCheck === false) {
      this._pythonValidPythonAndRobotEnv.set(folder, false);

      this.showErrorWithSelectPythonInterpreter(
        `Robot Framework version in workspace folder '${folder.name}' not supported. Only Robot Framework version >= 4.0.0 supported. ` +
          "Please install or update Robot Framework >= Version 4.0 to the current python environment or select a valid python environment."
      );

      return undefined;
    }

    this._pythonValidPythonAndRobotEnv.set(folder, true);

    const serverArgs = config.get<string[]>("languageServer.args", []);

    const args: string[] = ["-u", this.pythonManager.pythonLanguageServerMain];

    const debug_args: string[] = ["--log"];

    const transport = { stdio: TransportKind.stdio, pipe: TransportKind.pipe, socket: TransportKind.socket }[mode];

    const getPort = async () => {
      return getAvailablePort(["127.0.0.1"]);
    };

    return {
      run: {
        command: pythonCommand,
        args: [...args, ...serverArgs],
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
        args: [...args, ...debug_args, ...serverArgs],
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
    if (document.languageId !== "robotframework") return;

    return this.getLanguageClientForResource(document.uri);
  }

  public async getLanguageClientForResource(
    resource: string | vscode.Uri,
    create = true
  ): Promise<LanguageClient | undefined> {
    return this.clientsMutex.dispatch(async () => {
      const uri = resource instanceof vscode.Uri ? resource : vscode.Uri.parse(resource);
      let workspaceFolder = vscode.workspace.getWorkspaceFolder(uri);

      if (!workspaceFolder || !create) {
        if (vscode.workspace.workspaceFolders?.length === 1) {
          workspaceFolder = vscode.workspace.workspaceFolders[0];
        } else if (vscode.workspace.workspaceFolders?.length == 0) {
          workspaceFolder = undefined;
        } else {
          workspaceFolder = undefined;
        }
      }

      if (!workspaceFolder || !create) return undefined;

      let result = this.clients.get(workspaceFolder.uri.toString());

      if (result) return result;

      const config = vscode.workspace.getConfiguration(CONFIG_SECTION, uri);

      const mode = config.get<string>("languageServer.mode", "pipe");

      const serverOptions: ServerOptions | undefined =
        mode === "tcp" ? this.getServerOptionsTCP(workspaceFolder) : await this.getServerOptions(workspaceFolder, mode);

      if (serverOptions === undefined) {
        return undefined;
      }

      const name = `RobotCode Language Server mode=${mode} for folder "${workspaceFolder.name}"`;

      const outputChannel = this.outputChannels.get(name) ?? vscode.window.createOutputChannel(name);
      this.outputChannels.set(name, outputChannel);

      let closeHandlerAction = CloseAction.DoNotRestart;

      const clientOptions: LanguageClientOptions = {
        documentSelector:
          vscode.workspace.workspaceFolders?.length === 1
            ? [{ scheme: "file", language: "robotframework" }]
            : [{ scheme: "file", language: "robotframework", pattern: `${workspaceFolder.uri.fsPath}/**/*` }],
        synchronize: {
          configurationSection: [CONFIG_SECTION],
        },
        initializationOptions: {
          storageUri: this.extensionContext?.storageUri?.toString(),
          globalStorageUri: this.extensionContext?.globalStorageUri?.toString(),
        },
        revealOutputChannelOn: RevealOutputChannelOn.Never, // TODO: should we make this configurable?
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
          error(_error: Error, _message: Message | undefined, _count: number | undefined): ErrorHandlerResult {
            return {
              action: ErrorAction.Continue,
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
        outputChannel,
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
            next: ResolveCodeLensSignature
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
                        position.range.end.character
                      )
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
      result = new LanguageClient(`$robotCode:${workspaceFolder.uri.toString()}`, name, serverOptions, clientOptions);

      this.outputChannel.appendLine(`trying to start Language client: ${name}`);

      result.onDidChangeState((e) => {
        if (e.newState == State.Starting) {
          result?.diagnostics?.clear();

          this.outputChannel.appendLine(
            `client for ${result?.clientOptions.workspaceFolder?.uri ?? "unknown"} starting.`
          );
        } else if (e.newState == State.Running) {
          this.outputChannel.appendLine(
            `client for ${result?.clientOptions.workspaceFolder?.uri ?? "unknown"} running.`
          );
          closeHandlerAction = CloseAction.Restart;
        } else if (e.newState == State.Stopped) {
          this.outputChannel.appendLine(
            `client for ${result?.clientOptions.workspaceFolder?.uri ?? "unknown"} stopped.`
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
            `client for ${result?.clientOptions.workspaceFolder?.uri ?? "unknown"} started.`
          );
          return true;
        },
        (reason) => {
          this.outputChannel.appendLine(
            `client  ${result?.clientOptions.workspaceFolder?.uri ?? "unknown"} error: ${reason}`
          );
          return false;
        }
      );

      if (started) {
        this.clients.set(workspaceFolder.uri.toString(), result);
        return result;
      }

      return undefined;
    });
  }

  public async restart(uri?: vscode.Uri): Promise<void> {
    this._pythonValidPythonAndRobotEnv = new WeakMap<vscode.WorkspaceFolder, boolean>();
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
          await client.stop(5000);
          await sleep(500);
        }
      } else {
        if (await this.stopAllClients()) {
          await sleep(500);
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
      if (document.languageId === "robotframework") {
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
          new vscode.RelativePattern(f, "**/*.{robot,resource}"),
          undefined,
          1
        );
        if (robotFiles.length > 0) {
          folders.add(f);
        }
      }
    }

    for (const folder of folders) {
      try {
        await this.getLanguageClientForResource(folder.uri.toString()).catch((_) => undefined);
      } catch {
        // do noting
      }
    }
  }

  public async getTestsFromWorkspace(
    workspaceFolder: vscode.WorkspaceFolder,
    paths?: string[],
    suites?: string[],
    token?: vscode.CancellationToken
  ): Promise<RobotTestItem[] | undefined> {
    const robotFiles = await vscode.workspace.findFiles(
      new vscode.RelativePattern(workspaceFolder, "**/*.robot"),
      undefined,
      1,
      token
    );

    if (robotFiles.length === 0) {
      return undefined;
    }

    const client = await this.getLanguageClientForResource(workspaceFolder.uri);

    if (!client) return;

    return (
      (token
        ? await client.sendRequest<RobotTestItem[]>(
            "robot/discovering/getTestsFromWorkspace",
            {
              workspaceFolder: workspaceFolder.uri.toString(),
              paths: paths,
              suites,
            },
            token
          )
        : await client.sendRequest<RobotTestItem[]>("robot/discovering/getTestsFromWorkspace", {
            workspaceFolder: workspaceFolder.uri.toString(),
            paths: paths,
          })) ?? undefined
    );
  }

  public async getTestsFromDocument(
    document: vscode.TextDocument,
    base_name?: string,
    token?: vscode.CancellationToken
  ): Promise<RobotTestItem[] | undefined> {
    const client = await this.getLanguageClientForResource(document.uri);

    if (!client) return;

    return (
      (token
        ? await client.sendRequest<RobotTestItem[]>(
            "robot/discovering/getTestsFromDocument",
            {
              textDocument: { uri: document.uri.toString() },
              base_name: base_name,
            },
            token
          )
        : await client.sendRequest<RobotTestItem[]>("robot/discovering/getTestsFromDocument", {
            textDocument: { uri: document.uri.toString() },
            base_name: base_name,
          })) ?? undefined
    );
  }

  public async openUriInDocumentationView(uri: vscode.Uri): Promise<void> {
    const doc_uri = await this.convertToDocumententationUri(uri);
    if (doc_uri) {
      await vscode.commands.executeCommand("robotcode.showDocumentation", doc_uri.toString(true));
    } else {
      vscode.env.openExternal(uri).then(
        () => undefined,
        () => undefined
      );
    }
  }

  public async convertToDocumententationUri(
    uri: vscode.Uri,
    token?: vscode.CancellationToken
  ): Promise<vscode.Uri | undefined> {
    const client = await this.getLanguageClientForResource(uri);

    if (!client) return;

    return (
      (token
        ? vscode.Uri.parse(
            await client.sendRequest<string>(
              "robot/documentationServer/convertUri",
              {
                uri: uri.toString(),
              },
              token
            )
          )
        : vscode.Uri.parse(
            await client.sendRequest<string>("robot/documentationServer/convertUri", {
              uri: uri.toString(),
            })
          )) ?? undefined
    );
  }

  public async getEvaluatableExpression(
    document: vscode.TextDocument,
    position: Position,
    token?: vscode.CancellationToken
  ): Promise<EvaluatableExpression | undefined> {
    const client = await this.getLanguageClientForResource(document.uri);

    if (!client) return;

    return (
      (token
        ? await client.sendRequest<EvaluatableExpression | undefined>(
            "robot/debugging/getEvaluatableExpression",
            {
              textDocument: { uri: document.uri.toString() },
              position,
            },
            token
          )
        : await client.sendRequest<EvaluatableExpression | undefined>("robot/debugging/getEvaluatableExpression", {
            textDocument: { uri: document.uri.toString() },
            position,
          })) ?? undefined
    );
  }

  public async getInlineValues(
    document: vscode.TextDocument,
    viewPort: vscode.Range,
    context: vscode.InlineValueContext,
    token?: vscode.CancellationToken
  ): Promise<InlineValue[]> {
    const client = await this.getLanguageClientForResource(document.uri);

    if (!client) return [];

    return (
      (token
        ? await client.sendRequest<InlineValue[]>(
            "robot/debugging/getInlineValues",
            {
              textDocument: { uri: document.uri.toString() },
              viewPort: { start: viewPort.start, end: viewPort.end },
              context: {
                frameId: context.frameId,
                stoppedLocation: { start: context.stoppedLocation.start, end: context.stoppedLocation.end },
              },
            },
            token
          )
        : await client.sendRequest<InlineValue[]>("robot/debugging/getInlineValues", {
            textDocument: { uri: document.uri.toString() },
            viewPort: { start: viewPort.start, end: viewPort.end },
            context: {
              frameId: context.frameId,
              stoppedLocation: { start: context.stoppedLocation.start, end: context.stoppedLocation.end },
            },
          })) ?? []
    );
  }
}
