import { spawn } from "child_process";
import * as fs from "fs";
import * as path from "path";
import * as vscode from "vscode";
import { CONFIG_SECTION } from "./config";
import {
  PythonExtension,
  ActiveEnvironmentPathChangeEvent,
  ResolvedEnvironment as LegacyResolvedEnvironment,
} from "@vscode/python-extension";
import type { PythonEnvironmentApi, PythonEnvironment } from "@vscode/python-environments";

const UNKNOWN = "unknown";
const CUSTOM = "custom";
const PYTHON_ENVIRONMENTS_EXTENSION_ID = "ms-python.vscode-python-envs";
// What the Python extension's API reports as the active environment when nothing is selected.
const LEGACY_DEFAULT_PYTHON_ID = "DEFAULT_PYTHON";
const INTERPRETER_TIMEOUT = 30000;
const INTERPRETER_QUERY_SCRIPT =
  "import json, sys; print(json.dumps({'version': list(sys.version_info[:3]), 'prefix': sys.prefix}))";

// Environment names are case-insensitive on Windows, where Node would keep only one spelling of a name, the first in
// sort order; a name of `env` replaces an inherited variable of any case there.
function mergeEnvironment(env: { [key: string]: string }): NodeJS.ProcessEnv {
  const result = { ...process.env };
  if (process.platform === "win32") {
    const names = new Set(Object.keys(env).map((name) => name.toUpperCase()));
    for (const name of Object.keys(result)) {
      if (names.has(name.toUpperCase())) delete result[name];
    }
  }
  return Object.assign(result, env);
}

export interface PythonVersion {
  readonly major: number;
  readonly minor: number;
  /** Unknown when the Python side knows only `major.minor`, as for a venv whose `pyvenv.cfg` says `3.9`. */
  readonly micro?: number;
}

export function formatPythonVersion(version: PythonVersion): string {
  return `${version.major}.${version.minor}${version.micro !== undefined ? `.${version.micro}` : ""}`;
}

function parsePythonVersion(text: string | undefined): PythonVersion | undefined {
  const match = text === undefined ? null : /^\s*(\d+)\.(\d+)(?:\.(\d+))?/.exec(text);
  if (match === null) return undefined;
  return {
    major: Number(match[1]),
    minor: Number(match[2]),
    micro: match[3] !== undefined ? Number(match[3]) : undefined,
  };
}

function legacyPythonVersion(version: LegacyResolvedEnvironment["version"]): PythonVersion | undefined {
  if (version === undefined || version.major < 0 || version.minor < 0) return undefined;
  return { major: version.major, minor: version.minor, micro: version.micro < 0 ? undefined : version.micro };
}

/** Why a workspace folder has no interpreter RobotCode could start. */
export type PythonEnvironmentProblem = "noInterpreter" | "interpreterMissing";

/** What the Python side knows about the environment of a workspace folder, without Python having been started. */
export interface ResolvedPythonEnvironment {
  /** The setting `robotcode.python`, the Python Environments extension or the Python extension's API. */
  readonly source: "setting" | "pythonEnvironments" | "pythonExtension";
  readonly executable?: string;
  readonly version?: PythonVersion;
  readonly sysPrefix?: string;
  /** Set when `executable` cannot be used. */
  readonly problem?: PythonEnvironmentProblem;
  /** The environment's name as the Python side shows it. */
  readonly name?: string;
  /** The tool or manager of the environment, for example `venv` or `conda`. */
  readonly type?: string;
}

export interface PythonEnvironmentChangedEvent {
  /** The folder whose environment may have changed; `undefined` means every folder. */
  readonly folder: vscode.WorkspaceFolder | undefined;
  /** A selection changed, environments were found or removed, or packages of an environment changed. */
  readonly reason: "selection" | "environments" | "packages";
}

export interface InterpreterInfo {
  readonly version: PythonVersion;
  readonly sysPrefix: string;
}

export interface RobotFrameworkCheck {
  readonly kind: "ok" | "tooOld" | "missing" | "failed";
  readonly version?: string;
}

interface ProcessResult {
  status: number | null;
  stdout: string;
  stderr: string;
}

function runProcess(command: string, args: string[], timeout: number): Promise<ProcessResult> {
  return new Promise((resolve) => {
    let stdout = "";
    let stderr = "";
    const child = spawn(command, args, { timeout, windowsHide: true });
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (data: string) => (stdout += data));
    child.stderr.on("data", (data: string) => (stderr += data));
    child.on("error", (error) => resolve({ status: null, stdout, stderr: `${stderr}${error.message}` }));
    child.on("close", (code) => resolve({ status: code, stdout, stderr }));
  });
}

