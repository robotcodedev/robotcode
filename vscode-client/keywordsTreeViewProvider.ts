import * as vscode from "vscode";
import { LanguageClientsManager, SUPPORTED_LANGUAGES } from "./languageclientsmanger";
import { TreeItemCollapsibleState, TreeItemLabel } from "vscode";
import { Mutex } from "./utils";

class ItemBase extends vscode.TreeItem {
  private _document: WeakRef<vscode.TextDocument>;

  public get document(): vscode.TextDocument | undefined {
    return this._document.deref();
  }

  public constructor(
    document: vscode.TextDocument,
    public readonly label: string | TreeItemLabel,
    public readonly collapsibleState?: TreeItemCollapsibleState,
  ) {
    super(label, collapsibleState);
    this._document = new WeakRef(document);
  }
}

const SYMBOL_NAMESPACE = new vscode.ThemeIcon("symbol-namespace");
const SYMBOL_FUNCTION = new vscode.ThemeIcon("symbol-function");

class KeywordItem extends ItemBase {
  public readonly iconPath = SYMBOL_FUNCTION;
  public readonly contextValue = "keyword";
  //public readonly command: vscode.Command;

  public constructor(
    document: vscode.TextDocument,
    public readonly parent: ImportItem | undefined,
    public readonly label: string | TreeItemLabel,
    public readonly id: string | undefined,
    public readonly description?: string,
    public readonly tooltip?: string | vscode.MarkdownString | undefined,
  ) {
    super(document, label, TreeItemCollapsibleState.None);
    // this.command = {
    //   command: "robotcode.keywordsTreeView.openItem",
    //   title: "open",
    //   //arguments: [(label as string) + "\t"],
    // };
  }
}

class ImportItem extends ItemBase {
  public readonly iconPath = SYMBOL_NAMESPACE;
  public readonly contextValue = "import";

  public constructor(
    document: vscode.TextDocument,
    public readonly label: string | TreeItemLabel,
    public readonly id: string | undefined,
    public readonly description?: string,
    public readonly tooltip?: string | vscode.MarkdownString | undefined,
    public keywords: KeywordItem[] = [],
    collapsibleState?: TreeItemCollapsibleState,
  ) {
    super(document, label, collapsibleState || TreeItemCollapsibleState.Collapsed);
  }
}

class DocumentData {
  imports: ImportItem[] = [];
  keywords: KeywordItem[] = [];
}

