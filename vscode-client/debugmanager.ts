/* eslint-disable @typescript-eslint/no-unsafe-member-access */
/* eslint-disable @typescript-eslint/no-unsafe-assignment */
/* eslint-disable @typescript-eslint/no-unsafe-argument */
import * as path from "path";
import * as vscode from "vscode";
import { PythonManager } from "./pythonmanger";
import { CONFIG_SECTION } from "./config";
import { LanguageClientsManager, toVsCodeRange } from "./languageclientsmanger";
import { WeakValueSet } from "./utils";

const DEBUG_ADAPTER_DEFAULT_TCP_PORT = 6611;
const DEBUG_ADAPTER_DEFAULT_HOST = "127.0.0.1";

const DEBUG_CONFIGURATIONS = [
  {
    label: "RobotCode: Run Current",
    description: "Run the current RobotFramework file.",
    body: {
      name: "RobotCode: Run Current",
      type: "robotcode",
      request: "launch",
      cwd: "${workspaceFolder}",
      target: "${file}",
    },
  },
  {
    label: "RobotCode: Run All",
    description: "Run all RobotFramework files.",
    body: {
      name: "RobotCode: Run All",
      type: "robotcode",
      request: "launch",
      cwd: "${workspaceFolder}",
      target: ".",
    },
  },
];

class RobotCodeDebugConfigurationProvider implements vscode.DebugConfigurationProvider {
  constructor(private readonly pythonManager: PythonManager) {}

  resolveDebugConfiguration(
    folder: vscode.WorkspaceFolder | undefined,
    debugConfiguration: vscode.DebugConfiguration,
    token?: vscode.CancellationToken
  ): vscode.ProviderResult<vscode.DebugConfiguration> {
    return this._resolveDebugConfiguration(folder, debugConfiguration, token);
  }

  // eslint-disable-next-line class-methods-use-this
  async _resolveDebugConfiguration(
    _folder: vscode.WorkspaceFolder | undefined,
    debugConfiguration: vscode.DebugConfiguration,
    token?: vscode.CancellationToken
  ): Promise<vscode.DebugConfiguration> {
    if (!debugConfiguration.type && !debugConfiguration.request && !debugConfiguration.name) {
      const editor = vscode.window.activeTextEditor;
      if (editor && editor.document.languageId === "robotframework" && editor.document.fileName.endsWith(".robot")) {
        const result = await vscode.window.showQuickPick(
          DEBUG_CONFIGURATIONS.map((v) => v),
          { canPickMany: false },
          token
        );

        if (result !== undefined) {
          debugConfiguration = {
            ...result?.body,
            ...debugConfiguration,
          };
        }
      }
    }

    return debugConfiguration;
  }

  resolveDebugConfigurationWithSubstitutedVariables(
    folder: vscode.WorkspaceFolder | undefined,
    debugConfiguration: vscode.DebugConfiguration,
    _token?: vscode.CancellationToken
  ): vscode.ProviderResult<vscode.DebugConfiguration> {
    return this._resolveDebugConfigurationWithSubstitutedVariablesAsync(folder, debugConfiguration, _token);
  }

  async _resolveDebugConfigurationWithSubstitutedVariablesAsync(
    folder: vscode.WorkspaceFolder | undefined,
    debugConfiguration: vscode.DebugConfiguration,
    _token?: vscode.CancellationToken
  ): Promise<vscode.DebugConfiguration> {
    const config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);

    try {
      if (path.isAbsolute(debugConfiguration.target)) {
        debugConfiguration.target = path.relative(debugConfiguration.cwd, debugConfiguration.target).toString();
      }
    } catch {
      // empty
    }

    if (!debugConfiguration.python) debugConfiguration.python = this.pythonManager.getPythonCommand(folder);

    debugConfiguration.robotPythonPath = [
      ...config.get<string[]>("robot.pythonPath", []),
      ...(debugConfiguration.robotPythonPath ?? []),
    ];

    debugConfiguration.args = [...config.get<string[]>("robot.args", []), ...(debugConfiguration.args ?? [])];

    debugConfiguration.variables = {
      ...config.get<{ [Key: string]: unknown }>("robot.variables", {}),
      ...(debugConfiguration.variables ?? {}),
    };

    debugConfiguration.env = {
      ...config.get<{ [Key: string]: unknown }>("robot.env", {}),
      ...(debugConfiguration.env ?? {}),
    };

    debugConfiguration.outputDir =
      debugConfiguration?.outputDir ?? config.get<string | undefined>("robot.outputDir", undefined);

    debugConfiguration.attachPython = debugConfiguration?.attachPython ?? config.get<boolean>("debug.attachPython");

    debugConfiguration.outputMessages =
      debugConfiguration?.outputMessages ?? config.get<boolean>("debug.outputMessages");

    debugConfiguration.outputLog = debugConfiguration?.outputLog ?? config.get<boolean>("debug.outputLog");

    debugConfiguration.groupOutput = debugConfiguration?.groupOutput ?? config.get<boolean>("debug.groupOutput");

    if (!debugConfiguration.attachPython || debugConfiguration.noDebug) {
      debugConfiguration.attachPython = false;
    }

