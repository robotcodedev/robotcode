import * as net from 'net';
import * as path from 'path';
import * as vscode from 'vscode';

import { LanguageClient, LanguageClientOptions, ServerOptions, TransportKind } from 'vscode-languageclient/node';

const DEFAULT_TCP_PORT = 6601;
const CONFIG_SECTION = "robotcode";
const OUTPUT_CHANNEL_NAME = "RobotCode";
const OUTPUT_CHANNEL = vscode.window.createOutputChannel(OUTPUT_CHANNEL_NAME);

var extensionContext: vscode.ExtensionContext | undefined = undefined;
var pythonLanguageServerMain: string | undefined;

let clients: Map<string, LanguageClient> = new Map();

let _sortedWorkspaceFolders: string[] | undefined;
function sortedWorkspaceFolders(): string[] {
    if (_sortedWorkspaceFolders === void 0) {
        _sortedWorkspaceFolders = vscode.workspace.workspaceFolders ? vscode.workspace.workspaceFolders.map(folder => {
            let result = folder.uri.toString();
            if (result.charAt(result.length - 1) !== '/') {
                result = result + '/';
            }
            return result;
        }).sort(
            (a, b) => {
                return a.length - b.length;
            }
        ) : [];
    }
    return _sortedWorkspaceFolders;
}
vscode.workspace.onDidChangeWorkspaceFolders(() => _sortedWorkspaceFolders = undefined);

function getOuterMostWorkspaceFolder(folder: vscode.WorkspaceFolder): vscode.WorkspaceFolder {
    let sorted = sortedWorkspaceFolders();
    for (let element of sorted) {
        let uri = folder.uri.toString();
        if (uri.charAt(uri.length - 1) !== '/') {
            uri = uri + '/';
        }
        if (uri.startsWith(element)) {
            return vscode.workspace.getWorkspaceFolder(vscode.Uri.parse(element))!;
        }
    }
    return folder;
}


function startLanguageClientForDocument(document: vscode.TextDocument) {
    if (document.languageId !== 'robotframework') {
        return;
    }

    let uri = document.uri;

    let workspaceFolder = vscode.workspace.getWorkspaceFolder(uri);

    // Files outside a folder can't be handled. This might depend on the language.
    // Single file languages like JSON might handle files outside the workspace folders.
    if (!workspaceFolder) {
        return;
    }

    // If we have nested workspace folders we only start a server on the outer most workspace folder.
    workspaceFolder = getOuterMostWorkspaceFolder(workspaceFolder);

    if (!clients.has(workspaceFolder.uri.toString())) {
        let config = vscode.workspace.getConfiguration(CONFIG_SECTION, document);

        let mode = config.get<string>("language-server.mode", "stdio");

        const serverOptions: ServerOptions = mode === 'tcp' ? getServerOptionsTCP(workspaceFolder) : getServerOptionsStdIo(workspaceFolder, document);
        let name = `RobotCode Language Server mode=${mode} for workspace "${workspaceFolder.name}"`;

        // set the output channel only if we are running with debug and not in tcp mode
        let outputChannel = mode === 'stdio' ? vscode.window.createOutputChannel(name) : undefined;

        let clientOptions: LanguageClientOptions = {
            documentSelector: [
                { scheme: 'file', language: 'robotframework', pattern: `${workspaceFolder.uri.fsPath}/**/*` }
            ],
            synchronize: {
                configurationSection: [CONFIG_SECTION, "python"]
            },
            initializationOptions: {                
                "storageUri": extensionContext?.storageUri?.toString(),                
                "globalStorageUri": extensionContext?.globalStorageUri?.toString()
            },
            diagnosticCollectionName: 'robotcode',
            workspaceFolder: workspaceFolder,
            outputChannel: outputChannel
        };
        OUTPUT_CHANNEL.appendLine(`start Language client: ${name}`);
        let client = new LanguageClient(name, serverOptions, clientOptions);

        client.start();

        clients.set(workspaceFolder.uri.toString(), client);
    }
}

