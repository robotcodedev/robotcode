// The process of a RobotCode run terminal, started by the extension with VS Code's own runtime. It runs each run the
// extension sends over a local socket with the terminal as the run's input and output, then waits for a key, which
// closes the terminal, or for the next run, which goes below the earlier output.
import * as net from "net";
import { spawn } from "child_process";
import { commandLine } from "./commandLine";
import {
  COMMAND_EXECUTED,
  COMMAND_START,
  PROMPT_START,
  RICH_COMMAND_DETECTION,
  commandFinished,
  commandLineSequence,
} from "./shellIntegration";

interface RunMessage {
  type: "run";
  id: number;
  command: string;
  args: string[];
  cwd?: string;
  env?: { [key: string]: string };
  // the command line to show, when it differs from the one that runs
  shownArgs?: string[];
}

// marks a message of the terminal itself, as VS Code marks its own: " * " in inverse video
const MARK = "\x1b[0m\x1b[7m * \x1b[0m ";

const REUSE_MESSAGE = `\r\n${MARK}Terminal will be reused by RobotCode runs, press any key to close it.\r\n`;

// without the extension, as after a restart of the extension host, nothing reuses the terminal
const CLOSE_MESSAGE = `\r\n${MARK}Press any key to close the terminal.\r\n`;

const socketPath = process.env.ROBOTCODE_RUN_TERMINAL_SOCKET;
const terminalKey = process.env.ROBOTCODE_RUN_TERMINAL_KEY;
for (const name of ["ELECTRON_RUN_AS_NODE", "ROBOTCODE_RUN_TERMINAL_SOCKET", "ROBOTCODE_RUN_TERMINAL_KEY"]) {
  delete process.env[name];
}

// Ctrl+C belongs to the run; the terminal stays.
process.on("SIGINT", () => {});

let state: "idle" | "running" | "waiting" = "idle";
let socketClosed = false;

const socket = net.connect(socketPath ?? "");

function send(message: object): void {
  if (!socketClosed) socket.write(JSON.stringify(message) + "\n");
}

// how long input may take to arrive as a whole; a key is one character or one escape sequence, while VS Code's Rerun
// Command, Run Recent Command and a paste send a whole line at once
const INPUT_SETTLE = 50;
const SINGLE_KEY = /^(?:[^]|\x1b[[O][\d;]*[A-Za-z~])$/u;

let input = "";
let inputTimer: NodeJS.Timeout | undefined;

// After a run, a single key closes the terminal; a line sent at once is dropped, so that it neither closes the terminal
// nor starts anything.
function onInput(data: Buffer): void {
  input += data.toString();
  clearTimeout(inputTimer);
  inputTimer = setTimeout(() => {
    const key = SINGLE_KEY.test(input);
    input = "";
    if (key) process.exit(0);
  }, INPUT_SETTLE);
}

function waitForKeyOrRun(): void {
  state = "waiting";
  process.stdout.write(socketClosed ? CLOSE_MESSAGE : REUSE_MESSAGE);
  if (process.stdin.isTTY) process.stdin.setRawMode(true);
  process.stdin.resume();
  process.stdin.on("data", onInput);
}

function stopWaiting(): void {
  process.stdin.removeListener("data", onInput);
  clearTimeout(inputTimer);
  input = "";
  if (process.stdin.isTTY) process.stdin.setRawMode(false);
  process.stdin.pause();
  process.stdout.write("\r\n");
}

function run(message: RunMessage): void {
  if (state === "running") {
    send({ type: "ended", id: message.id, exitCode: null, error: "busy" });
    return;
  }
  if (state === "waiting") stopWaiting();
  state = "running";

  let reported = false;
  const ended = (exitCode: number | null, error?: string): void => {
    if (reported) return;
    reported = true;
    process.stdout.write(commandFinished(exitCode));
    // waiting first, so that a key right after the report already closes the terminal
    waitForKeyOrRun();
    send({ type: "ended", id: message.id, exitCode, error });
  };

  // The command line comes first, as a shell terminal shows the typed command, and is the command of VS Code's shell
  // integration, so that it gets VS Code's decoration with its menu. The mark and "Executing: " are the prompt. The
  // command line goes once more after the start of the output: VS Code reads the command from the screen at that point,
  // and only a command line sent after it wins over that without the nonce that VS Code gives its own shells.
  // VS Code shows the short line and copies the full one with Copy Command.
  const fullLine = commandLine([message.command, ...message.args]);
  const shownLine = message.shownArgs !== undefined ? commandLine(message.shownArgs) : fullLine;
  process.stdout.write(
    `${PROMPT_START}${MARK}Executing: ${COMMAND_START}${shownLine}\r\n${COMMAND_EXECUTED}${commandLineSequence(fullLine)}`,
  );

  const child = spawn(message.command, message.args, {
    cwd: message.cwd,
    env: { ...process.env, ...message.env },
    stdio: "inherit",
  });
  child.on("error", (e) => {
    process.stdout.write(`\r\n${e.message}\r\n`);
    ended(null, e.message);
  });
  child.on("close", (code) => ended(code));
}

process.stdout.write(RICH_COMMAND_DETECTION);

socket.on("connect", () => send({ type: "ready", key: terminalKey }));
// Without the extension the terminal takes no more runs. It keeps the output of its runs until a key; without a run yet
// it has nothing to show.
socket.on("close", () => {
  socketClosed = true;
  if (state === "idle") process.exit(0);
  if (state === "waiting") process.stdout.write(CLOSE_MESSAGE);
});
socket.on("error", () => {});

let buffer = "";
socket.on("data", (data) => {
  buffer += data.toString();
  for (let i = buffer.indexOf("\n"); i >= 0; i = buffer.indexOf("\n")) {
    const message = JSON.parse(buffer.slice(0, i)) as RunMessage;
    buffer = buffer.slice(i + 1);
    if (message.type === "run") run(message);
  }
});