async function fileExists(file: string): Promise<boolean> {
  try {
    await fs.promises.access(file);
    return true;
  } catch {
    return false;
  }
}

// Paths of the same file may differ in case and separators on Windows.
function samePath(a: string, b: string | undefined): boolean {
  if (b === undefined) return false;
  const normalize = (p: string) => (process.platform === "win32" ? path.normalize(p).toLowerCase() : path.normalize(p));
  return normalize(a) === normalize(b);
}

function isInside(file: string, dir: string): boolean {
  const relative = path.relative(dir, file);
  return relative !== "" && !relative.startsWith("..") && !path.isAbsolute(relative);
}

function pythonEnvironmentsName(environment: PythonEnvironment): string {
  // The Python Environments extension names a venv `<folder> (<version>)`; the version is shown on its own.
  const version = parsePythonVersion(environment.version);
  let name = environment.name;
  const match = /\s*\((\d+\.\d+[^)]*)\)$/.exec(name);
  if (match !== null && version !== undefined && match[1].startsWith(`${version.major}.${version.minor}`)) {
    name = name.slice(0, match.index);
  }
  return environment.description ? `${name} (${environment.description})` : name;
}

function legacyEnvironmentName(env: LegacyResolvedEnvironment): string {
  if (env.environment !== undefined) {
    const tool = env.tools[0];
    const name = env.environment.name ?? path.basename(env.environment.folderUri.fsPath);
    return tool !== undefined ? `${name} (${tool.toLowerCase()})` : name;
  }
  // a global interpreter has no environment; name it as the Python Environments extension does
  const version = legacyPythonVersion(env.version);
  return version !== undefined ? `Python ${formatPythonVersion(version)}` : (env.executable.uri?.fsPath ?? UNKNOWN);
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

  private readonly _onDidChangeEnvironmentEmitter = new vscode.EventEmitter<PythonEnvironmentChangedEvent>();
  /** The environment events of the Python extension's API and of the Python Environments API, merged. */
  public get onDidChangeEnvironment(): vscode.Event<PythonEnvironmentChangedEvent> {
    return this._onDidChangeEnvironmentEmitter.event;
  }

  _pythonLanguageServerMain: string;
  _checkRobotVersionMain: string;
  _robotCodeMain: string;

  private _pythonExtension: Promise<PythonExtension | undefined> | undefined;
  private _pythonEnvironmentsApi: Promise<PythonEnvironmentApi | undefined> | undefined;
  private readonly _disposables: vscode.Disposable[] = [this._onDidChangeEnvironmentEmitter];
  // Version and prefix of interpreters the Python side reported without them, asked once per interpreter.
  private readonly _interpreterInfos = new Map<string, InterpreterInfo>();
  // Interpreters of virtual environments that appeared in a workspace folder while the window was open.
  private readonly _virtualEnvironments = new Map<string, Set<string>>();

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
    vscode.Disposable.from(...this._disposables).dispose();
  }

  private fireEnvironmentChanged(
    folder: vscode.WorkspaceFolder | undefined,
    reason: PythonEnvironmentChangedEvent["reason"],
  ): void {
    if (reason === "selection") {
      this.outputChannel.appendLine(`Python environment selection changed: ${folder?.uri.toString() ?? "all folders"}`);
    }
    this._onDidChangeEnvironmentEmitter.fire({ folder, reason });
  }

  private doActiveEnvironmentPathChanged(event: ActiveEnvironmentPathChangeEvent): void {
    const wsFolder =
      event.resource === undefined
        ? undefined
        : event.resource instanceof vscode.Uri
          ? vscode.workspace.getWorkspaceFolder(event.resource)
          : event.resource;

    this.fireEnvironmentChanged(wsFolder, "selection");
  }

  getPythonExtension(): Promise<PythonExtension | undefined> {
    if (this._pythonExtension === undefined) {
      this._pythonExtension = (async () => {
        this.outputChannel.appendLine("Try to activate python extension");

        let pythonExtension: PythonExtension | undefined;
        try {
          pythonExtension = await PythonExtension.api();

          this.outputChannel.appendLine("Python Extension is active");
          await pythonExtension.ready;
        } catch (ex: unknown) {
          this.outputChannel.appendLine(`can't activate python extension ${ex?.toString() ?? ""}`);
        }

        if (pythonExtension !== undefined) {
          this._disposables.push(
            pythonExtension.environments.onDidChangeActiveEnvironmentPath((event) =>
              this.doActiveEnvironmentPathChanged(event),
            ),
            pythonExtension.environments.onDidChangeEnvironments(() =>
              this.fireEnvironmentChanged(undefined, "environments"),
            ),
          );
        }
        return pythonExtension;
      })();
    }
    return this._pythonExtension;
  }

  /**
   * The API of the Python Environments extension, or `undefined` when the extension is not installed or offers no
   * API, as it does when the setting `python.useEnvironmentsExtension` is `false`.
   */
  getPythonEnvironmentsApi(): Promise<PythonEnvironmentApi | undefined> {
    if (this._pythonEnvironmentsApi === undefined) {
      this._pythonEnvironmentsApi = (async () => {
        const extension = vscode.extensions.getExtension<PythonEnvironmentApi | undefined>(
          PYTHON_ENVIRONMENTS_EXTENSION_ID,
        );
        if (extension === undefined) return undefined;

        try {
          const api = await extension.activate();
          if (api === undefined || typeof api.getEnvironment !== "function") {
            this.outputChannel.appendLine("Python Environments extension offers no API, using the Python extension");
            return undefined;
          }

          this.outputChannel.appendLine("Python Environments extension is active");
          this._disposables.push(
            api.onDidChangeEnvironment((event) =>
              this.fireEnvironmentChanged(
                event.uri !== undefined ? vscode.workspace.getWorkspaceFolder(event.uri) : undefined,
                "selection",
              ),
            ),
            api.onDidChangeEnvironments(() => this.fireEnvironmentChanged(undefined, "environments")),
            api.onDidChangePackages(() => this.fireEnvironmentChanged(undefined, "packages")),
          );
          return api;
        } catch (ex: unknown) {
          this.outputChannel.appendLine(`can't activate Python Environments extension ${ex?.toString() ?? ""}`);
          return undefined;
        }
      })();
    }
    return this._pythonEnvironmentsApi;
  }

  /**
   * The Python environment of a workspace folder: the setting `robotcode.python` when set, otherwise what the
   * Python Environments extension reports for the folder, otherwise what the Python extension's API reports.
   */
  public async resolveEnvironment(folder: vscode.WorkspaceFolder | undefined): Promise<ResolvedPythonEnvironment> {
    const configPython = vscode.workspace.getConfiguration(CONFIG_SECTION, folder).get<string>("python");
    if (configPython !== undefined && configPython !== "") {
      return this.completeEnvironment({ source: "setting", executable: configPython, name: CUSTOM });
    }

    const pythonEnvironmentsApi = await this.getPythonEnvironmentsApi();
    if (pythonEnvironmentsApi !== undefined) {
      let environment: PythonEnvironment | undefined;
      try {
        environment = await pythonEnvironmentsApi.getEnvironment(folder?.uri);
      } catch (ex: unknown) {
        this.outputChannel.appendLine(`getEnvironment failed: ${ex?.toString() ?? ""}`);
      }
      if (environment === undefined) return { source: "pythonEnvironments", problem: "noInterpreter" };

      const executable = environment.execInfo?.run?.executable;
      const resolved: ResolvedPythonEnvironment = {
        source: "pythonEnvironments",
        executable: executable || undefined,
        version: parsePythonVersion(environment.version),
        sysPrefix: environment.sysPrefix || undefined,
        name: pythonEnvironmentsName(environment),
        type: environment.envId.managerId.split(":").pop(),
      };
      if (environment.error !== undefined || environment.version === "no-python" || !executable) {
        return { ...resolved, problem: "interpreterMissing" };
      }
      return this.completeEnvironment(resolved);
    }

    const pythonExtension = await this.getPythonExtension();
    if (pythonExtension === undefined) return { source: "pythonExtension", problem: "noInterpreter" };

    // Nothing selected is `DEFAULT_PYTHON` with the path `python`; it is resolved like any other path, so that a
    // `python` the Python extension finds on the PATH is used, and counts as "no interpreter selected" otherwise.
    const environmentPath = pythonExtension.environments.getActiveEnvironmentPath(folder);
    const env = await pythonExtension.environments.resolveEnvironment(environmentPath);
    const executable = env?.executable.uri?.fsPath;
    if (env === undefined || executable === undefined) {
      return environmentPath.id === LEGACY_DEFAULT_PYTHON_ID
        ? { source: "pythonExtension", problem: "noInterpreter" }
        : { source: "pythonExtension", executable: environmentPath.path, problem: "interpreterMissing" };
    }

    return this.completeEnvironment({
      source: "pythonExtension",
      executable,
      version: legacyPythonVersion(env.version),
      sysPrefix: env.executable.sysPrefix,
      name: legacyEnvironmentName(env),
      type: env.tools[0],
    });
  }

  // Adds what an earlier interpreter query found out, and reports an interpreter that is gone from disk.
  private async completeEnvironment(resolved: ResolvedPythonEnvironment): Promise<ResolvedPythonEnvironment> {
    const executable = resolved.executable;
    if (executable === undefined) return resolved;

    if (path.isAbsolute(executable) && !(await fileExists(executable))) {
      this._interpreterInfos.delete(executable);
      return { ...resolved, problem: "interpreterMissing" };
    }

    const info = this._interpreterInfos.get(executable);
    if (info === undefined) return resolved;

    return { ...resolved, version: resolved.version ?? info.version, sysPrefix: resolved.sysPrefix ?? info.sysPrefix };
  }

  public async getPythonCommand(folder: vscode.WorkspaceFolder | undefined): Promise<string | undefined> {
    return (await this.resolveEnvironment(folder)).executable;
  }

  /** Asks an interpreter for its version and prefix, once; used when the Python side reported neither. */
  public async queryInterpreter(executable: string): Promise<InterpreterInfo | undefined> {
    const cached = this._interpreterInfos.get(executable);
    if (cached !== undefined) return cached;

    const res = await runProcess(executable, ["-u", "-c", INTERPRETER_QUERY_SCRIPT], INTERPRETER_TIMEOUT);
    if (res.status !== 0) {
      this.outputChannel.appendLine(`queryInterpreter ${executable} failed: ${res.stderr || res.stdout}`);
      return undefined;
    }

    try {
      const data = JSON.parse(res.stdout.trim()) as { version: number[]; prefix: string };
      const info: InterpreterInfo = {
        version: { major: data.version[0], minor: data.version[1], micro: data.version[2] },
        sysPrefix: data.prefix,
      };
      this._interpreterInfos.set(executable, info);
      return info;
    } catch {
      this.outputChannel.appendLine(`queryInterpreter ${executable}: unexpected output ${res.stdout}`);
      return undefined;
    }
  }

  /** Forgets what interpreters answered, so that a changed interpreter is asked again. */
  public forgetInterpreters(): void {
    this._interpreterInfos.clear();
  }

  /**
   * Whether Robot Framework 5.0 or newer can be imported with the interpreter, found as Python itself finds it
   * (site-packages, user site, PYTHONPATH, .pth files): `missing` when the check script says so, `tooOld` with the
   * version for an older one, `failed` when the interpreter could not run the script at all.
   */
  public async checkRobotVersion(pythonCommand: string): Promise<RobotFrameworkCheck> {
    const res = await runProcess(pythonCommand, ["-u", this.checkRobotVersionMain], INTERPRETER_TIMEOUT);

    if (res.status === 0) {
      try {
        const data = JSON.parse(res.stdout.trim()) as { ok: boolean; version: string };
        return { kind: data.ok ? "ok" : "tooOld", version: data.version };
      } catch {
        this.outputChannel.appendLine(`checkRobotVersion ${pythonCommand}: unexpected output ${res.stdout}`);
        return { kind: "failed" };
      }
    }

    if (res.stderr.includes("Robot Framework not installed")) return { kind: "missing" };

    this.outputChannel.appendLine(
      `checkRobotVersion ${pythonCommand} failed${res.status === null ? " (timeout or not started)" : ` with code ${res.status}`}: ${res.stderr || res.stdout}`,
    );
    return { kind: "failed" };
  }

  /** Asks the Python side to look for environments again, after a virtual environment appeared in the folder. */
  public async refreshEnvironments(folder: vscode.WorkspaceFolder): Promise<void> {
    try {
      const pythonEnvironmentsApi = await this.getPythonEnvironmentsApi();
      if (pythonEnvironmentsApi !== undefined) {
        await pythonEnvironmentsApi.refreshEnvironments(folder.uri);
      } else {
        await (await this.getPythonExtension())?.environments.refreshEnvironments({ forceRefresh: true });
      }
    } catch (ex: unknown) {
      this.outputChannel.appendLine(`refreshEnvironments failed: ${ex?.toString() ?? ""}`);
    }
  }

  /** Notes the interpreter of a virtual environment whose `pyvenv.cfg` appeared, and returns it. */
  public rememberVirtualEnvironment(pyvenvCfg: vscode.Uri): string | undefined {
    const folder = vscode.workspace.getWorkspaceFolder(pyvenvCfg);
    if (folder === undefined) return undefined;

    const executable = virtualEnvironmentInterpreter(path.dirname(pyvenvCfg.fsPath));

    // a re-created environment may have another Python
    this._interpreterInfos.delete(executable);

    const key = folder.uri.toString();
    const candidates = this._virtualEnvironments.get(key) ?? new Set<string>();
    candidates.add(executable);
    this._virtualEnvironments.set(key, candidates);
    return executable;
  }

  /**
   * A virtual environment in the folder that is not selected: one the Python extension knows, one that appeared
   * while the window is open, or `.venv` and `venv` in the folder itself, which the Python extension may not have
   * found yet. Only with the Python extension's API: the Python Environments extension selects a new environment of
   * the folder itself.
   */
  public async findVirtualEnvironmentCandidate(
    folder: vscode.WorkspaceFolder,
    currentExecutable: string | undefined,
  ): Promise<string | undefined> {
    if ((await this.getPythonEnvironmentsApi()) !== undefined) return undefined;

    const candidates = new Set<string>(this._virtualEnvironments.get(folder.uri.toString()) ?? []);
    const folderPath = folder.uri.fsPath;
    for (const name of [".venv", "venv"]) {
      const dir = path.join(folderPath, name);
      if (await fileExists(path.join(dir, "pyvenv.cfg"))) candidates.add(virtualEnvironmentInterpreter(dir));
    }
    for (const env of (await this.getPythonExtension())?.environments.known ?? []) {
      const executable = env.executable.uri?.fsPath;
      const envFolder = env.environment?.folderUri.fsPath;
      if (executable !== undefined && envFolder !== undefined && isInside(envFolder, folderPath)) {
        candidates.add(executable);
      }
    }

    const existing: string[] = [];
    for (const candidate of candidates) {
      if (!samePath(candidate, currentExecutable) && (await fileExists(candidate))) existing.push(candidate);
    }
    // `.venv` first, then the others in a stable order
    existing.sort((a, b) => {
      const aVenv = path.basename(virtualEnvironmentDir(a)) === ".venv" ? 0 : 1;
      const bVenv = path.basename(virtualEnvironmentDir(b)) === ".venv" ? 0 : 1;
      return aVenv - bVenv || a.localeCompare(b);
    });
    return existing[0];
  }

  /** Selects an interpreter for the folder on the Python side, with the Python extension's API. */
  public async useVirtualEnvironment(folder: vscode.WorkspaceFolder, executable: string): Promise<void> {
    await (await this.getPythonExtension())?.environments.updateActiveEnvironmentPath(executable, folder);
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
    env?: { [key: string]: string },
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

    const processEnv = env !== undefined ? mergeEnvironment(env) : undefined;

    return new Promise((resolve, reject) => {
      const abortController = new AbortController();

      token?.onCancellationRequested(() => {
        abortController.abort();
      });

      const { signal } = abortController;

      const process = spawn(pythonCommand, final_args, {
        cwd: folder.uri.fsPath,
        env: processEnv,

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
      ...(profiles !== undefined ? profiles.flatMap((v) => ["-p", v]) : []),
      ...args,
    ];
    return { pythonCommand, final_args };
  }

  async getPythonInfo(folder: vscode.WorkspaceFolder): Promise<PythonInfo | undefined> {
    try {
      const environment = await this.resolveEnvironment(folder);
      if (environment.executable === undefined) return undefined;

      return new PythonInfo(
        environment.name ?? CUSTOM,
        environment.type,
        environment.version !== undefined ? formatPythonVersion(environment.version) : UNKNOWN,
        environment.executable,
      );
    } catch {
      return undefined;
    }
  }
}

/**
 * The directory of a virtual environment, from its interpreter `<dir>/bin/python` or `<dir>\Scripts\python.exe`;
 * a conda environment on Windows has `<dir>\python.exe`.
 */
export function virtualEnvironmentDir(executable: string): string {
  const parent = path.dirname(executable);
  return ["bin", "scripts"].includes(path.basename(parent).toLowerCase()) ? path.dirname(parent) : parent;
}

/** The interpreter of a virtual environment directory. */
function virtualEnvironmentInterpreter(dir: string): string {
  return process.platform === "win32" ? path.join(dir, "Scripts", "python.exe") : path.join(dir, "bin", "python");
}
