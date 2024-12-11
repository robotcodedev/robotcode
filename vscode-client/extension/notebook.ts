/* eslint-disable class-methods-use-this */
import { TextDecoder, TextEncoder } from "util";
import * as vscode from "vscode";
import { LanguageClientsManager } from "./languageclientsmanger";
import { PythonManager } from "./pythonmanger";
import * as cp from "child_process";
import * as rpc from "vscode-jsonrpc/node";
import { withTimeout } from "./utils";

interface RawNotebook {
  cells: RawNotebookCell[];
}

interface RawNotebookCellOutputItem {
  mime: string;
  data: string;
}

interface RawNotebookCellOutput {
  items: RawNotebookCellOutputItem[];
  metadata?: { [key: string]: unknown };
}

interface RawNotebookCellExecutionSummary {
  executionOrder?: number;
  success?: boolean;
  timing?: {
    startTime: number;
    endTime: number;
  };
}

interface RawNotebookCell {
  source: string[];
  languageId?: string;
  cell_type: "code" | "markdown";
  outputs?: RawNotebookCellOutput[];
  executionSummary?: RawNotebookCellExecutionSummary;
}

interface ExecutionOutput {
  mime: string;
  data: string;
}

interface ExecutionResult {
  success?: boolean;
  items?: ExecutionOutput[];
  metadata?: { [key: string]: unknown };
}

export class REPLNotebookSerializer implements vscode.NotebookSerializer {
  async deserializeNotebook(content: Uint8Array, _token: vscode.CancellationToken): Promise<vscode.NotebookData> {
    const contents = new TextDecoder().decode(content);

    let raw: RawNotebookCell[];
    try {
      raw = (<RawNotebook>JSON.parse(contents)).cells;
    } catch {
      raw = [];
    }

    const cells = raw.map((item) => {
      const result = new vscode.NotebookCellData(
        item.cell_type === "code" ? vscode.NotebookCellKind.Code : vscode.NotebookCellKind.Markup,
        item.source.join("\n"),
        item.languageId ?? (item.cell_type === "code" ? "robotframework-repl" : "markdown"),
      );
      result.outputs = item.outputs?.map((item) => {
        return new vscode.NotebookCellOutput(
          item.items.flatMap((item) => {
            if (item.mime === "x-application/robotframework-repl-log") {
              const data = new Uint8Array(Buffer.from(item.data, "base64"));
              return [
                {
                  mime: item.mime,
                  data: data,
                },
                {
                  mime: "text/x-json",
                  data: data,
                },
              ];
            }
            return [
              {
                mime: item.mime,
                data: new Uint8Array(Buffer.from(item.data, "base64")),
              },
            ];
          }),
          item.metadata,
        );
      });

      result.executionSummary = item.executionSummary
        ? {
            executionOrder: item.executionSummary.executionOrder,
            success: item.executionSummary.success,
            timing: item.executionSummary.timing
              ? {
                  startTime: item.executionSummary.timing.startTime,
                  endTime: item.executionSummary.timing.endTime,
                }
              : undefined,
          }
        : undefined;

      return result;
    });

    return new vscode.NotebookData(cells);
  }

  async serializeNotebook(data: vscode.NotebookData, _token: vscode.CancellationToken): Promise<Uint8Array> {
    const contents: RawNotebookCell[] = [];

    for (const cell of data.cells) {
      contents.push({
        cell_type: cell.kind === vscode.NotebookCellKind.Code ? "code" : "markdown",
        languageId: cell.languageId,
        source: cell.value.split(/\r?\n/g),
        outputs: cell.outputs?.map((item) => {
          return {
            metadata: item.metadata ? { ...item.metadata } : undefined,
            items: item.items
              .filter((item) => item.mime !== "text/x-json")
              .map((item) => {
                return {
                  mime: item.mime,
                  data: Buffer.from(item.data).toString("base64"),
                };
              }),
          };
        }),
        executionSummary: cell.executionSummary
          ? {
              executionOrder: cell.executionSummary.executionOrder,
              success: cell.executionSummary.success,
              timing: cell.executionSummary.timing ? { ...cell.executionSummary.timing } : undefined,
            }
          : undefined,
      });
    }

    return new TextEncoder().encode(JSON.stringify({ cells: contents }));
  }
}

export class ReplServerClient {
  private exitNotification = new rpc.NotificationType<void>("testNotification");

  constructor(
    public document: vscode.NotebookDocument,
    public readonly extensionContext: vscode.ExtensionContext,
    public readonly pythonManager: PythonManager,
    readonly _outputChannel: vscode.OutputChannel,
  ) {
    this._outputChannel.appendLine("Starting REPL server...");
  }

  connection: rpc.MessageConnection | undefined;
  childProcess: cp.ChildProcessWithoutNullStreams | undefined;
  private _cancelationTokenSource: vscode.CancellationTokenSource | undefined;

