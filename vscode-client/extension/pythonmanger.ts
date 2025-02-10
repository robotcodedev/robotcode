import { spawn, spawnSync } from "child_process";
import * as path from "path";
import * as vscode from "vscode";
import { CONFIG_SECTION } from "./config";
import { PythonExtension, ActiveEnvironmentPathChangeEvent } from "@vscode/python-extension";

const UNKNOWN = "unknown";
const CUSTOM = "custom";

export interface ActivePythonEnvironmentChangedEvent {
  readonly resource: vscode.WorkspaceFolder | undefined;
}

export class PythonInfo {
  constructor(
    public readonly name: string,
    public readonly type: string | undefined,
    public readonly version: string,
    public readonly path?: string,
  ) {}
}
export class PythonManager {
  public get pythonLanguageServerMain(): string {
    return this._pythonLanguageServerMain;
  }

  public get robotCodeMain(): string {
    return this._robotCodeMain;
  }

  public get checkRobotVersionMain(): string {
    return this._checkRobotVersionMain;
  }

  public get checkPythonVersionScript(): string {
    return this._pythonVersionScript;
  }

  private readonly _onActivePythonEnvironmentChangedEmitter =
    new vscode.EventEmitter<ActivePythonEnvironmentChangedEvent>();
  public get onActivePythonEnvironmentChanged(): vscode.Event<ActivePythonEnvironmentChangedEvent> {
    return this._onActivePythonEnvironmentChangedEmitter.event;
  }

  _pythonLanguageServerMain: string;
  _checkRobotVersionMain: string;
  _robotCodeMain: string;
  _pythonVersionScript = "import sys; print(sys.version_info[:2]>=(3,8))";

  _pythonExtension: PythonExtension | undefined;
  private _disposables: vscode.Disposable | undefined;

  constructor(
    public readonly extensionContext: vscode.ExtensionContext,
    public readonly outputChannel: vscode.OutputChannel,
  ) {
    this._pythonLanguageServerMain = this.extensionContext.asAbsolutePath(
      path.join("bundled", "tool", "language_server"),
    );

    this._checkRobotVersionMain = this.extensionContext.asAbsolutePath(
      path.join("bundled", "tool", "utils", "check_robot_version.py"),
    );

    this._robotCodeMain = this.extensionContext.asAbsolutePath(path.join("bundled", "tool", "robotcode"));
  }

  dispose(): void {
    if (this._disposables !== undefined) this._disposables.dispose();
  }

  private doActiveEnvironmentPathChanged(event: ActiveEnvironmentPathChangeEvent): void {
    this.outputChannel.appendLine(
      `ActiveEnvironmentPathChanged: ${event.resource?.uri.toString() ?? UNKNOWN} ${event.id}`,
    );
    this._onActivePythonEnvironmentChangedEmitter.fire({ resource: event.resource });
  }

  async getPythonExtension(): Promise<PythonExtension | undefined> {
    if (this._pythonExtension === undefined) {
      this.outputChannel.appendLine("Try to activate python extension");

      try {
        this._pythonExtension = await PythonExtension.api();

        this.outputChannel.appendLine("Python Extension is active");
        await this._pythonExtension.ready;
      } catch (ex: unknown) {
        this.outputChannel.appendLine(`can't activate python extension ${ex?.toString() ?? ""}`);
      }

      if (this._pythonExtension !== undefined) {
        this._disposables = vscode.Disposable.from(
          this._pythonExtension.environments.onDidChangeActiveEnvironmentPath((event) =>
            this.doActiveEnvironmentPathChanged(event),
          ),
        );
      }
    }
    return this._pythonExtension;
  }

  public async getPythonCommand(folder: vscode.WorkspaceFolder | undefined): Promise<string | undefined> {
    const config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);
    let result: string | undefined;

    const configPython = config.get<string>("python");

    if (configPython !== undefined && configPython !== "") {
      result = configPython;
    } else {
      const pythonExtension = await this.getPythonExtension();

      const environmentPath = pythonExtension?.environments.getActiveEnvironmentPath(folder);
      if (environmentPath === undefined) {
        return undefined;
      }

      const env = await pythonExtension?.environments.resolveEnvironment(environmentPath);
      result = env?.executable.uri?.fsPath;
    }

