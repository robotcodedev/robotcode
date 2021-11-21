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
      provideTerminalLinks(context: vscode.TerminalLinkContext, _token: vscode.CancellationToken) {
        if ((context.line.startsWith("Log:") || context.line.startsWith("Report:")) && context.line.endsWith("html")) {
          const result = /(Log|Report):\s*(?<link>\S.*)/.exec(context.line)?.groups?.link;

          if (result) {
            return [new TerminalLink(result, context.line.indexOf(result), result.length, "Open report.")];
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
    }),

    vscode.workspace.onDidChangeConfiguration(async (event) => {
      for (const s of [
        "robotcode.python",
        "robotcode.languageServer.mode",
        "robotcode.languageServer.tcpPort",
        "robotcode.languageServer.args",
      ]) {
        if (event.affectsConfiguration(s)) {
          await languageClientManger.refresh();
          await testControllerManger.refresh();
        }
      }
    })
  );

  await languageClientManger.refresh();
  await testControllerManger.refresh();
}

function displayProgress<R>(promise: Promise<R>): Thenable<R> {
  const progressOptions: vscode.ProgressOptions = {
    location: vscode.ProgressLocation.Window,
    title: "RobotCode extension loading ...",
  };
  return vscode.window.withProgress(progressOptions, () => promise);
}

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  return await displayProgress(activateAsync(context));
}

export async function deactivate(): Promise<void> {
  return await languageClientManger.stopAllClients();
}
