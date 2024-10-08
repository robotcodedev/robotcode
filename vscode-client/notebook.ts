/* eslint-disable class-methods-use-this */
import { TextDecoder, TextEncoder } from "util";
import * as vscode from "vscode";
import { LanguageClientsManager } from "./languageclientsmanger";
import { PythonManager } from "./pythonmanger";

interface RawNotebook {
  cells: RawNotebookCell[];
}

interface RawNotebookCell {
  source: string[];
  cell_type: "code" | "markdown";
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

    const cells = raw.map(
      (item) =>
        new vscode.NotebookCellData(
          item.cell_type === "code" ? vscode.NotebookCellKind.Code : vscode.NotebookCellKind.Markup,
          item.source.join("\n"),
          item.cell_type === "code" ? "python" : "markdown",
        ),
    );

    return new vscode.NotebookData(cells);
  }

  async serializeNotebook(data: vscode.NotebookData, _token: vscode.CancellationToken): Promise<Uint8Array> {
    const contents: RawNotebookCell[] = [];

    for (const cell of data.cells) {
      contents.push({
        cell_type: cell.kind === vscode.NotebookCellKind.Code ? "code" : "markdown",
        source: cell.value.split(/\r?\n/g),
      });
    }

    return new TextEncoder().encode(JSON.stringify(contents));
  }
}

export class REPLNotebookController {
  readonly controllerId = "robotframework-repl";
  readonly notebookType = "robotframework-repl";
  readonly label = "Robot Framework REPL";
  readonly supportedLanguages = ["robotframework-repl", "robotframework"];

  readonly controller: vscode.NotebookController;

  private _executionOrder = 0;

  constructor() {
    this.controller = vscode.notebooks.createNotebookController(this.controllerId, this.notebookType, this.label);

    this.controller.supportedLanguages = this.supportedLanguages;
    this.controller.supportsExecutionOrder = true;
    this.controller.executeHandler = this._execute.bind(this);
    this.controller.supportsExecutionOrder = true;
    this.controller.description = "Robot Framework REPL";
    this.controller.interruptHandler = async () => {
      // Do something here to interrupt execution.
    };
  }

  dispose(): void {
    this.controller.dispose();
  }

  private _execute(
    cells: vscode.NotebookCell[],
    _notebook: vscode.NotebookDocument,
    _controller: vscode.NotebookController,
  ): void {
    for (const cell of cells) {
      this._doExecution(cell);
    }
  }

  private async _doExecution(cell: vscode.NotebookCell): Promise<void> {
    const execution = this.controller.createNotebookCellExecution(cell);
    execution.executionOrder = ++this._executionOrder;
    execution.start(Date.now()); // Keep track of elapsed time to execute cell.

    /* Do some execution here; not implemented */

    execution.replaceOutput([
      new vscode.NotebookCellOutput([vscode.NotebookCellOutputItem.text("Dummy output text!")]),
    ]);
    execution.end(true, Date.now());
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
    this._notebookController = new REPLNotebookController();
    this._disposables = vscode.Disposable.from(
      this._notebookController,
      vscode.workspace.registerNotebookSerializer("robotframework-repl", new REPLNotebookSerializer(), {
        transientOutputs: true,
      }),
    );
  }

  dispose(): void {
    this._disposables.dispose();
  }
}
