import * as vscode from "vscode";
import { CONFIG_SECTION } from "./config";
import { DebugManager } from "./debugmanager";
// import { TestHub, testExplorerExtensionId } from "vscode-test-adapter-api";
// import { TestAdapterRegistrar } from "vscode-test-adapter-util";
// import { RobotTestAdapter } from "./robottestadapter";
import { LanguageClientsManager } from "./languageclientsmanger";
import { PythonManager } from "./pythonmanger";
import openExternal = require("open");

// let testHub: TestHub | undefined;

export async function activateAsync(context: vscode.ExtensionContext) {
    const outputChannel = vscode.window.createOutputChannel("RobotCode");

    outputChannel.appendLine("Activate RobotCode Extension.");

    let pythonManager = new PythonManager(context, outputChannel);

    let languageClientManger = new LanguageClientsManager(context, pythonManager, outputChannel);

    let debugManager = new DebugManager(context, pythonManager, languageClientManger, outputChannel);

    context.subscriptions.push(
        pythonManager,
        languageClientManger,
        debugManager,

        vscode.window.registerTerminalLinkProvider({
            provideTerminalLinks(context: vscode.TerminalLinkContext, token: vscode.CancellationToken) {
                if (
                    (context.line.startsWith("Log:") || context.line.startsWith("Report:")) &&
                    context.line.endsWith("html")
                ) {
                    let result = /(Log|Report):\s*(?<link>\S.*)/.exec(context.line)?.groups?.link;

                    if (result) {
                        return [
                            {
                                startIndex: context.line.indexOf(result),
                                length: result.length,
                                tooltip: "Open report.",
                                path: result,
                            },
                        ];
                    }
                }

                return [];
            },
            handleTerminalLink(link: any) {
                let config = vscode.workspace.getConfiguration(
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
            for (let s of [
                "robotcode.python",
                "robotcode.languageServer.mode",
                "robotcode.languageServer.tcpPort",
                "robotcode.languageServer.args",
            ]) {
                if (event.affectsConfiguration(s)) {
                    await vscode.window
                        .showWarningMessage(
                            'Please use the "Reload Window" action for changes in ' + s + " to take effect.",
                            ...["Reload Window"]
                        )
                        .then((selection) => {
                            if (selection === "Reload Window") {
                                vscode.commands.executeCommand("workbench.action.reloadWindow");
                            }
                        });
                    return;
                }
            }
        })
    );

    // const testExplorerExtension = vscode.extensions.getExtension<TestHub>(testExplorerExtensionId);
    // if (testExplorerExtension) {
    //     testHub = testExplorerExtension.exports;

    //     context.subscriptions.push(
    //         new TestAdapterRegistrar(testHub, (workspacefolder) => new RobotTestAdapter(workspacefolder))
    //     );
    // }

    await languageClientManger.refresh();
}

function displayProgress(promise: Promise<any>) {
    const progressOptions: vscode.ProgressOptions = {
        location: vscode.ProgressLocation.Window,
        title: "RobotCode extension loading ...",
    };
    vscode.window.withProgress(progressOptions, () => promise);
}

export async function activate(context: vscode.ExtensionContext) {
    displayProgress(activateAsync(context));
}

export async function deactivate() {
    //await stopAllClients();
}
