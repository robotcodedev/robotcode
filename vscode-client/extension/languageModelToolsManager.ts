import * as vscode from "vscode";
import { CONFIG_AI_ENABLE_LANGUAGE_MODEL_TOOLS, CONFIG_SECTION } from "./config";
import { LanguageClientsManager } from "./languageclientsmanger";
import { GetDocumentImportsTool, GetEnvironmentDetails, GetKeywordInfoTool, GetLibraryInfoTool } from "./lmTools";

export class LanguageModelToolsManager implements vscode.Disposable {
  private _toolDisposables: vscode.Disposable | undefined;
  private readonly _disposables: vscode.Disposable;

  constructor(
    public readonly extensionContext: vscode.ExtensionContext,
    public readonly languageClientsManager: LanguageClientsManager,
    public readonly outputChannel: vscode.OutputChannel,
  ) {
    this._disposables = vscode.Disposable.from(
      vscode.workspace.onDidChangeConfiguration((event) => {
        if (event.affectsConfiguration(`${CONFIG_SECTION}.${CONFIG_AI_ENABLE_LANGUAGE_MODEL_TOOLS}`)) {
          this.updateTools();
        }
      }),
    );

    this.updateTools();
  }

  private updateTools(): void {
    const isEnabled = vscode.workspace
      .getConfiguration(CONFIG_SECTION)
      .get<boolean>(CONFIG_AI_ENABLE_LANGUAGE_MODEL_TOOLS, false);

    if (isEnabled) {
      this.registerTools();
    } else {
      this.disposeTools();
    }
  }

  private registerTools(): void {
    if (this._toolDisposables !== undefined) {
      return;
    }

    this._toolDisposables = vscode.Disposable.from(
      vscode.lm.registerTool(
        "robot-get_library_documentation",
        new GetLibraryInfoTool(this.extensionContext, this.languageClientsManager, this.outputChannel),
      ),
      vscode.lm.registerTool(
        "robot-get_keyword_documentation",
        new GetKeywordInfoTool(this.extensionContext, this.languageClientsManager, this.outputChannel),
      ),
      vscode.lm.registerTool(
        "robot-get_file_imports",
        new GetDocumentImportsTool(this.extensionContext, this.languageClientsManager, this.outputChannel),
      ),
      vscode.lm.registerTool(
        "robot-get_environment_details",
        new GetEnvironmentDetails(this.extensionContext, this.languageClientsManager, this.outputChannel),
      ),
    );
  }

  private disposeTools(): void {
    this._toolDisposables?.dispose();
    this._toolDisposables = undefined;
  }

  dispose(): void {
    this.disposeTools();
    this._disposables.dispose();
  }
}
