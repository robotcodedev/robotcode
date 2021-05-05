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

        try {
            if (path.isAbsolute(debugConfiguration.target))
                debugConfiguration.target = path.relative(debugConfiguration.cwd, debugConfiguration.target).toString();
        } catch {}

        if (!debugConfiguration.python) debugConfiguration.python = getPythonCommand(folder);

        if (!debugConfiguration.robotPythonPath) debugConfiguration.robotPythonPath = [];
        debugConfiguration.robotPythonPath = config
            .get<Array<string>>("robot.pythonPath", [])
            .concat(debugConfiguration.robotPythonPath);

        if (!debugConfiguration.args) debugConfiguration.args = [];
        debugConfiguration.args = config.get<Array<string>>("robot.args", []).concat(debugConfiguration.args);

        if (!debugConfiguration.variables) debugConfiguration.variables = {};
        debugConfiguration.variables = Object.assign(
            {},
            config.get<Object>("robot.variables", {}),
            debugConfiguration.variables
        );

        if (!debugConfiguration.env) debugConfiguration.env = {};
        debugConfiguration.env = Object.assign({}, config.get<Object>("robot.env", {}), debugConfiguration.env);

        if (debugConfiguration.attachPython == undefined) debugConfiguration.attachPython = true;

        if (debugConfiguration.noDebug) {
            debugConfiguration.attachPython = false;
        }

        var template = config.get("debug.defaultConfiguration", {});

        return { ...template, ...debugConfiguration };
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

async function debugSuiteOrTestcase(
    resource: string | vscode.Uri,
    testcase?: string,
    options?: vscode.DebugSessionOptions
) {
    let uri = resource instanceof vscode.Uri ? resource : vscode.Uri.parse(resource);

    let folder = vscode.workspace.getWorkspaceFolder(uri);

    let config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);

    var args = [];

    if (testcase) {
        args.push("-t");
        args.push(testcase);
    }

    var template = config.get("debug.defaultConfiguration", {});

    vscode.debug.startDebugging(
        folder,
        {
            ...template,
            ...{
                type: "robotcode",
                name: `robotcode: Suite: ${resource}${testcase ? " Testcase: " + testcase : ""}`,
                request: "launch",
                cwd: folder?.uri.fsPath,
                target: uri.fsPath,
                args: args,
                console: config.get("debug.defaultConsole", "integratedTerminal"),
            },
        },
        options
    );
}

async function attachPython(session: vscode.DebugSession, event: string, options?: any) {
    if (
        session.type == "robotcode" &&
        !session.configuration.noDebug &&
        session.configuration.attachPython &&
        options &&
        options.port
    ) {
        vscode.debug.startDebugging(
            session.workspaceFolder,
            {
                ...session.configuration.pythonConfiguration,
                ...{
                    type: "python",
                    name: `Python ${session.name}`,
                    request: "attach",
                    connect: {
                        port: options.port,
                    },
                },
            },
            session
        );
    }
}

async function openReportInternal(reportFile: string) {
    let panel = vscode.window.createWebviewPanel("robotcode.report", "Robot Report", vscode.ViewColumn.Active, {
        enableScripts: true,
        enableFindWidget: true,
        enableCommandUris: true,
        retainContextWhenHidden: true,
        localResourceRoots: [vscode.Uri.file(path.dirname(reportFile))],
    });

    let uri = vscode.Uri.file(reportFile);

    panel.webview.html = `<!DOCTYPE html>
<html>

<head>
<meta http-equiv="Content-Security-Policy" content="
default-src none 'unsafe-inline'; 
frame-src ${panel.webview.cspSource} 'unsafe-inline';
style-src ${panel.webview.cspSource} 'unsafe-inline'; 
img-src ${panel.webview.cspSource}; 
script-src ${panel.webview.cspSource} 'unsafe-inline';">  

<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Robot Report</title>
</head>

<body>
<script>
function frame_loaded() {
function WhichLinkWasClicked(evt) {
alert(evt.target);
//evt.preventDefault();
}

var links = myFrame.document.querySelectorAll('a');
for (var link of links) {
console.log("blah link");
link.addEventListener('click', WhichLinkWasClicked);
}
}
</script>

<iframe style="position: absolute; height: 100%; width: 100%; border: none" src="${panel.webview
        .asWebviewUri(uri)
        .toString()}" name="myFrame"
onload="frame_loaded()" sandbox="allow-scripts allow-same-origin" referrerpolicy="origin" >
</iframe>
</body>

</html>`;
    //panel.webview.html = fs.readFileSync(event.body?.reportFile).toString();
    // panel.webview.onDidReceiveMessage(async (event) => {
    //     console.log(`hello ${JSON.stringify(event)}`);
    // });
}

