import * as vscode from "vscode";
import { DebugManager } from "./debugmanager";
import { LanguageClientsManager } from "./languageclientsmanger";
import { PythonManager } from "./pythonmanger";
import { TestControllerManager } from "./testcontrollermanager";

class TerminalLink extends vscode.TerminalLink {
  constructor(
    public path: string,
    startIndex: number,
    length: number,
    tooltip?: string,
  ) {
    super(startIndex, length, tooltip);
  }
}

let languageClientManger: LanguageClientsManager;

function getDocTheme(): string {
  switch (vscode.window.activeColorTheme.kind) {
    case vscode.ColorThemeKind.Dark:
    case vscode.ColorThemeKind.HighContrast:
      return "dark";
    case vscode.ColorThemeKind.Light:
    case vscode.ColorThemeKind.HighContrastLight:
    default:
      return "light";
  }
}

export async function activateAsync(context: vscode.ExtensionContext): Promise<void> {
  const outputChannel = vscode.window.createOutputChannel("RobotCode");

  outputChannel.appendLine("Activate RobotCode Extension.");

  const pythonManager = new PythonManager(context, outputChannel);

  languageClientManger = new LanguageClientsManager(context, pythonManager, outputChannel);

  const debugManager = new DebugManager(context, pythonManager, languageClientManger, outputChannel);

  const testControllerManger = new TestControllerManager(context, languageClientManger, debugManager, outputChannel);

  context.subscriptions.push(
    pythonManager,
    languageClientManger,
    debugManager,
    testControllerManger,
    vscode.commands.registerCommand("robotcode.showDocumentation", async (url: string) => {
      if (url.indexOf("&theme=%24%7Btheme%7D") > 0) {
        url = url.replace("%24%7Btheme%7D", getDocTheme());
      }
      const uri = vscode.Uri.parse(url);
      const external_uri = await vscode.env.asExternalUri(uri);
      await vscode.commands.executeCommand("simpleBrowser.api.open", external_uri.toString(true), {
        preserveFocus: true,
        viewColumn: vscode.ViewColumn.Beside,
      });
    }),
    vscode.window.registerTerminalLinkProvider({
      provideTerminalLinks(terminalContext: vscode.TerminalLinkContext, _token: vscode.CancellationToken) {
        const line = terminalContext.line.trimEnd();

        if ((line.startsWith("Log:") || line.startsWith("Report:")) && line.endsWith("html")) {
          const result = /(Log|Report):\s*(?<link>\S.*)/.exec(line)?.groups?.link;

          if (result) {
            return [
              new TerminalLink(
                result,
                line.indexOf(result),
                result.length,
                line.startsWith("Log:") ? "Open log." : "Open report.",
              ),
            ];
          }
        }

        return [];
      },
      async handleTerminalLink(link: TerminalLink) {
        await languageClientManger.openUriInDocumentationView(vscode.Uri.file(link.path));
      },
    }),
  );

  await languageClientManger.refresh();

  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration(async (event) => {
      const affectedFolders = new Set<vscode.Uri>();

      for (const s of [
        "robotcode.extraArgs",
        "robotcode.profiles",
        "robotcode.python",
        "robotcode.languageServer",
        "robotcode.robot",
        "robotcode.robocop",
        "robotcode.robotidy",
        "robotcode.analysis",
        "robotcode.workspace",
        "robotcode.documentationServer",
      ]) {
        for (const ws of vscode.workspace.workspaceFolders ?? []) {
          if (languageClientManger.clients.has(ws.uri.toString()))
            if (event.affectsConfiguration(s, ws)) {
              affectedFolders.add(ws.uri);
            }
        }
      }

      for (const uri of affectedFolders) {
        await languageClientManger.restart(uri);
      }
    }),
  );
}

function displayProgress<R>(promise: Promise<R>): Thenable<R> {
  const progressOptions: vscode.ProgressOptions = {
    location: vscode.ProgressLocation.Window,
    title: "RobotCode extension loading ...",
  };
  return vscode.window.withProgress(progressOptions, () => promise);
}

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  return displayProgress(activateAsync(context));
}

export async function deactivate(): Promise<void> {
  await languageClientManger.stopAllClients();
}
