import * as net from "net";
import * as path from "path";
import * as vscode from "vscode";
import { LanguageClient, LanguageClientOptions, ServerOptions } from "vscode-languageclient/node";
import { sleep, Mutex } from "./utils";

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
        const pythonExtension = vscode.extensions.getExtension("ms-python.python")!;
        let pythonExtensionPythonPath: string[] | undefined = pythonExtension.exports.settings.getExecutionDetails(
            folder?.uri
        )?.execCommand;

        if (pythonExtensionPythonPath !== undefined) {
            result = pythonExtensionPythonPath.join(" ");
        }
    }

    return result;
}

let clientsMutex = new Mutex();
let clients: Map<string, LanguageClient> = new Map();

async function pythonExcetionDidChangeExecutionDetails(uri: vscode.Uri | undefined) {
    if (uri && clients.has(uri.toString())) {
        await clientsMutex.dispatch(async () => {
            let client = clients.get(uri.toString());
            clients.delete(uri.toString());
            await client?.stop();
        });

        await getLanguageClientForResource(uri);
    }
}

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

async function getLanguageClientForDocument(document: vscode.TextDocument): Promise<LanguageClient | undefined> {
    if (document.languageId !== "robotframework") return;

    return await getLanguageClientForResource(document.uri);
}

async function getLanguageClientForResource(resource: string | vscode.Uri): Promise<LanguageClient | undefined> {
    let client = await clientsMutex.dispatch(async () => {
        let uri = resource instanceof vscode.Uri ? resource : vscode.Uri.parse(resource);
        let workspaceFolder = vscode.workspace.getWorkspaceFolder(uri);

        if (!workspaceFolder) {
            return undefined;
        }

        workspaceFolder = getOuterMostWorkspaceFolder(workspaceFolder);

        var result = clients.get(workspaceFolder.uri.toString());

        if (!result) {
            let config = vscode.workspace.getConfiguration(CONFIG_SECTION, uri);

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
            result = new LanguageClient(name, serverOptions, clientOptions);
            clients.set(workspaceFolder.uri.toString(), result);
        }
        return result;
    });

    if (client) {
        if (client.needsStart()) {
            client.start();
        }

        var counter = 0;
        while (!client.initializeResult && counter < 10_000) {
            await sleep(100);
            counter++;
        }

        await client.onReady().catch((reason) => {
            OUTPUT_CHANNEL.appendLine("puhhh: " + reason);
        });
    }

    return client;
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

    if (!pythonCommand) {
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

        if (debugConfiguration.attachPython == undefined) debugConfiguration.attachPython = false;

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

async function getCurrentTestFromActiveResource(
    resource: string | vscode.Uri | undefined,
    selection?: vscode.Selection
): Promise<string | undefined> {
    if (resource === undefined) return;

    let uri = resource instanceof vscode.Uri ? resource : vscode.Uri.parse(resource);
    let folder = vscode.workspace.getWorkspaceFolder(uri);
    if (!folder) return;

    if (!vscode.window.activeTextEditor) return;

    if (vscode.window.activeTextEditor.document.uri.toString() != uri.toString()) return;

    if (selection === undefined) selection = vscode.window.activeTextEditor.selection;

    let client = await getLanguageClientForResource(resource);

    if (!client) return;

    try {
        return (
            (await client?.sendRequest<string | undefined>("robotcode/getTestFromPosition", {
                textDocument: { uri: uri.toString() },
                position: selection.active,
            })) ?? undefined
        );
    } catch {}

    return;
}

interface Test {
    name: string;
    source: {
        uri: string;
    };
    lineNo: number;
}
async function getTestsFromResource(resource: string | vscode.Uri | undefined): Promise<Test[] | undefined> {
    if (resource === undefined) return [];

    let uri = resource instanceof vscode.Uri ? resource : vscode.Uri.parse(resource);
    let folder = vscode.workspace.getWorkspaceFolder(uri);
    if (!folder) return [];

    let client = await getLanguageClientForResource(resource);

    if (!client) return;

    let result =
        (await client.sendRequest<Test[]>("robotcode/getTests", {
            textDocument: { uri: uri.toString() },
        })) ?? undefined;

    return result;
}

async function getTestFromResource(resource: string | vscode.Uri | undefined): Promise<string | string[] | undefined> {
    var result = await getCurrentTestFromActiveResource(resource);
    if (!result) {
        let tests = await getTestsFromResource(resource);
        if (tests) {
            let items = tests.map((t) => {
                return { label: t.name, picked: false, description: "" };
            });
            if (items.length > 0) {
                items[0].picked = true;
                items[0].description = "(Default)";
            }
            let selection = await vscode.window.showQuickPick(items, { title: "Select test(s)" });
            if (selection) {
                return selection.label;
            }
        }
    }
    return result;
}

async function debugSuiteOrTestcase(
    resource: string | vscode.Uri | undefined,
    testcases?: string | string[],
    options?: vscode.DebugSessionOptions
) {
    if (resource === undefined) return;

    let uri = resource instanceof vscode.Uri ? resource : vscode.Uri.parse(resource);

    let folder = vscode.workspace.getWorkspaceFolder(uri);

    let config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);

    var args = [];

    if (testcases) {
        if (!(testcases instanceof Array)) {
            testcases = [testcases];
        }
        for (var testcase of testcases) {
            args.push("-t");
            args.push(testcase.toString());
        }
    }

    var template = config.get("debug.defaultConfiguration", {});

    vscode.debug.startDebugging(
        folder,
        {
            ...template,
            ...{
                type: "robotcode",
                name: `robotcode: Suite: ${resource}${testcases ? " Testcase: " + testcases : ""}`,
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
            {
                parentSession: session,
                compact: true,
                consoleMode: vscode.DebugConsoleMode.MergeWithParent,
            }
        );
    }
}

async function onRobotExited(session: vscode.DebugSession, outputFile?: string, logFile?: string, reportFile?: string) {
    if (reportFile) {
        let config = vscode.workspace.getConfiguration(CONFIG_SECTION, session.workspaceFolder);

        switch (config.get<string>("run.openReportAfterRun")) {
            case "disabled":
                return;
            case "external":
                vscode.env.openExternal(vscode.Uri.file(reportFile));
        }
    }
}

async function updateEditorContext(editor?: vscode.TextEditor) {
    if (editor === undefined) editor = vscode.window.activeTextEditor;

    var inTest = false;
    if (editor && editor == vscode.window.activeTextEditor && editor.document.languageId == "robotframework") {
        let currentTest = await getCurrentTestFromActiveResource(editor.document.uri);
        inTest = currentTest !== undefined && currentTest !== "";
    }

    vscode.commands.executeCommand("setContext", "robotCode.editor.inTest", inTest);
}

export async function activateAsync(context: vscode.ExtensionContext) {
    OUTPUT_CHANNEL.appendLine("Activate RobotCode Extension.");
    extensionContext = context;

    pythonLanguageServerMain = context.asAbsolutePath(path.join("robotcode", "language_server", "__main__.py"));
    pythonDebugAdapterMain = context.asAbsolutePath(path.join("robotcode", "debug_adapter", "__main__.py"));

    OUTPUT_CHANNEL.appendLine("Try to activate Python extension.");
    const pythonExtension = vscode.extensions.getExtension("ms-python.python")!;

    await pythonExtension.activate();

    OUTPUT_CHANNEL.appendLine("Python Extension is active");

    context.subscriptions.push(
        pythonExtension.exports.settings.onDidChangeExecutionDetails(pythonExcetionDidChangeExecutionDetails),
        vscode.commands.registerCommand("robotcode.runSuite", async (resource) => {
            return await debugSuiteOrTestcase(resource ?? vscode.window.activeTextEditor?.document.uri, undefined, {
                noDebug: true,
            });
        }),

        vscode.commands.registerCommand("robotcode.debugSuite", async (resource) => {
            return await debugSuiteOrTestcase(resource ?? vscode.window.activeTextEditor?.document.uri, undefined);
        }),

        vscode.commands.registerCommand(
            "robotcode.runTest",
            async (resource: vscode.Uri | string | undefined, test) => {
                let res = resource ?? vscode.window.activeTextEditor?.document.uri;

                let realTest =
                    (test !== undefined && typeof test === "string" ? test.toString() : undefined) ??
                    (await getTestFromResource(res));
                if (!realTest) return;

                return await debugSuiteOrTestcase(res, realTest, {
                    noDebug: true,
                });
            }
        ),

        vscode.commands.registerCommand(
            "robotcode.debugTest",
            async (resource: vscode.Uri | string | undefined, test) => {
                let res = resource ?? vscode.window.activeTextEditor?.document.uri;

                let realTest =
                    (test !== undefined && typeof test === "string" ? test.toString() : undefined) ??
                    (await getTestFromResource(res));
                if (!realTest) return;

                return await debugSuiteOrTestcase(res, realTest);
            }
        ),
        vscode.workspace.onDidChangeWorkspaceFolders(async (event) => {
            for (let folder of event.removed) {
                await clientsMutex.dispatch(async () => {
                    _sortedWorkspaceFolders = undefined;

                    let client = clients.get(folder.uri.toString());
                    if (client) {
                        clients.delete(folder.uri.toString());
                        client.stop();
                    }
                });
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
                        await onRobotExited(
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
                        vscode.env.openExternal(vscode.Uri.file(link.path));
                        break;
                }
            },
        }),

        vscode.workspace.onDidChangeConfiguration((event) => {
            for (let s of [
                //"python.pythonPath",
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
        }),
        vscode.window.onDidChangeTextEditorSelection(async (event) => {
            await updateEditorContext(event.textEditor);
        }),
        vscode.workspace.onDidOpenTextDocument(getLanguageClientForDocument),

        vscode.languages.registerInlineValuesProvider("robotframework", {
            provideInlineValues(
                document: vscode.TextDocument,
                viewPort: vscode.Range,
                context: vscode.InlineValueContext,
                token: vscode.CancellationToken
            ): vscode.ProviderResult<vscode.InlineValue[]> {
                const allValues: vscode.InlineValue[] = [];

                for (
                    let l = viewPort.start.line;
                    l <= Math.min(viewPort.end.line, context.stoppedLocation.end.line);
                    l++
                ) {
                    const line = document.lineAt(l);
                    let text = line.text.split("#")[0];

                    const variableMatches =
                        /([$@&%]\{)(?:((?:\d+\.?\d*)|(?:0x[\/da-f]+)|(?:0o[0-7]+)|(?:0b[01]+))|(true|false|none|null|empty|space|\/|:|\\n)|((.+?}*)))(\})(?:(\[)(?:(\d+)|(.*?))?(\]))?/gi;

                    let match;
                    while ((match = variableMatches.exec(text))) {
                        let varName = match[0];

                        const rng = new vscode.Range(l, match.index, l, match.index + varName.length);
                        allValues.push(new vscode.InlineValueVariableLookup(rng, varName, false));
                    }
                }
                return allValues;
            },
        })
    );

    for (let document of vscode.workspace.textDocuments) {
        getLanguageClientForDocument(document);
    }

    updateEditorContext();
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