export class KeywordsTreeViewProvider
  implements vscode.TreeDataProvider<ItemBase>, vscode.TreeDragAndDropController<ItemBase>
{
  private _disposables: vscode.Disposable;

  private _cancelationSource: vscode.CancellationTokenSource | undefined;
  private _documentsData: WeakMap<vscode.TextDocument, DocumentData> = new WeakMap();
  private _currentDocumentData: DocumentData | undefined;

  constructor(
    context: vscode.ExtensionContext,
    public languageClientsManager: LanguageClientsManager,
    public outputChannel: vscode.OutputChannel,
  ) {
    const view = vscode.window.createTreeView("robotcode.keywordsTreeView", {
      treeDataProvider: this,
      showCollapseAll: true,
      //canSelectMany: true,
      dragAndDropController: this,
    });
    context.subscriptions.push(view);

    this._disposables = vscode.Disposable.from(
      vscode.window.onDidChangeActiveTextEditor(async (_editor) => {
        await this.refresh();
      }),
      languageClientsManager.onClientStateChanged(async () => {
        await this.refresh();
      }),
      vscode.workspace.onWillSaveTextDocument(async (event) => {
        if (this._documentsData.has(event.document)) {
          this._documentsData.delete(event.document);
        }
        await this.refresh();
      }),

      vscode.commands.registerCommand("robotcode.keywordsTreeView.refresh", async () => {
        await this.refresh(true);
      }),
      vscode.commands.registerCommand("robotcode.keywordsTreeView.insertKeyword", async (item: vscode.TreeItem) => {
        const editor = vscode.window.activeTextEditor;
        if (editor !== undefined) {
          await vscode.window.showTextDocument(editor.document, undefined, false);

          await editor.edit((editBuilder) => {
            editBuilder.insert(editor.selection.active, (item.label as string) + "    ");
          });

          await vscode.commands.executeCommand("editor.action.triggerSuggest");
          await vscode.commands.executeCommand("editor.action.triggerParameterHints");
        }
      }),
      vscode.commands.registerCommand("robotcode.keywordsTreeView.showDocumentation", async (item: vscode.TreeItem) => {
        let url: string | undefined = undefined;

        if (item instanceof KeywordItem) {
          if (item.document === undefined) return;

          url = await this.languageClientsManager.getDocumentionUrl(item.document, item.parent?.id, item.id);
        } else if (item instanceof ImportItem) {
          if (item.document === undefined) return;

          url = await this.languageClientsManager.getDocumentionUrl(item.document, item.id);
        }

        if (url) {
          await vscode.commands.executeCommand("robotcode.showDocumentation", url);
        }
      }),
    );

    this.refresh().then(
      () => undefined,
      () => undefined,
    );
  }
  readonly dropMimeTypes: readonly string[] = [];
  readonly dragMimeTypes: readonly string[] = ["text/plain"];

  // eslint-disable-next-line class-methods-use-this
  handleDrag(
    source: readonly ItemBase[],
    dataTransfer: vscode.DataTransfer,
    _token: vscode.CancellationToken,
  ): void | Thenable<void> {
    for (const item of source) {
      if (item instanceof KeywordItem) {
        dataTransfer.set("text/plain", new vscode.DataTransferItem(item.label as string));
      }
    }
  }

  dispose(): void {
    this._disposables.dispose();
  }

  private refreshMutex = new Mutex();

  async refresh(full: boolean = false): Promise<void> {
    if (this._cancelationSource) {
      this._cancelationSource.cancel();
    }

    return this.refreshMutex.dispatch(async () => {
      this._cancelationSource = new vscode.CancellationTokenSource();

      this._currentDocumentData = undefined;

      let document: vscode.TextDocument | undefined = undefined;

      if (vscode.window.activeTextEditor) {
        const editor = vscode.window.activeTextEditor;

        if (editor && SUPPORTED_LANGUAGES.includes(editor.document.languageId)) {
          document = editor.document;
        }
      }

      try {
        if (document !== undefined) {
          if (!full && this._documentsData.has(document)) {
            this._currentDocumentData = this._documentsData.get(document);
            return;
          }
          this._currentDocumentData = new DocumentData();

          const currentDoc = document; // needed for the closure

          this._currentDocumentData.imports = (
            await this.languageClientsManager.getDocumentImports(document, this._cancelationSource.token)
          )
            .map((lib_or_res) => {
              if (this._cancelationSource?.token.isCancellationRequested) {
                throw new Error("Canceled");
              }
              const result = new ImportItem(
                currentDoc,
                lib_or_res.alias ?? lib_or_res.name,
                lib_or_res.id,
                lib_or_res.type?.toUpperCase(),
                toMarkdown(lib_or_res.documentation),
              );
              result.keywords =
                lib_or_res.keywords
                  ?.map(
                    (keyword) =>
                      new KeywordItem(
                        currentDoc,
                        result,
                        keyword.name,
                        keyword.id,
                        keyword.signature,
                        toMarkdown(keyword.documentation),
                      ),
                  )
                  .sort((a, b) => (a.label as string).localeCompare(b.label as string)) ?? [];

              return result;
            })
            .filter((value) => value !== undefined)
            .sort((a, b) =>
              `${a.description}_${a.label as string}`.localeCompare(`${b.description}_${b.label as string}`),
            );

          this._currentDocumentData.keywords = (
            await this.languageClientsManager.getDocumentKeywords(document, this._cancelationSource.token)
          )
            ?.map(
              (keyword) =>
                new KeywordItem(
                  currentDoc,
                  undefined,
                  keyword.name,
                  keyword.id,
                  keyword.signature,
                  toMarkdown(keyword.documentation),
                ),
            )
            .sort((a, b) => (a.label as string).localeCompare(b.label as string));
        }
      } catch (e) {
        this.outputChannel.appendLine(`Error: Can't get items for keywords treeview: ${e?.toString()}`);

        this._currentDocumentData = undefined;
      } finally {
        if (document !== undefined && this._currentDocumentData !== undefined) {
          this._documentsData.set(document, this._currentDocumentData);
        }
        this._onDidChangeTreeData.fire();
      }
    });
  }

  private readonly _onDidChangeTreeData = new vscode.EventEmitter<void | ItemBase | ItemBase[] | null | undefined>();

  public get onDidChangeTreeData(): vscode.Event<void | ItemBase | ItemBase[] | null | undefined> {
    return this._onDidChangeTreeData.event;
  }

  // eslint-disable-next-line class-methods-use-this
  getTreeItem(element: ItemBase): vscode.TreeItem | Thenable<vscode.TreeItem> {
    return element;
  }

  async getChildren(element?: ItemBase | undefined): Promise<ItemBase[]> {
    if (element === undefined) {
      if (this._currentDocumentData === undefined) {
        return Promise.resolve([]);
      }
      return Promise.resolve([...this._currentDocumentData.imports, ...this._currentDocumentData.keywords]);
    }
    if (element instanceof ImportItem) {
      return Promise.resolve(element.keywords);
    }
    return Promise.resolve([]);
  }

  // eslint-disable-next-line class-methods-use-this
  getParent(element: ItemBase): vscode.ProviderResult<ItemBase> {
    if (element instanceof KeywordItem) {
      return element.parent;
    }
    return undefined;
  }

  //   resolveTreeItem?(
  //     item: vscode.TreeItem,
  //     element: DocumentItem,
  //     token: vscode.CancellationToken,
  //   ): vscode.ProviderResult<vscode.TreeItem> {
  //     throw new Error("Method not implemented.");
  //   }
}

function toMarkdown(value: string | undefined): vscode.MarkdownString | undefined {
  const doc = value ? new vscode.MarkdownString(value) : undefined;
  if (doc) {
    doc.isTrusted = true;
    doc.supportHtml = true;
  }
  return doc;
}
