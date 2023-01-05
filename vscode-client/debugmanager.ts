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
    folder: vscode.WorkspaceFolder | undefined,
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

    if (debugConfiguration.request === "launch") {
      const config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);

      const template = config.get("debug.defaultConfiguration", {});

      const defaultLaunchConfig =
        vscode.workspace
          .getConfiguration("launch", folder)
          ?.get<{ [Key: string]: unknown }[]>("configurations")
          ?.find(
            (v) =>
              v?.type === "robotcode" &&
              (v?.purpose === "default" || (Array.isArray(v?.purpose) && v?.purpose?.indexOf("default") > -1))
          ) ?? {};

      debugConfiguration = { ...template, ...defaultLaunchConfig, ...debugConfiguration };

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
        ...(Array.isArray(defaultLaunchConfig?.robotPythonPath) ? defaultLaunchConfig.robotPythonPath : []),
        ...(debugConfiguration.robotPythonPath ?? []),
      ];

      debugConfiguration.args = [...config.get<string[]>("robot.args", []), ...(debugConfiguration.args ?? [])];

      debugConfiguration.variableFiles = [
        ...config.get<string[]>("robot.variableFiles", []),
        ...(Array.isArray(defaultLaunchConfig?.variableFiles) ? defaultLaunchConfig.variableFiles : []),
        ...(debugConfiguration.variableFiles ?? []),
      ];

      debugConfiguration.variables = {
        ...config.get<{ [Key: string]: unknown }>("robot.variables", {}),
        ...(Array.isArray(defaultLaunchConfig?.variables) ? defaultLaunchConfig.variables : []),
        ...(debugConfiguration.variables ?? {}),
      };

      debugConfiguration.env = {
        ...config.get<{ [Key: string]: unknown }>("robot.env", {}),
        ...(defaultLaunchConfig?.env ?? {}),
        ...(debugConfiguration.env ?? {}),
      };

      debugConfiguration.openOutputAfterRun =
        debugConfiguration?.openOutputAfterRun ?? config.get<string | undefined>("run.openOutputAfterRun", undefined);

      debugConfiguration.outputDir =
        debugConfiguration?.outputDir ?? config.get<string | undefined>("robot.outputDir", undefined);

      debugConfiguration.mode = debugConfiguration?.mode ?? config.get<string | undefined>("robot.mode", undefined);

      debugConfiguration.languages =
        debugConfiguration?.languages ?? config.get<string | undefined>("robot.languages", undefined);

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
    } else if (debugConfiguration.request === "attach") {
      // do nothing
    }
    return debugConfiguration;
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
    if (session.configuration.request === "launch") {
      switch (mode) {
        case "stdio": {
          const pythonCommand = this.pythonManager.getPythonCommand(session.workspaceFolder);

          if (pythonCommand === undefined) {
            throw new Error("Can't get a valid python command.");
          }

          let debugAdapterArgs = config.get<string[]>("debugAdapter.args", []);

          if (session.configuration.launcherArgs) {
            debugAdapterArgs = [...debugAdapterArgs, ...session.configuration.launcherArgs];
          }
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
    } else if (session.configuration.request === "attach") {
      const port = session.configuration.connect?.port ?? session.configuration.port ?? 6612;
      const host = session.configuration.connect?.host ?? session.configuration.host ?? "127.0.0.1";
      const server = new vscode.DebugAdapterServer(port, host);
      return server;
    } else {
      throw new Error(`Unsupported request type "${session.configuration.request}"`);
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
            case "disconnectRequested":
            case "terminateRequested": {
              for (const s of this._attachedSessions) {
                if (s.parentSession == event.session) {
                  await vscode.debug.stopDebugging(s);
                }
              }
              break;
            }
            case "robotExited": {
              await this.OnRobotExited(event.session, event.body.outputFile, event.body.logFile, event.body.reportFile);
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
        if (this._attachedSessions.has(session)) {
          this._attachedSessions.delete(session);
          if (session.parentSession?.type === "robotcode") {
            await vscode.debug.stopDebugging(session.parentSession);
          }
        }
        if (session.configuration.type === "robotcode") {
          for (const s of this._attachedSessions) {
            if (s.parentSession == session) {
              await vscode.debug.stopDebugging(s);
            }
          }
        }
      }),

      vscode.languages.registerEvaluatableExpressionProvider("robotframework", {
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
    options?: vscode.DebugSessionOptions,
    dryRun?: boolean,
    topLevelSuiteName?: string
  ): Promise<boolean> {
    const config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);

    const args = [];

    if (topLevelSuiteName) {
      args.push("--name");
      args.push(topLevelSuiteName);
    }

    for (const s of suites) {
      args.push("--suite");
      args.push(s);
    }

    if (included.length > 0) {
      args.push("--prerunmodifier");

      const separator = included.find((s) => s.indexOf(":") >= 0) === undefined ? ":" : ";";

      args.push(`robotcode.debugger.modifiers.ByLongName${separator}${included.join(separator)}`);
    }

    if (excluded.length > 0) {
      args.push("--prerunmodifier");

      const separator = included.find((s) => s.indexOf(":") >= 0) === undefined ? ":" : ";";

      args.push(`robotcode.debugger.modifiers.ExcludedByLongName${separator}${excluded.join(separator)}`);
    }

    const testLaunchConfig =
      vscode.workspace
        .getConfiguration("launch", folder)
        ?.get<{ [Key: string]: unknown }[]>("configurations")
        ?.find(
          (v) =>
            v?.type === "robotcode" &&
            (v?.purpose === "test" || (Array.isArray(v?.purpose) && v?.purpose?.indexOf("test") > -1))
        ) ?? {};

    if (!("target" in testLaunchConfig)) {
      testLaunchConfig.target = "";
    }

    const paths = config.get("robot.paths", []);

    return vscode.debug.startDebugging(
      folder,
      {
        ...testLaunchConfig,
        ...{
          type: "robotcode",
          name: "RobotCode: Run Tests",
          request: "launch",
          cwd: folder?.uri.fsPath,
          paths: paths,
          args: args,
          console: config.get("debug.defaultConsole", "integratedTerminal"),
          runId: runId,
          dryRun,
        },
      },
      options
    );
  }

  static async OnDebugpyStarted(
    session: vscode.DebugSession,
    _event: string,
    options?: { port: number; addresses: undefined | string[] | null }
  ): Promise<boolean> {
    if (
      session.type === "robotcode" &&
      !session.configuration.noDebug &&
      session.configuration.attachPython &&
      options &&
      options.port
    ) {
      let pythonConfiguration = session.configuration.pythonConfiguration ?? {};

      if (typeof pythonConfiguration === "string" || pythonConfiguration instanceof String) {
        pythonConfiguration =
          vscode.workspace
            .getConfiguration("launch", session.workspaceFolder)
            ?.get<{ [Key: string]: unknown }[]>("configurations")
            ?.find((v) => v?.type === "python" && v?.name === pythonConfiguration) ?? {};
      }

      const debugConfiguration = {
        ...pythonConfiguration,
        ...{
          type: "python",
          name: `Python ${session.name}`,
          request: "attach",
          connect: {
            port: options.port,
            host: options.addresses ? options.addresses[0] : undefined,
          },
        },
      };

      if (session.configuration?.request === "attach" && !debugConfiguration.pathMappings) {
        debugConfiguration.pathMappings = session.configuration.pathMappings;
      }

      return vscode.debug.startDebugging(session.workspaceFolder, debugConfiguration, {
        parentSession: session,
        compact: true,
        lifecycleManagedByParent: false,
        consoleMode: vscode.DebugConsoleMode.MergeWithParent,
      });
    }
    return false;
  }

  private async OnRobotExited(
    session: vscode.DebugSession,
    _outputFile?: string,
    logFile?: string,
    reportFile?: string
  ): Promise<void> {
    if (session.configuration?.openOutputAfterRun === "report" && reportFile) {
      await this.languageClientsManager.openUriInDocumentationView(vscode.Uri.file(reportFile));
    } else if (session.configuration?.openOutputAfterRun === "log" && logFile) {
      await this.languageClientsManager.openUriInDocumentationView(vscode.Uri.file(logFile));
    }
  }
}
