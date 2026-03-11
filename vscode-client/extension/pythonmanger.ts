import { spawn, spawnSync } from "child_process";
import * as fs from "fs";
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

export type IncrementalDiscoverItem = { id?: string; children?: IncrementalDiscoverItem[] } & Record<string, unknown>;

export type IncrementalDiscoverEvent =
  | { event: "start"; version?: number }
  | { event: "item"; item?: IncrementalDiscoverItem; parentId?: string }
  | { event: "diagnostics"; diagnostics?: Record<string, unknown> }
  | { event: "end" };

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
    const wsFolder =
      event.resource === undefined
        ? undefined
        : event.resource instanceof vscode.Uri
          ? vscode.workspace.getWorkspaceFolder(event.resource)
          : event.resource;

    this.outputChannel.appendLine(`ActiveEnvironmentPathChanged: ${wsFolder?.uri ?? UNKNOWN} ${event.id}`);

    this._onActivePythonEnvironmentChangedEmitter.fire({ resource: wsFolder });
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
    onIncrementalDiscoverEvent?: (event: IncrementalDiscoverEvent) => void,
  ): Promise<unknown> {
    const { pythonCommand, final_args } = await this.buildRobotCodeCommand(
      folder,
      args,
      profiles,
      format,
      noColor,
      noPager,
    );

    this.outputChannel.appendLine(`executeRobotCode: cwd=${folder.uri.fsPath}`);
    this.outputChannel.appendLine(`executeRobotCode: command=${pythonCommand}`);
    this.outputChannel.appendLine(`executeRobotCode: args=${this.formatArgsForLog(final_args)}`);

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

      const stdoutChunks: Buffer[] = [];
      const stderrChunks: Buffer[] = [];
      let stdoutBytes = 0;
      let exitCode: number | null = null;
      const incrementalOutput = final_args.includes("--incremental-output");
      const expectsStdin = final_args.includes("--read-from-stdin");
      const stderrLogLimit = 16_384;
      let stderrLoggedChars = 0;
      let stderrLogTruncated = false;
      const incrementalResult: { items: IncrementalDiscoverItem[]; diagnostics?: Record<string, unknown> } = {
        items: [],
      };
      const incrementalItemsById = new Map<string, IncrementalDiscoverItem>();
      let incrementalLineBuffer = "";
      let incrementalParseError: Error | undefined;

      const addIncrementalItem = (item: IncrementalDiscoverItem, parentId: string | undefined): void => {
        const itemId = typeof item.id === "string" ? item.id : undefined;
        if (itemId) {
          incrementalItemsById.set(itemId, item);
        }

        if (parentId) {
          const parent = incrementalItemsById.get(parentId);
          if (parent) {
            if (!Array.isArray(parent.children)) {
              parent.children = [];
            }
            parent.children.push(item);
          } else {
            incrementalParseError = new Error(
              `Executing robotcode failed: incremental discovery item '${itemId ?? "<unknown>"}' references missing parent '${parentId}'.`,
            );
          }
        } else {
          incrementalResult.items.push(item);
        }
      };

      const consumeIncrementalLine = (line: string): void => {
        if (incrementalParseError !== undefined) {
          return;
        }

        const trimmed = line.trim();
        if (trimmed.length === 0) {
          return;
        }

        try {
          const event = JSON.parse(trimmed) as IncrementalDiscoverEvent;

          if (onIncrementalDiscoverEvent) {
            try {
              onIncrementalDiscoverEvent(event);
            } catch (callbackError) {
              this.outputChannel.appendLine(
                `executeRobotCode: incremental callback failed: ${(callbackError as Error).message}`,
              );
            }
          }

          if (event.event === "item") {
            if (event.item && typeof event.item === "object") {
              addIncrementalItem(event.item, typeof event.parentId === "string" ? event.parentId : undefined);
            }
            return;
          }

          if (event.event === "diagnostics") {
            if (event.diagnostics && typeof event.diagnostics === "object") {
              incrementalResult.diagnostics = event.diagnostics;
            }
          }
        } catch (error) {
          incrementalParseError = new Error(
            `Executing robotcode failed: invalid incremental discovery event. ${(error as Error).message}`,
          );
        }
      };

      if (stdioData !== undefined) {
        process.stdin.write(stdioData, "utf8");
      } else if (expectsStdin) {
        this.outputChannel.appendLine("executeRobotCode: warning --read-from-stdin without stdioData payload");
      }
      process.stdin.end();

      process.stdout.on("data", (data: Buffer | string) => {
        const chunk = typeof data === "string" ? Buffer.from(data, "utf8") : data;
        stdoutBytes += chunk.length;
        if (incrementalOutput) {
          incrementalLineBuffer += chunk.toString("utf8");
          let newlineIndex = incrementalLineBuffer.indexOf("\n");
          while (newlineIndex !== -1) {
            const line = incrementalLineBuffer.slice(0, newlineIndex);
            consumeIncrementalLine(line);
            incrementalLineBuffer = incrementalLineBuffer.slice(newlineIndex + 1);
            newlineIndex = incrementalLineBuffer.indexOf("\n");
          }
          return;
        }

        stdoutChunks.push(chunk);
        // this.outputChannel.appendLine(data as string);
      });

      process.stderr.on("data", (data: Buffer | string) => {
        const chunk = typeof data === "string" ? Buffer.from(data, "utf8") : data;
        stderrChunks.push(chunk);
        if (!stderrLogTruncated) {
          const text = chunk.toString("utf8");
          const remaining = stderrLogLimit - stderrLoggedChars;
          if (remaining > 0) {
            const toLog = text.length > remaining ? text.slice(0, remaining) : text;
            if (toLog.length > 0) {
              this.outputChannel.appendLine(toLog);
              stderrLoggedChars += toLog.length;
            }
          }

          if (stderrLoggedChars >= stderrLogLimit) {
            stderrLogTruncated = true;
            this.outputChannel.appendLine(
              "executeRobotCode: stderr output truncated (showing first 16384 characters only)",
            );
          }
        }
      });

      process.on("error", (err) => {
        reject(err);
      });

      process.on("exit", (code) => {
        exitCode = code;
      });

      process.on("close", async () => {
        const stderr = Buffer.concat(stderrChunks).toString("utf8");
        this.outputChannel.appendLine(`executeRobotCode: exit code ${exitCode ?? "null"}`);
        this.outputChannel.appendLine(`executeRobotCode: stdout bytes=${stdoutBytes}`);
        if (exitCode === 0) {
          if (incrementalOutput) {
            if (incrementalLineBuffer.length > 0) {
              consumeIncrementalLine(incrementalLineBuffer);
              incrementalLineBuffer = "";
            }

            if (incrementalParseError !== undefined) {
              reject(incrementalParseError);
              return;
            }

            this.outputChannel.appendLine(
              `executeRobotCode: incremental parse done rootItems=${incrementalResult.items.length}`,
            );
            resolve(incrementalResult);
            return;
          }

          const stdoutDumpPath = await this.dumpDiscoveryStdout(final_args, stdoutChunks);
          if (stdoutDumpPath !== undefined) {
            this.outputChannel.appendLine(`executeRobotCode: dumped discovery stdout to ${stdoutDumpPath}`);
          }

          const stdout = Buffer.concat(stdoutChunks).toString("utf8");
          try {
            const parseStarted = Date.now();
            this.outputChannel.appendLine("executeRobotCode: parse json start");
            resolve(JSON.parse(stdout));
            this.outputChannel.appendLine(`executeRobotCode: parse json done elapsedMs=${Date.now() - parseStarted}`);
          } catch (err) {
            const head = stdout.slice(0, 1000);
            const tail = stdout.slice(-1000);
            this.outputChannel.appendLine(
              `executeRobotCode: invalid json output length=${stdout.length} head:\n${head}\n...tail:\n${tail}`,
            );
            reject(err);
          }
        } else {
          const stdout = Buffer.concat(stdoutChunks).toString("utf8");
          this.outputChannel.appendLine(`executeRobotCode: ${stdout}\n${stderr}`);

          reject(new Error(`Executing robotcode failed with code ${exitCode ?? "null"}: ${stdout}\n${stderr}`));
        }
      });
    });
  }

  // eslint-disable-next-line class-methods-use-this
  private isDiscoverCommand(args: string[]): boolean {
    return args.includes("discover");
  }

  private getDiscoveryDumpDir(): string {
    return path.join(
      this.extensionContext.globalStorageUri?.fsPath ?? this.extensionContext.extensionPath,
      "discover-dumps",
    );
  }

  private async dumpDiscoveryStdout(args: string[], stdoutChunks: Buffer[]): Promise<string | undefined> {
    if (!this.isDiscoverCommand(args)) {
      return undefined;
    }

    try {
      const dumpDir = this.getDiscoveryDumpDir();
      await fs.promises.mkdir(dumpDir, { recursive: true });

      const mode = args.includes("fast")
        ? "fast"
        : args.includes("all")
          ? "all"
          : args.includes("tests")
            ? "tests"
            : "discover";
      const fileName = `${new Date().toISOString().replace(/[.:]/g, "-")}_runner_stdout_${mode}.json`;
      const filePath = path.join(dumpDir, fileName);

      const fileHandle = await fs.promises.open(filePath, "w");
      try {
        for (const chunk of stdoutChunks) {
          await fileHandle.write(chunk);
        }
        await fileHandle.write("\n");
      } finally {
        await fileHandle.close();
      }

      return filePath;
    } catch (error) {
      this.outputChannel.appendLine(`executeRobotCode: failed to dump discovery stdout (${(error as Error).message})`);
      return undefined;
    }
  }

  // eslint-disable-next-line class-methods-use-this
  private formatArgsForLog(args: string[]): string {
    return JSON.stringify(args);
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
      ...(profiles !== undefined ? profiles.flatMap((v) => ["-p", v]) : []),
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
