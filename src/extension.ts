import * as net from "net";
import * as path from "path";
import * as vscode from "vscode";
import { LanguageClient, LanguageClientOptions, ServerOptions } from "vscode-languageclient/node";

const LANGUAGE_SERVER_DEFAULT_TCP_PORT = 6610;
const LANGUAGE_SERVER_DEFAULT_HOST = "127.0.0.1";

const DEBUG_ADAPTER_DEFAULT_TCP_PORT = 6611;
const DEBUG_ADAPTER_DEFAULT_HOST = "127.0.0.1";

const CONFIG_SECTION = "robotcode";
const OUTPUT_CHANNEL_NAME = "RobotCode";
const OUTPUT_CHANNEL = vscode.window.createOutputChannel(OUTPUT_CHANNEL_NAME);

var extensionContext: vscode.ExtensionContext | undefined = undefined;
var pythonLanguageServerMain: string | undefined;
var pythonDebugAdapterMain: string | undefined;

function getPythonCommand(folder: vscode.WorkspaceFolder | undefined): string | undefined {
    let config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);
    var result: string | undefined = undefined;

    let configPython = config.get<string>("python");

    if (configPython !== undefined && configPython != "") {
        result = configPython;
    } else {
        const extension = vscode.extensions.getExtension("ms-python.python")!;
        let pythonExtensionPythonPath: string[] | undefined = extension.exports.settings.getExecutionDetails(
            folder?.uri
        )?.execCommand;

        if (pythonExtensionPythonPath !== undefined) {
            result = pythonExtensionPythonPath.join(" ");
        }
    }

    return result;
}

let clients: Map<string, LanguageClient> = new Map();

let _sortedWorkspaceFolders: string[] | undefined;
function sortedWorkspaceFolders(): string[] {
    if (_sortedWorkspaceFolders === undefined) {
        _sortedWorkspaceFolders = vscode.workspace.workspaceFolders
            ? vscode.workspace.workspaceFolders
                  .map((folder) => {
                      let result = folder.uri.toString();
                      if (result.charAt(result.length - 1) !== "/") {
                          result = result + "/";
                      }
                      return result;
                  })
                  .sort((a, b) => {
                      return a.length - b.length;
                  })
            : [];
    }
    return _sortedWorkspaceFolders;
}
vscode.workspace.onDidChangeWorkspaceFolders(() => (_sortedWorkspaceFolders = undefined));

function getOuterMostWorkspaceFolder(folder: vscode.WorkspaceFolder): vscode.WorkspaceFolder {
    let sorted = sortedWorkspaceFolders();
    for (let element of sorted) {
        let uri = folder.uri.toString();
        if (uri.charAt(uri.length - 1) !== "/") {
            uri = uri + "/";
        }
        if (uri.startsWith(element)) {
            return vscode.workspace.getWorkspaceFolder(vscode.Uri.parse(element))!;
        }
    }
    return folder;
}

function startLanguageClientForDocument(document: vscode.TextDocument) {
    if (document.languageId !== "robotframework") {
        return;
    }

    let workspaceFolder = vscode.workspace.getWorkspaceFolder(document.uri);

    if (!workspaceFolder) {
        return;
    }

    workspaceFolder = getOuterMostWorkspaceFolder(workspaceFolder);

    if (!clients.has(workspaceFolder.uri.toString())) {
        let config = vscode.workspace.getConfiguration(CONFIG_SECTION, document);

        let mode = config.get<string>("languageServer.mode", "stdio");

        const serverOptions: ServerOptions =
            mode === "tcp" ? getServerOptionsTCP(workspaceFolder) : getServerOptionsStdIo(workspaceFolder);
        let name = `RobotCode Language Server mode=${mode} for workspace folder "${workspaceFolder.name}"`;

        let outputChannel = mode === "stdio" ? vscode.window.createOutputChannel(name) : undefined;

        let clientOptions: LanguageClientOptions = {
            documentSelector: [
                { scheme: "file", language: "robotframework", pattern: `${workspaceFolder.uri.fsPath}/**/*` },
            ],
            synchronize: {
                configurationSection: [CONFIG_SECTION, "python"],
            },
            initializationOptions: {
                storageUri: extensionContext?.storageUri?.toString(),
                globalStorageUri: extensionContext?.globalStorageUri?.toString(),
            },
            diagnosticCollectionName: "robotcode",
            workspaceFolder: workspaceFolder,
            outputChannel: outputChannel,
            markdown: {
                isTrusted: true,
            },
            progressOnInitialization: true,
        };
        OUTPUT_CHANNEL.appendLine(`start Language client: ${name}`);
        let client = new LanguageClient(name, serverOptions, clientOptions);

        client.start();

        clients.set(workspaceFolder.uri.toString(), client);
    }
}

