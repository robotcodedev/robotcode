import * as assert from "assert";

import {
  RICH_COMMAND_DETECTION,
  commandFinished,
  commandLineSequence,
  escapeOscValue,
} from "../runTerminal/shellIntegration";

suite("shellIntegration", () => {
  test("escapes backslashes, semicolons, spaces and control characters as VS Code reads them", () => {
    assert.strictEqual(escapeOscValue("C:\\shop\\python.exe"), "C:\\\\shop\\\\python.exe");
    assert.strictEqual(escapeOscValue("-v a;b"), "-v\\x20a\\x3bb");
    assert.strictEqual(escapeOscValue("line\nnext"), "line\\x0anext");
    assert.strictEqual(escapeOscValue("robot"), "robot");
  });

  test("writes the command line and the end of a command as OSC 633 sequences", () => {
    assert.strictEqual(commandLineSequence("robot -p ci"), "\x1b]633;E;robot\\x20-p\\x20ci\x07");
    assert.strictEqual(commandFinished(1), "\x1b]633;D;1\x07");
    assert.strictEqual(commandFinished(null), "\x1b]633;D\x07");
  });

  test("announces rich command detection, which VS Code's sticky scroll needs", () => {
    assert.strictEqual(RICH_COMMAND_DETECTION, "\x1b]633;P;HasRichCommandDetection=True\x07");
  });
});