    if (debugConfiguration.attachPython && !config.get<boolean>("debug.useExternalDebugpy")) {
      const debugpyPath = await this.pythonManager.pythonExtension?.exports.debug.getDebuggerPackagePath();

      if (debugpyPath) {
        const env = debugConfiguration.env ?? {};
        const envPythonPath: string = env.PYTHONPATH || "";

        env.PYTHONPATH = [
          path.dirname(debugpyPath),
          ...(envPythonPath ? envPythonPath.split(path.delimiter) : []),
        ].join(path.delimiter);
        debugConfiguration.env = env;
      }
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

    const mode = config.get<string>("debugAdapter.mode");

    switch (mode) {
      case "stdio": {
        const pythonCommand = this.pythonManager.getPythonCommand(session.workspaceFolder);

        if (pythonCommand === undefined) {
          throw new Error("Can't get a valid python command.");
        }

        const debugAdapterArgs = config.get<string[]>("debugAdapter.args", []);

        const args: string[] = ["-u", this.pythonManager.pythonDebugAdapterMain, "--mode", "stdio"].concat(
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
  private _attachedSessions = new WeakValueSet<vscode.DebugSession>();

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
      vscode.debug.registerDebugConfigurationProvider(
        "robotcode",
        {
          provideDebugConfigurations(
            _folder: vscode.WorkspaceFolder | undefined,
            _token?: vscode.CancellationToken
          ): vscode.ProviderResult<vscode.DebugConfiguration[]> {
            return DEBUG_CONFIGURATIONS.map((v) => v.body);
          },
        },
        vscode.DebugConfigurationProviderTriggerKind.Dynamic
      ),
      vscode.debug.registerDebugAdapterDescriptorFactory(
        "robotcode",
        new RobotCodeDebugAdapterDescriptorFactory(this.pythonManager)
      ),
      vscode.debug.onDidReceiveDebugSessionCustomEvent(async (event) => {
        if (event.session.configuration.type === "robotcode") {
          switch (event.event) {
            case "debugpyStarted": {
              await DebugManager.OnDebugpyStarted(event.session, event.event, event.body);
              break;
            }
            case "robotExited": {
              await DebugManager.OnRobotExited(
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
      vscode.debug.onDidStartDebugSession((session) => {
        if (session.parentSession?.type === "robotcode") {
          this._attachedSessions.add(session);
        }
      }),
      vscode.debug.onDidTerminateDebugSession(async (session) => {
        if (session.type === "robotcode") {
          for (const s of this._attachedSessions) {
            if (s.parentSession === session) {
              await vscode.debug.stopDebugging(s);
            }
          }
        }
        if (this._attachedSessions.has(session)) {
          this._attachedSessions.delete(session);
        }
      }),
      vscode.languages.registerInlineValuesProvider("robotcode", {
        provideInlineValues(
          document: vscode.TextDocument,
          viewPort: vscode.Range,
          context: vscode.InlineValueContext,
          token: vscode.CancellationToken
        ): vscode.ProviderResult<vscode.InlineValue[]> {
          return languageClientsManager.getInlineValues(document, viewPort, context, token).then(
            (r) => {
              const result: vscode.InlineValue[] = [];

              for (const c of r) {
                switch (c.type) {
                  case "text":
                    result.push(new vscode.InlineValueText(toVsCodeRange(c.range), c.text));

                    break;
                  case "variable":
                    result.push(
                      new vscode.InlineValueVariableLookup(
                        toVsCodeRange(c.range),
                        c.variableName,
                        c.caseSensitiveLookup
                      )
                    );
                    break;
                  case "expression":
                    result.push(new vscode.InlineValueEvaluatableExpression(toVsCodeRange(c.range), c.expression));
                }
              }
              if (r) return result;
              else return [];
            },
            (_) => []
          );
        },
      }),
      vscode.languages.registerEvaluatableExpressionProvider("robotcode", {
        provideEvaluatableExpression(
          document: vscode.TextDocument,
          position: vscode.Position,
          token: vscode.CancellationToken
        ): vscode.ProviderResult<vscode.EvaluatableExpression> {
          return languageClientsManager.getEvaluatableExpression(document, position, token).then(
            (r) => {
              if (r) return new vscode.EvaluatableExpression(toVsCodeRange(r.range), r.expression);
              else return undefined;
            },
            (_) => undefined
          );
        },
      })
    );
  }

  dispose(): void {
    this._disposables.dispose();
  }

  static async runTests(
    folder: vscode.WorkspaceFolder,
    suites: string[],
    included: string[],
    excluded: string[],
    runId?: string,
    options?: vscode.DebugSessionOptions
  ): Promise<void> {
    const config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);

    const args = [];

    for (const s of suites) {
      args.push("--suite");
      args.push(s);
    }

    if (included.length > 0) {
      args.push("--prerunmodifier");

      args.push(`robotcode.debugger.modifiers.ByLongName:${included.join(":")}`);
    }

    if (excluded.length > 0) {
      args.push("--prerunmodifier");

      args.push(`robotcode.debugger.modifiers.ExcludedByLongName:${excluded.join(":")}`);
    }
    const template = config.get("debug.defaultConfiguration", {});

    await vscode.debug.startDebugging(
      folder,
      {
        ...template,
        ...{
          type: "robotcode",
          name: "RobotCode: Run Tests",
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

  static async OnDebugpyStarted(
    session: vscode.DebugSession,
    _event: string,
    options?: { port: number }
  ): Promise<void> {
    if (
      session.type === "robotcode" &&
      !session.configuration.noDebug &&
      session.configuration.attachPython &&
      options &&
      options.port
    ) {
      await vscode.debug.startDebugging(
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

  private static async OnRobotExited(
    session: vscode.DebugSession,
    _outputFile?: string,
    _logFile?: string,
    reportFile?: string
  ): Promise<void> {
    if (reportFile) {
      const config = vscode.workspace.getConfiguration(CONFIG_SECTION, session.workspaceFolder);

      if (config.get<boolean>("run.openReportAfterRun")) {
        await vscode.env.openExternal(vscode.Uri.file(reportFile));
      }
    }
  }
}