function getServerOptionsTCP(folder: vscode.WorkspaceFolder) {
    let config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);
    let port = config.get<number>("languageServer.tcpPort", LANGUAGE_SERVER_DEFAULT_TCP_PORT);
    if (port === 0) {
        port = LANGUAGE_SERVER_DEFAULT_TCP_PORT;
    }
    const serverOptions: ServerOptions = function () {
        return new Promise((resolve, reject) => {
            var client = new net.Socket();
            client.on("error", function (err) {
                reject(err);
            });
            let host = LANGUAGE_SERVER_DEFAULT_HOST;
            client.connect(port, host, function () {
                resolve({
                    reader: client,
                    writer: client,
                });
            });
        });
    };
    return serverOptions;
}

function getServerOptionsStdIo(folder: vscode.WorkspaceFolder) {
    let config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);

    let pythonCommand = getPythonCommand(folder);

    if (pythonCommand === undefined) {
        throw new Error("Can't find a valid python executable.");
    }

    let serverArgs = config.get<Array<string>>("languageServer.args", []);

    var args: Array<string> = ["-u", pythonLanguageServerMain!, "--mode", "stdio"];

    const serverOptions: ServerOptions = {
        command: pythonCommand!,
        args: args.concat(serverArgs),
        options: {
            cwd: folder.uri.fsPath,
            // detached: true
        },
    };
    return serverOptions;
}