    return result;
  }

  public checkPythonVersion(pythonCommand: string): boolean {
    const res = spawnSync(pythonCommand, ["-u", "-c", this.checkPythonVersionScript], {
      encoding: "ascii",
    });
    if (res.status == 0 && res.stdout && res.stdout.trimEnd() === "True") return true;

    return false;
  }

  public checkRobotVersion(pythonCommand: string): boolean | undefined {
    const res = spawnSync(pythonCommand, ["-u", this.checkRobotVersionMain], {
      encoding: "ascii",
    });

    if (res.status == 0 && res.stdout && res.stdout.trimEnd() === "True") return true;

    const stdout = res.stdout;
    if (stdout) this.outputChannel.appendLine(`checkRobotVersion: ${stdout}`);
    const stderr = res.stderr;
    if (stderr) this.outputChannel.appendLine(`checkRobotVersion: ${stderr}`);

    if (res.status != 0) return undefined;

    return false;
  }

  public async getDebuggerPackagePath(): Promise<string | undefined> {
    // TODO: this is not enabled in debugpy extension yet
    const debugpy = vscode.extensions.getExtension("ms-python.debugpy");
    if (debugpy !== undefined) {
      if (!debugpy.isActive) {
        await debugpy.activate();
      }
      const path = (debugpy.exports as PythonExtension)?.debug.getDebuggerPackagePath();
      if (path !== undefined) {
        return path;
      }
    }
    return (await this.getPythonExtension())?.debug.getDebuggerPackagePath();
  }

  public async executeRobotCode(
    folder: vscode.WorkspaceFolder,
    args: string[],
    profiles?: string[],
    format?: string,
    noColor?: boolean,
    noPager?: boolean,
    stdioData?: string,
    token?: vscode.CancellationToken,
  ): Promise<unknown> {
    const { pythonCommand, final_args } = await this.buildRobotCodeCommand(
      folder,
      args,
      profiles,
      format,
      noColor,
      noPager,
    );

    this.outputChannel.appendLine(`executeRobotCode: ${pythonCommand} ${final_args.join(" ")}`);

    return new Promise((resolve, reject) => {
      const abortController = new AbortController();

      token?.onCancellationRequested(() => {
        abortController.abort();
      });

      const { signal } = abortController;

      const process = spawn(pythonCommand, final_args, {
        cwd: folder.uri.fsPath,

        signal,
      });

      let stdout = "";
      let stderr = "";

      process.stdout.setEncoding("utf8");
      process.stderr.setEncoding("utf8");
      if (stdioData !== undefined) {
        process.stdin.cork();
        process.stdin.write(stdioData, "utf8");
        process.stdin.end();
      }

      process.stdout.on("data", (data) => {
        stdout += data;
        // this.outputChannel.appendLine(data as string);
      });

      process.stderr.on("data", (data) => {
        stderr += data;
        this.outputChannel.appendLine(data as string);
      });

      process.on("error", (err) => {
        reject(err);
      });

      process.on("exit", (code) => {
        this.outputChannel.appendLine(`executeRobotCode: exit code ${code ?? "null"}`);
        if (code === 0) {
          try {
            resolve(JSON.parse(stdout));
          } catch (err) {
            reject(err);
          }
        } else {
          this.outputChannel.appendLine(`executeRobotCode: ${stdout}\n${stderr}`);

          reject(new Error(`Executing robotcode failed with code ${code ?? "null"}: ${stdout}\n${stderr}`));
        }
      });
    });
  }

  public async buildRobotCodeCommand(
    folder: vscode.WorkspaceFolder,
    args: string[],
    profiles?: string[],
    format?: string,
    noColor?: boolean,
    noPager?: boolean,
  ): Promise<{ pythonCommand: string; final_args: string[] }> {
    const config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);
    const robotCodeExtraArgs = config.get<string[]>("extraArgs", []);

    const pythonCommand = await this.getPythonCommand(folder);
    if (pythonCommand === undefined) throw new Error("Can't find python executable.");

    const final_args = [
      "-u",
      "-X",
      "utf8",
      this.robotCodeMain,
      ...robotCodeExtraArgs,
      ...(format ? ["--format", format] : []),
      ...(noColor ? ["--no-color"] : []),
      ...(noPager ? ["--no-pager"] : []),
      ...(profiles !== undefined ? profiles.flatMap((v) => ["--p", v]) : []),
      ...args,
    ];
    return { pythonCommand, final_args };
  }

  async getPythonInfo(folder: vscode.WorkspaceFolder): Promise<PythonInfo | undefined> {
    try {
      const config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);
      let name: string | undefined;
      let type: string | undefined;
      let path: string | undefined;
      let version: string | undefined;

      const configPython = config.get<string>("python");

      if (configPython !== undefined && configPython !== "") {
        path = configPython;
      } else {
        const pythonExtension = await this.getPythonExtension();

        const environmentPath = pythonExtension?.environments.getActiveEnvironmentPath(folder);
        if (environmentPath === undefined) {
          return undefined;
        }

        const env = await pythonExtension?.environments.resolveEnvironment(environmentPath);
        path = env?.executable.uri?.fsPath;
        version =
          env?.version !== undefined ? `${env.version.major}.${env.version.minor}.${env.version.micro}` : undefined;
        if (env?.environment !== undefined) {
          type = env?.tools?.[0];
          name = `('${env?.environment?.name ?? UNKNOWN}': ${type ?? UNKNOWN})`;
        } else {
          name = env?.executable.bitness ?? UNKNOWN;
        }
      }

      return new PythonInfo(name ?? CUSTOM, type, version ?? UNKNOWN, path);
    } catch {
      return undefined;
    }
  }
}
