import * as path from "path";
import * as vscode from "vscode";
import { PythonManager } from "./pythonmanger";
import { CONFIG_SECTION } from "./config";
import { LanguageClientsManager, SUPPORTED_LANGUAGES, toVsCodeRange } from "./languageclientsmanger";
import { WeakValueSet, waitForFile, sleep } from "./utils";
import * as cp from "child_process";
import { tmpdir } from "os";
import { join } from "path";
import { randomBytes } from "crypto";
import { platform } from "process";
import { getAvailablePort, isPortOpen } from "./net_utils";

const DEBUG_ADAPTER_DEFAULT_TCP_PORT = 6611;
const DEBUG_ADAPTER_DEFAULT_HOST = "127.0.0.1";

const DEBUG_ATTACH_DEFAULT_TCP_PORT = 6612;
const DEBUG_ATTACH_DEFAULT_HOST = "127.0.0.1";

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
      if (
        editor &&
        SUPPORTED_LANGUAGES.includes(editor.document.languageId) &&
        (editor.document.fileName.endsWith(".robot") || editor.document.fileName.endsWith(".feature"))
      ) {
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
        if (path.isAbsolute(debugConfiguration.target as string)) {
          debugConfiguration.target = path
            .relative(debugConfiguration.cwd as string, debugConfiguration.target as string)
            .toString();
        }
      } catch {
        // empty
      }

      if (!debugConfiguration.python) debugConfiguration.python = this.pythonManager.getPythonCommand(folder);

      debugConfiguration.robotPythonPath = [
        ...config.get<string[]>("robot.pythonPath", []),
        ...(Array.isArray(defaultLaunchConfig?.robotPythonPath)
          ? (defaultLaunchConfig.robotPythonPath as string[])
          : []),
        ...((debugConfiguration.robotPythonPath as string[]) ?? []),
      ];

      debugConfiguration.args = [
        ...config.get<string[]>("robot.args", []),
        ...(Array.isArray(defaultLaunchConfig?.args) ? (defaultLaunchConfig.args as string[]) : []),
        ...((debugConfiguration.args as string[]) ?? []),
      ];

      debugConfiguration.variableFiles = [
        ...config.get<string[]>("robot.variableFiles", []),
        ...(Array.isArray(defaultLaunchConfig?.variableFiles) ? (defaultLaunchConfig.variableFiles as string[]) : []),
        ...((debugConfiguration.variableFiles as string[]) ?? []),
      ];

      debugConfiguration.variables = {
        ...config.get<{ [Key: string]: unknown }>("robot.variables", {}),
        ...((defaultLaunchConfig?.variables ?? {}) as { [Key: string]: unknown }),
        ...((debugConfiguration.variables as { [Key: string]: unknown }) ?? {}),
      };

      debugConfiguration.env = {
        ...config.get<{ [Key: string]: unknown }>("robot.env", {}),
        ...((defaultLaunchConfig?.env ?? {}) as { [Key: string]: unknown }),
        ...((debugConfiguration.env as { [Key: string]: unknown }) ?? {}),
      };

      debugConfiguration.openOutputAfterRun =
        (debugConfiguration?.openOutputAfterRun as string | undefined) ??
        config.get<string | undefined>("run.openOutputAfterRun", undefined);

      debugConfiguration.profiles =
        (debugConfiguration?.profiles as string[] | undefined) ??
        config.get<string[] | undefined>("profiles", undefined);

      debugConfiguration.outputDir =
        (debugConfiguration?.outputDir as string | undefined) ??
        config.get<string | undefined>("robot.outputDir", undefined);

      debugConfiguration.mode =
        (debugConfiguration?.mode as string | undefined) ?? config.get<string | undefined>("robot.mode", undefined);

      debugConfiguration.languages =
        (debugConfiguration?.languages as string[] | undefined) ??
        config.get<string[] | undefined>("robot.languages", undefined);

      debugConfiguration.attachPython =
        (debugConfiguration?.attachPython as boolean | undefined) ?? config.get<boolean>("debug.attachPython");

      debugConfiguration.outputMessages =
        (debugConfiguration?.outputMessages as boolean | undefined) ?? config.get<boolean>("debug.outputMessages");

      debugConfiguration.outputLog =
        (debugConfiguration?.outputLog as boolean | undefined) ?? config.get<boolean>("debug.outputLog");

      debugConfiguration.outputTimestamps =
        (debugConfiguration?.outputTimestamps as boolean | undefined) ?? config.get<boolean>("debug.outputTimestamps");

      debugConfiguration.groupOutput =
        (debugConfiguration?.groupOutput as boolean | undefined) ?? config.get<boolean>("debug.groupOutput");

      if (!debugConfiguration.attachPython || debugConfiguration.noDebug) {
        debugConfiguration.attachPython = false;
      }

      if (debugConfiguration.attachPython && !config.get<boolean>("debug.useExternalDebugpy")) {
        const debugpyPath = await this.pythonManager.pythonExtension?.exports.debug.getDebuggerPackagePath();

        if (debugpyPath) {
          const env = (debugConfiguration.env as { [Key: string]: unknown }) ?? {};
          const envPythonPath: string = (env.PYTHONPATH as string) || "";

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
  constructor(private readonly pythonManager: PythonManager, private readonly outputChannel: vscode.OutputChannel) {}

  async createDebugAdapterDescriptor(
    session: vscode.DebugSession,
    _executable: vscode.DebugAdapterExecutable | undefined
  ): Promise<vscode.DebugAdapterDescriptor> {
    const config = vscode.workspace.getConfiguration(CONFIG_SECTION, session.workspaceFolder);

    const mode = config.get<string>("debugLauncher.mode");
    if (session.configuration.request === "launch") {
      let debugLauncherArgs = config.get<string[]>("debugLauncher.args", []);

      if (session.configuration.launcherArgs) {
        debugLauncherArgs = [...debugLauncherArgs, ...(session.configuration.launcherArgs as string[])];
      }

      switch (mode) {
        case "stdio": {
          const pythonCommand = this.pythonManager.getPythonCommand(session.workspaceFolder);

          if (pythonCommand === undefined) {
            throw new Error("Can't get a valid python command.");
          }

          const robotcodeExtraArgs = config.get<string[]>("extraArgs", []);
          const args: string[] = [
            "-u",
            this.pythonManager.robotCodeMain,
            ...robotcodeExtraArgs,
            "debug-launch",
            "--stdio",
          ].concat(debugLauncherArgs);

          const options: vscode.DebugAdapterExecutableOptions = {
            env: {},
            cwd: session.workspaceFolder?.uri.fsPath,
          };

          this.outputChannel.appendLine(`Starting debug launcher in stdio mode: ${pythonCommand} ${args.join(" ")}`);

          return new vscode.DebugAdapterExecutable(pythonCommand, args, options);
        }
        case "tcp": {
          const host = config.get("debugLauncher.host", DEBUG_ADAPTER_DEFAULT_HOST) || DEBUG_ADAPTER_DEFAULT_HOST;

          const port =
            (await getAvailablePort(
              [host],
              config.get("debugLauncher.tcpPort", DEBUG_ADAPTER_DEFAULT_TCP_PORT) ?? DEBUG_ADAPTER_DEFAULT_TCP_PORT
            )) ?? DEBUG_ADAPTER_DEFAULT_TCP_PORT;

          this.spawnDebugLauncher(session, config, ["debug-launch", "--tcp", `${host}:${port}`, ...debugLauncherArgs]);

          while (!(await isPortOpen(port, host))) {
            await sleep(1000);
          }

          try {
            return new vscode.DebugAdapterServer(port, host);
          } catch (error) {
            throw new Error("Failed to start debug launcher.");
          }
        }
        case "pipe-server": {
          const pipeName = randomBytes(16).toString("hex");
          const pipePath = platform === "win32" ? join("\\\\.\\pipe\\", pipeName) : join(tmpdir(), pipeName);

          const p = this.spawnDebugLauncher(session, config, [
            "debug-launch",
            "--pipe-server",
            pipePath,
            ...debugLauncherArgs,
          ]);

          if (!(await waitForFile(pipePath))) {
            p.kill();
            throw new Error("Failed to start debug launcher. Can't find pipe file.");
          }

          return new vscode.DebugAdapterNamedPipeServer(pipePath);
        }
        default:
          throw new Error("Unsupported debug launcher mode.");
      }
    } else if (session.configuration.request === "attach") {
      const connect = session.configuration.connect as { [Key: string]: unknown };
      const port =
        (connect?.port as number) ?? (session.configuration?.port as number) ?? DEBUG_ATTACH_DEFAULT_TCP_PORT;
      const host = (connect?.host as string) ?? (session.configuration?.host as string) ?? DEBUG_ATTACH_DEFAULT_HOST;
      const server = new vscode.DebugAdapterServer(port, host);
      return server;
    } else {
      throw new Error(`Unsupported request type "${session.configuration.request}"`);
    }
  }

  private spawnDebugLauncher(
    session: vscode.DebugSession,
    config: vscode.WorkspaceConfiguration,
    launchArgs: string[]
  ) {
    const pythonCommand = this.pythonManager.getPythonCommand(session.workspaceFolder);

    if (pythonCommand === undefined) {
      throw new Error("Can't get a valid python command.");
    }

    let robotcodeExtraArgs = config.get<string[]>("extraArgs", []);

    if (session.configuration.launcherArgs) {
      robotcodeExtraArgs = [...robotcodeExtraArgs, ...(session.configuration.launcherArgs as string[])];
    }

    const options: cp.SpawnOptions = {
      cwd: session.workspaceFolder?.uri.fsPath,
      env: {},
    };

    const args: string[] = ["-u", this.pythonManager.robotCodeMain, ...robotcodeExtraArgs, ...launchArgs];

    this.outputChannel.appendLine(`Starting debug launcher with command: ${pythonCommand} ${args.join(" ")}`);

    const p = cp.spawn(pythonCommand, args, options);
    p.stdout?.on("data", (data) => {
      this.outputChannel.append(`${data as string}`);
    });
    p.stderr?.on("data", (data) => {
      this.outputChannel.append(`${data as string}`);
    });
    p.on("error", (e) => {
      throw new Error(`Failed to start debug launcher: ${e.message}`);
    });
    p.on("close", (code, signal) => {
      if (code !== 0) {
        this.outputChannel.appendLine(
          `debug launcher exited with code ${code ?? "unknown"} and signal ${signal ?? "unknown"}`
        );
      }
    });

    return p;
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
        new RobotCodeDebugAdapterDescriptorFactory(this.pythonManager, this.outputChannel)
      ),

      vscode.debug.onDidReceiveDebugSessionCustomEvent(async (event) => {
        if (event.session.configuration.type === "robotcode") {
          switch (event.event) {
            case "debugpyStarted": {
              await DebugManager.OnDebugpyStarted(
                event.session,
                event.event,
                event.body as { port: number; addresses: undefined | string[] | null }
              );
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
              const body = event.body as { [Key: string]: unknown };
              await this.OnRobotExited(
                event.session,
                body.outputFile as string,
                body.logFile as string,
                body.reportFile as string
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
      for (const s of included) {
        args.push("--by-longname");
        args.push(s);
      }
    }

    if (excluded.length > 0) {
      for (const s of excluded) {
        args.push("--exclude-by-longname");
        args.push(s);
      }
    }

    const testLaunchConfig: { [Key: string]: unknown } =
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

    let paths = config.get<string[]>("robot.paths", []);
    paths = "paths" in testLaunchConfig ? [...(testLaunchConfig.paths as string[]), ...paths] : paths;

    return vscode.debug.startDebugging(
      folder,
      {
        ...testLaunchConfig,
        ...{
          type: "robotcode",
          name: `RobotCode: Run Tests ${folder.name}`,
          request: "launch",
          cwd: folder?.uri.fsPath,
          paths: paths?.length > 0 ? paths : ["."],
          args: "args" in testLaunchConfig ? [...(testLaunchConfig.args as string[]), ...args] : args,
          console:
            "console" in testLaunchConfig
              ? testLaunchConfig.console
              : config.get("debug.defaultConsole", "integratedTerminal"),
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
      let pythonConfiguration = (session.configuration.pythonConfiguration as { [Key: string]: unknown }) ?? {};

      if (typeof pythonConfiguration === "string" || pythonConfiguration instanceof String) {
        pythonConfiguration =
          vscode.workspace
            .getConfiguration("launch", session.workspaceFolder)
            ?.get<{ [Key: string]: unknown }[]>("configurations")
            ?.find((v) => v?.type === "python" && v?.name === pythonConfiguration) ?? {};
      }

      const debugConfiguration: vscode.DebugConfiguration = {
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
        debugConfiguration.pathMappings = session.configuration.pathMappings as { [Key: string]: unknown };
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
