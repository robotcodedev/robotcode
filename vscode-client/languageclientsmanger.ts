import * as net from "net";
import * as vscode from "vscode";
import { LanguageClient, LanguageClientOptions, ServerOptions } from "vscode-languageclient/node";
import { sleep, Mutex } from "./utils";
import { CONFIG_SECTION } from "./config";
import { PythonManager } from "./pythonmanger";

const LANGUAGE_SERVER_DEFAULT_TCP_PORT = 6610;
const LANGUAGE_SERVER_DEFAULT_HOST = "127.0.0.1";

export interface RobotPosition {
  line: number;
  character: number;
}

export interface RobotRange {
  start: RobotPosition;
  end: RobotPosition;
}

export interface RobotTestItem {
  type: string;
  id: string;
  uri?: string;
  children: RobotTestItem[] | undefined;
  label: string;
  description?: string;
  range?: RobotRange;
  error?: string;
}

export class LanguageClientsManager {
  private clientsMutex = new Mutex();

  public readonly clients: Map<string, LanguageClient> = new Map();

  private _disposables: vscode.Disposable;

  constructor(
    public readonly extensionContext: vscode.ExtensionContext,
    public readonly pythonManager: PythonManager,
    public readonly outputChannel: vscode.OutputChannel
  ) {
    this._disposables = vscode.Disposable.from(
      this.pythonManager.pythonExtension?.exports.settings.onDidChangeExecutionDetails(
        async (_event) => await this.refresh()
      ) ?? {
        // eslint-disable-next-line @typescript-eslint/no-empty-function
        dispose() {},
      },
      vscode.workspace.onDidChangeWorkspaceFolders(async (_event) => await this.refresh()),
      vscode.workspace.onDidOpenTextDocument(this.getLanguageClientForDocument)
    );
  }

  public async stopAllClients(): Promise<void> {
    await this.clientsMutex.dispatch(async () => {
      const promises: Promise<void>[] = [];

      for (const client of this.clients.values()) {
        promises.push(client.stop());
      }

      await Promise.all(promises);

      this.clients.clear();
    });
  }

  async dispose(): Promise<void> {
    await this.stopAllClients();
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

  private getServerOptionsStdIo(folder: vscode.WorkspaceFolder) {
    const config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);

    const pythonCommand = this.pythonManager.getPythonCommand(folder);

    if (!pythonCommand) {
      throw new Error("Can't find a valid python executable.");
    }

    const serverArgs = config.get<Array<string>>("languageServer.args", []);

    const args: Array<string> = ["-u", this.pythonManager.pythonLanguageServerMain!, "--mode", "stdio"];

    const serverOptions: ServerOptions = {
      command: pythonCommand!,
      args: args.concat(serverArgs),
      options: {
        cwd: folder.uri.fsPath,
        // detached: true
      },
    };
    return serverOptions;
  }

  public async getLanguageClientForDocument(document: vscode.TextDocument): Promise<LanguageClient | undefined> {
    if (document.languageId !== "robotframework") return;

    return await this.getLanguageClientForResource(document.uri);
  }

  public async getLanguageClientForResource(resource: string | vscode.Uri): Promise<LanguageClient | undefined> {
    return await this.clientsMutex.dispatch(async () => {
      const uri = resource instanceof vscode.Uri ? resource : vscode.Uri.parse(resource);
      const workspaceFolder = vscode.workspace.getWorkspaceFolder(uri);

      if (!workspaceFolder) {
        return undefined;
      }

      let result = this.clients.get(workspaceFolder.uri.toString());

      if (result) return result;

      const config = vscode.workspace.getConfiguration(CONFIG_SECTION, uri);

      const mode = config.get<string>("languageServer.mode", "stdio");

      const serverOptions: ServerOptions =
        mode === "tcp" ? this.getServerOptionsTCP(workspaceFolder) : this.getServerOptionsStdIo(workspaceFolder);
      const name = `RobotCode Language Server mode=${mode} for folder "${workspaceFolder.name}"`;

      const outputChannel = mode === "stdio" ? vscode.window.createOutputChannel(name) : undefined;

      const clientOptions: LanguageClientOptions = {
        documentSelector: [
          { scheme: "file", language: "robotframework", pattern: `${workspaceFolder.uri.fsPath}/**/*` },
        ],
        synchronize: {
          configurationSection: [CONFIG_SECTION],
        },
        initializationOptions: {
          storageUri: this.extensionContext?.storageUri?.toString(),
          globalStorageUri: this.extensionContext?.globalStorageUri?.toString(),
        },
        diagnosticCollectionName: "robotcode",
        workspaceFolder,
        outputChannel,
        markdown: {
          isTrusted: true,
        },
        progressOnInitialization: true,
      };

      this.outputChannel.appendLine(`create Language client: ${name}`);
      result = new LanguageClient(name, serverOptions, clientOptions);

      this.outputChannel.appendLine(`trying to start Language client: ${name}`);
      result.start();

      result = await result.onReady().then(
        async (_) => {
          this.outputChannel.appendLine(`client  ${result?.clientOptions.workspaceFolder?.uri ?? "unknown"} ready.`);
          let counter = 0;
          try {
            while (!result?.initializeResult && counter < 1000) {
              await sleep(10);
              counter++;
            }
          } catch {
            return undefined;
          }
          return result;
        },
        async (reason) => {
          this.outputChannel.appendLine(
            `client  ${result?.clientOptions.workspaceFolder?.uri ?? "unknown"} error: ${reason}`
          );
          vscode.window.showErrorMessage(reason.message ?? "Unknown error.");
          return undefined;
        }
      );

      if (result) this.clients.set(workspaceFolder.uri.toString(), result);

      return result;
    });
  }

  public async refresh(_uri?: vscode.Uri | undefined): Promise<void> {
    await this.clientsMutex.dispatch(async () => {
      for (const client of this.clients.values()) {
        // eslint-disable-next-line @typescript-eslint/no-empty-function
        await client.stop().catch((_) => {});
      }
      this.clients.clear();
    });

    for (const document of vscode.workspace.textDocuments) {
      try {
        // eslint-disable-next-line @typescript-eslint/no-empty-function
        await this.getLanguageClientForDocument(document).catch((_) => {});
      } catch {
        // do nothing
      }
    }
  }

  public async getTestsFromWorkspace(
    workspaceFolder: vscode.WorkspaceFolder,
    paths?: Array<string>
  ): Promise<RobotTestItem[] | undefined> {
    const client = await this.getLanguageClientForResource(workspaceFolder.uri);

    if (!client) return;

    const result =
      (await client.sendRequest<RobotTestItem[]>("robot/discovering/getTestsFromWorkspace", {
        paths: paths ?? ["."],
      })) ?? undefined;

    return result;
  }

  public async getTestsFromDocument(document: vscode.TextDocument, id?: string): Promise<RobotTestItem[] | undefined> {
    const client = await this.getLanguageClientForResource(document.uri);

    if (!client) return;

    const result =
      (await client.sendRequest<RobotTestItem[]>("robot/discovering/getTestsFromDocument", {
        textDocument: { uri: document.uri.toString() },
        id: id,
      })) ?? undefined;

    return result;
  }
}
