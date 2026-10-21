import * as assert from "assert";
import * as path from "path";
import * as vscode from "vscode";

import { chooseRunTerminal, RunTerminalRun, RunTerminals, shownArgs } from "../extension/runTerminals";

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

suite("RunTerminals", function () {
  // the terminals are real ones of the VS Code that runs the tests
  this.timeout(60000);

  const name = "RobotCode Test Run";
  // the script as `npm run compile` builds it next to the compiled tests
  const script = path.join(__dirname, "..", "runTerminal.js");
  let runTerminals: RunTerminals;

  // a run of VS Code's own runtime, which reports the result of `code` as its exit code
  function run(code: string): RunTerminalRun {
    return { args: [process.execPath, "-e", code], env: { ELECTRON_RUN_AS_NODE: "1" } };
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

  setup(() => {
    runTerminals = new RunTerminals(script);
  });

  teardown(() => {
    runTerminals.dispose();
    for (const terminal of vscode.window.terminals) {
      if (terminal.name === name) terminal.dispose();
    }
  });

  test("runs with the terminal as its output and reuses the terminal for the next run", async () => {
    const first = await runTerminals.start(name, undefined, run("process.exit(process.stdout.isTTY ? 3 : 4)"));
    assert.strictEqual(await first.ended, 3);

    const second = await runTerminals.start(name, undefined, run("process.exit(5)"));
    assert.strictEqual(second.terminal, first.terminal);
    assert.strictEqual(await second.ended, 5);
  });

  test("gives a run while another is in progress a terminal of its own", async () => {
    const first = await runTerminals.start(name, undefined, run("setTimeout(() => process.exit(0), 3000)"));
    const second = await runTerminals.start(name, undefined, run("process.exit(0)"));
    assert.notStrictEqual(second.terminal, first.terminal);
    assert.deepStrictEqual(await Promise.all([first.ended, second.ended]), [0, 0]);
  });

  test("closes the terminal on a key after the run, and the next run gets a new one", async () => {
    const started = await runTerminals.start(name, undefined, run("process.exit(0)"));
    await started.ended;

    const terminalClosed = closed(started.terminal);
    started.terminal.sendText("x", false);
    await terminalClosed;

    const next = await runTerminals.start(name, undefined, run("process.exit(0)"));
    assert.notStrictEqual(next.terminal, started.terminal);
    assert.strictEqual(await next.ended, 0);
  });

  test("drops a line sent at once after the run, as Rerun Command sends it", async () => {
    const started = await runTerminals.start(name, undefined, run("process.exit(0)"));
    await started.ended;

    const terminalClosed = closed(started.terminal);
    started.terminal.sendText("robot --version", true);
    await new Promise((resolve) => setTimeout(resolve, 1000));
    assert.ok(vscode.window.terminals.includes(started.terminal));

    started.terminal.sendText("x", false);
    await terminalClosed;
  });

  test("keeps the output of a run whose extension is gone until a key", async () => {
    const started = await runTerminals.start(name, undefined, run("setTimeout(() => process.exit(0), 1500)"));
    // as a restart of the extension host closes the connection
    runTerminals.dispose();

    await new Promise((resolve) => setTimeout(resolve, 3000));
    assert.ok(vscode.window.terminals.includes(started.terminal));

    const terminalClosed = closed(started.terminal);
    started.terminal.sendText("x", false);
    await terminalClosed;
  });

  test("runs in a new terminal when the previous one was closed by a key just before", async () => {
    const started = await runTerminals.start(name, undefined, run("process.exit(0)"));
    await started.ended;

    started.terminal.sendText("x", false);
    // the script has ended, VS Code may not have reported the terminal closed yet
    await new Promise((resolve) => setTimeout(resolve, 200));

    const next = await runTerminals.start(name, undefined, run("process.exit(7)"));
    assert.notStrictEqual(next.terminal, started.terminal);
    assert.strictEqual(await next.ended, 7);
  });
});