  dispose(): void {
    this.exitClient().finally(() => {});
  }

  async sendShutdown(): Promise<void> {
    await this.connection?.sendRequest("shutdown");
  }

  async _waitForServerToExit(): Promise<void> {
    while (this.childProcess?.exitCode === null) {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }

  async exitClient(): Promise<void> {
    this.cancelCurrentExecution();

    try {
      await withTimeout(this.sendShutdown(), 50000);
    } catch (e) {
      this._outputChannel.appendLine(`Error shutting down server: ${e?.toString()}`);
    }
    this.connection?.sendNotification(this.exitNotification);

    try {
      await withTimeout(this._waitForServerToExit(), 5000);
    } catch (e) {
      this._outputChannel.appendLine(`Error waiting for server to exit: ${e?.toString()}`);

      this.connection?.dispose();
      this.childProcess?.kill();
    }
  }

  cancelCurrentExecution(): void {
    if (this._cancelationTokenSource) {
      this._cancelationTokenSource.cancel();
      this._cancelationTokenSource.dispose();
    }
  }

  async ensureInitialized(): Promise<void> {
    if (this.connection) {
      return;
    }

    let folder = vscode.workspace.getWorkspaceFolder(this.document.uri);
    if (!folder) {
      if (vscode.workspace.workspaceFolders?.length == 1) {
        folder = vscode.workspace.workspaceFolders[0];
      } else {
        // TODO: select a workspace folder if there are multiple and ensure that robotframework is installed.
        throw new Error("No workspace folder found for the document.");
      }
    }

    const pipeName = rpc.generateRandomPipeName();

    const transport = await rpc.createClientPipeTransport(pipeName, "utf-8");

    const { pythonCommand, final_args } = await this.pythonManager.buildRobotCodeCommand(
      folder,
      //["-v", "--debugpy", "--debugpy-wait-for-client", "repl-server", "--pipe", pipeName],
      ["repl-server", "--pipe", pipeName, "--source", this.document.uri.fsPath],
      undefined,
      true,
      true,
    );

    this._outputChannel.appendLine(`Starting server with command: ${pythonCommand} ${final_args.join(" ")}`);

    this.childProcess = cp.spawn(pythonCommand, final_args, { cwd: folder.uri.fsPath });

    this.childProcess.stdout.on("data", (message) => {
      this._outputChannel.appendLine(`${message}`);
    });

    this.childProcess.stderr.on("data", (message) => {
      this._outputChannel.appendLine(`${message}`);
    });

    this.childProcess.on("exit", (code) => {
      this.cancelCurrentExecution();

      this._outputChannel.appendLine(`Server exited with code ${code}`);
      if (this.connection) {
        this._outputChannel.appendLine("Disposing connection...");
        this.connection.dispose();
        this.connection = undefined;
      }
    });
    this.childProcess.on("error", (error) => {
      this._outputChannel.appendLine(`Error starting server: ${error?.toString()}`);
    });

    let connection: rpc.MessageConnection | undefined = undefined;

    try {
      this._outputChannel.appendLine("Waiting for server to connect...");
      const [reader, writer] = await withTimeout(transport.onConnected(), 5000);
      this._outputChannel.appendLine("Server connected.");

      connection = rpc.createMessageConnection(reader, writer);

      connection.listen();

      const result = await connection.sendRequest<string>("initialize", { message: "Hello World" });
      this._outputChannel.appendLine(`Server initialized: ${result}`);
    } catch (error) {
      this._outputChannel.appendLine(`Error connecting to server: ${error?.toString()}`);
      throw new Error("Error connecting to RPC server", { cause: error });
    }

    this.connection = connection;
  }

  async executeCell(source: string): Promise<{ success?: boolean; output: vscode.NotebookCellOutput }> {
    this._cancelationTokenSource = new vscode.CancellationTokenSource();

    try {
      await this.ensureInitialized();

      const result = await this.connection?.sendRequest<ExecutionResult>(
        "executeCell",
        { source },
        this._cancelationTokenSource.token,
      );

      return {
        success: result?.success || false,
        output: new vscode.NotebookCellOutput(
          result?.items?.flatMap((item) => {
            return item.mime === "x-application/robotframework-repl-log"
              ? [
                  vscode.NotebookCellOutputItem.json(JSON.parse(item.data), item.mime),
                  vscode.NotebookCellOutputItem.json(JSON.parse(item.data), "text/x-json"),
                ]
              : [vscode.NotebookCellOutputItem.text(item.data, item.mime)];
          }) ?? [],
          result?.metadata,
        ),
      };
    } finally {
      this._cancelationTokenSource.dispose();
      this._cancelationTokenSource = undefined;
    }
  }
}

export class REPLNotebookController {
  readonly controllerId = "robotframework-repl";
  readonly notebookType = "robotframework-repl";
  readonly label = "Robot Framework REPL";
  readonly supportedLanguages = ["robotframework-repl", "robotframework"];
  readonly description = "A Robot Framework REPL notebook controller";
  readonly supportsExecutionOrder = true;
  readonly controller: vscode.NotebookController;
  readonly _clients = new Map<vscode.NotebookDocument, ReplServerClient>();

