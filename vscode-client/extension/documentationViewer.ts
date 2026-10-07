import * as crypto from "crypto";
import * as path from "path";
import * as vscode from "vscode";
import { CONFIG_SECTION } from "./config";
import { DocumentationTarget } from "./languageclientsmanger";
import { PythonManager } from "./pythonmanger";

const VIEW_TYPE = "robotcode.documentationViewer";
const DEFAULT_TARGET = "BuiltIn";
const CACHE_FOLDER = "documentation-viewer";
const KEPT_PAGES = 50;
// The id of the viewer pinned with its pin button, so that a reload keeps the pin that was chosen last.
const PINNED_KEY = "robotcode.documentationViewer.pinned";
// A window that gets the focus back activates its last active editor for a moment; only a longer activation is use.
const ACTIVATION_DELAY_MS = 300;

interface NamedAnchor {
  name: string;
  anchor: string;
}

interface DocumentationJson {
  name: string;
  type: string;
  version?: string;
  scope?: string;
  source?: string;
  lineno?: number;
  markdown: string;
  keywords: NamedAnchor[];
  types: NamedAnchor[];
}

interface HistoryEntry {
  folder: string;
  text: string;
}

interface ViewerState {
  v: number;
  id?: string;
  history?: HistoryEntry[];
  index?: number;
  pinned?: boolean;
}

interface ShowMessage {
  type: "show";
  folder: string;
  text: string;
  keyword?: string;
  anchor?: string;
  dataType?: string;
  focusTarget?: boolean;
}

type ViewerMessage =
  | { type: "ready"; state?: ViewerState }
  | { type: "load"; seq: number; folder?: string; text: string; refresh: boolean; typed?: boolean }
  | { type: "pin"; pinned: boolean }
  | { type: "pickFolder" }
  | { type: "openMarkdown"; seq: number };

// What a generation depends on besides the folder and the Python command.
interface GenerationCommand {
  args: string[];
  profiles: string[];
  env: Record<string, string>;
  // Not passed on: `executeRobotCode` adds them itself; they are part of the cache key.
  extraArgs: string[];
}

interface Generation {
  promise: Promise<DocumentationJson>;
  source: vscode.CancellationTokenSource;
  waiters: Set<Viewer>;
  cancelled: boolean;
}

class Viewer {
  id: string | undefined;
  ready = false;
  // Created to take the focus: its first page asks for the focus even if the panel is not reported active yet.
  focusOnReady = false;
  disposed = false;
  pendingShow: ShowMessage | undefined;
  lastUsed = 0;
  seq = -1;
  key: string | undefined;
  current: HistoryEntry | undefined;
  // The Markdown of the page sent last, for "Open as Markdown": the page itself only has its HTML.
  lastPage: { seq: number; markdown: string } | undefined;

  constructor(
    readonly panel: vscode.WebviewPanel,
    public folder: vscode.WorkspaceFolder | undefined,
  ) {}

  post(message: unknown): void {
    if (!this.disposed) void this.panel.webview.postMessage(message);
  }

  show(message: ShowMessage): void {
    // Kept until the page loads the shown target, and sent again after the next `ready`, so that a show is not lost
    // while the webview is hidden or recreated.
    this.pendingShow = message;
    if (this.ready) this.post(message);
  }
}

function folderOf(uri: string | undefined): vscode.WorkspaceFolder | undefined {
  return uri ? vscode.workspace.workspaceFolders?.find((f) => f.uri.toString() === uri) : undefined;
}

function postFolders(viewer: Viewer): void {
  viewer.post({
    type: "folders",
    folders: (vscode.workspace.workspaceFolders ?? []).map((f) => ({ uri: f.uri.toString(), name: f.name })),
  });
}

