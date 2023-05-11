import { spawn, spawnSync } from "child_process";
import * as path from "path";
import * as vscode from "vscode";
import { CONFIG_SECTION } from "./config";

interface PythonExtensionApi {
  /**
   * Promise indicating whether all parts of the extension have completed loading or not.
   * @type {Promise<void>}
   * @memberof IExtensionApi
   */
  ready: Promise<void>;
  jupyter: {
    registerHooks(): void;
  };
  debug: {
    /**
     * Generate an array of strings for commands to pass to the Python executable to launch the debugger for remote debugging.
     * Users can append another array of strings of what they want to execute along with relevant arguments to Python.
     * E.g `['/Users/..../pythonVSCode/pythonFiles/lib/python/debugpy', '--listen', 'localhost:57039', '--wait-for-client']`
     * @param {string} host
     * @param {number} port
     * @param {boolean} [waitUntilDebuggerAttaches=true]
     * @returns {Promise<string[]>}
     */
    getRemoteLauncherCommand(host: string, port: number, waitUntilDebuggerAttaches: boolean): Promise<string[]>;

    /**
     * Gets the path to the debugger package used by the extension.
     * @returns {Promise<string>}
     */
    getDebuggerPackagePath(): Promise<string | undefined>;
  };
  /**
   * Return internal settings within the extension which are stored in VSCode storage
   */
  settings: {
    /**
     * An event that is emitted when execution details (for a resource) change. For instance, when interpreter configuration changes.
     */
    readonly onDidChangeExecutionDetails: vscode.Event<vscode.Uri | undefined>;
    /**
     * Returns all the details the consumer needs to execute code within the selected environment,
     * corresponding to the specified resource taking into account any workspace-specific settings
     * for the workspace to which this resource belongs.
     * @param {Resource} [resource] A resource for which the setting is asked for.
     * * When no resource is provided, the setting scoped to the first workspace folder is returned.
     * * If no folder is present, it returns the global setting.
     * @returns {({ execCommand: string[] | undefined })}
     */
    getExecutionDetails(resource?: vscode.Uri | undefined): {
      /**
       * E.g of execution commands returned could be,
       * * `['<path to the interpreter set in settings>']`
       * * `['<path to the interpreter selected by the extension when setting is not set>']`
       * * `['conda', 'run', 'python']` which is used to run from within Conda environments.
       * or something similar for some other Python environments.
       *
       * @type {(string[] | undefined)} When return value is `undefined`, it means no interpreter is set.
       * Otherwise, join the items returned using space to construct the full execution command.
       */
      execCommand: string[] | undefined;
    };
  };
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

  _pythonLanguageServerMain: string;
  _checkRobotVersionMain: string;
  _robotCodeMain: string;
  _pythonVersionScript = "import sys; print(sys.version_info[:2]>=(3,8))";

  _pythonExtension: vscode.Extension<PythonExtensionApi> | undefined;

  constructor(
    public readonly extensionContext: vscode.ExtensionContext,
    public readonly outputChannel: vscode.OutputChannel
  ) {
    this._pythonLanguageServerMain = this.extensionContext.asAbsolutePath(
      path.join("bundled", "tool", "language_server")
    );

    this._checkRobotVersionMain = this.extensionContext.asAbsolutePath(
      path.join("bundled", "tool", "utils", "check_robot_version.py")
    );

    this._robotCodeMain = this.extensionContext.asAbsolutePath(path.join("bundled", "tool", "robotcode"));
  }

  async dispose(): Promise<void> {
    // empty
  }

  get pythonExtension(): vscode.Extension<PythonExtensionApi> | undefined {
    if (!this._pythonExtension) {
      this.outputChannel.appendLine("Try to activate python extension");
      try {
        this._pythonExtension = vscode.extensions.getExtension("ms-python.python")!;

        this._pythonExtension.activate().then(
          (_) => undefined,
          (_) => undefined
        );

        this.outputChannel.appendLine("Python Extension is active");

        this._pythonExtension.exports.ready.then(
          (_) => undefined,
          (_) => undefined
        );
      } catch (ex) {
        this.outputChannel.appendLine("can't activate python extension");
      }
    }
    return this._pythonExtension;
  }

  // eslint-disable-next-line class-methods-use-this
  public getPythonCommand(folder: vscode.WorkspaceFolder | undefined): string | undefined {
    const config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);
    let result: string | undefined;

    const configPython = config.get<string>("python");

    if (configPython !== undefined && configPython !== "") {
      result = configPython;
    } else {
      const pythonExtensionPythonPath: string[] | undefined =
        this.pythonExtension?.exports?.settings?.getExecutionDetails(folder?.uri)?.execCommand;

      if (pythonExtensionPythonPath !== undefined) {
        result = pythonExtensionPythonPath.join(" ");
      }
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

  public async executeRobotCode(
    folder: vscode.WorkspaceFolder,
    args: string[],
    stdioData?: string,
    token?: vscode.CancellationToken
  ): Promise<unknown> {
    const config = vscode.workspace.getConfiguration(CONFIG_SECTION, folder);
    const robotCodeExtraArgs = config.get<string[]>("extraArgs", []);

    const pythonCommand = this.getPythonCommand(folder);
    if (pythonCommand === undefined) throw new Error("Can't find python executable.");

    const final_args = [
      "-u",
      "-X",
      "utf8",
      this.robotCodeMain,
      ...robotCodeExtraArgs,
      "--format",
      "json",
      "--no-color",
      "--no-pager",
      ...args,
    ];

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
      });

      process.stderr.on("data", (data) => {
        stderr += data;
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
          this.outputChannel.show(true);

          reject(new Error(`Executing robotcode failed with code ${code ?? "null"}: ${stdout}\n${stderr}`));
        }
      });
    });
  }
}