  _outputChannel: vscode.OutputChannel | undefined;

  private readonly _disposables: vscode.Disposable;
  private _executionOrder = 0;
  private readonly finalizeRegistry: FinalizationRegistry<{ dispose(): unknown }>;

  constructor(
    public readonly extensionContext: vscode.ExtensionContext,
    public readonly pythonManager: PythonManager,
  ) {
    this.controller = vscode.notebooks.createNotebookController(this.controllerId, this.notebookType, this.label);
    this.finalizeRegistry = new FinalizationRegistry((heldValue) => {
      heldValue.dispose();
    });

    this.controller.supportedLanguages = this.supportedLanguages;
    this.controller.supportsExecutionOrder = true;
    this.controller.executeHandler = this._execute.bind(this);
    this.controller.supportsExecutionOrder = true;
    this.controller.description = "Robot Framework REPL";
    this.controller.interruptHandler = async (notebook: vscode.NotebookDocument) => {
      this._clients.get(notebook)?.dispose();
      this._clients.delete(notebook);
    };
    this._disposables = vscode.Disposable.from(
      this.controller,
      vscode.workspace.onDidCloseNotebookDocument((document) => {
        this._clients.get(document)?.dispose();
        this._clients.delete(document);
      }),
    );
  }

  outputChannel(): vscode.OutputChannel {
    if (!this._outputChannel) {
      this._outputChannel = vscode.window.createOutputChannel("RobotCode REPL");
    }
    return this._outputChannel;
  }

  dispose(): void {
    for (const client of this._clients.values()) {
      client.dispose();
    }
    this._disposables.dispose();
  }

  private getClient(document: vscode.NotebookDocument): ReplServerClient {
    let client = this._clients.get(document);
    if (!client) {
      client = new ReplServerClient(document, this.extensionContext, this.pythonManager, this.outputChannel());
      this.finalizeRegistry.register(document, client);
      this._clients.set(document, client);
    }
    return client;
  }

  private async _execute(
    cells: vscode.NotebookCell[],
    _notebook: vscode.NotebookDocument,
    _controller: vscode.NotebookController,
  ): Promise<void> {
    const client = this.getClient(_notebook);

    for (const cell of cells) {
      await this._doExecution(client, cell);
    }
  }

  private async _doExecution(client: ReplServerClient, cell: vscode.NotebookCell): Promise<void> {
    const execution = this.controller.createNotebookCellExecution(cell);
    execution.executionOrder = ++this._executionOrder;
    let success: boolean | undefined = undefined;

    execution.start(Date.now());
    try {
      const source = cell.document.getText();
      const result = await client.executeCell(source);
      if (result !== undefined) {
        success = result.success;

        await execution.clearOutput();
        await execution.appendOutput(result.output);
      }
    } catch (error) {
      await execution.clearOutput();
      await execution.appendOutput([
        new vscode.NotebookCellOutput([
          vscode.NotebookCellOutputItem.error(
            error instanceof Error ? error : new Error(error?.toString() ?? "Unknown error"),
          ),
        ]),
      ]);
    } finally {
      execution.end(success, Date.now());
    }
  }
}

export class NotebookManager {
  private readonly _disposables: vscode.Disposable;
  private _notebookController: REPLNotebookController;

  constructor(
    public readonly extensionContext: vscode.ExtensionContext,
    public readonly pythonManager: PythonManager,
    public readonly languageClientsManager: LanguageClientsManager,
    public readonly outputChannel: vscode.OutputChannel,
  ) {
    this._notebookController = new REPLNotebookController(extensionContext, pythonManager);

    this._disposables = vscode.Disposable.from(
      this._notebookController,
      vscode.workspace.registerNotebookSerializer("robotframework-repl", new REPLNotebookSerializer()),
      vscode.commands.registerCommand("robotcode.createNewNotebook", async () => {
        const newNotebook = await vscode.workspace.openNotebookDocument(
          this._notebookController.notebookType,
          new vscode.NotebookData([
            new vscode.NotebookCellData(vscode.NotebookCellKind.Code, "Log  Hello World!!!", "robotframework-repl"),
          ]),
        );
        await vscode.commands.executeCommand("vscode.openWith", newNotebook.uri, "robotframework-repl");
      }),
    );
  }

  dispose(): void {
    this._disposables.dispose();
  }
}
