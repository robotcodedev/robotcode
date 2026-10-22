import * as net from "net";
import * as vscode from "vscode";
import { randomBytes } from "crypto";
import { resolve } from "path";
import { platform } from "process";
import { commandLine } from "./commandLine";
import { runHeader } from "./shellIntegration";

// how long a new run terminal may take until its script has connected
const READY_TIMEOUT = 20000;

/**
 * A run for a run terminal: the command line of the run's process, its working directory and environment, and the
 * command line to show for it, when that differs.
 */
export interface RunTerminalRun {
  args: string[];
  cwd?: string;
  env?: { [key: string]: string };
  shownArgs?: string[];
}

function samePath(a: string, b: string): boolean {
  return platform === "win32" ? resolve(a).toLowerCase() === resolve(b).toLowerCase() : resolve(a) === resolve(b);
}

/**
 * The command line `args` as a run terminal shows it: the interpreter with RobotCode's script `robotCodeMain`, or with
 * `-m robotcode.cli`, as `robotcode`, the way one types it in a terminal; any other command line as it is.
 */
export function shownArgs(args: readonly string[], robotCodeMain: string): string[] {
  if (args.length >= 2 && samePath(args[1], robotCodeMain)) return ["robotcode", ...args.slice(2)];
  if (args.length >= 3 && args[1] === "-m" && args[2] === "robotcode.cli") return ["robotcode", ...args.slice(3)];
  return [...args];
}

/** What the choice of a run terminal looks at. */
export interface RunTerminalState {
  name: string;
  folder: string | undefined;
  busy: boolean;
}

/**
 * The run terminal for a run with the name `name` in the workspace folder `folder`: one of the same name and folder
 * with no run in progress, or `undefined` when the run needs a new one.
 */
export function chooseRunTerminal<T extends RunTerminalState>(
  terminals: readonly T[],
  name: string,
  folder: string | undefined,
): T | undefined {
  return terminals.find((t) => !t.busy && t.name === name && t.folder === folder);
}

// a message of a run terminal's script, one JSON object per line
interface ScriptMessage {
  type?: string;
  key?: string;
  id?: number;
  exitCode?: number | null;
}

function parseMessage(line: string): ScriptMessage | undefined {
  try {
    const message: unknown = JSON.parse(line);
    return typeof message === "object" && message !== null ? (message as ScriptMessage) : undefined;
  } catch {
    return undefined;
  }
}

interface RunTerminal extends RunTerminalState {
  key: string;
  terminal: vscode.Terminal;
  socket: net.Socket;
  runId?: number;
}

interface PendingTerminal {
  terminal?: vscode.Terminal;
  resolve: (socket: net.Socket) => void;
  reject: (reason: Error) => void;
}

/** A run that started in a run terminal; `ended` resolves with its exit code, `null` when it has none. */
export interface StartedRun {
  terminal: vscode.Terminal;
  ended: Promise<number | null>;
}

/**
 * RobotCode's run terminals: terminals whose process is the Python script `scriptPath`, which runs the runs it gets
 * over a local connection with the terminal as their input and output and waits after each run for a key or the next
 * run.
 */
export class RunTerminals implements vscode.Disposable {
  private readonly _terminals: RunTerminal[] = [];
  private readonly _pending = new Map<string, PendingTerminal>();
  private readonly _ended = new Map<number, (exitCode: number | null) => void>();
  private readonly _disposable: vscode.Disposable;
  private _server: net.Server | undefined;
  private _address: Promise<string> | undefined;
  private _nextId = 1;

  constructor(private readonly scriptPath: string) {
    this._disposable = vscode.window.onDidCloseTerminal((terminal) => this.forget(terminal));
  }

  dispose(): void {
    this._disposable.dispose();
    // the terminals keep their output, and their scripts take no more runs
    for (const runTerminal of [...this._terminals]) this.remove(runTerminal);
    this._server?.close();
    this._server = undefined;
  }

  /**
   * Starts `run` in a run terminal named `name` of the workspace folder `folder`. A new run terminal runs its script
   * with the Python interpreter `python`.
   */
  async start(
    name: string,
    folder: vscode.WorkspaceFolder | undefined,
    run: RunTerminalRun,
    python: string,
  ): Promise<StartedRun> {
    const folderKey = folder?.uri.toString();
    const runTerminal =
      chooseRunTerminal(this._terminals, name, folderKey) ?? (await this.create(name, folder, python));

    const id = this._nextId++;
    runTerminal.busy = true;
    runTerminal.runId = id;
    const ended = new Promise<number | null>((resolve) => this._ended.set(id, resolve));

    runTerminal.terminal.show(true);
    runTerminal.socket.write(
      JSON.stringify({
        type: "run",
        id,
        command: run.args[0],
        args: run.args.slice(1),
        cwd: run.cwd,
        env: run.env,
        header: runHeader(commandLine(run.shownArgs ?? run.args), commandLine(run.args)),
      }) + "\n",
    );
    return { terminal: runTerminal.terminal, ended };
  }

