import * as path from "path";
import * as vscode from "vscode";
import { PythonManager } from "./pythonmanger";
import { CONFIG_SECTION } from "./config";
import { LanguageClientsManager } from "./languageclientsmanger";
import openExternal = require("open");

const DEBUG_ADAPTER_DEFAULT_TCP_PORT = 6611;
const DEBUG_ADAPTER_DEFAULT_HOST = "127.0.0.1";

class RobotCodeDebugConfigurationProvider implements vscode.DebugConfigurationProvider {
    constructor(private readonly pythonManager: PythonManager) {}

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

        if (!debugConfiguration.python) debugConfiguration.python = this.pythonManager.getPythonCommand(folder);

        debugConfiguration.robotPythonPath = [
            ...config.get<Array<string>>("robot.pythonPath", []),
            ...(debugConfiguration.robotPythonPath ?? []),
        ];

        debugConfiguration.args = [...config.get<Array<string>>("robot.args", []), ...(debugConfiguration.args ?? [])];

        debugConfiguration.variables = {
            ...config.get<Object>("robot.variables", {}),
            ...(debugConfiguration.variables ?? {}),
        };

        debugConfiguration.env = { ...config.get<Object>("robot.env", {}), ...(debugConfiguration.env ?? {}) };

        // if (pythonDebugpyPath) {
        //     debugConfiguration.env = { PYTHONPATH: path.dirname(pythonDebugpyPath), ...debugConfiguration.env };
        // }

        if (!debugConfiguration.attachPython || debugConfiguration.noDebug) {
            debugConfiguration.attachPython = false;
        }

        let template = config.get("debug.defaultConfiguration", {});

        return { ...template, ...debugConfiguration };
    }
}

class RobotCodeDebugAdapterDescriptorFactory implements vscode.DebugAdapterDescriptorFactory {
    constructor(private readonly pythonManager: PythonManager) {}
    createDebugAdapterDescriptor(
        session: vscode.DebugSession,
        executable: vscode.DebugAdapterExecutable | undefined
    ): vscode.ProviderResult<vscode.DebugAdapterDescriptor> {
        let config = vscode.workspace.getConfiguration(CONFIG_SECTION, session.workspaceFolder);

        let mode = config.get("debugAdapter.mode", "stdio");

        switch (mode) {
            case "stdio":
                let pythonCommand = this.pythonManager.getPythonCommand(session.workspaceFolder);

                if (pythonCommand === undefined) {
                    throw new Error("Can't get a valid python command.");
                }

                let debugAdapterArgs = config.get<Array<string>>("debugAdapter.args", []);

                let args: Array<string> = ["-u", this.pythonManager.pythonDebugAdapterMain!, "--mode", "stdio"].concat(
                    debugAdapterArgs
                );

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

export class DebugManager {
    private _disposables: vscode.Disposable;

    constructor(
        public readonly extensionContext: vscode.ExtensionContext,
        public readonly pythonManager: PythonManager,
        public readonly languageClientsManager: LanguageClientsManager,
        public readonly outputChannel: vscode.OutputChannel
    ) {
        this._disposables = vscode.Disposable.from(
            vscode.commands.registerCommand("robotcode.runSuite", async (resource) => {
                return await this.debugSuiteOrTestcase(
                    resource ?? vscode.window.activeTextEditor?.document.uri,
                    undefined,
                    {
                        noDebug: true,
                    }
                );
            }),

            vscode.commands.registerCommand("robotcode.debugSuite", async (resource) => {
                return await this.debugSuiteOrTestcase(
                    resource ?? vscode.window.activeTextEditor?.document.uri,
                    undefined
                );
            }),

            vscode.commands.registerCommand(
                "robotcode.runTest",
                async (resource: vscode.Uri | string | undefined, test) => {
                    let res = resource ?? vscode.window.activeTextEditor?.document.uri;

                    let realTest =
                        (test !== undefined && typeof test === "string" ? test.toString() : undefined) ??
                        (await this.languageClientsManager.getTestFromResource(res));
                    if (!realTest) return;

                    return await this.debugSuiteOrTestcase(res, realTest, {
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
                        (await this.languageClientsManager.getTestFromResource(res));
                    if (!realTest) return;

                    return await this.debugSuiteOrTestcase(res, realTest);
                }
            ),
            vscode.debug.registerDebugConfigurationProvider(
                "robotcode",
                new RobotCodeDebugConfigurationProvider(this.pythonManager)
            ),
            vscode.debug.registerDebugAdapterDescriptorFactory(
                "robotcode",
                new RobotCodeDebugAdapterDescriptorFactory(this.pythonManager)
            ),
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
                            await this.attachPython(event.session, event.event, event.body);
                            break;
                        }
                        case "robotExited": {
                            await this.onRobotExited(
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
    }

    async dispose() {
        this._disposables.dispose();
    }

    async debugSuiteOrTestcase(
        resource: string | vscode.Uri | undefined,
        testcases?: string | string[],
        options?: vscode.DebugSessionOptions
    ) {
        if (resource === undefined) return;

        let uri = resource instanceof vscode.Uri ? resource : vscode.Uri.parse(resource);

        let folder = vscode.workspace.getWorkspaceFolder(uri);

        let config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);

        let args = [];

        if (testcases) {
            if (!(testcases instanceof Array)) {
                testcases = [testcases];
            }
            for (let testcase of testcases) {
                args.push("-t");
                args.push(testcase.toString());
            }
        }

        let template = config.get("debug.defaultConfiguration", {});

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

    async attachPython(session: vscode.DebugSession, event: string, options?: any) {
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
    async onRobotExited(session: vscode.DebugSession, outputFile?: string, logFile?: string, reportFile?: string) {
        if (reportFile) {
            let config = vscode.workspace.getConfiguration(CONFIG_SECTION, session.workspaceFolder);

            switch (config.get<string>("run.openReportAfterRun")) {
                case "disabled":
                    return;
                case "external":
                    openExternal(reportFile);
            }
        }
    }
}