function generationCommand(folder: vscode.WorkspaceFolder, text: string): GenerationCommand {
  const config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);
  const variables = config.get<Record<string, string>>("robot.variables", {});
  return {
    args: [
      "doc",
      "lib",
      ...config.get<string[]>("robot.pythonPath", []).flatMap((v) => ["-P", v]),
      ...config.get<string[]>("robot.languages", []).flatMap((v) => ["--language", v]),
      ...Object.entries(variables).flatMap(([name, value]) => ["-v", `${name}:${value}`]),
      ...config.get<string[]>("robot.variableFiles", []).flatMap((v) => ["-V", v]),
      // A target that starts with `-` is still the target.
      "--",
      text,
    ],
    profiles: config.get<string[]>("profiles", []),
    env: config.get<Record<string, string>>("robot.env", {}),
    extraArgs: config.get<string[]>("extraArgs", []),
  };
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

async function exists(uri: vscode.Uri): Promise<boolean> {
  try {
    await vscode.workspace.fs.stat(uri);
    return true;
  } catch {
    return false;
  }
}

function openColumn(): vscode.ViewColumn {
  return vscode.workspace.getConfiguration(CONFIG_SECTION).get<string>("documentationViewer.openLocation") === "active"
    ? vscode.ViewColumn.Active
    : vscode.ViewColumn.Beside;
}

function showOutline(): boolean {
  return vscode.workspace.getConfiguration(CONFIG_SECTION).get<boolean>("documentationViewer.showOutline", true);
}

async function pickFolder(): Promise<vscode.WorkspaceFolder | undefined> {
  const editor = vscode.window.activeTextEditor;
  const editorFolder = editor !== undefined ? vscode.workspace.getWorkspaceFolder(editor.document.uri) : undefined;
  if (editorFolder !== undefined) return editorFolder;

  const folders = vscode.workspace.workspaceFolders ?? [];
  if (folders.length === 0) {
    void vscode.window.showErrorMessage("The Documentation Viewer needs a workspace folder.");
    return undefined;
  }
  if (folders.length === 1) return folders[0];

  return vscode.window.showWorkspaceFolderPick({ placeHolder: "Workspace folder for the Documentation Viewer" });
}

// The target as it is typed: the path of the library or file relative to the folder, or the name.
async function targetText(target: DocumentationTarget, folder: vscode.WorkspaceFolder): Promise<string> {
  let name = target.name;

  const file =
    target.baseDir !== undefined
      ? path.resolve(target.baseDir, target.name)
      : path.isAbsolute(target.name)
        ? target.name
        : undefined;

  if (file !== undefined && (await exists(vscode.Uri.file(file)))) {
    const relative = path.relative(folder.uri.fsPath, file);
    name =
      relative && !relative.startsWith("..") && !path.isAbsolute(relative) ? relative.split(path.sep).join("/") : file;
  }

  return [name, ...(target.args ?? [])].join("::");
}

function markdownStyles(): vscode.Uri[] {
  const markdown = vscode.extensions.getExtension("vscode.markdown-language-features");
  const styles: unknown = markdown?.packageJSON?.contributes?.["markdown.previewStyles"];
  if (markdown === undefined || !Array.isArray(styles)) return [];

  return styles
    .filter((s): s is string => typeof s === "string")
    .map((s) => vscode.Uri.joinPath(markdown.extensionUri, s));
}

async function sendPage(
  viewer: Viewer,
  seq: number,
  folder: vscode.WorkspaceFolder,
  text: string,
  json: DocumentationJson,
  busy: boolean,
): Promise<void> {
  let html: string | undefined;
  let renderError: string | undefined;
  try {
    html = await vscode.commands.executeCommand<string>("markdown.api.render", json.markdown);
    if (typeof html !== "string") renderError = "markdown.api.render returned no HTML";
  } catch (error) {
    renderError = errorMessage(error);
  }
  if (viewer.seq !== seq || viewer.disposed) return;

  viewer.lastPage = { seq, markdown: json.markdown };
  viewer.panel.title = json.name;
  viewer.post({
    type: "page",
    seq,
    folder: folder.uri.toString(),
    text,
    meta: {
      name: json.name,
      type: json.type,
      version: json.version,
      scope: json.scope,
      source: json.source,
      lineno: json.lineno,
    },
    keywords: (json.keywords ?? []).map(({ name, anchor }) => ({ name, anchor })),
    types: (json.types ?? []).map(({ name, anchor }) => ({ name, anchor })),
    ...(renderError === undefined ? { html } : { renderError, markdown: json.markdown }),
    busy,
  });
}