  private async create(name: string, folder: vscode.WorkspaceFolder | undefined, python: string): Promise<RunTerminal> {
    const address = await this.listen();
    const key = randomBytes(8).toString("hex");
    const pending: PendingTerminal = { resolve: () => {}, reject: () => {} };
    const connected = new Promise<net.Socket>((resolve, reject) => {
      pending.resolve = resolve;
      pending.reject = reject;
    });
    this._pending.set(key, pending);

    // Created hidden and shown at once, as the REPL's terminal: the Python extensions type no activation into it.
    const terminal = (pending.terminal = vscode.window.createTerminal({
      name,
      // isolated, so that neither PYTHONPATH nor the user's site packages nor the working directory reach the script;
      // the runs get the whole environment
      shellPath: python,
      shellArgs: ["-I", this.scriptPath],
      cwd: folder?.uri,
      env: { ROBOTCODE_RUN_TERMINAL_ADDRESS: address, ROBOTCODE_RUN_TERMINAL_KEY: key },
      iconPath: new vscode.ThemeIcon("robotcode-robot"),
      hideFromUser: true,
      isTransient: true,
    }));
    terminal.show(true);

    let timer: NodeJS.Timeout | undefined;
    const timeout = new Promise<never>((_, reject) => {
      timer = setTimeout(() => reject(new Error(`The run terminal "${name}" did not start.`)), READY_TIMEOUT);
    });
    try {
      const socket = await Promise.race([connected, timeout]);
      const runTerminal: RunTerminal = { key, name, folder: folder?.uri.toString(), busy: false, terminal, socket };
      this._terminals.push(runTerminal);
      return runTerminal;
    } catch (e) {
      terminal.dispose();
      throw e;
    } finally {
      clearTimeout(timer);
      this._pending.delete(key);
    }
  }

  // TCP on the loopback interface: on Windows, Python cannot write to a named pipe while it reads from it, which the
  // script does. Every local process can connect, though, so a connection counts only as `connected` describes.
  private listen(): Promise<string> {
    if (this._address === undefined) {
      this._address = new Promise((resolve, reject) => {
        const server = net.createServer((socket) => this.connected(socket));
        server.once("error", (e) => {
          // the next run tries again
          this._address = undefined;
          reject(e);
        });
        server.listen(0, "127.0.0.1", () => resolve(`127.0.0.1:${(server.address() as net.AddressInfo).port}`));
        this._server = server;
      });
    }
    return this._address;
  }

  // A connection whose first message is not `ready` with the key of a terminal being created is closed; a key binds
  // one connection. Only the connection of the terminal that has a run ends it.
  private connected(socket: net.Socket): void {
    let bound = false;
    let buffer = "";
    socket.on("data", (data) => {
      buffer += data.toString();
      for (let i = buffer.indexOf("\n"); i >= 0; i = buffer.indexOf("\n")) {
        const message = parseMessage(buffer.slice(0, i));
        buffer = buffer.slice(i + 1);
        if (!bound) {
          const key = message?.type === "ready" ? message.key : undefined;
          const pending = key !== undefined ? this._pending.get(key) : undefined;
          if (key === undefined || pending === undefined) {
            socket.destroy();
            return;
          }
          this._pending.delete(key);
          bound = true;
          pending.resolve(socket);
        } else if (message?.type === "ended" && message.id !== undefined) {
          const runTerminal = this._terminals.find((t) => t.socket === socket && t.runId === message.id);
          if (runTerminal !== undefined) {
            runTerminal.busy = false;
            runTerminal.runId = undefined;
            this.end(message.id, message.exitCode ?? null);
          }
        }
      }
    });
    socket.on("error", () => {});
    // The script has ended, as after a key, before VS Code reports the terminal closed; a run starting in between needs
    // a new terminal.
    socket.on("close", () => {
      const runTerminal = this._terminals.find((t) => t.socket === socket);
      if (runTerminal !== undefined) this.remove(runTerminal);
    });
  }

  private end(id: number, exitCode: number | null): void {
    this._ended.get(id)?.(exitCode);
    this._ended.delete(id);
  }

  private forget(terminal: vscode.Terminal): void {
    for (const pending of this._pending.values()) {
      if (pending.terminal === terminal)
        pending.reject(new Error(`The run terminal "${terminal.name}" closed at once.`));
    }

    const runTerminal = this._terminals.find((t) => t.terminal === terminal);
    if (runTerminal !== undefined) this.remove(runTerminal);
  }

  // A run terminal whose terminal closed or whose script is gone takes no more runs, and a run in it is over.
  private remove(runTerminal: RunTerminal): void {
    const i = this._terminals.indexOf(runTerminal);
    if (i < 0) return;
    this._terminals.splice(i, 1);
    runTerminal.socket.destroy();
    if (runTerminal.runId !== undefined) this.end(runTerminal.runId, null);
  }
}
