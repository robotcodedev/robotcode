import * as vscode from "vscode";
import { CONFIG_SECTION } from "./config";
import { DebugManager } from "./debugmanager";
import { LanguageClientsManager } from "./languageclientsmanger";
import { PythonManager } from "./pythonmanger";
import openExternal = require("open");
import { TestControllerManager } from "./testcontrollermanager";

class TerminalLink extends vscode.TerminalLink {
  constructor(public path: string, startIndex: number, length: number, tooltip?: string) {
    super(startIndex, length, tooltip);
  }
}

export async function activateAsync(context: vscode.ExtensionContext): Promise<void> {
  const outputChannel = vscode.window.createOutputChannel("RobotCode");

  outputChannel.appendLine("Activate RobotCode Extension.");

  const pythonManager = new PythonManager(context, outputChannel);

  const languageClientManger = new LanguageClientsManager(context, pythonManager, outputChannel);

  const debugManager = new DebugManager(context, pythonManager, languageClientManger, outputChannel);

  const testControllerManger = new TestControllerManager(context, languageClientManger, outputChannel);

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
        const config = vscode.workspace.getConfiguration(
          CONFIG_SECTION,
          vscode.workspace.getWorkspaceFolder(vscode.Uri.file(link.path))
        );

        switch (config.get<string>("run.openReportAfterRun")) {
          default:
            openExternal(link.path);
            break;
        }
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

function displayProgress(promise: Promise<unknown>) {
  const progressOptions: vscode.ProgressOptions = {
    location: vscode.ProgressLocation.Window,
    title: "RobotCode extension loading ...",
  };
  vscode.window.withProgress(progressOptions, () => promise);
}

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  displayProgress(activateAsync(context));
}

// eslint-disable-next-line @typescript-eslint/no-empty-function
export async function deactivate(): Promise<void> {}