async function openMarkdown(viewer: Viewer, seq: number): Promise<void> {
  // Only the page of the load on screen; a page of another load is never opened.
  const page = viewer.lastPage;
  if (viewer.disposed || page === undefined || page.seq !== seq) return;

  // Read before the first `await`: the getter throws once the panel is disposed. It counts the groups of all
  // windows, so a viewer in a window of its own gets the document in that window.
  const viewColumn = viewer.panel.viewColumn ?? vscode.ViewColumn.Active;
  try {
    const document = await vscode.workspace.openTextDocument({ language: "markdown", content: page.markdown });
    await vscode.window.showTextDocument(document, { viewColumn });
  } catch (error) {
    void vscode.window.showErrorMessage(`Cannot open the page as Markdown: ${errorMessage(error)}`);
  }
}

async function resolveFolder(
  viewer: Viewer,
  folderUri: string | undefined,
  text: string,
  typed: boolean,
): Promise<vscode.WorkspaceFolder | undefined> {
  // A typed absolute path inside another workspace folder switches the viewer to that folder. The absolute path of
  // an action's target keeps the folder of the document the action came from.
  const name = text.split("::")[0];
  if (typed && path.isAbsolute(name)) {
    const folder = vscode.workspace.getWorkspaceFolder(vscode.Uri.file(name));
    if (folder !== undefined) return folder;
  }

  return folderOf(folderUri) ?? viewer.folder ?? (await pickFolder());
}

export class DocumentationViewerManager implements vscode.Disposable {
  private readonly _disposables: vscode.Disposable;
  private readonly _viewers = new Set<Viewer>();
  private readonly _generations = new Map<string, Generation>();
  private readonly _generatedThisSession = new Set<string>();
  private _pinned: Viewer | undefined;
  private _useCounter = 0;

  constructor(
    private readonly context: vscode.ExtensionContext,
    private readonly pythonManager: PythonManager,
  ) {
    this._disposables = vscode.Disposable.from(
      vscode.window.registerWebviewPanelSerializer(VIEW_TYPE, {
        deserializeWebviewPanel: async (panel: vscode.WebviewPanel, state: unknown) => {
          const viewerState = state as ViewerState | undefined;
          const entry = viewerState?.history?.[viewerState.index ?? -1];
          const viewer = this.attach(panel, folderOf(entry?.folder));
          if (panel.active) this.markUsed(viewer);
        },
      }),
      vscode.commands.registerCommand("robotcode.openDocumentationViewer", () => this.openViewer()),
      vscode.commands.registerCommand("robotcode.openDocumentationViewerInNewWindow", () =>
        this.openViewerInNewWindow(),
      ),
      vscode.commands.registerCommand("robotcode.showInDocumentationViewer", (target: DocumentationTarget) =>
        this.showTarget(target, false),
      ),
      vscode.commands.registerCommand("robotcode.showInNewDocumentationViewer", (target: DocumentationTarget) =>
        this.showTarget(target, true),
      ),
      vscode.workspace.onDidChangeWorkspaceFolders(() => {
        for (const viewer of this._viewers) if (viewer.ready) postFolders(viewer);
      }),
    );
  }

  dispose(): void {
    for (const generation of this._generations.values()) generation.source.cancel();
    for (const viewer of [...this._viewers]) viewer.panel.dispose();
    this._disposables.dispose();
  }

  private async openViewer(): Promise<void> {
    const folder = await pickFolder();
    if (folder === undefined) return;

    const viewer = this.createViewer(openColumn(), false, folder, DEFAULT_TARGET);
    viewer.show({ type: "show", folder: folder.uri.toString(), text: DEFAULT_TARGET, focusTarget: true });
  }

  private async openViewerInNewWindow(): Promise<void> {
    const source = [...this._viewers].find((v) => v.panel.active) ?? this.lastUsedViewer();
    const folder = folderOf(source?.current?.folder) ?? source?.folder ?? (await pickFolder());
    if (folder === undefined) return;

    const text = source?.current?.text ?? DEFAULT_TARGET;
    // The new viewer must be the active editor, because the command moves the active editor of the focused window.
    const viewer = this.createViewer(vscode.ViewColumn.Active, false, folder, text);
    viewer.show({ type: "show", folder: folder.uri.toString(), text });

    await vscode.commands.executeCommand("workbench.action.moveEditorToNewWindow");
  }