async function on_robotExited(
    session: vscode.DebugSession,
    outputFile?: string,
    logFile?: string,
    reportFile?: string
) {
    if (reportFile) {
        let config = vscode.workspace.getConfiguration(CONFIG_SECTION, session.workspaceFolder);

        switch (config.get<string>("run.openReportAfterRun")) {
            case "disabled":
                return;
            case "external":
                vscode.env.openExternal(vscode.Uri.file(reportFile));
                break;

            case "internal":
                openReportInternal(reportFile);
                break;
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
            return await debugSuiteOrTestcase(resource, undefined, { noDebug: true });
        }),

        vscode.commands.registerCommand("robotcode.debugSuite", async (resource) => {
            return await debugSuiteOrTestcase(resource, undefined);
        }),

        vscode.commands.registerCommand("robotcode.runTest", async (resource, test) => {
            return await debugSuiteOrTestcase(resource, test, { noDebug: true });
        }),

        vscode.commands.registerCommand("robotcode.debugTest", async (resource, test) => {
            return await debugSuiteOrTestcase(resource, test);
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
        // vscode.debug.registerDebugAdapterTrackerFactory("robotcode", {
        //     createDebugAdapterTracker(session: vscode.DebugSession) {
        //         return {
        //             onWillStartSession: () => OUTPUT_CHANNEL.appendLine(`DEBUG_ADAPTER start session`),
        //             onWillStopSession: () => OUTPUT_CHANNEL.appendLine(`DEBUG_ADAPTER stop session`),
        //             onWillReceiveMessage: (m) =>
        //                 OUTPUT_CHANNEL.appendLine(`DEBUG_ADAPTER > ${JSON.stringify(m, undefined, 2)}`),
        //             onDidSendMessage: (m) =>
        //                 OUTPUT_CHANNEL.appendLine(`DEBUG_ADAPTER < ${JSON.stringify(m, undefined, 2)}`),
        //             onError: (e) =>
        //                 OUTPUT_CHANNEL.appendLine(`DEBUG_ADAPTER ERROR: ${JSON.stringify(e, undefined, 2)}`),
        //             onExit: (c, s) => OUTPUT_CHANNEL.appendLine(`DEBUG_ADAPTER EXIT code ${c} signal ${s}`),
        //         };
        //     },
        // }),
        vscode.debug.onDidReceiveDebugSessionCustomEvent(async (event) => {
            if (event.session.configuration.type === "robotcode") {
                switch (event.event) {
                    case "debugpyStarted": {
                        await attachPython(event.session, event.event, event.body);
                        break;
                    }
                    case "robotExited": {
                        await on_robotExited(
                            event.session,
                            event.body.outputFile,
                            event.body.logFile,
                            event.body.reportFile
                        );
                        break;
                    }
                }
            }
        }),
        vscode.window.onDidOpenTerminal(async (terminal) => {
            console.log("ho");
        }),
        vscode.window.registerTerminalLinkProvider({
            provideTerminalLinks(context: vscode.TerminalLinkContext, token: vscode.CancellationToken) {
                console.log("ho");
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
                    case "internal":
                        openReportInternal(link.path);
                        break;
                    default:
                        vscode.env.openExternal(vscode.Uri.file(link.path));
                        break;
                }
            },
        })

        // vscode.debug.onDidStartDebugSession(async (session) => {
        //     if (session.configuration.type === "robotcode") {
        //         await attachPython(session);
        //     }
        // })
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