function getServerOptionsTCP(folder: vscode.WorkspaceFolder) {
    let config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);
    let port = config.get<number>("language-server.tcp-port", DEFAULT_TCP_PORT);
    if (port === 0) {
        port = DEFAULT_TCP_PORT;
    }
    const serverOptions: ServerOptions = function () {
        return new Promise((resolve, reject) => {
            var client = new net.Socket();
            client.on("error", function (err) {
                reject(err);
            });            
            client.connect(port, "127.0.0.1", function () {
                resolve({
                    reader: client,
                    writer: client
                });
            });
        });
    };
    return serverOptions;
}

function getServerOptionsStdIo(folder: vscode.WorkspaceFolder, document: vscode.TextDocument) {

    let config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);
    let serverArgs = config.get<Array<string>>("language-server.args", []);
    const extension = vscode.extensions.getExtension('ms-python.python')!;
    const pythonPath: string[] = extension.exports.settings.getExecutionDetails(document.uri)?.execCommand;
    if (pythonPath === undefined) {
        throw new Error("Can't get valid python executable");
    }

    var args: Array<string> = [
        "-u",
        pythonLanguageServerMain!,
        "--mode", "stdio",
        //"--debug",
        //"--debugpy",
        //"--debugpy-wait-for-client"
    ];

    const serverOptions: ServerOptions = {
        command: pythonPath.join(" "),
        args: args.concat(serverArgs),
        options: {
            cwd: folder.uri.fsPath,
            // detached: true
        }
    };
    return serverOptions;
}


export async function activateAsync(context: vscode.ExtensionContext) {

    OUTPUT_CHANNEL.appendLine("Activate RobotCode Extension.");
    extensionContext = context;    

    pythonLanguageServerMain = context.asAbsolutePath(path.join('robotcode', 'server', '__main__.py'));

    OUTPUT_CHANNEL.appendLine("Try to activate Python extension.");
    const extension = vscode.extensions.getExtension('ms-python.python')!;

    await extension.activate().then(function () {
        OUTPUT_CHANNEL.appendLine("Python Extension is active");
    });

    context.subscriptions.push(extension.exports.settings.onDidChangeExecutionDetails((uri: vscode.Uri) => {
        OUTPUT_CHANNEL.appendLine(uri.toString());
    }));

    context.subscriptions.push(vscode.commands.registerCommand('robotcode.helloWorld', async (resource, some) => {

        const p = extension.exports.settings.getExecutionDetails();
        OUTPUT_CHANNEL.appendLine(p.execCommand.join());

        const pythonPath = extension.exports.settings.getExecutionDetails(resource);

        vscode.window.showInformationMessage('Hello World from robotcode! ' + pythonPath.execCommand.join());
    }));

    context.subscriptions.push(vscode.workspace.onDidOpenTextDocument(startLanguageClientForDocument));
    vscode.workspace.textDocuments.forEach(startLanguageClientForDocument);

    context.subscriptions.push(vscode.workspace.onDidChangeWorkspaceFolders((event) => {
        for (let folder of event.removed) {
            let client = clients.get(folder.uri.toString());
            if (client) {
                clients.delete(folder.uri.toString());
                client.stop();
            }
        }
    }));

    vscode.workspace.onDidChangeConfiguration(event => {
        for (let s of ["robotcode.language-server.mode", "robotcode.language-server.tcp-port", "robotcode.language-server.args", "robotcode.language-server.python", "python.pythonPath"]) {
            if (event.affectsConfiguration(s)) {
                vscode.window.showWarningMessage('Please use the "Reload Window" action for changes in ' + s + ' to take effect.', ...["Reload Window"]).then((selection) => {
                    if (selection === "Reload Window") {
                        vscode.commands.executeCommand("workbench.action.reloadWindow");
                    }
                });
                return;
            }
        }
    });
}


function displayProgress(promise: Promise<any>) {
    const progressOptions: vscode.ProgressOptions = { location: vscode.ProgressLocation.Window, title: "RobotCode extension loading ..." };
    vscode.window.withProgress(progressOptions, () => promise);
}

export async function activate(context: vscode.ExtensionContext) {
    displayProgress(activateAsync(context));
}

export function deactivate(): Thenable<void> {
    let promises: Thenable<void>[] = [];

    for (let client of clients.values()) {
        promises.push(client.stop());
    }
    return Promise.all(promises).then(() => undefined);
}