  private async showTarget(target: DocumentationTarget, newViewer: boolean): Promise<void> {
    const folder = vscode.workspace.getWorkspaceFolder(vscode.Uri.parse(target.uri)) ?? (await pickFolder());
    if (folder === undefined) return;

    const text = await targetText(target, folder);

    let viewer = newViewer ? undefined : (this._pinned ?? this.lastUsedViewer());
    if (viewer !== undefined) {
      viewer.panel.reveal(viewer.panel.viewColumn, true);
      this.markUsed(viewer);
    } else {
      // Beside the editor, the editor keeps the focus; in its own group, the new viewer covers it and takes it.
      const column = openColumn();
      viewer = this.createViewer(column, column !== vscode.ViewColumn.Active, folder, text);
    }

    viewer.show({
      type: "show",
      folder: folder.uri.toString(),
      text,
      keyword: target.keyword,
      anchor: target.anchor,
      dataType: target.dataType,
    });
  }

  private lastUsedViewer(): Viewer | undefined {
    let result: Viewer | undefined;
    for (const viewer of this._viewers) {
      if (result === undefined || viewer.lastUsed > result.lastUsed) result = viewer;
    }
    return result;
  }

  private markUsed(viewer: Viewer): void {
    viewer.lastUsed = ++this._useCounter;
  }

  private options(): vscode.WebviewPanelOptions & vscode.WebviewOptions {
    const markdown = vscode.extensions.getExtension("vscode.markdown-language-features");

    return {
      enableScripts: true,
      enableForms: false,
      enableFindWidget: false,
      localResourceRoots: [
        vscode.Uri.joinPath(this.context.extensionUri, "out", "documentationViewer"),
        ...(markdown !== undefined ? [markdown.extensionUri] : []),
      ],
    };
  }

