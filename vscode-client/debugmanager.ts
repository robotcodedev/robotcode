import * as path from "path";
import * as vscode from "vscode";
import { PythonManager } from "./pythonmanger";
import { CONFIG_SECTION } from "./config";
import { LanguageClientsManager } from "./languageclientsmanger";

const DEBUG_ADAPTER_DEFAULT_TCP_PORT = 6611;
const DEBUG_ADAPTER_DEFAULT_HOST = "127.0.0.1";

class RobotCodeDebugConfigurationProvider implements vscode.DebugConfigurationProvider {
  constructor(private readonly pythonManager: PythonManager) {}

  resolveDebugConfigurationWithSubstitutedVariables?(
    folder: vscode.WorkspaceFolder | undefined,
    debugConfiguration: vscode.DebugConfiguration,
    _token?: vscode.CancellationToken
  ): vscode.ProviderResult<vscode.DebugConfiguration> {
    const config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);

    try {
      if (path.isAbsolute(debugConfiguration.target)) {
        debugConfiguration.target = path.relative(debugConfiguration.cwd, debugConfiguration.target).toString();
      }
    } catch {}

    if (!debugConfiguration.python) debugConfiguration.python = this.pythonManager.getPythonCommand(folder);

    debugConfiguration.robotPythonPath = [
      ...config.get<Array<string>>("robot.pythonPath", []),
      ...(debugConfiguration.robotPythonPath ?? []),
    ];

    debugConfiguration.args = [...config.get<Array<string>>("robot.args", []), ...(debugConfiguration.args ?? [])];

    debugConfiguration.variables = {
      ...config.get<{ [Key: string]: unknown }>("robot.variables", {}),
      ...(debugConfiguration.variables ?? {}),
    };

    debugConfiguration.env = {
      ...config.get<{ [Key: string]: unknown }>("robot.env", {}),
      ...(debugConfiguration.env ?? {}),
    };

    // if (pythonDebugpyPath) {
    //     debugConfiguration.env = { PYTHONPATH: path.dirname(pythonDebugpyPath), ...debugConfiguration.env };
    // }

    if (!debugConfiguration.attachPython || debugConfiguration.noDebug) {
      debugConfiguration.attachPython = false;
    }

    const template = config.get("debug.defaultConfiguration", {});

    return { ...template, ...debugConfiguration };
  }
}

class RobotCodeDebugAdapterDescriptorFactory implements vscode.DebugAdapterDescriptorFactory {
  constructor(private readonly pythonManager: PythonManager) {}

  createDebugAdapterDescriptor(
    session: vscode.DebugSession,
    _executable: vscode.DebugAdapterExecutable | undefined
  ): vscode.ProviderResult<vscode.DebugAdapterDescriptor> {
    const config = vscode.workspace.getConfiguration(CONFIG_SECTION, session.workspaceFolder);

    const mode = config.get<string>("debugAdapter.mode", "stdio");

    switch (mode) {
      case "stdio": {
        const pythonCommand = this.pythonManager.getPythonCommand(session.workspaceFolder);

        if (pythonCommand === undefined) {
          throw new Error("Can't get a valid python command.");
        }

        const debugAdapterArgs = config.get<Array<string>>("debugAdapter.args", []);

        const args: Array<string> = ["-u", this.pythonManager.pythonDebugAdapterMain!, "--mode", "stdio"].concat(
          debugAdapterArgs
        );

        const options: vscode.DebugAdapterExecutableOptions = {
          env: {},
          cwd: session.workspaceFolder?.uri.fsPath,
        };

        return new vscode.DebugAdapterExecutable(pythonCommand, args, options);
      }
      case "tcp": {
        const port =
          config.get("debugAdapter.tcpPort", DEBUG_ADAPTER_DEFAULT_TCP_PORT) || DEBUG_ADAPTER_DEFAULT_TCP_PORT;

        const host = config.get("debugAdapter.host", DEBUG_ADAPTER_DEFAULT_HOST) || DEBUG_ADAPTER_DEFAULT_HOST;

        return new vscode.DebugAdapterServer(port, host);
      }
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
              await DebugManager.attachPython(event.session, event.event, event.body);
              break;
            }
            case "robotExited": {
              await DebugManager.onRobotExited(
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
          _token: vscode.CancellationToken
        ): vscode.ProviderResult<vscode.InlineValue[]> {
          const allValues: vscode.InlineValue[] = [];

          for (let l = viewPort.start.line; l <= Math.min(viewPort.end.line, context.stoppedLocation.end.line); l++) {
            const line = document.lineAt(l);
            const text = line.text.split("#")[0];

            const variableMatches =
              /([$@&%]\{)(?:((?:\d+\.?\d*)|(?:0x[/da-f]+)|(?:0o[0-7]+)|(?:0b[01]+))|(true|false|none|null|empty|space|\/|:|\\n)|((.+?}*)))(\})(?:(\[)(?:(\d+)|(.*?))?(\]))?/gi;

            let match;
            while ((match = variableMatches.exec(text))) {
              const varName = match[0];

              const rng = new vscode.Range(l, match.index, l, match.index + varName.length);
              allValues.push(new vscode.InlineValueVariableLookup(rng, varName, false));
            }
          }
          return allValues;
        },
      })
    );
  }

  async dispose(): Promise<void> {
    this._disposables.dispose();
  }

  static async runTests(
    folder: vscode.WorkspaceFolder,
    tests: string[],
    runId?: string,
    options?: vscode.DebugSessionOptions
  ): Promise<void> {
    if (tests.length) {
      const config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);

      const args = [];
      args.push("--prerunmodifier");

      args.push(`robotcode.debugger.modifiers.ByLongName:${tests.join(":")}`);

      const template = config.get("debug.defaultConfiguration", {});

      await vscode.debug.startDebugging(
        folder,
        {
          ...template,
          ...{
            type: "robotcode",
            name: "robotcode: Run Tests",
            request: "launch",
            cwd: folder?.uri.fsPath,
            target: ".",
            args: args,
            console: config.get("debug.defaultConsole", "integratedTerminal"),
            runId: runId,
          },
        },
        options
      );
    }
  }

  static async attachPython(session: vscode.DebugSession, event: string, options?: { port: number }): Promise<void> {
    if (
      session.type === "robotcode" &&
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
          lifecycleManagedByParent: true,
          consoleMode: vscode.DebugConsoleMode.Separate,
        }
      );
    }
  }

  private static async onRobotExited(
    session: vscode.DebugSession,
    outputFile?: string,
    logFile?: string,
    reportFile?: string
  ): Promise<void> {
    if (reportFile) {
      const config = vscode.workspace.getConfiguration(CONFIG_SECTION, session.workspaceFolder);

      if (config.get<boolean>("run.openReportAfterRun")) {
        vscode.env.openExternal(vscode.Uri.file(reportFile));
      }
    }
  }
}