class RobotCodeDebugConfigurationProvider implements vscode.DebugConfigurationProvider {
    resolveDebugConfiguration?(
        folder: vscode.WorkspaceFolder | undefined,
        debugConfiguration: vscode.DebugConfiguration,
        token?: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.DebugConfiguration> {
        return debugConfiguration;
    }

    resolveDebugConfigurationWithSubstitutedVariables?(
        folder: vscode.WorkspaceFolder | undefined,
        debugConfiguration: vscode.DebugConfiguration,
        token?: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.DebugConfiguration> {
        let config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);
        debugConfiguration.python = getPythonCommand(folder);

        if (!debugConfiguration.pythonPath) debugConfiguration.pythonPath = [];

        debugConfiguration.pythonPath = config
            .get<Array<string>>("robot.pythonPath", [])
            .concat(debugConfiguration.pythonPath);

        if (!debugConfiguration.variables) debugConfiguration.variables = {};

        debugConfiguration.variables = Object.assign(
            {},
            config.get<Object>("robot.variables", {}),
            debugConfiguration.variables
        );
        
        return debugConfiguration;
    }
}

class RobotCodeDebugAdapterDescriptorFactory implements vscode.DebugAdapterDescriptorFactory {
    createDebugAdapterDescriptor(
        session: vscode.DebugSession,
        executable: vscode.DebugAdapterExecutable | undefined
    ): vscode.ProviderResult<vscode.DebugAdapterDescriptor> {
        let config = vscode.workspace.getConfiguration(CONFIG_SECTION, session.workspaceFolder);

        let mode = config.get("debugAdapter.mode", "stdio");

        switch (mode) {
            case "stdio":
                let pythonCommand = getPythonCommand(session.workspaceFolder);

                if (pythonCommand === undefined) {
                    throw new Error("Can't get a valid python command.");
                }

                let debugAdapterArgs = config.get<Array<string>>("debugAdapter.args", []);

                var args: Array<string> = ["-u", pythonDebugAdapterMain!, "--mode", "stdio"].concat(debugAdapterArgs);

                const options: vscode.DebugAdapterExecutableOptions = {
                    env: {},
                    cwd: session.workspaceFolder?.uri.fsPath,
                };

                return new vscode.DebugAdapterExecutable(pythonCommand, args, options);

            case "tcp":
                let port =
                    config.get("debugAdapter.tcpPort", DEBUG_ADAPTER_DEFAULT_TCP_PORT) ||
                    DEBUG_ADAPTER_DEFAULT_TCP_PORT;

                let host = config.get("debugAdapter.host", DEBUG_ADAPTER_DEFAULT_HOST) || DEBUG_ADAPTER_DEFAULT_HOST;

                return new vscode.DebugAdapterServer(port, host);
            default:
                throw new Error("Unsupported Mode.");
        }
    }
}

export async function activateAsync(context: vscode.ExtensionContext) {
    OUTPUT_CHANNEL.appendLine("Activate RobotCode Extension.");
    extensionContext = context;

    pythonLanguageServerMain = context.asAbsolutePath(path.join("robotcode", "language_server", "__main__.py"));
    pythonDebugAdapterMain = context.asAbsolutePath(path.join("robotcode", "debug_adapter", "__main__.py"));

    OUTPUT_CHANNEL.appendLine("Try to activate Python extension.");
    const extension = vscode.extensions.getExtension("ms-python.python")!;

    await extension.activate().then(function () {
        OUTPUT_CHANNEL.appendLine("Python Extension is active");
    });

    context.subscriptions.push(
        extension.exports.settings.onDidChangeExecutionDetails((uri: vscode.Uri) => {
            OUTPUT_CHANNEL.appendLine(uri.toString());
        }),

        vscode.commands.registerCommand("robotcode.runSuite", async (resource) => {
            vscode.window.showInformationMessage(`robotcode.runSuite currently not implemented (${resource})`);
        }),

        vscode.commands.registerCommand("robotcode.debugSuite", async (resource) => {
            vscode.window.showInformationMessage(`robotcode.debugSuite currently not implemented (${resource})`);
        }),

        vscode.commands.registerCommand("robotcode.runTest", async (resource, test) => {
            vscode.window.showInformationMessage(`robotcode.runTest currently not implemented (${resource} - ${test})`);
        }),

        vscode.commands.registerCommand("robotcode.debugTest", async (resource, test) => {
            vscode.window.showInformationMessage(
                `robotcode.debugTest currently not implemented (${resource} - ${test})`
            );
        }),
        vscode.workspace.onDidChangeWorkspaceFolders((event) => {
            for (let folder of event.removed) {
                let client = clients.get(folder.uri.toString());
                if (client) {
                    clients.delete(folder.uri.toString());
                    client.stop();
                }
            }
        }),
        vscode.debug.registerDebugConfigurationProvider("robotcode", new RobotCodeDebugConfigurationProvider()),
        vscode.debug.registerDebugAdapterDescriptorFactory("robotcode", new RobotCodeDebugAdapterDescriptorFactory()),
        vscode.debug.registerDebugAdapterTrackerFactory("robotcode", {
            createDebugAdapterTracker(session: vscode.DebugSession) {
                return {
                    onWillStartSession: () => OUTPUT_CHANNEL.appendLine(`DEBUG_ADAPTER start session`),
                    onWillStopSession: () => OUTPUT_CHANNEL.appendLine(`DEBUG_ADAPTER stop session`),
                    onWillReceiveMessage: (m) =>
                        OUTPUT_CHANNEL.appendLine(`DEBUG_ADAPTER > ${JSON.stringify(m, undefined, 2)}`),
                    onDidSendMessage: (m) =>
                        OUTPUT_CHANNEL.appendLine(`DEBUG_ADAPTER < ${JSON.stringify(m, undefined, 2)}`),
                    onError: (e) =>
                        OUTPUT_CHANNEL.appendLine(`DEBUG_ADAPTER ERROR: ${JSON.stringify(e, undefined, 2)}`),
                    onExit: (c, s) => OUTPUT_CHANNEL.appendLine(`DEBUG_ADAPTER EXIT code ${c} signal ${s}`),
                };
            },
        })
    );

    vscode.workspace.onDidChangeConfiguration((event) => {
        for (let s of [
            "python.pythonPath",
            "robotcode.python",
            "robotcode.languageServer.mode",
            "robotcode.languageServer.tcpPort",
            "robotcode.languageServer.args",
            "robotcode.debugAdapter.mode",
            "robotcode.debugAdapter.tcpPort",
            "robotcode.debugAdapter.args",
            "robotcode.robot.environment",
            "robotcode.robot.variables",
            "robotcode.robot.args",
        ]) {
            if (event.affectsConfiguration(s)) {
                vscode.window
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
    });

    vscode.workspace.onDidOpenTextDocument(startLanguageClientForDocument);
    vscode.workspace.textDocuments.forEach(startLanguageClientForDocument);
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
    let promises: Thenable<void>[] = [];

    for (let client of clients.values()) {
        promises.push(client.stop());
    }
    return Promise.all(promises).then(() => undefined);
}