  private html(webview: vscode.Webview): string {
    const nonce = crypto.randomBytes(16).toString("hex");
    const out = vscode.Uri.joinPath(this.context.extensionUri, "out", "documentationViewer");
    const uri = (file: string) => webview.asWebviewUri(vscode.Uri.joinPath(out, file)).toString();
    const styles = markdownStyles().map((s) => webview.asWebviewUri(s).toString());
    const csp = [
      "default-src 'none'",
      `script-src 'nonce-${nonce}'`,
      `style-src ${webview.cspSource}`,
      `font-src ${webview.cspSource}`,
      `img-src ${webview.cspSource} https: data:`,
      "base-uri 'none'",
    ].join("; ");

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy" content="${csp}">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  ${styles.map((s) => `<link rel="stylesheet" href="${s}">`).join("\n  ")}
  <link rel="stylesheet" id="vscode-codicon-stylesheet" href="${uri("codicon.css")}">
  <link rel="stylesheet" href="${uri("viewer.css")}">
</head>
<body>
  <div id="root" data-show-outline="${showOutline()}"></div>
  <script type="module" nonce="${nonce}" src="${uri("documentationViewer.js")}"></script>
</body>
</html>`;
  }

  private createViewer(
    column: vscode.ViewColumn,
    preserveFocus: boolean,
    folder: vscode.WorkspaceFolder,
    title: string,
  ): Viewer {
    const panel = vscode.window.createWebviewPanel(
      VIEW_TYPE,
      title,
      { viewColumn: column, preserveFocus },
      this.options(),
    );
    const viewer = this.attach(panel, folder);
    viewer.focusOnReady = !preserveFocus;
    this.markUsed(viewer);
    return viewer;
  }

  private attach(panel: vscode.WebviewPanel, folder: vscode.WorkspaceFolder | undefined): Viewer {
    const viewer = new Viewer(panel, folder);
    this._viewers.add(viewer);

    panel.iconPath = new vscode.ThemeIcon("book");
    // A revived panel keeps the stored options and HTML until they are set again.
    panel.webview.options = this.options();
    panel.webview.html = this.html(panel.webview);

    panel.onDidDispose(() => {
      viewer.disposed = true;
      // A load that is still on its way to a generation ends at its next check.
      viewer.seq = Number.NaN;
      this._viewers.delete(viewer);
      this.stopWaiting(viewer);
      if (this._pinned === viewer) this._pinned = undefined;
    });
    let activation: ReturnType<typeof setTimeout> | undefined;
    panel.onDidChangeViewState(() => {
      // Without `retainContextWhenHidden`, a hidden webview is gone and is loaded again when it is shown.
      if (!panel.visible) viewer.ready = false;

      clearTimeout(activation);
      if (panel.active) {
        activation = setTimeout(() => {
          if (!viewer.disposed && panel.active) this.markUsed(viewer);
        }, ACTIVATION_DELAY_MS);
      }
    });
    panel.webview.onDidReceiveMessage((message: ViewerMessage) => this.onMessage(viewer, message));

    return viewer;
  }

  private onMessage(viewer: Viewer, message: ViewerMessage): void {
    switch (message.type) {
      case "ready": {
        viewer.ready = true;
        postFolders(viewer);
        const state = message.state;
        viewer.id = state?.id ?? viewer.id;
        viewer.current = state?.history?.[state.index ?? -1] ?? viewer.current;
        // A viewer that was hidden or not restored when another viewer was pinned still reports its old pin.
        if (state?.pinned) {
          if (viewer.id !== undefined && viewer.id === this.context.workspaceState.get<string>(PINNED_KEY)) {
            this._pinned = viewer;
          } else {
            viewer.post({ type: "pin", pinned: false });
          }
        }
        if (viewer.pendingShow !== undefined) viewer.post(viewer.pendingShow);
        // The focus VS Code gives the active webview while its page loads does not stick, for example in a new
        // window or with openLocation `active`; the page takes it itself.
        if (viewer.focusOnReady || viewer.panel.active) viewer.post({ type: "focus" });
        viewer.focusOnReady = false;
        break;
      }
      case "load":
        void this.load(viewer, message.seq, message.folder, message.text, message.refresh, message.typed ?? false);
        break;
      case "pickFolder":
        void vscode.window
          .showWorkspaceFolderPick({ placeHolder: "Workspace folder of this Documentation Viewer" })
          .then((folder) => {
            if (folder !== undefined) viewer.post({ type: "folder", folder: folder.uri.toString() });
          });
        break;
      case "openMarkdown":
        void openMarkdown(viewer, message.seq);
        break;
      case "pin":
        if (message.pinned) {
          if (this._pinned !== undefined && this._pinned !== viewer) this._pinned.post({ type: "pin", pinned: false });
          this._pinned = viewer;
          void this.context.workspaceState.update(PINNED_KEY, viewer.id);
        } else if (this._pinned === viewer) {
          this._pinned = undefined;
          void this.context.workspaceState.update(PINNED_KEY, undefined);
        }
        break;
    }
  }

  private async load(
    viewer: Viewer,
    seq: number,
    folderUri: string | undefined,
    text: string,
    refresh: boolean,
    typed: boolean,
  ): Promise<void> {
    viewer.seq = seq;
    // The page has taken the show into its history before it loads it, with the folder and text of the show.
    const show = viewer.pendingShow;
    if (show !== undefined && show.folder === folderUri && show.text === text) viewer.pendingShow = undefined;

    const folder = await resolveFolder(viewer, folderUri, text, typed);
    if (viewer.seq !== seq) return;
    if (folder === undefined) {
      viewer.post({ type: "status", seq, busy: false, error: "There is no workspace folder for this target." });
      return;
    }

    viewer.folder = folder;
    viewer.current = { folder: folder.uri.toString(), text };

    const pythonCommand = await this.pythonManager.getPythonCommand(folder);
    if (viewer.seq !== seq) return;

    const command = generationCommand(folder, text);
    const key = crypto
      .createHash("sha256")
      .update([folder.uri.toString(), pythonCommand ?? "", JSON.stringify(command)].join("\n"))
      .digest("hex");
    if (viewer.key !== key) this.stopWaiting(viewer);
    viewer.key = key;

    const kept = await this.readKept(key);
    if (viewer.seq !== seq) return;

    const generate = refresh || kept === undefined || !this._generatedThisSession.has(key);

    if (kept !== undefined) {
      await sendPage(viewer, seq, folder, text, kept, generate);
    } else {
      if (!viewer.disposed) viewer.panel.title = text;
      viewer.post({ type: "status", seq, busy: true });
    }
    if (!generate || viewer.seq !== seq) return;

    const generation = this.generate(key, folder, command);
    generation.waiters.add(viewer);
    try {
      const json = await generation.promise;
      if (viewer.seq !== seq) return;

      if (kept === undefined || JSON.stringify(json) !== JSON.stringify(kept)) {
        await sendPage(viewer, seq, folder, text, json, false);
      } else {
        viewer.post({ type: "status", seq, busy: false });
      }
    } catch (error) {
      if (viewer.seq !== seq) return;

      viewer.post(
        generation.cancelled
          ? { type: "status", seq, busy: false }
          : { type: "status", seq, busy: false, error: errorMessage(error) },
      );
    } finally {
      generation.waiters.delete(viewer);
    }
  }

  private generate(key: string, folder: vscode.WorkspaceFolder, command: GenerationCommand): Generation {
    const running = this._generations.get(key);
    if (running !== undefined) return running;

    const source = new vscode.CancellationTokenSource();
    const generation: Generation = {
      promise: Promise.resolve(undefined as never),
      source,
      waiters: new Set(),
      cancelled: false,
    };
    generation.promise = (async () => {
      try {
        const json = (await this.pythonManager.executeRobotCode(
          folder,
          command.args,
          command.profiles,
          "json",
          true,
          true,
          undefined,
          source.token,
          command.env,
        )) as DocumentationJson;

        this._generatedThisSession.add(key);
        await this.writeKept(key, json);
        return json;
      } finally {
        if (this._generations.get(key) === generation) this._generations.delete(key);
        source.dispose();
      }
    })();

    this._generations.set(key, generation);
    return generation;
  }

  // A viewer that switches its target or is closed stops waiting; a generation without waiters is ended.
  private stopWaiting(viewer: Viewer): void {
    for (const [key, generation] of this._generations) {
      if (generation.waiters.delete(viewer) && generation.waiters.size === 0) {
        generation.cancelled = true;
        generation.source.cancel();
        this._generations.delete(key);
      }
    }
  }

  private cacheFolder(): vscode.Uri | undefined {
    return this.context.storageUri !== undefined
      ? vscode.Uri.joinPath(this.context.storageUri, CACHE_FOLDER)
      : undefined;
  }

  private async readKept(key: string): Promise<DocumentationJson | undefined> {
    const folder = this.cacheFolder();
    if (folder === undefined) return undefined;

    try {
      const data = await vscode.workspace.fs.readFile(vscode.Uri.joinPath(folder, `${key}.json`));
      return JSON.parse(new TextDecoder().decode(data)) as DocumentationJson;
    } catch {
      return undefined;
    }
  }

  private async writeKept(key: string, json: DocumentationJson): Promise<void> {
    const folder = this.cacheFolder();
    if (folder === undefined) return;

    try {
      await vscode.workspace.fs.createDirectory(folder);
      await vscode.workspace.fs.writeFile(
        vscode.Uri.joinPath(folder, `${key}.json`),
        new TextEncoder().encode(JSON.stringify(json)),
      );

      const files = await Promise.all(
        (await vscode.workspace.fs.readDirectory(folder))
          .filter(([name, type]) => type === vscode.FileType.File && name.endsWith(".json"))
          .map(async ([name]) => {
            const uri = vscode.Uri.joinPath(folder, name);
            return { uri, mtime: (await vscode.workspace.fs.stat(uri)).mtime };
          }),
      );
      files.sort((a, b) => b.mtime - a.mtime);
      for (const file of files.slice(KEPT_PAGES)) await vscode.workspace.fs.delete(file.uri);
    } catch {
      // The kept pages only save time; a page that cannot be kept is generated again.
    }
  }
}
