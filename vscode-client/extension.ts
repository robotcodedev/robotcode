import * as vscode from "vscode";
import { DebugManager } from "./debugmanager";
import { LanguageClientsManager } from "./languageclientsmanger";
import { PythonManager } from "./pythonmanger";
import { TestControllerManager } from "./testcontrollermanager";

class TerminalLink extends vscode.TerminalLink {
  constructor(public path: string, startIndex: number, length: number, tooltip?: string) {
    super(startIndex, length, tooltip);
  }
}

let languageClientManger: LanguageClientsManager;

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
                line.startsWith("Log:") ? "Open log." : "Open report."
              ),
            ];
          }
        }

        return [];
      },
      handleTerminalLink(link: TerminalLink) {
        vscode.env.openExternal(vscode.Uri.file(link.path)).then(
          () => undefined,
          () => undefined
        );
      },
    })
  );

  await languageClientManger.refresh();

  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration(async (event) => {
      for (const s of ["robotcode.python", "robotcode.languageServer", "robotcode.robot", "robotcode.robocop"]) {
        if (event.affectsConfiguration(s)) {
          await languageClientManger.refresh();
        }
      }
    })
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
