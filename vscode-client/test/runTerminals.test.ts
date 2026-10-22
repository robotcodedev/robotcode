import * as assert from "assert";
import * as net from "net";
import * as path from "path";
import { spawnSync } from "child_process";
import * as vscode from "vscode";

import { chooseRunTerminal, RunTerminalRun, RunTerminals, shownArgs, StartedRun } from "../extension/runTerminals";

suite("shownArgs", () => {
  const main = path.join(path.sep, "ext", "bundled", "tool", "robotcode");
  const python = path.join(path.sep, "project", ".venv", "bin", "python");

  test("shows the interpreter with RobotCode's script as robotcode", () => {
    assert.deepStrictEqual(shownArgs([python, main, "-p", "ci", "debug", "--", "-I", "tests/a.robot"], main), [
      "robotcode",
      "-p",
      "ci",
      "debug",
      "--",
      "-I",
      "tests/a.robot",
    ]);
  });

  test("shows the interpreter with -m robotcode.cli as robotcode", () => {
    assert.deepStrictEqual(shownArgs([python, "-m", "robotcode.cli", "debug"], main), ["robotcode", "debug"]);
  });

  test("leaves another command line as it is", () => {
    assert.deepStrictEqual(shownArgs([python, "other.py", "debug"], main), [python, "other.py", "debug"]);
  });
});

suite("chooseRunTerminal", () => {
  const folder = "file:///project";

  test("reuses a free terminal of the same name and folder", () => {
    const free = { name: "RobotCode: Run Tests", folder, busy: false };
    assert.strictEqual(chooseRunTerminal([free], "RobotCode: Run Tests", folder), free);
  });

  test("takes no busy terminal and none of another name or folder", () => {
    const terminals = [
      { name: "RobotCode: Run Tests", folder, busy: true },
      { name: "RobotCode: Debug Tests", folder, busy: false },
      { name: "RobotCode: Run Tests", folder: "file:///other", busy: false },
    ];
    assert.strictEqual(chooseRunTerminal(terminals, "RobotCode: Run Tests", folder), undefined);
  });
});

// The Python interpreter for the run terminals and their runs: ROBOTCODE_TEST_PYTHON, or else python3 or python on the
// path, 3.10 or newer as RobotCode needs.
function findPython(): string {
  const configured = process.env.ROBOTCODE_TEST_PYTHON;
  for (const candidate of configured ? [configured] : ["python3", "python"]) {
    const result = spawnSync(
      candidate,
      ["-c", "import sys; print(sys.executable); sys.exit(sys.version_info < (3, 10))"],
      { encoding: "utf8" },
    );
    if (result.status === 0) return result.stdout.trim();
  }
  throw new Error("The tests need Python 3.10 or newer, as python3 or python on the path or in ROBOTCODE_TEST_PYTHON.");
}

suite("RunTerminals", function () {
  // the terminals are real ones of the VS Code that runs the tests
  this.timeout(60000);

  const name = "RobotCode Test Run";
  // the script as the package has it
  const script = path.join(__dirname, "..", "..", "bundled", "tool", "utils", "run_terminal.py");
  let python: string;
  let runTerminals: RunTerminals;

  // a run of the interpreter that also runs the script, which reports the result of `code` as its exit code
  function start(code: string): Promise<StartedRun> {
    const run: RunTerminalRun = { args: [python, "-c", code] };
    return runTerminals.start(name, undefined, run, python);
  }

  function closed(terminal: vscode.Terminal): Promise<void> {
    return new Promise((resolve) => {
      const disposable = vscode.window.onDidCloseTerminal((t) => {
        if (t === terminal) {
          disposable.dispose();
          resolve();
        }
      });
    });
  }

  suiteSetup(() => {
    python = findPython();
  });

  setup(() => {
    runTerminals = new RunTerminals(script);
  });

  teardown(() => {
    runTerminals.dispose();
    for (const terminal of vscode.window.terminals) {
      if (terminal.name === name) terminal.dispose();
    }
  });

  test("runs with the terminal as its input and output and reuses the terminal for the next run", async () => {
    const first = await start("import sys; sys.exit(3 if sys.stdin.isatty() and sys.stdout.isatty() else 4)");
    assert.strictEqual(await first.ended, 3);

    const second = await start("import sys; sys.exit(5)");
    assert.strictEqual(second.terminal, first.terminal);
    assert.strictEqual(await second.ended, 5);
  });

  test("gives a run while another is in progress a terminal of its own", async () => {
    const first = await start("import time; time.sleep(3)");
    const second = await start("pass");
    assert.notStrictEqual(second.terminal, first.terminal);
    assert.deepStrictEqual(await Promise.all([first.ended, second.ended]), [0, 0]);
  });

  test("closes the terminal on a key after the run, and the next run gets a new one", async () => {
    const started = await start("pass");
    await started.ended;

    const terminalClosed = closed(started.terminal);
    started.terminal.sendText("x", false);
    await terminalClosed;

    const next = await start("pass");
    assert.notStrictEqual(next.terminal, started.terminal);
    assert.strictEqual(await next.ended, 0);
  });

  test("drops a line sent at once after the run, as Rerun Command sends it", async () => {
    const started = await start("pass");
    await started.ended;

    const terminalClosed = closed(started.terminal);
    started.terminal.sendText("robot --version", true);
    await new Promise((resolve) => setTimeout(resolve, 1000));
    assert.ok(vscode.window.terminals.includes(started.terminal));

    started.terminal.sendText("x", false);
    await terminalClosed;
  });

  test("keeps the output of a run whose extension is gone until a key", async () => {
    const started = await start("import time; time.sleep(1.5)");
    // as a restart of the extension host closes the connection
    runTerminals.dispose();

    await new Promise((resolve) => setTimeout(resolve, 3000));
    assert.ok(vscode.window.terminals.includes(started.terminal));

    const terminalClosed = closed(started.terminal);
    started.terminal.sendText("x", false);
    await terminalClosed;
  });

  test("runs in a new terminal when the previous one was closed by a key just before", async () => {
    const started = await start("pass");
    await started.ended;

    started.terminal.sendText("x", false);
    // the script has ended, VS Code may not have reported the terminal closed yet
    await new Promise((resolve) => setTimeout(resolve, 200));

    const next = await start("import sys; sys.exit(7)");
    assert.notStrictEqual(next.terminal, started.terminal);
    assert.strictEqual(await next.ended, 7);
  });

  test("closes a connection without the key of a terminal being created, which ends no run", async () => {
    const started = await start("import time; time.sleep(3)");
    const env = (started.terminal.creationOptions as vscode.TerminalOptions).env ?? {};
    const [host, port] = (env.ROBOTCODE_RUN_TERMINAL_ADDRESS ?? "").split(":");

    // what another local process gets that connects and sends `messages`, until its connection is closed
    async function connect(...messages: object[]): Promise<string> {
      const socket = net.connect(Number(port), host);
      let received = "";
      socket.on("data", (data) => (received += data.toString()));
      socket.on("error", () => {});
      const socketClosed = new Promise((resolve) => socket.on("close", resolve));
      socket.write(messages.map((message) => JSON.stringify(message) + "\n").join(""));
      await socketClosed;
      return received;
    }

    // as the end of the run, whose id is the first, and with the key of the terminal, which has started already
    const ended = { type: "ended", id: 1, exitCode: 42 };
    assert.strictEqual(await connect(ended), "");
    assert.strictEqual(await connect({ type: "ready", key: env.ROBOTCODE_RUN_TERMINAL_KEY }, ended), "");

    assert.strictEqual(await started.ended, 0);
  });
});
